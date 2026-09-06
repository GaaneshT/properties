import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { base } from '$app/paths';
import type { CameraId, ThemeId } from './catalog';

type CameraData = {
	id: string;
	location: number[];
	target: number[];
	lens_mm: number;
	ortho_scale: number | null;
};
type Status = (state: { loading: boolean; progress: number; error: string }) => void;

export function createViewer(host: HTMLElement, status: Status) {
	const scene = new THREE.Scene();
	scene.background = new THREE.Color('#141816');
	const camera = new THREE.PerspectiveCamera(55, 1, 0.025, 180);
	const renderer = new THREE.WebGLRenderer({
		antialias: true,
		alpha: false,
		powerPreference: 'high-performance'
	});
	renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
	renderer.toneMapping = THREE.AgXToneMapping;
	renderer.toneMappingExposure = 1.1;
	renderer.shadowMap.enabled = true;
	renderer.shadowMap.type = THREE.PCFSoftShadowMap;
	renderer.domElement.setAttribute(
		'aria-label',
		'Interactive house model. Drag to look around, scroll to zoom, or use the camera controls.'
	);
	renderer.domElement.tabIndex = 0;
	host.appendChild(renderer.domElement);
	const controls = new OrbitControls(camera, renderer.domElement);
	controls.enableDamping = true;
	controls.dampingFactor = 0.09;
	controls.maxDistance = 55;
	controls.minDistance = 0.2;
	controls.maxPolarAngle = Math.PI * 0.96;
	const environment = new RoomEnvironment();
	const pmrem = new THREE.PMREMGenerator(renderer);
	const environmentMap = pmrem.fromScene(environment, 0.04);
	scene.environment = environmentMap.texture;
	scene.environmentIntensity = 0.55;
	environment.dispose();
	pmrem.dispose();
	const ambient = new THREE.HemisphereLight('#edf2ff', '#9f8060', 1.5);
	scene.add(ambient);
	const sun = new THREE.DirectionalLight('#ffe7c2', 3.2);
	sun.position.set(1, 12, -19);
	sun.target.position.set(5.7, 0, -7);
	sun.castShadow = true;
	sun.shadow.mapSize.set(2048, 2048);
	Object.assign(sun.shadow.camera, {
		left: -12,
		right: 12,
		top: 12,
		bottom: -12,
		near: 0.1,
		far: 45
	});
	sun.shadow.normalBias = 0.035;
	sun.shadow.bias = -0.0001;
	scene.add(sun, sun.target);
	const practicals = new THREE.Group();
	for (const [x, z] of [
		[9.4, -8.7],
		[9.4, -4.6],
		[3, -10.7],
		[6.2, -9.2],
		[1.9, -4.5],
		[7.7, -1.4],
		[2.5, -7.2],
		[4.4, -4]
	]) {
		const light = new THREE.PointLight('#ffd49a', 9, 5, 2);
		light.position.set(x, 2.5, z);
		practicals.add(light);
	}
	scene.add(practicals);
	let model: THREE.Group | null = null;
	let cameraData: CameraData[] = [];
	let currentCamera: CameraId = 'C01';
	let currentTheme: ThemeId | null = null;
	let disposed = false;
	let request = 0;
	let animation = 0;
	let visible = true;
	let exposure = 1.1;
	let abort: AbortController | null = null;
	const loader = new GLTFLoader();
	const metadataAbort = new AbortController();
	const metadata = fetch(`${base}/house/cameras.json`, { signal: metadataAbort.signal }).then(
		async (response) => {
			if (!response.ok) throw new Error('Camera information could not be loaded.');
			cameraData = await response.json();
		}
	);
	// The load routine reports metadata failures along with model failures.
	void metadata.catch(() => {});

	function disposeModel(group: THREE.Group) {
		const geometries = new Set<THREE.BufferGeometry>();
		const materials = new Set<THREE.Material>();
		group.traverse((object) => {
			if (object instanceof THREE.Mesh) {
				geometries.add(object.geometry);
				for (const material of Array.isArray(object.material) ? object.material : [object.material])
					materials.add(material);
			}
		});
		geometries.forEach((geometry) => geometry.dispose());
		materials.forEach((material) => material.dispose());
	}

	function setCamera(id: CameraId) {
		currentCamera = id;
		const data = cameraData.find((item) => item.id === id);
		if (!data) return;
		const overview = ['C01', 'C02', 'C13', 'C14'].includes(id);
		model?.traverse((object) => {
			const mode = object.userData.viewMode as string | undefined;
			if (mode)
				object.visible =
					mode === 'shared' ||
					(overview ? mode === 'cutaway' : mode === 'full' || mode === 'ceiling');
		});
		camera.position.fromArray(data.location);
		camera.up.set(0, 1, 0);
		controls.target.fromArray(data.target);
		if (data.ortho_scale) {
			camera.fov = 35;
			const distance = data.ortho_scale / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
			camera.position
				.sub(controls.target)
				.normalize()
				.multiplyScalar(distance)
				.add(controls.target);
			if (id === 'C02') {
				camera.up.set(0, 0, -1);
				camera.position.z += 0.001;
			}
		} else {
			camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(36 / (2 * data.lens_mm * camera.aspect)));
		}
		if (!overview) {
			// Keep the rotation pivot at eye position: drag explores the room from its saved camera.
			const direction = controls.target.clone().sub(camera.position).normalize();
			controls.target.copy(camera.position).addScaledVector(direction, 0.25);
		}
		controls.enablePan = overview;
		controls.minDistance = overview ? 2 : 0.12;
		controls.maxDistance = overview ? 55 : 12;
		sun.intensity = id === 'C16' ? 0.15 : 3.2;
		ambient.intensity = id === 'C16' ? 0.65 : 1.5;
		practicals.visible = !overview;
		scene.environmentIntensity = id === 'C16' ? 0.22 : 0.55;
		renderer.toneMappingExposure = exposure;
		camera.updateProjectionMatrix();
		controls.update();
	}

	async function load(theme: ThemeId) {
		const token = ++request;
		abort?.abort();
		// Returning to the displayed theme must also cancel an intervening download.
		if (theme === currentTheme && model) {
			status({ loading: false, progress: 100, error: '' });
			return;
		}
		abort = new AbortController();
		status({ loading: true, progress: 0, error: '' });
		try {
			const response = await fetch(`${base}/house/${theme}/house.glb`, { signal: abort.signal });
			if (!response.ok) throw new Error('The house model could not be downloaded.');
			const total = Number(response.headers.get('content-length'));
			const reader = response.body?.getReader();
			const chunks: Uint8Array[] = [];
			let received = 0;
			if (!reader) throw new Error('Model streaming is unavailable in this browser.');
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				chunks.push(value);
				received += value.length;
				if (token === request && !disposed)
					status({
						loading: true,
						progress: total ? Math.min(95, Math.round((received / total) * 95)) : 0,
						error: ''
					});
			}
			if (token !== request || disposed) return;
			const buffer = new Uint8Array(received);
			let offset = 0;
			for (const chunk of chunks) {
				buffer.set(chunk, offset);
				offset += chunk.length;
			}
			await metadata;
			const gltf = await loader.parseAsync(buffer.buffer, '');
			if (token !== request || disposed) {
				disposeModel(gltf.scene);
				return;
			}
			if (model) {
				scene.remove(model);
				disposeModel(model);
			}
			model = gltf.scene;
			model.traverse((object) => {
				if (object instanceof THREE.Mesh) {
					const materials = Array.isArray(object.material) ? object.material : [object.material];
					// Shadow maps cannot model refractive transmission. Let daylight through glazing.
					object.castShadow = !materials.some(
						(material) =>
							material instanceof THREE.MeshPhysicalMaterial && material.transmission > 0.6
					);
					object.receiveShadow = true;
				}
			});
			scene.add(model);
			currentTheme = theme;
			setCamera(currentCamera);
			status({ loading: false, progress: 100, error: '' });
		} catch (error) {
			if (token !== request || disposed || (error instanceof Error && error.name === 'AbortError'))
				return;
			status({
				loading: false,
				progress: 0,
				error: error instanceof Error ? error.message : '3D could not be loaded.'
			});
		}
	}

	function resize() {
		const width = Math.max(1, host.clientWidth);
		const height = Math.max(1, host.clientHeight);
		renderer.setSize(width, height);
		camera.aspect = width / height;
		camera.updateProjectionMatrix();
	}
	const observer = new ResizeObserver(resize);
	observer.observe(host);
	resize();
	function frame() {
		if (disposed) return;
		animation = requestAnimationFrame(frame);
		if (!visible || document.hidden) return;
		controls.update();
		renderer.render(scene, camera);
	}
	const intersection = new IntersectionObserver(([entry]) => {
		visible = entry.isIntersecting;
	});
	intersection.observe(host);
	function lost(event: Event) {
		event.preventDefault();
		status({
			loading: false,
			progress: 0,
			error: 'The graphics connection was interrupted. Return to renders, then reopen 3D.'
		});
	}
	renderer.domElement.addEventListener('webglcontextlost', lost);
	frame();
	return {
		load,
		setCamera,
		setExposure(value: number) {
			exposure = value;
			renderer.toneMappingExposure = value;
		},
		rotate(direction: number) {
			const offset = camera.position.clone().sub(controls.target);
			offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), (direction * Math.PI) / 12);
			camera.position.copy(controls.target).add(offset);
			controls.update();
		},
		zoom(factor: number) {
			const offset = camera.position.clone().sub(controls.target);
			const distance = THREE.MathUtils.clamp(
				offset.length() * factor,
				controls.minDistance,
				controls.maxDistance
			);
			camera.position.copy(controls.target).add(offset.setLength(distance));
			controls.update();
		},
		dispose() {
			disposed = true;
			++request;
			abort?.abort();
			metadataAbort.abort();
			cancelAnimationFrame(animation);
			observer.disconnect();
			intersection.disconnect();
			controls.dispose();
			if (model) disposeModel(model);
			environmentMap.dispose();
			sun.shadow.map?.dispose();
			renderer.domElement.removeEventListener('webglcontextlost', lost);
			renderer.dispose();
			renderer.forceContextLoss();
			renderer.domElement.remove();
		}
	};
}
