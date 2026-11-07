import { build } from 'esbuild';
import { mkdir, unlink } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
const output=new URL('../../deploy-output/child-ui-redesign/account-shell-check.cjs',import.meta.url);
await mkdir(new URL('.',output),{recursive:true});
try {
 await build({entryPoints:[new URL('./account-shell.tsx',import.meta.url).pathname],outfile:output.pathname,bundle:true,platform:'node',format:'cjs',external:['react','react/*','react-dom','react-dom/*','react-test-renderer','next','next/*','framer-motion','framer-motion/*'],mainFields:['module','main'],jsx:'automatic',tsconfig:new URL('../../apps/web/tsconfig.json',import.meta.url).pathname,loader:{'.css':'empty'}});
 const result=spawnSync(process.execPath,[output.pathname],{stdio:'inherit'});process.exitCode=result.status??1;
} finally {await unlink(output).catch(()=>{});}
