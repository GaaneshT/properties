import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Box3, Mesh, Vector3 } from 'three';

// Validate the actual exported binaries using the same loader as the website.
// This does not claim to exercise WebGL or browser interactions.
const root = fileURLToPath(new URL('../static/house/', import.meta.url));
const themes = ['dark-luxe', 'warm-japandi', 'tropical-modern', 'soft-contemporary'];
const metadata = JSON.parse(await readFile(path.join(root, 'cameras.json'), 'utf8'));
assert.equal(new Set(metadata.map((camera) => camera.id)).size, 20);
const provenance = JSON.parse(await readFile(path.join(root, 'provenance.json'), 'utf8'));
assert.equal(provenance.renders.length, 80);
let images = 0;
let surfaces = 0;
let textures = 0;
for (const theme of themes) {
	const bytes = await readFile(path.join(root, theme, 'house.glb'));
	assert.equal(bytes.toString('utf8', 0, 4), 'glTF');
	assert.equal(bytes.readUInt32LE(4), 2);
	assert.equal(bytes.readUInt32LE(8), bytes.length);
	const data = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
	const model = await new GLTFLoader().parseAsync(data, '');
	const modes = new Set();
	const materialNames = new Set();
	let triangles = 0;
	let meshes = 0;
	model.scene.traverse((object) => {
		if (object.userData.viewMode) modes.add(object.userData.viewMode);
		if (object instanceof Mesh) {
			meshes++;
			triangles += (object.geometry.index?.count ?? object.geometry.attributes.position.count) / 3;
			assert.ok(object.geometry.attributes.normal, 'Missing evaluated normals');
			assert.ok(object.geometry.attributes.uv, 'Missing metric furniture UV coordinates');
			const positions = object.geometry.attributes.position.array;
			assert.ok(positions.every(Number.isFinite), 'Non-finite model coordinates');
			for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
				assert.ok(material.color.toArray().every(Number.isFinite), 'Invalid material colour');
				materialNames.add(material.name);
			}
		}
	});
	assert.deepEqual([...modes].sort(), ['ceiling', 'cutaway', 'full', 'shared']);
	assert.ok(triangles > 100000 && meshes < 100, 'Unexpected geometry loss or draw count');
	// Joined groups retain their first object's transform. Use transformed vertices,
	// not rotated local bounding-box corners, to measure the actual house envelope.
	const size = new Box3().setFromObject(model.scene, true).getSize(new Vector3());
	assert.ok(
		size.x > 10 && size.x < 18 && size.z > 10 && size.z < 23 && size.y > 2.7 && size.y < 5,
		`Unexpected house dimensions: ${size.toArray()}`
	);
	// The viewer refuses to open without these companion files, so check them too.
	const grid = JSON.parse(await readFile(path.join(root, theme, 'navigation.json'), 'utf8'));
	assert.equal(grid.rows.length, grid.height, 'Walk grid row count');
	assert.ok(
		grid.rows.every((row) => row.length === grid.width && /^[01]+$/.test(row)),
		'Walk grid rows must be 0/1 strings of the declared width'
	);
	assert.ok(grid.cell > 0 && grid.eyeHeight > 1 && grid.bodyRadius > 0, 'Walk grid metrics');
	const walkable = grid.rows.reduce((total, row) => total + row.split('1').length - 1, 0);
	assert.ok(walkable > 1000, 'Walk grid has no usable floor');
	const manifest = JSON.parse(
		await readFile(path.join(root, theme, 'surfaces', 'manifest.json'), 'utf8')
	);
	for (const surface of manifest.surfaces) {
		assert.ok(
			materialNames.has(surface.material),
			`${theme}: surface ${surface.material} matches no exported material`
		);
		for (const kind of ['albedo', 'normal']) {
			const file = path.join(root, theme, 'surfaces', `${surface.index}-${kind}.png`);
			assert.ok((await stat(file)).size > 1000, `Missing surface texture ${file}`);
			textures++;
		}
	}
	surfaces += manifest.surfaces.length;

	for (let index = 1; index <= 20; index++) {
		const camera = `C${String(index).padStart(2, '0')}`;
		for (const suffix of ['', '-thumb', '-compare']) {
			const image = await readFile(path.join(root, theme, `${camera}${suffix}.webp`));
			assert.equal(image.toString('utf8', 0, 4), 'RIFF');
			assert.equal(image.toString('utf8', 8, 12), 'WEBP');
			assert.ok(image.length > 1000);
			images++;
		}
	}
	console.log(
		`${theme}: ${meshes} meshes, ${triangles.toLocaleString()} triangles, ${(bytes.length / 1024 / 1024).toFixed(1)} MiB; ${manifest.surfaces.length} surfaces, ${walkable.toLocaleString()} walkable cells; all view states present`
	);
}
assert.equal(images, 240);
for (const page of ['index.html', 'recent.html', 'house.html']) {
	const file = path.join(root, '..', '..', 'build', page);
	assert.ok((await stat(file)).size > 1000, `Missing built page ${page}`);
}
console.log(
	`PASS: 4 models parsed, 240 WebP assets checked, ${surfaces} surface materials with ${textures} textures, 4 walk grids, 20 cameras, 80 provenance entries, all 3 routes built.`
);
