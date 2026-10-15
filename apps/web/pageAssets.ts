import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Plugin } from 'vite';

type Chunk = { file: string; imports?: string[]; css?: string[] };
type Assets = { scripts: string[]; styles: string[] };
const entries = {
  home: 'index.html',
  point: 'src/features/week/WeekForecastPage.tsx',
  route: 'src/features/week/WeekForecastPage.tsx',
  destinations: 'src/features/destinations/DestinationsPage.tsx',
  routes: 'src/features/destinations/DestinationsPage.tsx',
  login: 'src/pages/LoginPage.tsx',
  plans: 'src/pages/SubscriptionPlansPage.tsx',
  'not-found': 'index.html',
};
const bootstrapPath = resolve('../api/src/hawatch/modules/catalog/templates/catalog/page_load_bootstrap.html');

/** One build artifact supplies Django and the standalone web HTML. */
export function pageAssetsPlugin(assetVersion: string): Plugin {
  return {
    name: 'page-assets',
    transformIndexHtml: {
      order: 'post',
      handler: html => html.replace('</body>', `${readFileSync(bootstrapPath, 'utf8')}\n</body>`),
    },
    closeBundle() {
      const manifest = JSON.parse(readFileSync(resolve('dist/.vite/manifest.json'), 'utf8')) as Record<string, Chunk>;
      function assetsFor(entry: string): Assets {
        const scripts = new Set<string>(), styles = new Set<string>(), seen = new Set<string>();
        function visit(key: string) {
          if (seen.has(key)) return;
          seen.add(key);
          const chunk = manifest[key];
          if (!chunk) throw new Error(`Missing page entry in Vite manifest: ${key}`);
          scripts.add(chunk.file);
          chunk.css?.forEach(file => styles.add(file));
          chunk.imports?.forEach(visit);
        }
        visit('index.html');
        visit(entry);
        return { scripts: [...scripts], styles: [...styles] };
      }
      const pages = Object.fromEntries(Object.entries(entries).map(([kind, entry]) => [kind, assetsFor(entry)]));
      const target = resolve(`dist/static-assets/${assetVersion}`);
      mkdirSync(target, { recursive: true });
      writeFileSync(resolve(target, 'page-assets.json'), JSON.stringify({ version: assetVersion, pages }));
      const html = readFileSync(resolve('dist/index.html'), 'utf8');
      for (const [kind, assets] of Object.entries(pages)) {
        const prefix = `/static-assets/${assetVersion}/`;
        const links = [
          ...assets.scripts.map(file => `<link rel="modulepreload" crossorigin href="${prefix}${file}" />`),
          ...assets.styles.filter(file => !html.includes(`href="${prefix}${file}"`)).map(file => `<link rel="preload" as="style" crossorigin href="${prefix}${file}" />`),
        ].join('\n');
        writeFileSync(resolve(`dist/${kind}.html`), html.replace('</head>', `${links}\n</head>`));
      }
    },
  };
}
