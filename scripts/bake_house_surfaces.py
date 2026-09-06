"""Render native procedural surface swatches for web PBR delivery. Never saves the native."""
import bpy, hashlib, json, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
STYLES = {'dark-luxe': ('20260906_Dark_Luxe','04_Dark_Luxe'),
          'warm-japandi': ('20260905_155249_3e36c2','01_Warm_Japandi'),
          'tropical-modern': ('20260905_155249_3e36c2','02_Tropical_Modern'),
          'soft-contemporary': ('20260905_155249_3e36c2','03_Soft_Contemporary')}
slug=sys.argv[sys.argv.index('--')+1]
run,name=STYLES[slug]
native=ROOT.parent/'Carissa_Park_Native'/'deliverables'/run/f'Carissa_Park_{name}.blend'
before=hashlib.sha256(native.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False,use_scripts=False)
source=bpy.data.scenes['01_DAY_INTERIOR']
used={m for o in source.objects if o.type=='MESH' and not o.hide_render for m in o.data.materials if m}
fabric={'Fabric','Fabric_Light','Accent','Rug','Towel','Rattan','Paper','Sofa_Cashmere','Bed_Velvet','Drape','Patio_Cushion'}
roles=fabric|{'Wood','Wood_Dark','Stone','Black_Marble','Tile','Floor_Stone','Outdoor_Tile','Plaster','Trim','Cabinet','Feature_Charcoal','Ceiling','Service_Plaster'}
materials=sorted([m for m in used if m.get('role') in roles],key=lambda m:m.name)
scene=bpy.data.scenes.new('WEB_SURFACE_BAKE')
bpy.context.window.scene=scene
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.cycles.device='CPU'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    if any(d.type=='OPTIX' for d in prefs.devices):
        for d in prefs.devices:d.use=d.type=='OPTIX'
        scene.cycles.device='GPU'
except (TypeError,AttributeError):pass
columns=math.ceil(math.sqrt(len(materials)));tile=512
scene.render.resolution_x=columns*tile;scene.render.resolution_y=columns*tile;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
camdata=bpy.data.cameras.new('Texture_camera');cam=bpy.data.objects.new('Texture_camera',camdata);scene.collection.objects.link(cam)
cam.location=(columns/2,columns/2,10);camdata.type='ORTHO';camdata.ortho_scale=columns;scene.camera=cam
entries=[];shaders=[]
for i,original in enumerate(materials):
    role=original.get('role');axis=original.get('grain_axis','Z');size=.25 if role in fabric else 1.0
    material=original.copy();material.name='BAKE_'+original.name
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    texcoord=nodes.new('ShaderNodeTexCoord');separate=nodes.new('ShaderNodeSeparateXYZ');links.new(texcoord.outputs['UV'],separate.inputs[0])
    # Every swatch has vertical grain. UVs on the exported furniture follow the original grain axis.
    combine=nodes.new('ShaderNodeCombineXYZ')
    components=(1,0) if role in {'Wood','Wood_Dark'} and axis=='X' else (0,2) if role in {'Wood','Wood_Dark'} and axis=='Z' else (0,1)
    for channel,target in zip(('X','Y'),components):
        scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY_ADD';scale.inputs[1].default_value=size;scale.inputs[2].default_value=-size/2
        links.new(separate.outputs[channel],scale.inputs[0]);links.new(scale.outputs[0],combine.inputs[target])
    for node in list(nodes):
        if node.type=='TEX_COORD' and node!=texcoord:
            for link in list(node.outputs['Object'].links):links.new(combine.outputs[0],link.to_socket)
    emit=nodes.new('ShaderNodeEmission');emit.inputs['Strength'].default_value=1
    links.new(emit.outputs[0],output.inputs['Surface'])
    color=bsdf.inputs['Base Color'];normal=bsdf.inputs['Normal']
    color_socket=color.links[0].from_socket if color.is_linked else None
    normal_socket=normal.links[0].from_socket if normal.is_linked else None
    if color_socket:links.new(color_socket,emit.inputs['Color'])
    else:emit.inputs['Color'].default_value=color.default_value
    mesh=bpy.data.meshes.new(f'Swatch_{i}');mesh.from_pydata([(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0)],[],[(0,1,2,3)])
    uv=mesh.uv_layers.new(name='UVMap')
    for j,coord in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[j].uv=coord
    obj=bpy.data.objects.new(f'Swatch_{i}',mesh);obj.location=(i%columns+.5,i//columns+.5,0);scene.collection.objects.link(obj);mesh.materials.append(material)
    entries.append(dict(material=original.name,role=role,grainAxis=axis,tileMetres=size,column=i%columns,row=i//columns,index=i,roughness=bsdf.inputs['Roughness'].default_value))
    shaders.append((material,emit,normal_socket))
out=ROOT/'.house-cache'/slug;out.mkdir(parents=True,exist_ok=True)
scene.render.filepath=str(out/'albedo-atlas.png');bpy.ops.render.render(write_still=True)
scene.view_settings.view_transform='Raw'
for material,emit,normal_socket in shaders:
    nodes=material.node_tree.nodes;links=material.node_tree.links
    for link in list(emit.inputs['Color'].links):links.remove(link)
    if normal_socket:
        encode=nodes.new('ShaderNodeVectorMath');encode.operation='MULTIPLY_ADD';encode.inputs[1].default_value=(.5,.5,.5);encode.inputs[2].default_value=(.5,.5,.5)
        links.new(normal_socket,encode.inputs[0]);links.new(encode.outputs[0],emit.inputs['Color'])
    else:emit.inputs['Color'].default_value=(.5,.5,1,1)
scene.render.filepath=str(out/'normal-atlas.png');bpy.ops.render.render(write_still=True)
(out/'surfaces.json').write_text(json.dumps(dict(tilePixels=tile,columns=columns,surfaces=entries,sourceHash=before),indent=2))
assert hashlib.sha256(native.read_bytes()).hexdigest()==before
print(f'SURFACE_BAKE_COMPLETE {slug}: {len(entries)} native materials, albedo and normal swatches')
