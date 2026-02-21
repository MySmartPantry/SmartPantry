<script lang="ts">
	import { getContext } from 'svelte';
	import type { SupabaseClient } from '@supabase/supabase-js';
	import type { Household } from '$lib/types';

	let { data } = $props();
	const supabase = getContext<SupabaseClient>('supabase');
	const household = $derived(data.household as Household | null);

	// ── Import state ──────────────────────────────────────────────
	let importTab = $state<'url' | 'pdf'>('url');
	let urlInput = $state('');
	let pdfFile = $state<File | null>(null);
	let importing = $state(false);
	let importError = $state('');
	let preview = $state<ParsedRecipe | null>(null);
	let saving = $state(false);
	let saveError = $state('');

	// ── Recipe library ────────────────────────────────────────────
	let recipes = $state<SavedRecipe[]>([]);
	let loadingRecipes = $state(true);

	interface ParsedIngredient {
		name: string;
		quantity: number | null;
		unit: string | null;
		note: string | null;
	}

	interface ParsedRecipe {
		title: string;
		servings: number | null;
		source_url: string | null;
		image_url: string | null;
		instructions: string[];
		ingredients: ParsedIngredient[];
	}

	interface SavedRecipe {
		id: string;
		title: string;
		source_url: string | null;
		image_url: string | null;
		servings: number | null;
		created_at: string;
	}

	$effect(() => {
		supabase
			.from('recipes')
			.select('id, title, source_url, image_url, servings, created_at')
			.eq('created_by', data.user?.id)
			.order('created_at', { ascending: false })
			.then(({ data: rows }) => {
				recipes = rows ?? [];
				loadingRecipes = false;
			});
	});

	async function importFromUrl() {
		importing = true;
		importError = '';
		preview = null;
		const res = await fetch('/api/import/url', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url: urlInput.trim() })
		});
		if (!res.ok) {
			try {
				const body = await res.json();
				importError = body?.message || `Error ${res.status}`;
			} catch { importError = `Error ${res.status}`; }
		} else {
			preview = await res.json();
		}
		importing = false;
	}

	async function importFromPdf() {
		if (!pdfFile) return;
		importing = true;
		importError = '';
		preview = null;
		const form = new FormData();
		form.append('file', pdfFile);
		const res = await fetch('/api/import/pdf', { method: 'POST', body: form });
		if (!res.ok) {
			try {
				const body = await res.json();
				importError = body?.message || `Error ${res.status}`;
			} catch { importError = `Error ${res.status}`; }
		} else {
			preview = await res.json();
		}
		importing = false;
	}

	async function saveRecipe() {
		if (!preview) return;
		saving = true;
		saveError = '';

		const { data: recipe, error: recipeErr } = await supabase
			.from('recipes')
			.insert({
				title: preview.title,
				source_url: preview.source_url,
				image_url: preview.image_url,
				instructions: preview.instructions.join('\n\n'),
				servings: preview.servings,
				created_by: data.user?.id,
				is_public: false
			})
			.select()
			.single();

		if (recipeErr || !recipe) {
			saveError = recipeErr?.message ?? 'Failed to save recipe';
			saving = false;
			return;
		}

		// Save ingredients
		if (preview.ingredients.length > 0) {
			await supabase.from('recipe_ingredients').insert(
				preview.ingredients.map((ing) => ({
					recipe_id: recipe.id,
					name: ing.name,
					quantity: ing.quantity,
					unit: ing.unit,
					note: ing.note
				}))
			);
		}

		recipes = [recipe, ...recipes];
		preview = null;
		urlInput = '';
		pdfFile = null;
		saving = false;
	}

	function discardPreview() {
		preview = null;
		importError = '';
	}

	async function deleteRecipe(id: string) {
		await supabase.from('recipes').delete().eq('id', id);
		recipes = recipes.filter((r) => r.id !== id);
	}
</script>

<svelte:head><title>Recipes — SmartPantry</title></svelte:head>

<div class="flex items-center justify-between mb-6">
	<h1 class="text-2xl font-bold">Recipes</h1>
</div>

