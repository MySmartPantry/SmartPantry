<script lang="ts">
	import { getContext } from 'svelte';
	import type { SupabaseClient } from '@supabase/supabase-js';
	import type { Household } from '$lib/types';

	let { data } = $props();
	const supabase = getContext<SupabaseClient>('supabase');
	const household = $derived(data.household as Household | null);

	let pantryCount = $state<number | null>(null);

	$effect(() => {
		if (household) {
			supabase
				.from('pantry_items')
				.select('id', { count: 'exact', head: true })
				.eq('household_id', household.id)
				.then(({ count }) => { pantryCount = count; });
		}
	});
</script>

<svelte:head><title>Dashboard — SmartPantry</title></svelte:head>

{#if !household}
	<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-800 text-sm">
		You're not in a household yet. Go to <a href="/pantry" class="underline font-medium">Pantry</a> to create or join one.
	</div>
{:else}
	<div class="mb-6">
		<h1 class="text-2xl font-bold">Welcome to {household.name}</h1>
		<p class="text-sm text-gray-500 mt-1">
			Invite code: <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono">{household.invite_code}</code>
			— share this to add household members
		</p>
	</div>

	<div class="grid grid-cols-3 gap-4 mb-8">
		<div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
			<p class="text-3xl font-bold">{pantryCount ?? '—'}</p>
			<p class="text-sm text-gray-500 mt-1">Pantry Items</p>
		</div>
		<div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
			<p class="text-3xl font-bold text-gray-300">—</p>
			<p class="text-sm text-gray-500 mt-1">Saved Recipes</p>
		</div>
		<div class="bg-white rounded-xl border border-gray-200 p-4 text-center">
			<p class="text-3xl font-bold text-gray-300">—</p>
			<p class="text-sm text-gray-500 mt-1">This Week's Meals</p>
		</div>
	</div>

	<div class="grid sm:grid-cols-2 gap-6">
		<div class="bg-white rounded-xl border border-gray-200 p-5">
			<h2 class="font-semibold mb-2">Upcoming Meals</h2>
			<p class="text-sm text-gray-400">Meal planning coming soon.</p>
		</div>
		<div class="bg-white rounded-xl border border-gray-200 p-5">
			<h2 class="font-semibold mb-2">Shopping List</h2>
			<p class="text-sm text-gray-400">Shopping list coming soon.</p>
		</div>
	</div>
{/if}
