import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.session) redirect(303, '/login');

	const { data: memberData } = await locals.supabase
		.from('household_members')
		.select('role, households(id, name, invite_code)')
		.eq('user_id', locals.user!.id)
		.limit(1)
		.single();

	const household = memberData
		? { ...(memberData.households as object), role: memberData.role }
		: null;

	// Create household from pending name set at signup
	if (!household) {
		const pendingName = locals.user!.user_metadata?.pending_household_name as string | undefined;
		if (pendingName) {
			const { data: hh } = await locals.supabase
				.from('households')
				.insert({ name: pendingName })
				.select()
				.single();
			if (hh) {
				await locals.supabase
					.from('household_members')
					.insert({ user_id: locals.user!.id, household_id: hh.id, role: 'owner' });
				return { session: locals.session, user: locals.user, household: { ...hh, role: 'owner' } };
			}
		}
	}

	return { session: locals.session, user: locals.user, household };
};
