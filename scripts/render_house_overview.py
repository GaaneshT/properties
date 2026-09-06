"""Reference-inspired overview from the actual native geometry, without saving the source."""
import bpy,sys,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refine_house_furniture import refine_furniture
STYLES={'dark-luxe':('20260906_Dark_Luxe','04_Dark_Luxe'),'warm-japandi':('20260905_155249_3e36c2','01_Warm_Japandi'),'tropical-modern':('20260905_155249_3e36c2','02_Tropical_Modern'),'soft-contemporary':('20260905_155249_3e36c2','03_Soft_Contemporary')}
slug=sys.argv[sys.argv.index('--')+1];run,name=STYLES[slug]
native=ROOT.parent/'Carissa_Park_Native/deliverables'/run/f'Carissa_Park_{name}.blend'
before=hashlib.sha256(native.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False,use_scripts=False)
refine_furniture(bpy.data.scenes['01_DAY_INTERIOR'])
scene=bpy.data.scenes['00_START_OVERVIEW'];bpy.context.window.scene=scene
scene.frame_set(10);camera=scene.camera
camera.location=(9.0,-13.5,32);target=Vector((5.75,7,.35));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=21.4
ground=bpy.data.objects.get('STUDIO_GROUND_NOT_PROPERTY')
if ground:
    material=bpy.data.materials.new('WEB_DARK_STUDIO_GROUND');material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.014,.018,.016,1);bsdf.inputs['Roughness'].default_value=.86
    ground.data=ground.data.copy();ground.data.materials.clear();ground.data.materials.append(material)
scene.world=scene.world.copy();scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.22
for obj in scene.objects:
    if obj.type=='LIGHT':
        obj.data=obj.data.copy()
        if 'fill' in obj.name.lower():obj.data.energy*=.65
scene.cycles.samples=96;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    if any(d.type=='OPTIX' for d in prefs.devices):
        for d in prefs.devices:d.use=d.type=='OPTIX'
        scene.cycles.device='GPU'
except (TypeError,AttributeError):pass
scene.render.resolution_x=1920;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
out=ROOT/'.house-cache'/slug;out.mkdir(parents=True,exist_ok=True);scene.render.filepath=str(out/'overview.png')
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(native.read_bytes()).hexdigest()==before
print('WHOLE_HOUSE_OVERVIEW_COMPLETE',slug)
