/** Only public avatar metadata is exported; no curriculum or account data. */
import { readFile, writeFile } from 'node:fs/promises';
const root = new URL('../../', import.meta.url);
const catalog = JSON.parse(await readFile(new URL('apps/api/app/avatars/catalog.json', root), 'utf8'));
const ids = catalog.presets.map(p => p.id);
if (!catalog.version || !ids.includes(catalog.default_id) || new Set(ids).size !== ids.length ||
    catalog.presets.some(p => !/^[a-z][a-z0-9-]{0,31}$/.test(p.id) || !p.name?.trim()) ||
    ['panda','fox','rabbit','bear'].some(id => !ids.includes(id))) throw Error('Invalid avatar catalog');
const output = new URL('apps/web/src/lib/avatars/catalog.json', root);
const contents = JSON.stringify(catalog, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== contents) throw Error('Avatar catalog export is stale');
} else await writeFile(output, contents);
console.log(`Avatar catalog ${catalog.version}: ${ids.length} presets verified`);
