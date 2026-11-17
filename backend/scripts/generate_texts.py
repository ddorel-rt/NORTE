#!/usr/bin/env python3
"""Reescribe los textos de NORTE con gpt-5-mini (proxy de Sherpas) cumpliendo las 7 normas.

Los textos se generan UNA VEZ y se guardan en JSON: la web no llama a la IA ni lleva claves.
Solo usa la librería estándar (sin pip).

Uso:
  cp .env.example .env   # rellena LLM_API_KEY
  node scripts/export_cases.mjs index.html cases_texts.json
  python3 scripts/generate_texts.py --dry-run                 # no gasta nada: muestra el primer prompt y el coste estimado
  python3 scripts/generate_texts.py --only michael-carter --limit 2   # prueba de 2 llamadas
  python3 scripts/generate_texts.py                           # todo (unas 32 llamadas)
Salida: texts_generated.json (se puede reanudar: guarda el progreso en .texts_progress.json)
"""
import argparse, copy, json, os, re, sys, time, urllib.request, urllib.error

PRICE_IN, PRICE_OUT = 0.25, 2.00  # USD por 1M tokens, gpt-5-mini (README de Sherpas, 11 nov 2026)
REWRITE_KEYS = {
    "introSpeech", "mainQuest", "summitBadge", "label", "desc", "title", "detail", "noraHint", "resultTitle",
    "resultText", "text", "currentTitle", "currentMetric", "currentDetail", "improvedTitle", "improvedMetric",
    "improvedDetail", "day3", "day30",
}
COUPLES = {"timothy-melanie-weah", "daniel-emily-johnson"}


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http(method, url, key, body=None, timeout=120):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def spend(base, key):
    try:
        info = http("GET", f"{base}/key/info", key)["info"]
        return float(info.get("spend", 0)), float(info.get("max_budget", 0) or 0)
    except Exception as e:  # noqa
        print(f"  (no pude leer /key/info: {e})")
        return None, None


def sections(p):
    """Trozos del perfil que se reescriben, cada uno en una llamada."""
    yield "intro", {k: p[k] for k in ("introSpeech", "mainQuest", "summitBadge") if k in p} | {
        "concerns": [{"id": c["id"], "label": c["label"], "desc": c["desc"]} for c in p["concerns"]]}
    yield "buffs", {"buffs": [{"title": b["title"], "detail": b["detail"]} for b in p.get("buffs", [])]}
    for key, st in p["stages"].items():
        yield f"stage:{key}", {"stages": {key: st}}
    yield "event_futures", {"randomEvent": p.get("randomEvent", {}), "twoFutures": p["twoFutures"]}
    yield "steps", {"firstSteps": p["firstSteps"], "followUp": p["followUp"]}


def merge(orig, new):
    """Copia solo los textos permitidos desde 'new' a 'orig' manteniendo estructura, cifras de barras, deltas, ids..."""
    if isinstance(orig, dict) and isinstance(new, dict):
        for k in orig:
            if k in new:
                if isinstance(orig[k], str) and k in REWRITE_KEYS and isinstance(new[k], str) and new[k].strip():
                    orig[k] = new[k].strip()
                elif isinstance(orig[k], (dict, list)):
                    merge(orig[k], new[k])
    elif isinstance(orig, list) and isinstance(new, list):
        for a, b in zip(orig, new):
            merge(a, b)


def build_messages(system_prompt, slug, prof, name, frag):
    couple = slug in COUPLES
    facts = {k: prof[k] for k in ("name", "ageLabel", "city", "miniMetrics", "mainQuest") if k in prof}
    user = (
        f"Perfil: {prof['name']} ({'pareja/familia: habla de vosotros' if couple else 'una persona: habla de tú'}).\n"
        f"Datos del perfil (más las cifras que ya aparecen en el fragmento, no puedes usar otras):\n{json.dumps(facts, ensure_ascii=False)}\n\n"
        f"Fragmento a reescribir ({name}):\n{json.dumps(frag, ensure_ascii=False, indent=1)}\n\n"
        "Reescribe SOLO los textos de este fragmento cumpliendo las 7 normas. Mantén exactamente la misma estructura, "
        "las mismas claves, ids, números de barras, deltas, iconos y valores true/false. No añadas ni quites cifras que "
        "no estén ya en el fragmento. Si una opción está 'fuera del plan' (simulated: false), explícalo en 2 frases y "
        "redirige al gestor. Devuelve SOLO JSON válido, sin comentarios ni markdown."
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]


