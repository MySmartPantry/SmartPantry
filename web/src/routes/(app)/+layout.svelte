<script lang="ts">
	import { getContext } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import type { SupabaseClient } from '@supabase/supabase-js';

	let { children, data } = $props();
	const supabase = getContext<SupabaseClient>('supabase');

	const nav = [
		{ href: '/', label: 'Dashboard' },
		{ href: '/pantry', label: 'Pantry' },
		{ href: '/recipes', label: 'Recipes' },
		{ href: '/meal-plan', label: 'Meal Plan' },
		{ href: '/shopping', label: 'Shopping' },
		{ href: '/settings', label: 'Settings' },
	];

	async function signOut() {
		await supabase.auth.signOut();
		goto('/login');
	}
</script>

<div class="min-h-screen bg-gray-50 flex flex-col">
	<!-- Top nav -->
	<header class="bg-white border-b border-gray-200 sticky top-0 z-10">
		<div class="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
			<span class="font-bold text-lg">🍎 SmartPantry</span>
			<nav class="hidden sm:flex gap-1">
				{#each nav as { href, label }}
					<a {href} class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
						{page.url.pathname === href ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'}">
						{label}
					</a>
				{/each}
			</nav>
			<div class="flex items-center gap-3">
				<span class="hidden sm:block text-xs text-gray-500">{data.user?.email}</span>
				<button onclick={signOut} class="text-sm text-gray-600 hover:text-gray-900">Sign out</button>
			</div>
		</div>
		<!-- Mobile nav -->
		<nav class="sm:hidden flex overflow-x-auto gap-1 px-4 pb-2">
			{#each nav as { href, label }}
				<a {href} class="shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
					{page.url.pathname === href ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'}">
					{label}
				</a>
			{/each}
		</nav>
	</header>

	<main class="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
		{@render children()}
	</main>
</div>
