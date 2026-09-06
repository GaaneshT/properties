# House Studio validation — 6 September 2026

Implementation: `feat/house-studio`, based on the existing clean clone of `GaaneshT/properties` at `d56102c`. The remote was fetched and the local starting branch matched `origin/main`.

## Executed

- `npm run check`: **0 errors, 0 warnings** with Node 22.20.0.
- `npm run build`: **passed**, SvelteKit adapter-static produced the existing overview/recent routes and new `/house` route. The optional dynamically imported Three.js chunk is 635 KB minified / 162 KB gzip and triggers Vite's default chunk-size warning. It is not part of the initial house render or analytics page bundle.
- ESLint on all changed Svelte/TypeScript/JavaScript files: **passed**. Prettier formatting completed for changed files. Prettier was pinned to 3.6.2 to resolve the existing plugin compatibility failure.
- `node scripts/verify_house.mjs`: **passed**. The website's actual GLTFLoader parsed all four GLBs. All expected visibility states, finite mesh coordinates, normals, materials and bounded house extents were checked. All 240 WebP file headers, 80 render provenance entries, 20 camera records and three built routes were checked.
- Pillow decoded all **240 images**. Every comparison camera has identical delivered image dimensions across the four themes.
- Local HTTP requests for `/`, `/recent` and `/house` all returned **200**; the house route includes its title and Dark Luxe theme content.
- Separate Blender 5.2.1 LTS processes exported all four models. Their recorded source hashes were identical before and after export; the native files were not saved or replaced.
- Two additional Dark Luxe service cutaway comparison renders were produced with Cycles from the existing C13/C14 cameras at 1024×768 to match the other themes. Both generated PNGs were visually inspected. The original beauty renders were preserved.
- The existing four-theme living-room comparison was visually inspected before implementation. House renders in the site are sourced from the native projects, not AI images.

| Concept           | Native objects exported | Browser mesh groups | Triangles | GLB size |
| ----------------- | ----------------------: | ------------------: | --------: | -------: |
| Dark Luxe         |                   2,107 |                  67 |   576,982 | 16.4 MiB |
| Warm Japandi      |                   2,080 |                  52 |   520,434 | 15.5 MiB |
| Tropical Modern   |                   2,289 |                  52 |   529,906 | 15.9 MiB |
| Soft Contemporary |                   2,054 |                  52 |   545,818 | 15.9 MiB |

## Remaining verification and publication

The Browser runtime reported **“No browser is available”**, and its discovery list was empty. No live desktop/mobile screenshots, browser interaction tests or WebGL visual/performance tests were executed. The model loader checks do not substitute for GPU or UI testing. A local preview server is provided for owner review.

No public upload, remote push, deployment or change to the existing live website was made. The original project specification explicitly withholds publishing/upload permission for the owner's plan; publication of the exported house assets is treated as a separate owner decision. The existing GitHub repository and GitHub Pages website are public. See `HOUSE_STUDIO.md` for rendering and measurement limits.
