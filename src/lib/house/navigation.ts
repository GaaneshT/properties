export type NavigationMode = 'orbit' | 'walk';
export type MoveDirection = 'forward' | 'back' | 'left' | 'right';
export type WalkGrid = {
	origin: [number, number];
	cell: number;
	width: number;
	height: number;
	rows: string[];
	eyeHeight: number;
	bodyRadius: number;
};

export function isWalkable(grid: WalkGrid, x: number, z: number) {
	const column = Math.floor((x - grid.origin[0]) / grid.cell);
	const row = Math.floor((z - grid.origin[1]) / grid.cell);
	return (
		column >= 0 &&
		row >= 0 &&
		column < grid.width &&
		row < grid.height &&
		grid.rows[row]?.[column] === '1'
	);
}

export function nearestWalkable(grid: WalkGrid, x: number, z: number, maxDistance = 2) {
	if (isWalkable(grid, x, z)) return { x, z };
	let result: { x: number; z: number } | null = null;
	let best = maxDistance * maxDistance;
	const minX = Math.max(0, Math.floor((x - maxDistance - grid.origin[0]) / grid.cell));
	const maxX = Math.min(grid.width - 1, Math.ceil((x + maxDistance - grid.origin[0]) / grid.cell));
	const minZ = Math.max(0, Math.floor((z - maxDistance - grid.origin[1]) / grid.cell));
	const maxZ = Math.min(grid.height - 1, Math.ceil((z + maxDistance - grid.origin[1]) / grid.cell));
	for (let row = minZ; row <= maxZ; row++) {
		for (let column = minX; column <= maxX; column++) {
			if (grid.rows[row][column] !== '1') continue;
			const px = grid.origin[0] + (column + 0.5) * grid.cell;
			const pz = grid.origin[1] + (row + 0.5) * grid.cell;
			const distance = (px - x) ** 2 + (pz - z) ** 2;
			if (distance < best) {
				best = distance;
				result = { x: px, z: pz };
			}
		}
	}
	return result;
}

// Substeps prevent tunnelling. Independent axes let the camera slide along walls.
export function moveOnFloor(grid: WalkGrid, x: number, z: number, dx: number, dz: number) {
	const steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dz)) / (grid.cell * 0.45)));
	for (let i = 0; i < steps; i++) {
		const nx = x + dx / steps;
		const nz = z + dz / steps;
		if (isWalkable(grid, nx, z)) x = nx;
		if (isWalkable(grid, x, nz)) z = nz;
	}
	return { x, z };
}
