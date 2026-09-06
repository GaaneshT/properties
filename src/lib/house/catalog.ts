import { base } from '$app/paths';

export const themes = [
	{
		id: 'dark-luxe',
		name: 'Dark Luxe',
		note: 'Smoked walnut · dark stone · warm brass',
		colors: ['#454440', '#65503f', '#ac8b55', '#b5a590']
	},
	{
		id: 'warm-japandi',
		name: 'Warm Japandi',
		note: 'Light oak · warm white · natural linen',
		colors: ['#dbd3c2', '#b59a72', '#eee9de', '#92947b']
	},
	{
		id: 'tropical-modern',
		name: 'Tropical Modern',
		note: 'Rich timber · muted green · woven details',
		colors: ['#7e8a70', '#866144', '#c29c78', '#e5ddc9']
	},
	{
		id: 'soft-contemporary',
		name: 'Soft Contemporary',
		note: 'Pale stone · soft taupe · warm metal',
		colors: ['#d5cfc5', '#ada18e', '#e8e4dc', '#9c8d74']
	}
] as const;
export type ThemeId = (typeof themes)[number]['id'];
export type ViewMode = 'render' | 'compare' | 'explore';
export const views = [
	{
		id: 'C01',
		name: 'Whole house',
		detail: 'Complete furnished overview',
		group: 'Overview',
		kind: 'cutaway'
	},
	{ id: 'C03', name: 'Living room', detail: 'Toward the patio', group: 'Living', kind: 'day' },
	{ id: 'C04', name: 'Living room', detail: 'Media wall', group: 'Living', kind: 'day' },
	{
		id: 'C16',
		name: 'Living at dusk',
		detail: 'Evening lighting',
		group: 'Living',
		kind: 'evening'
	},
	{ id: 'C05', name: 'Dining & entry', detail: 'Connected living', group: 'Living', kind: 'day' },
	{ id: 'C06', name: 'Master bedroom', detail: 'Bed & headwall', group: 'Bedrooms', kind: 'day' },
	{
		id: 'C07',
		name: 'Master storage',
		detail: 'Wardrobe & joinery',
		group: 'Bedrooms',
		kind: 'day'
	},
	{ id: 'C08', name: 'Bedroom 2', detail: 'Bed & workspace', group: 'Bedrooms', kind: 'day' },
	{ id: 'C20', name: 'Bedroom 2', detail: 'Reverse view', group: 'Bedrooms', kind: 'day' },
	{ id: 'C09', name: 'Bedroom 3', detail: 'Bed & storage', group: 'Bedrooms', kind: 'day' },
	{
		id: 'C10',
		name: 'Kitchen',
		detail: 'Cabinetry & worktop',
		group: 'Kitchen & baths',
		kind: 'day'
	},
	{
		id: 'C11',
		name: 'Master bathroom',
		detail: 'Bath zone · wide lens',
		group: 'Kitchen & baths',
		kind: 'day'
	},
	{
		id: 'C17',
		name: 'Master vanity',
		detail: 'Vanity & shower · wide lens',
		group: 'Kitchen & baths',
		kind: 'day'
	},
	{
		id: 'C12',
		name: 'Common bathroom',
		detail: 'Vanity & shower · wide lens',
		group: 'Kitchen & baths',
		kind: 'day'
	},
	{
		id: 'C15',
		name: 'Patio / PES',
		detail: 'Outdoor living',
		group: 'Outdoor & service',
		kind: 'day'
	},
	{
		id: 'C18',
		name: 'Yard',
		detail: 'Service area · wide lens',
		group: 'Outdoor & service',
		kind: 'day'
	},
	{
		id: 'C19',
		name: 'Service WC',
		detail: 'Wide-lens view',
		group: 'Outdoor & service',
		kind: 'day'
	},
	{
		id: 'C13',
		name: 'Utility & store',
		detail: 'Service cutaway',
		group: 'Outdoor & service',
		kind: 'cutaway'
	},
	{
		id: 'C14',
		name: 'Yard, WC & bin',
		detail: 'Service cutaway',
		group: 'Outdoor & service',
		kind: 'cutaway'
	},
	{ id: 'C02', name: 'Floor plan', detail: 'Furnished plan', group: 'Overview', kind: 'plan' }
] as const;
export type CameraId = (typeof views)[number]['id'];
export const groups = [
	'All spaces',
	'Living',
	'Bedrooms',
	'Kitchen & baths',
	'Outdoor & service',
	'Overview'
];
export function asset(theme: ThemeId, camera: CameraId, variant: '' | '-thumb' | '-compare' = '') {
	return `${base}/house/${theme}/${camera}${variant}.webp`;
}
export function isTheme(value: string | null): value is ThemeId {
	return themes.some((theme) => theme.id === value);
}
export function isCamera(value: string | null): value is CameraId {
	return views.some((view) => view.id === value);
}
