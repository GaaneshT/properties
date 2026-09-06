"""Split the native shader atlases into lossless, individually tileable PBR textures."""
import json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
for manifest in (ROOT/'.house-cache').glob('*/surfaces.json'):
    data=json.loads(manifest.read_text());slug=manifest.parent.name;out=ROOT/'static/house'/slug/'surfaces';out.mkdir(parents=True,exist_ok=True)
    tile=data['tilePixels'];columns=data['columns']
    for channel in ['albedo','normal']:
        with Image.open(manifest.parent/f'{channel}-atlas.png') as atlas:
            for entry in data['surfaces']:
                left=entry['column']*tile;top=(columns-entry['row']-1)*tile
                atlas.crop((left,top,left+tile,top+tile)).save(out/f"{entry['index']}-{channel}.png",optimize=True)
    (out/'manifest.json').write_text(json.dumps(data,indent=2))
    print(f"PACKAGED_SURFACES {slug}: {len(data['surfaces'])} pairs")
