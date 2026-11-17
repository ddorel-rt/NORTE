#!/usr/bin/env python3
"""Comprueba las 7 normas de redacción de NORTE sobre un JSON de perfiles.

Uso:
  python3 scripts/validate_texts.py cases_texts.json
  python3 scripts/validate_texts.py texts_generated.json --baseline cases_texts.json --facts cases
  --facts  carpeta con cases/<slug>/*.json oficiales (opcional): las cifras de los textos deben salir de ahí
  --baseline JSON original: las cifras que ya estaban en el original también se consideran válidas
Sale con código 1 si hay ERRORES (normas 2, 6 y 7). Los AVISOS (cifras no halladas, jerga, tono) se revisan a mano.
"""
import argparse, glob, json, os, re, sys
from collections import Counter

COUPLES = {"timothy-melanie-weah", "daniel-emily-johnson"}

# (regex sobre la ruta del campo, tipo)
KINDS = [
    (r"\.introSpeech$|\.stages\.\w+\.noraHint$|\.options\.\d+\.resultText$|\.(good|low)Outcome\.text$|\.followUp\.day(3|30)$", "nora"),
    (r"\.stages\.\w+\.title$|\.options\.\d+\.resultTitle$|\.randomEvent\.title$|\.(good|low)Outcome\.title$|\.summitBadge$|\.twoFutures\.(current|improved)Title$", "title"),
    (r"\.stages\.\w+\.options\.\d+\.label$|\.concerns\.\d+\.label$|\.firstSteps\.\d+\.title$", "opt_title"),
    (r"\.stages\.\w+\.options\.\d+\.desc$|\.concerns\.\d+\.desc$", "opt_sub"),
    (r"\.firstSteps\.\d+\.effort$", "effort"),
]
TAG_PATHS = re.compile(r"cardTag|\.dir$|\.badge$|initials|rpgClass|summaryTag")
INDICATORS = r"(Colchón Seguro|Holgura Mensual|Rumbo Futuro)"
JARGON = ["liquidez de emergencia", "flujo de caja libre", "patrimonio proyectado", "TAE", "amortiz", "apalanc"]
PROMISES = ["blind", "garantiz", "seguro que", "sin riesgo"]


def leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}.{i}")
    elif isinstance(obj, str):
        yield path, obj


def kind_of(path):
    for rx, k in KINDS:
        if re.search(rx, path):
            return k
    return None


def n_words(s):
    return len(s.split())


def n_sentences(s):
    return len([p for p in re.split(r"(?<=[.!?…])\s+", s.strip()) if p.strip()])


def to_num(tok):
    t = tok.replace("$", "").replace(" ", "")
    mult = 1
    if t[-1:] in "kK":
        mult, t = 1000, t[:-1]
    elif t[-1:] in "mM":
        mult, t = 1_000_000, t[:-1]
    t = t.rstrip("%")
    if "," in t and "." in t:
        t = t.replace(",", "")
    elif t.count(",") > 1 or re.search(r",\d{3}$", t):
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        return float(t) * mult
    except ValueError:
        return None


NUM_RX = re.compile(r"\$\s?\d[\d,\.]*[kKmM]?|\d+(?:[.,]\d+)?\s?%|\b\d{2,3}\s+años\b|\b20\d\d\b")


def numbers_in(text):
    out = []
    for m in NUM_RX.finditer(text):
        tok = m.group(0)
        num = to_num(re.sub(r"\s+años", "", tok))
        if num is not None:
            out.append((tok, num))
    return out


def number_set(obj):
    vals = set()

    def add(v):
        vals.add(round(v, 4))
        if abs(v) < 1:
            vals.add(round(v * 100, 4))

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, bool):
            pass
        elif isinstance(o, (int, float)):
            add(float(o))
        elif isinstance(o, str):
            for m in re.finditer(r"\d[\d,]*\.?\d*", o):
                v = to_num(m.group(0))
                if v is not None:
                    add(v)
    walk(obj)
    return vals


def known(num, pool):
    for f in pool:
        if abs(num - f) <= (0.51 if abs(f) >= 1 else 0.006):
            return True
    return False