def extract_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="cases_texts.json")
    ap.add_argument("--out", default="texts_generated.json")
    ap.add_argument("--prompt", default="scripts/system_prompt.md")
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-usd", type=float, default=3.0, help="corta si el gasto estimado supera esto")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    load_env()
    base = (os.environ.get("LLM_BASE_URL") or os.environ.get("LLM_PROXY_URL") or "https://llm-hackathon.sherpaswealth.com").rstrip("/").removesuffix("/v1")
    key = (os.environ.get("LLM_API_KEY") or os.environ.get("TEAM_KEY") or "")
    system_prompt = open(a.prompt, encoding="utf-8").read()
    src = json.load(open(a.src, encoding="utf-8"))
    progress_file = ".texts_progress.json"
    prog = json.load(open(progress_file)) if os.path.exists(progress_file) else {"done": [], "data": {}}
    out = prog["data"] or copy.deepcopy(src)

    jobs = [(slug, name, frag) for slug, p in src.items() if not a.only or slug == a.only for name, frag in sections(p)]
    todo = [j for j in jobs if f"{j[0]}:{j[1]}" not in prog["done"]]
    if a.limit:
        todo = todo[: a.limit]
    est_in = sum(len(json.dumps(j[2])) + len(system_prompt) + 900 for j in todo) / 3.5
    est_out = sum(len(json.dumps(j[2])) for j in todo) / 3.5 * 1.3 + 400 * len(todo)  # + razonamiento
    print(f"Llamadas: {len(todo)} | tokens aprox. entrada {est_in:,.0f} salida {est_out:,.0f} | coste aprox. ${est_in*PRICE_IN/1e6 + est_out*PRICE_OUT/1e6:.3f}")
    if a.dry_run:
        slug, name, frag = todo[0]
        msgs = build_messages(system_prompt, slug, src[slug], name, frag)
        print("\n--- USER PROMPT (primera llamada) ---\n" + msgs[1]["content"])
        return
    if not key:
        sys.exit("Falta la clave (LLM_API_KEY o TEAM_KEY) en .env")

    s0, cap = spend(base, key)
    print(f"Gasto inicial del equipo: {s0} de {cap} USD")
    used = 0.0
    for slug, name, frag in todo:
        msgs = build_messages(system_prompt, slug, src[slug], name, frag)
        for attempt in (1, 2, 3):
            try:
                r = http("POST", f"{base}/v1/chat/completions", key, {"model": a.model, "messages": msgs})
                u = r.get("usage", {})
                used += u.get("prompt_tokens", 0) * PRICE_IN / 1e6 + u.get("completion_tokens", 0) * PRICE_OUT / 1e6
                new = extract_json(r["choices"][0]["message"]["content"])
                merge(out[slug], new)
                prog["done"].append(f"{slug}:{name}")
                prog["data"] = out
                json.dump(prog, open(progress_file, "w"), ensure_ascii=False)
                print(f"  ok {slug}:{name}  (gasto estimado de esta ejecución ${used:.3f})")
                break
            except urllib.error.HTTPError as e:
                wait = 15 if e.code == 429 else 3
                print(f"  HTTP {e.code} en {slug}:{name}; reintento {attempt}/3 en {wait}s")
                time.sleep(wait)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  respuesta no válida en {slug}:{name} ({e}); reintento {attempt}/3")
        else:
            print(f"  SALTADO {slug}:{name}; se queda el texto original")
        if used > a.max_usd:
            print("Corto: superado --max-usd")
            break
        time.sleep(1.2)  # muy por debajo de 60 peticiones/minuto
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    s1, _ = spend(base, key)
    print(f"Escrito {a.out}. Gasto final del equipo: {s1} (antes {s0})")


if __name__ == "__main__":
    main()
