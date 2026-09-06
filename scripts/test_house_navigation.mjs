import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { isWalkable, nearestWalkable, moveOnFloor } from '../src/lib/house/navigation.ts';

// An isolated wall, opening and outside boundary exercise movement independently of the implementation.
const sample = {
	origin: [0, 0],
	cell: 1,
	width: 7,
	height: 5,
	rows: ['0000000', '0110110', '0111110', '0110110', '0000000'],
	eyeHeight: 1.62,
	bodyRadius: 0.13
};
assert.equal(isWalkable(sample, -1, 2), false);
assert.equal(isWalkable(sample, 7, 2), false);
assert.equal(isWalkable(sample, 3.5, 1.5), false);
assert.ok(moveOnFloor(sample, 1.5, 1.5, 5, 0).x < 3, 'Movement must not tunnel through a wall');
assert.ok(moveOnFloor(sample, 1.5, 2.5, 4, 0).x > 5, 'A doorway must remain traversable');
const slide = moveOnFloor(sample, 2.5, 1.5, 1, 1.2);
assert.ok(slide.z > 2.5, 'Diagonal movement must slide along a blocked axis');
assert.equal(nearestWalkable(sample, -20, -20), null);
assert.ok(nearestWalkable(sample, 3.5, 1.5));

const cameras = JSON.parse(
	await readFile(new URL('../static/house/cameras.json', import.meta.url), 'utf8')
);
for (const theme of ['dark-luxe', 'warm-japandi', 'tropical-modern', 'soft-contemporary']) {
	const grid = JSON.parse(
		await readFile(new URL(`../static/house/${theme}/navigation.json`, import.meta.url), 'utf8')
	);
	assert.equal(grid.rows.length, grid.height);
	assert.ok(grid.rows.every((row) => row.length === grid.width && /^[01]+$/.test(row)));
	const visited = new Set();
	const living = cameras.find((camera) => camera.id === 'C03');
	const start = nearestWalkable(grid, living.location[0], living.location[2]);
	assert.ok(start, 'Living room must have a walking start');
	const sx = Math.floor((start.x - grid.origin[0]) / grid.cell),
		sz = Math.floor((start.z - grid.origin[1]) / grid.cell);
	const queue = [[sx, sz]];
	visited.add(`${sx},${sz}`);
	for (let i = 0; i < queue.length; i++) {
		const [x, z] = queue[i];
		for (const [dx, dz] of [
			[1, 0],
			[-1, 0],
			[0, 1],
			[0, -1]
		]) {
			const nx = x + dx,
				nz = z + dz,
				key = `${nx},${nz}`;
			if (
				nx >= 0 &&
				nz >= 0 &&
				nx < grid.width &&
				nz < grid.height &&
				grid.rows[nz][nx] === '1' &&
				!visited.has(key)
			) {
				visited.add(key);
				queue.push([nx, nz]);
			}
		}
	}
	const disconnected = [];
	for (const camera of cameras.filter((camera) => !camera.ortho_scale)) {
		const point = nearestWalkable(grid, camera.location[0], camera.location[2]);
		assert.ok(point, `${theme} ${camera.id}: no nearby walking start`);
		assert.ok(isWalkable(grid, point.x, point.z));
		const key = `${Math.floor((point.x - grid.origin[0]) / grid.cell)},${Math.floor((point.z - grid.origin[1]) / grid.cell)}`;
		if (!visited.has(key)) disconnected.push(camera.id);
		// Repeated large moves must always remain inside the navigable floor.
		let p = point;
		for (const [dx, dz] of [
			[30, 0],
			[0, -30],
			[-30, 30],
			[30, 30]
		]) {
			p = moveOnFloor(grid, p.x, p.z, dx, dz);
			assert.ok(isWalkable(grid, p.x, p.z));
		}
	}
	console.log(
		`${theme}: ${visited.size} cells connected to living; separate camera zones: ${disconnected.join(', ') || 'none'}`
	);
	assert.equal(disconnected.length, 0, 'Room starts must not strand the camera behind furniture');
}
console.log(
	'PASS: collision, wall sliding, doorway passage, bounds, safe room starts and repeated movements.'
);
