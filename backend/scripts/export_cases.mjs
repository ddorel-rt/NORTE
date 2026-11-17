// Extrae CASES_DB de index.html a JSON (cases_texts.json). Uso: node export_cases.mjs ../index.html ../cases_texts.json
import fs from 'node:fs';
import vm from 'node:vm';
const [,, src = '../index.html', out = '../cases_texts.json'] = process.argv;
const html = fs.readFileSync(src, 'utf8');
const start = html.indexOf('const CASES_DB =');
if (start < 0) throw new Error('No encuentro const CASES_DB en ' + src);
const end = html.indexOf('\n    };', start);
const code = html.slice(start, end + 7).replace('const CASES_DB =', 'CASES_DB =');
const ctx = {};
vm.createContext(ctx);
vm.runInContext(code, ctx);
fs.writeFileSync(out, JSON.stringify(ctx.CASES_DB, null, 2));
console.log('Perfiles:', Object.keys(ctx.CASES_DB).join(', '));
