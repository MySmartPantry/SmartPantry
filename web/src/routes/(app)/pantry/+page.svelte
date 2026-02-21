<script lang="ts">
	import { getContext } from 'svelte';
	import type { SupabaseClient } from '@supabase/supabase-js';
	import type { PantryItem, Substitution, Household } from '$lib/types';
	import { namesMatch } from '$lib/ingredient_matcher';

	let { data } = $props();
	const supabase = getContext<SupabaseClient>('supabase');
	const household = $derived(data.household as Household | null);

	// ── State ─────────────────────────────────────────────────
	let items = $state<PantryItem[]>([]);
	let substitutions = $state<Substitution[]>([]);
	let flash = $state<{ msg: string; kind: 'success' | 'info' } | null>(null);

	// Add item form
	let addOpen = $state(false);
	let newName = $state('');
	let newQty = $state(1);
	let newUnit = $state('count');
	let adding = $state(false);

	// Substitutions form
	let subOpen = $state(false);
	let subA = $state('');
	let subB = $state('');
	let addingSub = $state(false);

	// ── Load ──────────────────────────────────────────────────
	async function load() {
		if (!household) return;
		const [{ data: pantry }, { data: subs }] = await Promise.all([
			supabase.from('pantry_items').select('*').eq('household_id', household.id).order('specific_name'),
			supabase.from('ingredient_substitutions').select('*')
		]);
		items = pantry ?? [];
		substitutions = subs ?? [];
	}

	$effect(() => { load(); });

	function showFlash(msg: string, kind: 'success' | 'info' = 'success') {
		flash = { msg, kind };
		setTimeout(() => { flash = null; }, 4000);
	}

	// ── Add pantry item ───────────────────────────────────────
	async function addItem() {
		if (!newName.trim() || !household) return;
		adding = true;

		const existing = items.find((i) => namesMatch(newName, i.specific_name, substitutions));

		if (existing) {
			const newQtyTotal = (existing.quantity ?? 0) + newQty;
			await supabase.from('pantry_items')
				.update({ quantity: newQtyTotal, specific_name: newName })
				.eq('id', existing.id);
			showFlash(`Updated ${newName} — now ${newQtyTotal} ${newUnit} on hand.`);
		} else {
			await supabase.from('pantry_items').insert({
				household_id: household.id,
				specific_name: newName.trim(),
				quantity: newQty,
				unit: newUnit.trim() || 'count'
			});
			showFlash(`Added ${newName} to pantry.`);
		}

		newName = '';
		newQty = 1;
		newUnit = 'count';
		addOpen = false;
		await load();
		adding = false;
	}

	// ── Update quantity inline ────────────────────────────────
	async function updateQty(item: PantryItem, qty: number) {
		if (qty <= 0) {
			await supabase.from('pantry_items').delete().eq('id', item.id);
		} else {
			await supabase.from('pantry_items').update({ quantity: qty }).eq('id', item.id);
		}
		await load();
	}

	// ── Delete item ───────────────────────────────────────────
	async function deleteItem(id: string) {
		await supabase.from('pantry_items').delete().eq('id', id);
		await load();
	}

	// ── Add substitution pair ─────────────────────────────────
	async function addSub() {
		if (!subA.trim() || !subB.trim() || !household) return;
		addingSub = true;
		const { error } = await supabase.from('ingredient_substitutions').insert({
			household_id: household.id,
			ingredient_a: subA.trim(),
			ingredient_b: subB.trim()
		});
		if (error) {
			showFlash('That pair already exists.', 'info');
		} else {
			subA = '';
			subB = '';
			subOpen = false;
			await load();
		}
		addingSub = false;
	}

	// ── Delete substitution ───────────────────────────────────
	async function deleteSub(id: string) {
		await supabase.from('ingredient_substitutions').delete().eq('id', id);
		await load();
	}

	const hhSubs = $derived(substitutions.filter((s) => s.household_id === household?.id));
</script>

<svelte:head><title>Pantry — SmartPantry</title></svelte:head>

