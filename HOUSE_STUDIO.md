# Carissa Park House Studio

The `/house` tab uses the owner's four finished native Blender projects. Dark Luxe is the default. The existing analytics pages retain their styling and static GitHub Pages build.

- **Blender renders:** 20 viewpoints per theme, using the highest existing render tier at its original dimensions and composition, encoded as quality-94 WebP. These retain Cycles lighting, procedural detail and Blender colour treatment; WebP is a lossy delivery format. The exception is **C01 ("Whole house")**, which is not an original deliverable render: `scripts/render_house_overview.py` re-renders it from the native geometry with a refitted orthographic camera, a darkened studio ground, reduced world strength and reduced fill-light energy. Its provenance is recorded separately in `static/house/<theme>/overview.json`.
- **Compare themes:** the same camera, image dimensions and preview tier on both sides, with a pointer, touch and keyboard slider. The Dark Luxe C13/C14 source images had a different aspect ratio, so those two comparison images were re-rendered from the native project at 1024×768 using the existing cameras; C02 is proportionally downsampled to 1120×1280. Includes whole-house, floor-plan, room and evening views. Evening coverage is the original living-room camera, not invented evening renders for every room.
- **Explore 3D:** lazy-loaded Three.js, then the selected theme's GLB, walk grid and surface textures. Exports retain evaluated native geometry and metre scale, with shared, full-height, ceiling and cutaway states. The room buttons select final Blender camera positions; browser perspective and illumination are approximations. The GLBs use base PBR colours, roughness, metal, emission and transmission, plus metric box-projected `SurfaceUV` coordinates. The viewer then loads per-material albedo and normal maps baked from the native shaders (`static/house/<theme>/surfaces/`), so those materials render with their own colour from the texture rather than the base colour. Native procedural textures, accurate mirror reflections and Cycles indirect light are represented by the render mode, not reproduced by the real-time viewer. Generic external garden context is omitted from 3D.
- **Walk inside:** a first-person mode over a pre-computed floor grid (`static/house/<theme>/navigation.json`, 6.5 cm cells at a 1.62 m eye height and 13 cm body radius, restricted to the floor area reachable from the living room). Movement substeps and per-axis sliding prevent tunnelling through walls. The grid is a conservative approximation from the native floor zones and object bounds; it is not a survey.
- **Controls:** whole-house/walk switch, room filters, view arrows, theme switching, shareable query parameters, fullscreen, full-resolution render links, orbit/zoom/reset, exposure, and an ambient-occlusion ("Contact shadows") toggle. Walking takes WASD or arrow keys, Shift to move faster, pointer drag to look, and an on-screen hold-to-walk pad for touch. Errors and unavailable WebGL have a render fallback. Switching themes cancels stale downloads and disposes replaced geometry/materials.

## Accuracy and ownership

This reflects the supplied renovation concepts. The original model's scale, ceiling heights, openings, services, boundaries, products and site dimensions remain unverified. The owner's reported 1,647 sq ft is not a measured net floor area. No replacement floor plan, room, measurement or AI interior image was invented.

The original `.blend` files are never saved by the export process. SHA-256 values and export scope are recorded in each `static/house/<theme>/export.json`. Render source paths, hashes, tier and dimensions are in `static/house/provenance.json`; these paths are relative and contain no owner account paths. The source plans and packed design references are not copied into the website. Web assets are owner-supplied project content, not stock assets licensed for redistribution.

## Develop and verify

Use Node **22.20.0** (the repository's existing Volta version) or a supported later Node 22 release. Node 22.12 does not meet the installed tooling's minimum. On Windows, use `npm.cmd` if PowerShell script execution is disabled.

```sh
npm ci
npm run dev
npm run check
npm run build
npm run test:house
```

`npm run test:house` runs the navigation unit tests (collision, wall sliding, doorway passage, bounds, per-room walking starts) and then `scripts/verify_house.mjs`, which parses all four GLBs with the website's own loader and checks view states, UVs, the walk grids, every surface texture and the built routes. `verify_house.mjs` needs `npm run build` first because it asserts the built pages exist. The navigation tests import TypeScript directly, so the script passes `--experimental-strip-types`; it is unnecessary on Node 22.18 and later.

The viewer is loaded only when Explore 3D is selected. Each complete theme GLB is about 19.7–21.4 MiB before HTTP compression, plus about 5–7 MB of surface textures (20 material pairs per theme; 28 for Dark Luxe) and a walk grid of a few kilobytes. Mobile graphics performance depends on device hardware. The graphics engine chunk is intentionally separate from the initial house tab and analytics pages.

Prettier is pinned to 3.6.2 because the previous 3.8.4 resolution crashes while formatting Svelte with the existing Tailwind plugin (`getVisitorKeys`). No global Node or Blender settings are changed.

## Refresh from the native project

The preparation scripts expect the sibling `Carissa_Park_Native` folder and its recorded final deliverable runs. They are local authoring tools; a web visitor does not need Python or Blender.

Surfaces must be baked and packaged **before** exporting: `export_house.py` reads
`static/house/<slug>/surfaces/manifest.json` to choose each face's tile size and grain
axis, and silently falls back to untextured 1 m tiles if that file is missing.

```sh
python scripts/prepare_house_assets.py
blender --background --disable-autoexec --python scripts/bake_house_surfaces.py -- dark-luxe   # and each other slug
python scripts/package_house_surfaces.py
blender --background --disable-autoexec --python scripts/export_house.py -- dark-luxe
blender --background --disable-autoexec --python scripts/export_house.py -- warm-japandi
blender --background --disable-autoexec --python scripts/export_house.py -- tropical-modern
blender --background --disable-autoexec --python scripts/export_house.py -- soft-contemporary
```

Before the first asset preparation, run `blender --background --disable-autoexec --python scripts/render_house_comparisons.py` to cache the two matching service comparisons. The original beauty renders remain untouched.

Whole-house stills are regenerated with `blender --background --disable-autoexec --python scripts/render_house_overview.py -- <slug>` followed by `python scripts/package_house_overviews.py`.

Run the exporter in separate background Blender processes, one at a time. Do not run it inside an unsaved interactive scene. Host image packaging requires Pillow. Export was executed with the locally installed Blender 5.2.1 LTS.

## Publishing

The existing repository and GitHub Pages website are public. The standard deployment workflow publishes pushes to `main`. Publishing this tab also makes the exported house geometry and images downloadable; `noindex` is not access control. Private access requires private hosting or actual authentication, not a client-side password.

Implementation is on `feat/house-studio`. Public publication is a separate decision from local implementation.

## Technical references

- [Blender glTF material conversion](https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html)
- [Three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)
- [Three.js renderer and colour treatment](https://threejs.org/docs/pages/WebGLRenderer.html)
