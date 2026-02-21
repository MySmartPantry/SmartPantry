import { createBrowserClient, createServerClient, isBrowser } from '@supabase/ssr';
import { PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY } from '$env/static/public';
import type { CookieSerializeOptions } from 'cookie';

export function createClient(
	cookieStore?: { getAll: () => { name: string; value: string }[]; setAll: (cookies: { name: string; value: string; options: CookieSerializeOptions }[]) => void }
) {
	if (isBrowser()) {
		return createBrowserClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY);
	}
	return createServerClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY, {
		cookies: cookieStore ?? { getAll: () => [], setAll: () => {} }
	});
}
