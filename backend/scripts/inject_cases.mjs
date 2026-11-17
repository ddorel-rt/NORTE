// Mete los textos generados dentro de index.html (sustituye el bloque const CASES_DB = {...};).
// Uso: node scripts/inject_cases.mjs index.html texts_generated.json index.new.html
// Revisa index.new.html en el navegador y, si está bien, cámbialo por index.html.
import fs from 'node:fs';
const [,, htmlPath = 'index.html', jsonPath = 'texts_generated.json', outPath = 'index.new.html'] = process.argv;
const html = fs.readFileSync(htmlPath, 'utf8');
const start = html.indexOf('const CASES_DB =');
if (start < 0) throw new Error('No encuentro const CASES_DB');
const end = html.indexOf('\n    };', start) + '\n    };'.length;
const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const block = 'const CASES_DB = ' + JSON.stringify(data, null, 2).replace(/\n/g, '\n    ') + ';';
fs.writeFileSync(outPath, html.slice(0, start) + block + html.slice(end));
console.log('Escrito', outPath, '(' + Object.keys(data).length + ' perfiles)');
