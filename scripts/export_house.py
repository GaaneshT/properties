"""Run in a fresh Blender background process. Export only; never save native files.

blender --background --disable-autoexec --python scripts/export_house.py -- dark-luxe
Evaluated geometry is joined by material/state for modest browser draw-call counts.
Native procedural shaders become their base PBR values; Cycles stills retain full fidelity.
"""
import bpy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO.parent / 'Carissa_Park_Native' / 'deliverables'
STYLES = {
    'dark-luxe': ('20260906_Dark_Luxe', '04_Dark_Luxe'),
    'warm-japandi': ('20260905_155249_3e36c2', '01_Warm_Japandi'),
    'tropical-modern': ('20260905_155249_3e36c2', '02_Tropical_Modern'),
    'soft-contemporary': ('20260905_155249_3e36c2', '03_Soft_Contemporary'),
}
slug = sys.argv[sys.argv.index('--') + 1]
run, name = STYLES[slug]
native = SOURCE / run / f'Carissa_Park_{name}.blend'
before = hashlib.sha256(native.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
full = bpy.data.scenes['01_DAY_INTERIOR']
cut = bpy.data.scenes['00_START_OVERVIEW']
full_ids = {o.name for o in full.objects}
cut_ids = {o.name for o in cut.objects}
bpy.context.window.scene = full
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
target = bpy.data.scenes.new('WEB_EXPORT')
groups = defaultdict(list)
source_count = 0

for obj in sorted(set(full.objects) | set(cut.objects), key=lambda o: o.name):
    if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT'} or obj.hide_render:
        continue
    if any(c.name.startswith(('EXTERIOR_GENERIC_CONTEXT', 'PRESENTATION_GROUND', 'REFERENCE_', 'OPTION_')) for c in obj.users_collection):
        continue
    # Evaluate in the source scene so modifiers, parents and cutaway states are retained.
    scene = full if obj.name in full_ids else cut
    if bpy.context.scene != scene:
        bpy.context.window.scene = scene
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
    if not mesh or not mesh.vertices:
        continue
    mode = 'shared' if obj.name in full_ids and obj.name in cut_ids else 'full' if obj.name in full_ids else 'cutaway'
    if any(c.name.startswith('ARCH_CEILINGS') or c.name == 'DL_CONCEALED_CEILING_DETAILS' for c in obj.users_collection):
        mode = 'ceiling'
    copy = bpy.data.objects.new(f'{mode}_{obj.name}', mesh)
    target.collection.objects.link(copy)
    copy.matrix_world = obj.matrix_world.copy()
    key = (mode, tuple(m.name if m else '' for m in mesh.materials))
    groups[key].append(copy)
    source_count += 1

# Disconnect procedural graph inputs only in memory; preserve native base colours,
# roughness, metal, transmission and emissive factors supported by glTF.
used = {m for objects in groups.values() for o in objects for m in o.data.materials if m}
for mat in used:
    if not mat.use_nodes:
        continue
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        for socket in bsdf.inputs:
            for link in list(socket.links):
                mat.node_tree.links.remove(link)

bpy.context.window.scene = target
for (mode, _), objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = f'{mode}__{joined.data.materials[0].name if joined.data.materials else "mesh"}'
    joined['viewMode'] = mode

out = REPO / 'static' / 'house' / slug
out.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out / 'house.glb'), export_format='GLB',
    use_active_scene=True, export_apply=True, export_animations=False,
    export_cameras=False, export_lights=False, export_extras=True,
    export_yup=True, export_materials='EXPORT')
after = hashlib.sha256(native.read_bytes()).hexdigest()
assert before == after, 'Native file was modified'
report = dict(style=slug, source_file=native.name, source_sha256=before,
    source_objects=source_count, exported_meshes=len(target.objects),
    bytes=(out / 'house.glb').stat().st_size, geometry='Evaluated native geometry, no decimation',
    materials='Base PBR values; native procedural grain/bump and Cycles illumination are represented by the separate renders',
    omitted='Generic garden context, studio ground, lights, cameras, reference images')
(out / 'export.json').write_text(json.dumps(report, indent=2))
print('HOUSE_EXPORT_COMPLETE ' + json.dumps(report))
