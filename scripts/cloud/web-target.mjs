/** 独立构建根目录；云端绝不把原 public/ 或本地路由树交给 Next。 */
import {
  cp,
  mkdir,
  readdir,
  rm,
  symlink,
  writeFile,
  link,
  copyFile,
} from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { spawn } from "node:child_process";

await import("./export-avatar-catalog.mjs");

const root = fileURLToPath(new URL("../../", import.meta.url));
const web = path.join(root, "apps/web");
const action = process.argv[2];
const explicitMode = ["local", "cloud"].includes(process.argv[3]);
const mode = explicitMode
  ? process.argv[3]
  : process.env.NEXT_PUBLIC_APP_MODE || "cloud";
if (!["dev", "build"].includes(action) || !["local", "cloud"].includes(mode)) {
  throw new Error(
    "用法：node scripts/cloud/web-target.mjs <dev|build> <cloud|local> [Next 参数]",
  );
}
const stage = path.join(web, ".build", action === "dev" ? `${mode}-dev` : mode);
await mkdir(path.join(stage, "src"), { recursive: true });
await rm(path.join(stage, "public"), { recursive: true, force: true });
await mkdir(path.join(stage, "public"), { recursive: true });
if (action === "build")
  await rm(path.join(stage, "out"), { recursive: true, force: true });
for (const name of [
  "next.config.mjs",
  "postcss.config.mjs",
  "tailwind.config.ts",
  "next-env.d.ts",
]) {
  await rm(path.join(stage, name), { force: true });
  await symlink(path.join(web, name), path.join(stage, name));
}
await cp(path.join(web, "tsconfig.json"), path.join(stage, "tsconfig.json"));
await writeFile(
  path.join(stage, "package.json"),
  JSON.stringify({
    name: `congcong-web-${mode}`,
    version: "0.1.0",
    private: true,
  }),
);
for (const name of await readdir(path.join(web, "src"))) {
  if (name === "app") continue;
  await rm(path.join(stage, "src", name), { recursive: true, force: true });
  await symlink(path.join(web, "src", name), path.join(stage, "src", name));
}
await rm(path.join(stage, "src/app"), { recursive: true, force: true });
if (mode === "local") {
  await symlink(path.join(web, "src/app"), path.join(stage, "src/app"));
  await rm(path.join(stage, "public/data"), { recursive: true, force: true });
  await symlink(path.join(web, "public/data"), path.join(stage, "public/data"));
} else {
  await cp(path.join(web, "src/cloud/app"), path.join(stage, "src/app"), {
    recursive: true,
  });
  for (const name of [
    "login",
    "change-password",
    "admin",
    "parent",
    "learn",
    "globals.css",
    "manifest.ts",
    "icon.svg",
  ]) {
    await cp(
      path.join(web, "src/app", name),
      path.join(stage, "src/app", name),
      { recursive: true },
    );
  }
}
if (mode === "local" && action === "dev") {
  await rm(path.join(stage, "public"), { recursive: true, force: true });
  await symlink(path.join(web, "public"), path.join(stage, "public"));
} else {
  await cp(path.join(web, "public/icons"), path.join(stage, "public/icons"), {
    recursive: true,
  });
}
if (!(mode === "local" && action === "dev")) await cp(path.join(web, "public/forest"), path.join(stage, "public/forest"), { recursive: true });
const env = {
  ...process.env,
  NEXT_PUBLIC_APP_MODE: mode,
  CSF_ISOLATED_WEB: "1",
  CSF_SOURCE_WEB_ROOT: web,
  NEXT_IGNORE_INCORRECT_LOCKFILE: "1",
};
const command = path.join(root, "node_modules/next/dist/bin/next");
const child = spawn(
  process.execPath,
  [command, action, ...process.argv.slice(explicitMode ? 4 : 3)],
  { cwd: stage, env, stdio: "inherit" },
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill(signal));
const code = await new Promise((resolve, reject) => {
  child.on("error", reject);
  child.on("exit", resolve);
});
if (code !== 0) process.exit(code || 1);
if (action === "build") {
  if (mode === "cloud") {
    const scanner = spawn(
      process.execPath,
      [
        path.join(root, "scripts/run-python.mjs"),
        path.join(root, "scripts/cloud/scan-artifact.py"),
        path.join(stage, "out"),
      ],
      { cwd: root, env, stdio: "inherit" },
    );
    const scanCode = await new Promise((resolve, reject) => {
      scanner.on("error", reject);
      scanner.on("exit", resolve);
    });
    if (scanCode !== 0) process.exit(scanCode || 1);
  }
  // 静态媒体使用硬链接装配，避免将二十余 GB 的本地资源再复制一份。
  if (mode === "local") {
    async function assemble(source, destination) {
      await mkdir(destination, { recursive: true });
      for (const entry of await readdir(source, { withFileTypes: true })) {
        const from = path.join(source, entry.name),
          to = path.join(destination, entry.name);
        if (entry.isDirectory()) await assemble(from, to);
        else if (entry.isFile()) {
          try {
            await link(from, to);
          } catch (error) {
            if (error.code === "EEXIST") continue;
            if (error.code !== "EXDEV") throw error;
            await copyFile(from, to);
          }
        } else throw new Error(`不支持的公共资源类型：${entry.name}`);
      }
    }
    await assemble(path.join(web, "public"), path.join(stage, "out"));
  }
  console.log(`独立 ${mode} 产物：apps/web/.build/${mode}/out`);
}
