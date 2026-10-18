import {cpSync,existsSync,mkdirSync,readFileSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { pageAssetsPlugin } from "./pageAssets";

const apiProxy = {
  target: "http://localhost:8000",
  changeOrigin: true,
};

const assetVersion=process.env.VITE_ASSET_VERSION||"local";
export default defineConfig(({command})=>{
const publicVersion=process.env.VITE_PUBLIC_ASSET_VERSION||assetVersion;
const publicPrefix=command==="build"?`/static-public/${publicVersion}`:"";
const assetPrefix=command==="build"?`/static-assets/${assetVersion}`:"";
// Keep browser/Google favicon URLs stable at the domain root. Versioned public
// URLs are useful for larger assets, but changing a favicon URL can delay
// Google's favicon refresh.
const publicRoots=["new-design/","fonts/","images/","brand/"];
const stableIconRoots=["favicon.png","favicon.ico","apple-touch-icon.png"];
const escapeRegExp=(value:string)=>value.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
const rewritePublic=(code:string)=>{
const versioned=publicRoots.reduce((text,root)=>text.replaceAll(`${assetPrefix}/${root}`,`${publicPrefix}/${root}`),code);
return stableIconRoots.reduce((text,root)=>text.replaceAll(`${assetPrefix}/${root}`,`/${root}`),versioned);
};
const rewriteAndValidateCss=()=>{
const cssPath=resolve("dist/assets/hawatch.css");
const css=rewritePublic(readFileSync(cssPath,"utf8"));
const staleAssetUrl=new RegExp(`${escapeRegExp(assetPrefix)}/(?:${publicRoots.map(escapeRegExp).join("|")})`);
if(staleAssetUrl.test(css))throw new Error("CSS contains public asset URLs under /static-assets; refusing to publish a broken stylesheet.");
const publicRoot=resolve("public");
for(const match of css.matchAll(new RegExp(`${escapeRegExp(publicPrefix)}/([^\\s)\"']+)`,"g"))){
const relativeUrl=decodeURIComponent(match[1].split(/[?#]/,1)[0]);
const publicFile=resolve(publicRoot,relativeUrl);
if(!publicFile.startsWith(`${publicRoot}/`)||!existsSync(publicFile))throw new Error(`CSS references a missing public asset: ${match[0]}`);
}
writeFileSync(cssPath,css);
};
return {
  base: `${assetPrefix}/`,
  cacheDir: "../../.tmp/vite-cache",
  envDir: "../../",
  plugins: [{name:"version-public-assets",
    transform(code,id){if(id.includes("/src/")&&/\.[jt]sx?$/.test(id))return code.replace(/(["'`])\/(new-design|fonts|images|brand)\//g,(_m,quote,folder)=>`${quote}${publicPrefix}/${folder}/`);},
    transformIndexHtml:{order:"post",handler:html=>rewritePublic(html)},
    closeBundle(){if(command!=="build")return;rewriteAndValidateCss();const target=resolve("dist",`static-assets/${assetVersion}`);mkdirSync(target,{recursive:true});cpSync(resolve("public"),resolve("dist",`static-public/${publicVersion}`),{recursive:true});cpSync(resolve("dist/assets"),resolve(target,"assets"),{recursive:true});}
  },react(), pageAssetsPlugin(assetVersion), {
    name: "qa-noindex",
    transformIndexHtml(html) {
      return process.env.VITE_QA_PREVIEW === "true"
        ? html.replace(/<head>/, '<head><meta name="robots" content="noindex,nofollow,noarchive" />')
        : html;
    },
  }],
  build: {
    manifest: true,
    // A lost lazy stylesheet/chunk must not strand an otherwise loaded page.
    // Every route uses the same application entry and initial stylesheet.
    cssCodeSplit: false,
    // Django serves the first HTML response for public SEO pages. Keep the
    // entry CSS/JS paths stable so that server-rendered HTML never needs to
    // know Vite's content hash. The versioned directory isolates releases.
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
