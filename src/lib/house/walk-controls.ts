import { Euler, PerspectiveCamera } from 'three';
import { moveOnFloor, nearestWalkable, type WalkGrid, type MoveDirection } from './navigation';

const directions: Record<string, MoveDirection> = {
	KeyW: 'forward',
	ArrowUp: 'forward',
	KeyS: 'back',
	ArrowDown: 'back',
	KeyA: 'left',
	ArrowLeft: 'left',
	KeyD: 'right',
	ArrowRight: 'right'
};

export function createWalkControls(camera: PerspectiveCamera, canvas: HTMLCanvasElement) {
	let enabled = false;
	let grid: WalkGrid | null = null;
	let yaw = 0,
		pitch = 0;
	let pointer: { id: number; x: number; y: number } | null = null;
	const keys = new Set<string>();
	const held = new Set<MoveDirection>();
	const euler = new Euler(0, 0, 0, 'YXZ');
	function look() {
		pitch = Math.max(-1.25, Math.min(1.25, pitch));
		camera.quaternion.setFromEuler(euler.set(pitch, yaw, 0, 'YXZ'));
	}
	function stop() {
		keys.clear();
		held.clear();
		pointer = null;
	}
	function reset() {
		euler.setFromQuaternion(camera.quaternion, 'YXZ');
		yaw = euler.y;
		pitch = euler.x;
		if (grid) {
			const safe = nearestWalkable(grid, camera.position.x, camera.position.z);
			if (safe) camera.position.set(safe.x, grid.eyeHeight, safe.z);
		}
		look();
		stop();
	}
	function move(forward: number, right: number, distance: number) {
		if (!grid || !enabled) return;
		const length = Math.hypot(forward, right) || 1;
		const dx = ((-Math.sin(yaw) * forward + Math.cos(yaw) * right) * distance) / length;
		const dz = ((-Math.cos(yaw) * forward - Math.sin(yaw) * right) * distance) / length;
		const next = moveOnFloor(grid, camera.position.x, camera.position.z, dx, dz);
		camera.position.set(next.x, grid.eyeHeight, next.z);
	}
	function down(event: PointerEvent) {
		canvas.focus({ preventScroll: true });
		if (!enabled || event.button !== 0) return;
		pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
		canvas.setPointerCapture(event.pointerId);
	}
	function drag(event: PointerEvent) {
		if (!enabled || pointer?.id !== event.pointerId) return;
		yaw -= (event.clientX - pointer.x) * 0.0032;
		pitch -= (event.clientY - pointer.y) * 0.0032;
		pointer.x = event.clientX;
		pointer.y = event.clientY;
		look();
	}
	function up(event: PointerEvent) {
		if (pointer?.id === event.pointerId) pointer = null;
	}
	function keydown(event: KeyboardEvent) {
		if (!enabled || document.activeElement !== canvas) return;
		if (event.ctrlKey || event.metaKey || event.altKey) return;
		if (directions[event.code] || event.code.startsWith('Shift')) {
			event.preventDefault();
			keys.add(event.code);
		}
		if (event.code === 'Escape') {
			stop();
			canvas.blur();
		}
	}
	function keyup(event: KeyboardEvent) {
		keys.delete(event.code);
	}
	canvas.addEventListener('pointerdown', down);
	canvas.addEventListener('pointermove', drag);
	canvas.addEventListener('pointerup', up);
	canvas.addEventListener('pointercancel', up);
	canvas.addEventListener('lostpointercapture', up);
	canvas.addEventListener('keydown', keydown);
	canvas.addEventListener('blur', stop);
	window.addEventListener('keyup', keyup);
	window.addEventListener('blur', stop);
	document.addEventListener('visibilitychange', stop);
	return {
		reset,
		stop,
		setGrid(value: WalkGrid) {
			grid = value;
			if (enabled) reset();
		},
		setEnabled(value: boolean) {
			enabled = value;
			stop();
			if (enabled) reset();
		},
		focus() {
			canvas.focus({ preventScroll: true });
		},
		hold(direction: MoveDirection, value: boolean) {
			if (value) held.add(direction);
			else held.delete(direction);
		},
		rotate(direction: number) {
			yaw -= (direction * Math.PI) / 12;
			look();
		},
		nudge(forward: number) {
			move(forward, 0, 0.25);
		},
		update(dt: number) {
			if (!enabled) return;
			const pressed = new Set([
				...held,
				...[...keys].map((key) => directions[key]).filter(Boolean)
			]);
			const forward = Number(pressed.has('forward')) - Number(pressed.has('back'));
			const right = Number(pressed.has('right')) - Number(pressed.has('left'));
			if (forward || right)
				move(
					forward,
					right,
					Math.min(0.05, dt) * (keys.has('ShiftLeft') || keys.has('ShiftRight') ? 2.5 : 1.35)
				);
		},
		dispose() {
			stop();
			canvas.removeEventListener('pointerdown', down);
			canvas.removeEventListener('pointermove', drag);
			canvas.removeEventListener('pointerup', up);
			canvas.removeEventListener('pointercancel', up);
			canvas.removeEventListener('lostpointercapture', up);
			canvas.removeEventListener('keydown', keydown);
			canvas.removeEventListener('blur', stop);
			window.removeEventListener('keyup', keyup);
			window.removeEventListener('blur', stop);
			document.removeEventListener('visibilitychange', stop);
		}
	};
}
