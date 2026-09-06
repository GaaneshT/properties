# Carissa Park House Studio

The `/house` tab uses the owner's four finished native Blender projects. Dark Luxe is the default. The existing analytics pages retain their styling and static GitHub Pages build.

- **Blender renders:** 20 viewpoints per theme, using the highest existing render tier at its original dimensions and composition, encoded as quality-94 WebP. These retain Cycles lighting, procedural detail and Blender colour treatment; WebP is a lossy delivery format.
- **Compare themes:** the same camera, image dimensions and preview tier on both sides, with a pointer, touch and keyboard slider. The Dark Luxe C13/C14 source images had a different aspect ratio, so those two comparison images were re-rendered from the native project at 1024×768 using the existing cameras; C02 is proportionally downsampled to 1120×1280. Includes whole-house, floor-plan, room and evening views. Evening coverage is the original living-room camera, not invented evening renders for every room.
- **Explore 3D:** lazy-loaded Three.js and the selected GLB only. Exports retain evaluated native geometry and metre scale, with shared, full-height, ceiling and cutaway states. The room buttons select final Blender camera positions; browser perspective and illumination are approximations. The GLBs use base PBR colours, roughness, metal, emission and transmission. Native procedural textures, accurate mirror reflections and Cycles indirect light are represented by the render mode, not reproduced by the real-time viewer. Generic external garden context is omitted from 3D.
- **Controls:** room filters, view arrows, theme switching, shareable query parameters, fullscreen, full-resolution render links, orbit/zoom/reset and exposure. Errors and unavailable WebGL have a render fallback. Switching themes cancels stale downloads and disposes replaced geometry/materials.

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
node scripts/verify_house.mjs
```

The viewer is loaded only when Explore 3D is selected. Each complete theme GLB is about 16–17 MB before HTTP compression. Mobile graphics performance depends on device hardware. The graphics engine chunk is intentionally separate from the initial house tab and analytics pages.

Prettier is pinned to 3.6.2 because the previous 3.8.4 resolution crashes while formatting Svelte with the existing Tailwind plugin (`getVisitorKeys`). No global Node or Blender settings are changed.

## Refresh from the native project

The preparation scripts expect the sibling `Carissa_Park_Native` folder and its recorded final deliverable runs. They are local authoring tools; a web visitor does not need Python or Blender.

```sh
python scripts/prepare_house_assets.py
blender --background --disable-autoexec --python scripts/export_house.py -- dark-luxe
blender --background --disable-autoexec --python scripts/export_house.py -- warm-japandi
blender --background --disable-autoexec --python scripts/export_house.py -- tropical-modern
blender --background --disable-autoexec --python scripts/export_house.py -- soft-contemporary
```

Before the first asset preparation, run `blender --background --disable-autoexec --python scripts/render_house_comparisons.py` to cache the two matching service comparisons. The original beauty renders remain untouched.

Run the exporter in separate background Blender processes, one at a time. Do not run it inside an unsaved interactive scene. Host image packaging requires Pillow. Export was executed with the locally installed Blender 5.2.1 LTS.

## Publishing

The existing repository and GitHub Pages website are public. The standard deployment workflow publishes pushes to `main`. Publishing this tab also makes the exported house geometry and images downloadable; `noindex` is not access control. Private access requires private hosting or actual authentication, not a client-side password.

Implementation is on `feat/house-studio`. Public publication is a separate decision from local implementation.

## Technical references

- [Blender glTF material conversion](https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html)
- [Three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)
- [Three.js renderer and colour treatment](https://threejs.org/docs/pages/WebGLRenderer.html)
