#!/usr/bin/env python3
"""Genera unas pocas frases de NORA con ElevenLabs a través del proxy de Sherpas (sin pip).

Reglas del README: tope total de ElevenLabs $1.40 (compartido con transcripción), eleven-flash-v2.5 cuesta
$0.04 por 1.000 caracteres, y la voz debe pasar por el backend/proxy (nunca directo al proveedor).
Este script corre en vuestro ordenador una vez; la web solo reproduce los mp3 guardados.

Uso:
  python3 scripts/make_audio.py --dry-run          # muestra frases, caracteres y coste. No gasta nada
  python3 scripts/make_audio.py --max-usd 0.40     # genera audio/<perfil>-intro.mp3 ...
Variables en .env: LLM_API_KEY, LLM_BASE_URL (opcional), TTS_VOICE (nombre de voz: mira el ejemplo de voz del README)
"""
import argparse, json, os, sys, urllib.request, urllib.error

PRICE_PER_1K = {"eleven-flash-v2.5": 0.04, "eleven-multilingual-v2": 0.08, "eleven-v3": 0.08}


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts", default="texts_generated.json")
    ap.add_argument("--model", default="eleven-flash-v2.5")
    ap.add_argument("--max-usd", type=float, default=0.40)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="audio")
    a = ap.parse_args()
    load_env()
    data = json.load(open(a.texts, encoding="utf-8"))
    lines = []  # (archivo, texto): solo las frases clave
    for slug, p in data.items():
        lines.append((f"{slug}-intro", p["introSpeech"]))
        lines.append((f"{slug}-day3", p["followUp"]["day3"]))
    chars = sum(len(t) for _, t in lines)
    cost = chars / 1000 * PRICE_PER_1K[a.model]
    print(f"{len(lines)} frases, {chars} caracteres, coste estimado ${cost:.3f} con {a.model} (tope del equipo $1.40)")
    for n, t in lines:
        print(f"  {n}: {t}")
    if cost > a.max_usd:
        sys.exit(f"Coste estimado ${cost:.3f} supera --max-usd {a.max_usd}. Quita frases o sube el límite.")
    if a.dry_run:
        return
    key, voice = (os.environ.get("LLM_API_KEY") or os.environ.get("TEAM_KEY") or ""), (os.environ.get("TTS_VOICE") or "alloy")
    base = (os.environ.get("LLM_BASE_URL") or os.environ.get("LLM_PROXY_URL") or "https://llm-hackathon.sherpaswealth.com").rstrip("/").removesuffix("/v1")
    if not key or not voice:
        sys.exit("Falta la clave (LLM_API_KEY o TEAM_KEY) en .env")
    os.makedirs(a.out, exist_ok=True)
    for n, t in lines:
        body = json.dumps({"model": a.model, "input": t, "voice": voice, "response_format": "mp3"}).encode()
        req = urllib.request.Request(f"{base}/v1/audio/speech", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                open(os.path.join(a.out, n + ".mp3"), "wb").write(r.read())
            print("  ok", n)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} en {n}: {e.read()[:200]!r}")
            break


if __name__ == "__main__":
    main()
