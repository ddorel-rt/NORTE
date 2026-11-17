# Motor de textos de NORTE

Genera `cases.json`, el archivo que alimenta el juego, a partir de los casos oficiales de Sherpas (`../cases/`).

## Cómo funciona
1. `cases_texts.json`: base con los 4 perfiles (cifras tomadas de los JSON oficiales).
2. `scripts/generate_texts.py`: envía cada perfil por secciones a **gpt-5-mini** (proxy de Sherpas) con las reglas de copywriting de `scripts/system_prompt.md`. Solo reescribe los campos de texto y conserva cifras y estructura.
3. `scripts/validate_texts.py`: comprueba longitudes, tono, verbos de acción y que **todas las cifras salgan de los datos oficiales**. Si falla, no se usa.
4. `scripts/make_audio.py` (opcional): voz de NORA con ElevenLabs.

La clave solo vive en `.env` (nunca en el navegador). El juego es estático: lee `cases.json`.

## Uso (desde esta carpeta)
```
cp .env.example .env        # y pega tu TEAM_KEY
python scripts/generate_texts.py --dry-run
python scripts/generate_texts.py
python scripts/validate_texts.py texts_generated.json --baseline cases_texts.json --facts ../cases
```
Si el validador da 0 errores, copia `texts_generated.json` a `../cases.json`.