{#if !household}
	<p class="text-gray-500">No household found. <a href="/pantry/setup" class="underline">Set one up</a>.</p>
{:else}
	<div class="flex items-center justify-between mb-4">
		<div>
			<h1 class="text-2xl font-bold">📦 My Pantry</h1>
			<p class="text-sm text-gray-500 mt-0.5">
				{household.name} · Invite code:
				<code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-xs">{household.invite_code}</code>
			</p>
		</div>
		<button onclick={() => { addOpen = !addOpen; }}
			class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700">
			+ Add item
		</button>
	</div>

	{#if flash}
		<div class="mb-4 px-4 py-2.5 rounded-lg text-sm {flash.kind === 'success' ? 'bg-green-50 text-green-800' : 'bg-blue-50 text-blue-800'}">
			{flash.msg}
		</div>
	{/if}

	<!-- Add item form -->
	{#if addOpen}
		<div class="bg-white border border-gray-200 rounded-xl p-4 mb-4">
			<form onsubmit={(e) => { e.preventDefault(); addItem(); }} class="flex gap-3 flex-wrap">
				<input type="text" bind:value={newName} placeholder="Item name (e.g. Goat Milk)" required
					class="flex-1 min-w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				<input type="number" bind:value={newQty} min="0" step="0.5"
					class="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				<input type="text" bind:value={newUnit} list="unit-suggestions" placeholder="unit"
					class="w-28 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				<datalist id="unit-suggestions">
					{#each ['count','cups','oz','lbs','tbsp','tsp','liters','ml','grams','kg','bunch','clove','slice','cans','bags','jars','bottles'] as u}
						<option value={u}></option>
					{/each}
				</datalist>
				<button type="submit" disabled={adding}
					class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50">
					{adding ? 'Adding…' : 'Add'}
				</button>
				<button type="button" onclick={() => { addOpen = false; }}
					class="text-gray-500 hover:text-gray-800 px-2 py-2 text-sm">Cancel</button>
			</form>
		</div>
	{/if}

	<!-- Inventory -->
	{#if items.length === 0}
		<p class="text-gray-400 text-sm py-8 text-center">Your pantry is empty. Add items above.</p>
	{:else}
		<div class="bg-white border border-gray-200 rounded-xl overflow-hidden mb-6">
			{#each items as item, i}
				<div class="flex items-center gap-3 px-4 py-3 {i < items.length - 1 ? 'border-b border-gray-100' : ''}">
					<span class="flex-1 text-sm font-medium">{item.specific_name}</span>
					<input type="number" value={item.quantity} min="0" step="0.5"
						onchange={(e) => updateQty(item, parseFloat((e.target as HTMLInputElement).value))}
						class="w-20 border border-gray-200 rounded-lg px-2 py-1 text-sm text-center focus:outline-none focus:ring-2 focus:ring-gray-900" />
					<span class="text-sm text-gray-400 w-16">{item.unit}</span>
					<button onclick={() => deleteItem(item.id)}
						class="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none">×</button>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Substitution pairs -->
	<div class="border-t border-gray-200 pt-6">
		<div class="flex items-center justify-between mb-3">
			<h2 class="font-semibold text-sm text-gray-700">🔄 Substitutions</h2>
			<button onclick={() => { subOpen = !subOpen; }}
				class="text-sm text-gray-500 hover:text-gray-900">
				{subOpen ? 'Cancel' : '+ Add pair'}
			</button>
		</div>

		{#if subOpen}
			<form onsubmit={(e) => { e.preventDefault(); addSub(); }}
				class="flex gap-3 flex-wrap mb-4 bg-white border border-gray-200 rounded-xl p-4">
				<input type="text" bind:value={subA} placeholder="Ingredient A (e.g. EVOO)" required
					class="flex-1 min-w-36 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				<span class="self-center text-gray-400">↔</span>
				<input type="text" bind:value={subB} placeholder="Ingredient B (e.g. Olive Oil)" required
					class="flex-1 min-w-36 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				<button type="submit" disabled={addingSub}
					class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50">
					{addingSub ? 'Saving…' : 'Save'}
				</button>
			</form>
		{/if}

		{#if hhSubs.length === 0}
			<p class="text-sm text-gray-400">No substitutions yet.</p>
		{:else}
			<div class="space-y-1">
				{#each hhSubs as sub}
					<div class="flex items-center justify-between bg-white border border-gray-100 rounded-lg px-3 py-2">
						<span class="text-sm">{sub.ingredient_a} ↔ {sub.ingredient_b}</span>
						<button onclick={() => deleteSub(sub.id)} class="text-gray-300 hover:text-red-500 text-lg leading-none">×</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