def load_facts(folder, slug):
    pool = set()
    alts = {slug, slug.replace("melanie", "melania")}
    for p in [q for a in alts for q in glob.glob(os.path.join(folder, a, "*.json"))]:
        try:
            pool |= number_set(json.load(open(p, encoding="utf-8")))
        except Exception as e:  # noqa
            print(f"  (no pude leer {p}: {e})", file=sys.stderr)
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("texts")
    ap.add_argument("--baseline")
    ap.add_argument("--facts")
    ap.add_argument("--report", default="validation_report.md")
    a = ap.parse_args()
    data = json.load(open(a.texts, encoding="utf-8"))
    base = json.load(open(a.baseline, encoding="utf-8")) if a.baseline else {}
    errors, warns, checked = [], [], Counter()

    for slug, prof in data.items():
        pool = set()
        if a.facts:
            pool |= load_facts(a.facts, slug)
        if slug in base:
            pool |= number_set(base[slug])
        for path, s in leaves(prof, slug):
            k = kind_of(path)
            short = path.split(".", 1)[1] if "." in path else path
            if k:
                checked[k] += 1
            w, sent = n_words(s), n_sentences(s)
            if k == "nora":
                if sent > 2 or not (15 <= w <= 28):
                    errors.append((slug, short, f"NORA debe tener 2 frases y 15-28 palabras (tiene {sent} frases, {w} palabras)", s))
            elif k == "title":
                if not (2 <= w <= 5):
                    errors.append((slug, short, f"Título de 2-5 palabras (tiene {w})", s))
            elif k == "opt_title":
                first = s.split()[0].lower() if s.split() else ""
                if w > 10 or not re.match(r"^\w+(ar|er|ir|ír)(me|te|se|nos|os|lo|la|los|las)?$", first):
                    errors.append((slug, short, f"Acción: máx. 10 palabras y verbo en infinitivo (tiene {w}, empieza por '{first}')", s))
            elif k == "opt_sub":
                if w > 12 or sent > 1:
                    errors.append((slug, short, f"Subtítulo: 1 frase y máx. 12 palabras (tiene {sent} frases, {w} palabras)", s))
            elif k == "effort":
                if not re.search(r"·\s*\+\d+\s+" + INDICATORS, s):
                    errors.append((slug, short, "Etiqueta de esfuerzo con impacto, tipo 'Misión Inmediata · +15 Colchón Seguro'", s))
            if "!!" in s or "¡¡" in s:
                errors.append((slug, short, "Sin signos de exclamación dobles", s))
            if not TAG_PATHS.search(path) and len(s.split()) > 3:
                caps = [x for x in s.split() if len(x) >= 4 and x.isupper()]
                if len(caps) >= 3:
                    errors.append((slug, short, "Mayúsculas sostenidas en una frase larga", s))
            low = s.lower()
            for j in JARGON:
                if j.lower() in low:
                    warns.append((slug, short, f"Jerga bancaria: '{j}'", s))
            for pr in PROMISES:
                if pr in low:
                    warns.append((slug, short, f"Posible promesa: '{pr}'", s))
            if slug in COUPLES and re.search(r"\b(tú|tu|tus|tienes|puedes|quieres|has)\b", low):
                warns.append((slug, short, "Perfil de pareja/familia: usar 'vosotros'", s))
            if slug not in COUPLES and re.search(r"\b(vuestr\w+|habéis|tenéis|podéis)\b", low):
                warns.append((slug, short, "Perfil individual: usar 'tú'", s))
            if k and pool:
                for tok, num in numbers_in(s):
                    if not known(num, pool):
                        warns.append((slug, short, f"Cifra no encontrada en los datos: {tok}", s))

    with open(a.report, "w", encoding="utf-8") as f:
        f.write(f"# Informe de textos NORTE\n\nCampos comprobados: {dict(checked)}\n\n")
        f.write(f"## Errores ({len(errors)})\n\n")
        for slug, p, msg, s in errors:
            f.write(f"- `{slug}` `{p}`: {msg}\n  > {s}\n")
        f.write(f"\n## Avisos ({len(warns)})\n\n")
        for slug, p, msg, s in warns:
            f.write(f"- `{slug}` `{p}`: {msg}\n  > {s}\n")
    per = Counter(e[0] for e in errors)
    print(f"Errores: {len(errors)} {dict(per)} | Avisos: {len(warns)} | Informe: {a.report}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
