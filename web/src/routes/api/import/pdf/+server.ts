import { json, error } from '@sveltejs/kit';
import { extractRecipeFromPdf } from '$lib/recipe_parser';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.session) throw error(401, 'Unauthorized');

	try {
		// Get household's Claude API key
		const { data: memberData, error: dbErr } = await locals.supabase
			.from('household_members')
			.select('household_id, households(claude_api_key)')
			.eq('user_id', locals.user!.id)
			.limit(1)
			.single();

		if (dbErr) throw error(500, `DB error: ${dbErr.message}`);

		const apiKey = (memberData?.households as { claude_api_key?: string } | null)?.claude_api_key;
		if (!apiKey) throw error(402, 'No Claude API key configured. Add one in Settings.');

		const formData = await request.formData();
		const file = formData.get('file') as File | null;
		if (!file) throw error(400, 'file is required');
		if (file.type !== 'application/pdf') throw error(400, 'Only PDF files are supported');

		const buffer = await file.arrayBuffer();
		const base64 = Buffer.from(buffer).toString('base64');

		const recipe = await extractRecipeFromPdf(apiKey, base64);
		return json(recipe);
	} catch (e: unknown) {
		console.error('[import/pdf] Error:', e);
		if (e && typeof e === 'object' && 'status' in e) throw e;
		const msg = e instanceof Error ? e.message : String(e);
		throw error(500, msg);
	}
};
