import Fuse from 'fuse.js';
import type { Substitution } from './types';

// Calibrated to match rapidfuzz token_sort_ratio >= 82
// Fuse score is inverted (0 = perfect). 0.2 ≈ ratio 80, tuned empirically.
const FUZZY_THRESHOLD = 0.2;

export function namesMatch(a: string, b: string, substitutions: Substitution[]): boolean {
	const aL = a.trim().toLowerCase();
	const bL = b.trim().toLowerCase();

	if (aL === bL) return true;

	for (const sub of substitutions) {
		const pa = sub.ingredient_a.trim().toLowerCase();
		const pb = sub.ingredient_b.trim().toLowerCase();
		if ((aL === pa || aL === pb) && (bL === pa || bL === pb)) return true;
	}

	const fuse = new Fuse([bL], { threshold: FUZZY_THRESHOLD, includeScore: true });
	return fuse.search(aL).length > 0;
}

export function findMatch(
	needle: string,
	items: { id: string; specific_name: string }[],
	substitutions: Substitution[]
): { id: string; specific_name: string } | null {
	return items.find((item) => namesMatch(needle, item.specific_name, substitutions)) ?? null;
}
