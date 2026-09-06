const PORTFOLIO = 'https://gaanesh.com';

export const identity = {
	name: 'Gaanesh Theivasigamani',
	location: 'Singapore',
	email: 'gaanesh@u.nus.edu',
	portfolio: PORTFOLIO,
	tagline:
		'A private viewer over Singapore URA private residential transactions. Trends and distributions only, no listings and nothing for sale.'
};

export const links = {
	portfolio: PORTFOLIO,
	github: 'https://github.com/GaaneshT',
	linkedin: 'https://www.linkedin.com/in/gaanesht/',
	twitter: 'https://x.com/PlantSecurity',
	blog: 'https://blog.gaanesh.com',
	tools: 'https://tools.gaanesh.com'
};

export type Link = { label: string; url: string; external?: boolean; here?: boolean };

export const navLinks: Link[] = [
	{ label: 'Projects', url: `${PORTFOLIO}/#projects`, external: true },
	{ label: 'Overview', url: '/' },
	{ label: 'Recent', url: '/recent' },
	{ label: 'House Studio', url: '/house' },
	{ label: 'Tools', url: links.tools, external: true },
	{ label: 'Contact', url: `${PORTFOLIO}/#contact`, external: true }
];

export const footerLinks: Link[] = [
	{ label: 'GitHub', url: links.github },
	{ label: 'LinkedIn', url: links.linkedin },
	{ label: 'Portfolio', url: links.portfolio },
	{ label: 'Blog', url: links.blog },
	{ label: 'Tools', url: links.tools }
];

export const copy = {
	footer: `© ${new Date().getFullYear()} ${identity.name} · ${identity.location}`
};
