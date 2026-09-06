import {
	Group,
	Mesh,
	MeshStandardMaterial,
	MeshPhysicalMaterial,
	Texture,
	SRGBColorSpace,
	NoColorSpace,
	RepeatWrapping
} from 'three';

type Surface = { material: string; role: string; index: number };

export async function applySurfaces(
	model: Group,
	root: string,
	signal: AbortSignal,
	progress: (value: number) => void
) {
	const response = await fetch(`${root}/surfaces/manifest.json`, { signal });
	if (!response.ok) throw new Error('Furniture surface details could not be loaded.');
	const { surfaces }: { surfaces: Surface[] } = await response.json();
	const materials = new Map<string, MeshStandardMaterial>();
	model.traverse((object) => {
		if (object instanceof Mesh)
			for (const material of Array.isArray(object.material) ? object.material : [object.material])
				materials.set(material.name, material);
	});
	const created = new Set<Texture>();
	async function texture(url: string, isColor: boolean) {
		const response = await fetch(url, { signal });
		if (!response.ok) throw new Error('A furniture texture could not be downloaded.');
		const bitmap = await createImageBitmap(await response.blob(), {
			imageOrientation: 'none',
			premultiplyAlpha: 'none',
			colorSpaceConversion: 'none'
		});
		const map = new Texture(bitmap);
		created.add(map);
		map.flipY = false;
		map.colorSpace = isColor ? SRGBColorSpace : NoColorSpace;
		map.wrapS = map.wrapT = RepeatWrapping;
		map.anisotropy = 4;
		map.needsUpdate = true;
		return map;
	}
	let count = 0;
	const results = await Promise.allSettled(
		surfaces.map(async (surface) => {
			const material = materials.get(surface.material);
			if (!material) return;
			const pair = await Promise.allSettled([
				texture(`${root}/surfaces/${surface.index}-albedo.png`, true),
				texture(`${root}/surfaces/${surface.index}-normal.png`, false)
			]);
			const failed = pair.find((result) => result.status === 'rejected');
			if (failed?.status === 'rejected') throw failed.reason;
			material.map = (pair[0] as PromiseFulfilledResult<Texture>).value;
			material.normalMap = (pair[1] as PromiseFulfilledResult<Texture>).value;
			material.color.set('#ffffff');
			material.normalScale.set(0.8, 0.8);
			if (
				material instanceof MeshPhysicalMaterial &&
				/Fabric|Velvet|Cashmere|Drape|Rug|Accent/.test(surface.role)
			) {
				material.sheen = 0.4;
				material.sheenRoughness = 0.7;
				material.sheenColor.set('#b5a68f');
			}
			material.needsUpdate = true;
			progress(++count / surfaces.length);
		})
	);
	const failed = results.find((result) => result.status === 'rejected');
	if (failed?.status === 'rejected') {
		created.forEach((texture) => {
			texture.dispose();
			if (texture.image instanceof ImageBitmap) texture.image.close();
		});
		// Detached textures have already been disposed; leave model disposal responsible for meshes/materials.
		materials.forEach((material) => {
			material.map = null;
			material.normalMap = null;
		});
		throw failed.reason;
	}
}