{#if !household}
	<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-800 text-sm">
		You need to be in a household to use recipes.
	</div>
{:else}

<!-- ── Import Panel ─────────────────────────────────────────── -->
<div class="bg-white rounded-xl border border-gray-200 p-5 mb-8">
	<h2 class="font-semibold mb-4">Import a Recipe</h2>

	<!-- Tab toggle -->
	<div class="flex rounded-lg overflow-hidden border border-gray-200 mb-4 w-fit">
		<button
			class="px-4 py-1.5 text-sm font-medium transition-colors {importTab === 'url' ? 'bg-gray-900 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
			onclick={() => { importTab = 'url'; importError = ''; preview = null; }}>
			From URL
		</button>
		<button
			class="px-4 py-1.5 text-sm font-medium transition-colors {importTab === 'pdf' ? 'bg-gray-900 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
			onclick={() => { importTab = 'pdf'; importError = ''; preview = null; }}>
			From PDF
		</button>
	</div>

	{#if importTab === 'url'}
		<form onsubmit={(e) => { e.preventDefault(); importFromUrl(); }} class="flex gap-2">
			<input
				type="url"
				bind:value={urlInput}
				placeholder="https://www.allrecipes.com/recipe/…  or Pinterest URL"
				required
				class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
			/>
			<button
				type="submit"
				disabled={importing || !urlInput.trim()}
				class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 whitespace-nowrap"
			>
				{importing ? 'Importing…' : 'Import'}
			</button>
		</form>
	{:else}
		<div class="flex gap-2 items-center">
			<label class="flex-1">
				<input
					type="file"
					accept="application/pdf"
					class="hidden"
					onchange={(e) => { pdfFile = (e.currentTarget as HTMLInputElement).files?.[0] ?? null; }}
				/>
				<div class="border border-dashed border-gray-300 rounded-lg px-3 py-3 text-sm text-gray-500 cursor-pointer hover:border-gray-400 text-center">
					{pdfFile ? pdfFile.name : 'Click to choose a PDF recipe file'}
				</div>
			</label>
			<button
				onclick={importFromPdf}
				disabled={importing || !pdfFile}
				class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 whitespace-nowrap"
			>
				{importing ? 'Importing…' : 'Import'}
			</button>
		</div>
	{/if}

	{#if importError}
		<p class="text-red-600 text-sm mt-3 bg-red-50 rounded-lg px-3 py-2">
			{importError}
			{#if importError.includes('API key')}
				— <a href="/settings" class="underline font-medium">Go to Settings</a>
			{/if}
		</p>
	{/if}
</div>

<!-- ── Preview Panel ──────────────────────────────────────────── -->
{#if preview}
	<div class="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-8">
		<div class="flex items-start justify-between mb-3">
			<h2 class="font-semibold text-lg">{preview.title}</h2>
			<button onclick={discardPreview} class="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">×</button>
		</div>

		{#if preview.image_url}
			<img src={preview.image_url} alt={preview.title} class="w-full max-w-xs rounded-lg mb-3 object-cover h-40" />
		{/if}

		{#if preview.servings}
			<p class="text-sm text-gray-600 mb-3">Serves {preview.servings}</p>
		{/if}

		<div class="grid sm:grid-cols-2 gap-4 mb-4">
			<div>
				<h3 class="text-sm font-semibold text-gray-700 mb-2">Ingredients ({preview.ingredients.length})</h3>
				<ul class="text-sm text-gray-700 space-y-1">
					{#each preview.ingredients as ing}
						<li class="flex gap-1">
							{#if ing.quantity}<span class="font-medium">{ing.quantity}</span>{/if}
							{#if ing.unit}<span class="text-gray-500">{ing.unit}</span>{/if}
							<span>{ing.name}</span>
							{#if ing.note}<span class="text-gray-400 italic">({ing.note})</span>{/if}
						</li>
					{/each}
				</ul>
			</div>
			<div>
				<h3 class="text-sm font-semibold text-gray-700 mb-2">Instructions</h3>
				<ol class="text-sm text-gray-700 space-y-2 list-decimal list-inside">
					{#each preview.instructions as step}
						<li>{step}</li>
					{/each}
				</ol>
			</div>
		</div>

		{#if saveError}
			<p class="text-red-600 text-sm mb-3 bg-red-50 rounded-lg px-3 py-2">{saveError}</p>
		{/if}

		<div class="flex gap-2">
			<button
				onclick={saveRecipe}
				disabled={saving}
				class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50"
			>
				{saving ? 'Saving…' : 'Save to My Recipes'}
			</button>
			<button
				onclick={discardPreview}
				class="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50"
			>
				Discard
			</button>
		</div>
	</div>
{/if}

<!-- ── Recipe Library ──────────────────────────────────────────── -->
<h2 class="font-semibold mb-3">My Recipes</h2>

{#if loadingRecipes}
	<p class="text-sm text-gray-400">Loading…</p>
{:else if recipes.length === 0}
	<p class="text-sm text-gray-400">No recipes saved yet. Import one above.</p>
{:else}
	<div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
		{#each recipes as recipe (recipe.id)}
			<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
				{#if recipe.image_url}
					<img src={recipe.image_url} alt={recipe.title} class="w-full h-36 object-cover" />
				{:else}
					<div class="w-full h-36 bg-gray-100 flex items-center justify-center text-3xl">🍽️</div>
				{/if}
				<div class="p-3">
					<p class="font-medium text-sm leading-snug mb-1">{recipe.title}</p>
					{#if recipe.servings}
						<p class="text-xs text-gray-400 mb-2">Serves {recipe.servings}</p>
					{/if}
					<div class="flex gap-2">
						{#if recipe.source_url}
							<a href={recipe.source_url} target="_blank"
								class="text-xs text-gray-500 underline hover:text-gray-700">Source</a>
						{/if}
						<button
							onclick={() => deleteRecipe(recipe.id)}
							class="text-xs text-red-400 hover:text-red-600 ml-auto">Delete</button>
					</div>
				</div>
			</div>
		{/each}
	</div>
{/if}

{/if}
