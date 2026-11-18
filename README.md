# NORTE · La partida

**Sherpas x UPV Sigma Data Club · reto "Bring the plan to life"**

> NORTE convierte el plan financiero de una familia en una partida de montaña. NORA, "tu guía hacia el norte", sube con el cliente carta a carta: decide sobre su propio plan, ve el impacto de cada decisión y termina con **un único primer paso** que puede dar esta semana. Después, simula qué pasa los días +3 y +30.

**Demo (versión móvil y ordenaador):** https://ddorel-rt.github.io/NORTE/
**Vídeo (2 min):** [ver video](https://acortar.link/76fcNC)

## Qué hace

1. **Eliges a la familia** (los 4 casos de Sherpas) y qué te preocupa más.
2. **Subes la ruta** con tres cartas. Cada carta enseña una cifra real del plan (barras) y dos decisiones. Cada decisión muestra su impacto en tres indicadores: **Colchón Seguro**, **Holgura Mensual** y **Rumbo Futuro**.
3. **Las decisiones fuera del plan** (por ejemplo, retrasar el retiro) no se simulan: NORA lo explica con empatía y remite al gestor o asesor.
4. **Un imprevisto aleatorio** ("Un sueldo se interrumpe") usa los meses de efectivo reales de la familia.
5. **"Tus 2 futuros":** qué pasa si no cambia nada frente a la estrategia del plan.
6. **Tu único primer paso:** acciones concretas, ordenadas según las jugadas del plan, con esfuerzo e impacto (por ejemplo, *Misión Inmediata · +15 Colchón Seguro*).
7. **Día +3 y día +30:** botón para avanzar el tiempo y recibir el seguimiento de NORA.

Está pensado tanto para móvil como para ordenador, para alguien que no sabe de finanzas (casi sin jerga) y para que cada familia vea **sus** cifras, no ejemplos genéricos.

## Los datos

Los 4 casos son los oficiales de Sherpas y están en [`cases/`](cases/). Todas las cifras que aparecen en el juego (edades, importes, fechas, puntuaciones) salen de esos archivos. No se inventan números.

## Cómo usa la IA

La IA se usa **al preparar los textos**, no mientras se juega. Así la demo es rápida, no depende de la red y no expone ninguna clave.

```
JSON oficiales (cases/) ─► gpt-5-mini reescribe los textos ─► validador ─► cases.json ─► juego
```

- [`backend/scripts/generate_texts.py`](backend/scripts/generate_texts.py) envía cada perfil, por secciones, a **gpt-5-mini** (proxy de Sherpas) con 7 normas de redacción ([`system_prompt.md`](backend/scripts/system_prompt.md)). El modelo solo reescribe textos: la estructura, los números y las decisiones no cambian.
- [`backend/scripts/validate_texts.py`](backend/scripts/validate_texts.py) comprueba longitudes, tono, verbos de acción y que **cada cifra exista en los datos oficiales**.
- [`backend/scripts/merge_validated.py`](backend/scripts/merge_validated.py) conserva los textos de la IA que pasan las reglas y recupera la versión segura en los que fallan.
- Después, el equipo revisó el resultado a mano.
- El juego lee `cases.json` al abrirse. Si no puede, usa los mismos datos incrustados en `index.html`.

Coste real de generar los textos de los 4 perfiles: unos **$0.15** de los $50.

## Cómo ejecutarlo

**Solo ver el juego:** abre la demo, o descarga el repo y haz doble clic en `index.html`.

**En local, leyendo `cases.json`:**
```
python -m http.server 8000
```
y abre http://localhost:8000. No hace falta instalar nada más.

**Regenerar los textos (opcional):**
```
cd backend
copy .env.example .env      (Windows)   o   cp .env.example .env
```
Pega en `.env` la clave del equipo (`TEAM_KEY`). **Nunca subas el `.env`.** Después:
```
python scripts/generate_texts.py
python scripts/validate_texts.py texts_generated.json --baseline cases_texts.json --facts ../cases
python scripts/merge_validated.py texts_generated.json cases_texts.json validation_report.md cases_merged.json
```
Si la validación da 0 errores, `cases_merged.json` se copia a la raíz como `cases.json`.

## El juego (frontend)

- **Tecnología:** un único `index.html` con HTML, CSS y JavaScript sin framework ni paso de compilación. Iconos [Lucide](https://lucide.dev) con versión fija y fotos en `families/` y `nora/`.
- **Datos:** todo el contenido sale de un objeto de datos con la misma estructura para las 4 familias. Al abrirse, la página intenta leer `cases.json` con `fetch`; si no puede, usa los mismos datos incrustados en el HTML, así que la demo funciona aunque falle la red.
- **Pantallas:** bienvenida, ficha del personaje, preocupación, ventajas, tres cartas de etapa, evento aleatorio, "Tus 2 futuros", primer paso y misión con seguimiento de los días +3 y +30.
- **Despliegue:** GitHub Pages, directamente desde la rama `main`. Diseño pensado para móvil, con vista de ordenador.

## Estructura

```
index.html      el juego (HTML, CSS y JavaScript sin dependencias de build)
cases.json      textos de los 4 perfiles (salida del motor)
cases/          datos oficiales de Sherpas
backend/        motor de textos: generar, validar, mezclar
families/ nora/ imágenes
```

## Equipo

- **Darius**: motor de IA (generación y validación de textos), datos y revisión.
- **Marc Jordà**: vídeo, HTML del juego y carga de `cases.json`.

Hemos usado asistentes de IA durante el desarrollo, y los textos finales fueron validados y revisados por el equipo.

## Qué no hace (todavía)

- No hay chat ni voz en directo: es una experiencia guiada.
- El juego trata al hogar como una unidad. Una evolución natural es dejar que cada miembro de la pareja decida por separado y mostrar el punto medio.
- Los seguimientos de los días +3 y +30 están simulados; en un producto real podrían salir por WhatsApp o correo.
