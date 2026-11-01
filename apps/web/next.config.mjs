import { fileURLToPath } from "node:url";

const appMode = process.env.NEXT_PUBLIC_APP_MODE || "cloud";
if (!["local", "cloud"].includes(appMode)) {
  throw new Error("NEXT_PUBLIC_APP_MODE 必须为 cloud 或 local");
}
if (appMode === "cloud" && process.env.CSF_ISOLATED_WEB !== "1") {
  throw new Error(
    "cloud 必须使用 npm run dev 或 npm run build 的隔离入口，不能直接发布原 public 目录",
  );
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  outputFileTracingRoot: fileURLToPath(new URL("../../", import.meta.url)),
  productionBrowserSourceMaps: false,
  ...(process.env.NODE_ENV === "development"
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${process.env.CSF_DEV_API_URL || "http://127.0.0.1:8000"}/api/:path*`,
            },
          ];
        },
      }
    : {}),
  images: { unoptimized: true },
  trailingSlash: true,
  transpilePackages: ["@cstf/core"],
};

export default nextConfig;
