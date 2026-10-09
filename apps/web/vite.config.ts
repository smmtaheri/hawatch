import {cpSync,mkdirSync} from "node:fs";
import {resolve} from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const apiProxy = {
  target: "http://localhost:8000",
  changeOrigin: true,
};

const assetVersion=process.env.VITE_ASSET_VERSION||"local";
export default defineConfig(({command})=>{
const publicVersion=process.env.VITE_PUBLIC_ASSET_VERSION||assetVersion;
const publicPrefix=command==="build"?`/static-public/${publicVersion}`:"";
const publicRoots=["new-design/","fonts/","images/","brand/","favicon.png","favicon.ico","apple-touch-icon.png"];
const rewritePublic=(code:string)=>publicRoots.reduce((text,root)=>text.replaceAll(`${assetPrefix}/${root}`,`${publicPrefix}/${root}`),code);
const assetPrefix=command==="build"?`/static-assets/${assetVersion}`:"";
return {
  base: `${assetPrefix}/`,
  cacheDir: "../../.tmp/vite-cache",
  envDir: "../../",
  plugins: [{name:"version-public-assets",
    transform(code,id){if(id.includes("/src/")&&/\.[jt]sx?$/.test(id))return code.replace(/(["'`])\/(new-design|fonts|images|brand)\//g,(_m,quote,folder)=>`${quote}${publicPrefix}/${folder}/`);},
    transformIndexHtml:{order:"post",handler:html=>rewritePublic(html)},
    generateBundle(_options,bundle){for(const output of Object.values(bundle))if(output.type==="asset"&&output.fileName.endsWith(".css"))output.source=rewritePublic(String(output.source));},
    closeBundle(){const target=resolve("dist",`static-assets/${assetVersion}`);mkdirSync(target,{recursive:true});cpSync(resolve("public"),resolve("dist",`static-public/${publicVersion}`),{recursive:true});cpSync(resolve("dist/assets"),resolve(target,"assets"),{recursive:true});}
  },react(), {
    name: "qa-noindex",
    transformIndexHtml(html) {
      return process.env.VITE_QA_PREVIEW === "true"
        ? html.replace(/<head>/, '<head><meta name="robots" content="noindex,nofollow,noarchive" />')
        : html;
    },
  }],
  build: {
    // Django serves the first HTML response for public SEO pages. Keep the
    // entry CSS/JS paths stable so that server-rendered HTML never needs to
    // know Vite's content hash. Lazy chunks remain content-addressed.
    rollupOptions: {
      output: {
        entryFileNames: "assets/hawatch.js",
        chunkFileNames: "assets/chunks/[name]-[hash].js",
        assetFileNames: (assetInfo) =>
          assetInfo.name?.endsWith(".css") ? "assets/hawatch.css" : "assets/[name]-[hash][extname]",
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: { "/api": apiProxy },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: { "/api": apiProxy },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    css: true,
  },
};
});
