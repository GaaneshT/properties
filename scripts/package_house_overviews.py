"""Deliver whole-house stills while retaining the original native C01 renders on disk."""
import hashlib,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
for slug in ['dark-luxe','warm-japandi','tropical-modern','soft-contemporary']:
    source=ROOT/'.house-cache'/slug/'overview.png';out=ROOT/'static/house'/slug
    with Image.open(source) as image:
        image.save(out/'C01.webp',quality=95,method=6)
        comparison=image.resize((1280,1000),Image.Resampling.LANCZOS)
        comparison.save(out/'C01-compare.webp',quality=94,method=6)
        thumb=image.copy();thumb.thumbnail((400,250));thumb.save(out/'C01-thumb.webp',quality=85,method=6)
    report=json.loads((out/'export.json').read_text())
    (out/'overview.json').write_text(json.dumps(dict(source_native_sha256=report['source_sha256'],source_render_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        camera_location=[9,-13.5,32],target=[5.75,7,.35],ortho_scale=21.4,dimensions=[1920,1500],
        refinements='Dark studio backdrop, refitted whole-house camera, subtle drape and cushion shaping; native files unchanged'),indent=2))
    print('PACKAGED_OVERVIEW',slug)
