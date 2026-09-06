"""Re-render the two Dark Luxe service cutaways at the other concepts' aspect ratio.

Run in a separate Blender background process before prepare_house_assets.py.
Native scenes and files are read-only. Output is cached in .house-cache/.
"""
import bpy
import hashlib
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
native = repo.parent / 'Carissa_Park_Native/deliverables/20260906_Dark_Luxe/Carissa_Park_04_Dark_Luxe.blend'
before = hashlib.sha256(native.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
scene = bpy.data.scenes['04_SERVICE_DIAGNOSTIC']
bpy.context.window.scene = scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    if any(d.type == 'OPTIX' for d in prefs.devices):
        for device in prefs.devices:
            device.use = device.type == 'OPTIX'
        scene.cycles.device = 'GPU'
except (TypeError, AttributeError):
    pass
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
out = repo / '.house-cache'
out.mkdir(exist_ok=True)
for cid in ['C13', 'C14']:
    scene.frame_set(int(cid[1:]) * 10)
    scene.camera = next(o for o in scene.objects if o.type == 'CAMERA' and o.get('camera_id') == cid)
    scene.render.filepath = str(out / f'{cid}-dark-luxe-aligned.png')
    bpy.ops.render.render(write_still=True)
assert hashlib.sha256(native.read_bytes()).hexdigest() == before
print('COMPARISON_RENDER_COMPLETE: C13 and C14, original cameras, matched 1024x768 frame; native unchanged.')
