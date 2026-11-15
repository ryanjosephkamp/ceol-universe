// The site of the Common English OpenList: static pages for Cloudflare Pages,
// with React islands for the lookup and the grammar box.
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({
  site: 'https://common-english-openlist.pages.dev',
  integrations: [react()],
  build: { format: 'directory' },
  // keep the whitespace as written: compression drops the space before an
  // inline element that starts a source line
  compressHTML: false,
  devToolbar: { enabled: false },
  // the build reads the pipeline's figures and the repository's examples
  vite: { server: { fs: { allow: ['..'] } } },
});
