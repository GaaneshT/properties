"""Package existing owner-supplied Blender renders without changing their composition.

Run with host Python (Pillow required): python scripts/prepare_house_assets.py
The native project remains read-only; no external services are used.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO.parent / 'Carissa_Park_Native'
DEST = REPO / 'static' / 'house'
STYLES = [
    ('dark-luxe', '04_Dark_Luxe', '20260906_Dark_Luxe'),
    ('warm-japandi', '01_Warm_Japandi', '20260905_155249_3e36c2'),
    ('tropical-modern', '02_Tropical_Modern', '20260905_155249_3e36c2'),
    ('soft-contemporary', '03_Soft_Contemporary', '20260905_155249_3e36c2'),
]

def main():
    records = []
    for slug, name, run in STYLES:
        root = SOURCE / 'deliverables' / run
        out = DEST / slug
        out.mkdir(parents=True, exist_ok=True)
        for preview in sorted((root / 'renders' / 'preview' / name).glob('C*.png')):
            final = root / 'renders' / 'standard' / name / preview.name
            original = final if final.exists() else preview
            cid = preview.name.split('_')[0]
            with Image.open(original) as img:
                img.convert('RGB').save(out / f'{cid}.webp', quality=94, method=6)
                thumb = img.convert('RGB')
                thumb.thumbnail((400, 250))
                thumb.save(out / f'{cid}-thumb.webp', quality=82, method=6)
                size = list(img.size)
            # Equal-resolution, equal-quality images for the comparison slider.
            reference = SOURCE / 'deliverables/20260905_155249_3e36c2/renders/preview/01_Warm_Japandi' / preview.name
            with Image.open(reference) as img:
                comparison_size = img.size
            comparison_source = preview
            if slug == 'dark-luxe' and cid in ['C13', 'C14']:
                comparison_source = REPO / '.house-cache' / f'{cid}-dark-luxe-aligned.png'
                if not comparison_source.exists():
                    raise RuntimeError('Run render_house_comparisons.py in Blender first; source service views use different aspect ratios.')
            with Image.open(comparison_source) as img:
                assert abs(img.width / img.height - comparison_size[0] / comparison_size[1]) < .001
                img.convert('RGB').resize(comparison_size, Image.Resampling.LANCZOS).save(out / f'{cid}-compare.webp', quality=94, method=6)
            records.append(dict(style=slug, camera=cid, image=f'{slug}/{cid}.webp',
                dimensions=size, tier='standard' if final.exists() else 'preview',
                source=str(original.relative_to(SOURCE)), sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
    cameras = json.loads((SOURCE / 'data' / 'cameras_final_snapshot.json').read_text())['by_style']['01_Warm_Japandi']
    # Blender Z-up to glTF Y-up, preserving the final corrected camera positions.
    for c in cameras:
        for key in ('location', 'target'):
            x, y, z = c[key]
            c[key] = [x, z, -y]
    (DEST / 'cameras.json').write_text(json.dumps(cameras, indent=2))
    (DEST / 'provenance.json').write_text(json.dumps(dict(
        notice='Concept — dimensions unverified. Browser materials approximate native procedural shaders.',
        renders=records), indent=2), encoding='utf-8')
    assert len(records) == 80, f'Expected four concepts × 20 cameras, got {len(records)}'
    print(f'Packaged {len(records)} native views, comparison images and thumbnails.')

if __name__ == '__main__':
    main()
