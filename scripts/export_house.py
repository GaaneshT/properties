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
sys.path.insert(0,str(REPO/'scripts'))
from house_navigation import write_navigation
from refine_house_furniture import refine_furniture
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
refinements=refine_furniture(full)
cut = bpy.data.scenes['00_START_OVERVIEW']
full_ids = {o.name for o in full.objects}
cut_ids = {o.name for o in cut.objects}
bpy.context.window.scene = full
bpy.context.view_layer.update()
out = REPO / 'static' / 'house' / slug
out.mkdir(parents=True, exist_ok=True)
write_navigation(full,REPO,out/'navigation.json')
surface_file=out/'surfaces/manifest.json'
surface_data=json.loads(surface_file.read_text()) if surface_file.exists() else {'surfaces':[]}
surfaces={s['material']:s for s in surface_data['surfaces']}
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
    # Metric box-projected UVs, chosen per face and material before joining objects.
    # This retains grain orientation on furniture without adding draw calls.
    while mesh.uv_layers:mesh.uv_layers.remove(mesh.uv_layers[0])
    uv=mesh.uv_layers.new(name='SurfaceUV')
    for face in mesh.polygons:
        material=mesh.materials[face.material_index] if mesh.materials else None
        surface=surfaces.get(material.name if material else '',{})
        size=surface.get('tileMetres',1.0);normal_axis=max(range(3),key=lambda i:abs(face.normal[i]))
        axes=[i for i in range(3) if i!=normal_axis]
        if surface.get('role') in {'Wood','Wood_Dark'}:
            grain='XYZ'.index(surface.get('grainAxis','Z'))
            if grain in axes:axes=[next(a for a in axes if a!=grain),grain]
        for li in face.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/size+.5,co[axes[1]]/size+.5)
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
        mat['surfaceRole']=mat.get('role','')
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
    export_yup=True, export_materials='EXPORT',export_texcoords=True)
after = hashlib.sha256(native.read_bytes()).hexdigest()
assert before == after, 'Native file was modified'
report = dict(style=slug, source_file=native.name, source_sha256=before,
    source_objects=source_count, exported_meshes=len(target.objects),
    bytes=(out / 'house.glb').stat().st_size, geometry='Evaluated native geometry with subtle cloth/pillow surface refinement, no decimation',
    refined_textile_objects=len(refinements),
    materials='Base PBR values plus metric SurfaceUV coordinates. Native shader albedo/normal maps are loaded from the companion surfaces manifest by the viewer.',
    omitted='Generic garden context, studio ground, lights, cameras, reference images')
(out / 'export.json').write_text(json.dumps(report, indent=2))
print('HOUSE_EXPORT_COMPLETE ' + json.dumps(report))
