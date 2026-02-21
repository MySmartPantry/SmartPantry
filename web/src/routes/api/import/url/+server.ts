import { json, error } from '@sveltejs/kit';
import { parseIngredientStrings, extractRecipeFromText } from '$lib/recipe_parser';
import type { RequestHandler } from './$types';

interface JsonLdRecipe {
	title: string;
	servings: number | null;
	source_url: string;
	image_url: string | null;
	instructions: string[];
	rawIngredients: string[];
}

function extractJsonLd(html: string): JsonLdRecipe | null {
	const matches = html.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi);
	for (const match of matches) {
		try {
			const data = JSON.parse(match[1]);
			const recipes = Array.isArray(data) ? data : data['@graph'] ?? [data];
			const recipe = recipes.find((r: Record<string, unknown>) => r['@type'] === 'Recipe');
			if (!recipe) continue;

			const instructions: string[] = [];
			for (const step of recipe.recipeInstructions ?? []) {
				if (typeof step === 'string') instructions.push(step);
				else if (step.text) instructions.push(step.text);
			}

			return {
				title: recipe.name ?? 'Untitled Recipe',
				servings: parseInt(recipe.recipeYield) || null,
				source_url: recipe.url ?? '',
				image_url: Array.isArray(recipe.image) ? recipe.image[0] : recipe.image ?? null,
				instructions,
				rawIngredients: recipe.recipeIngredient ?? []
			};
		} catch {
			continue;
		}
	}
	return null;
}

async function getHouseholdApiKey(locals: App.Locals): Promise<string> {
	const { data: memberData, error: dbErr } = await locals.supabase
		.from('household_members')
		.select('household_id, households(claude_api_key)')
		.eq('user_id', locals.user!.id)
		.limit(1)
		.single();

	if (dbErr) throw error(500, `DB error: ${dbErr.message}`);

	const apiKey = (memberData?.households as { claude_api_key?: string } | null)?.claude_api_key;
	if (!apiKey) throw error(402, 'No Claude API key configured. Add one in Settings.');
	return apiKey;
}

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) throw error(401, 'Unauthorized');

	try {
		const apiKey = await getHouseholdApiKey(locals);
		const { url } = await request.json();
		if (!url || typeof url !== 'string') throw error(400, 'url is required');

		// Resolve Pinterest: follow to the actual recipe page
		let targetUrl = url;
		if (url.includes('pinterest.com')) {
			const res = await fetch(url, { redirect: 'follow', headers: { 'User-Agent': 'Mozilla/5.0' } });
			const html = await res.text();
			const ogUrl = html.match(/<meta[^>]+property=["']og:url["'][^>]+content=["']([^"']+)["']/i)?.[1];
			if (ogUrl && !ogUrl.includes('pinterest.com')) targetUrl = ogUrl;
		}

		const res = await fetch(targetUrl, {
			headers: { 'User-Agent': 'Mozilla/5.0 (compatible; SmartPantry/1.0)' }
		});
		if (!res.ok) throw error(502, `Could not fetch URL: ${res.status}`);
		const html = await res.text();

		// Try JSON-LD first (free), fall back to full Claude extraction
		const jsonLd = extractJsonLd(html);
		if (jsonLd) {
			const ingredients = await parseIngredientStrings(apiKey, jsonLd.rawIngredients);
			return json({
				title: jsonLd.title,
				servings: jsonLd.servings,
				source_url: jsonLd.source_url,
				image_url: jsonLd.image_url,
				instructions: jsonLd.instructions,
				ingredients
			});
		}

		// No JSON-LD — let Claude extract everything
		const pageText = html
			.replace(/<script[\s\S]*?<\/script>/gi, '')
			.replace(/<style[\s\S]*?<\/style>/gi, '')
			.replace(/<[^>]+>/g, ' ')
			.replace(/\s+/g, ' ');

		const recipe = await extractRecipeFromText(apiKey, pageText, targetUrl);
		return json(recipe);
	} catch (e: unknown) {
		console.error('[import/url] Error:', e);
		if (e && typeof e === 'object' && 'status' in e) throw e;
		const msg = e instanceof Error ? e.message : String(e);
		throw error(500, msg);
	}
};
