<script lang="ts">
	import { getContext } from 'svelte';
	import type { SupabaseClient } from '@supabase/supabase-js';
	import type { Household } from '$lib/types';

	let { data } = $props();
	const supabase = getContext<SupabaseClient>('supabase');
	const household = $derived(data.household as Household | null);

	let claudeKey = $state('');
	let saving = $state(false);
	let saved = $state(false);
	let error = $state('');

	// Load existing key (masked) on mount
	$effect(() => {
		if (household) {
			supabase
				.from('households')
				.select('claude_api_key')
				.eq('id', household.id)
				.single()
				.then(({ data: hh }) => {
					if (hh?.claude_api_key) {
						claudeKey = hh.claude_api_key;
					}
				});
		}
	});

	async function saveKey() {
		if (!household) return;
		saving = true;
		error = '';
		saved = false;

		const { error: err } = await supabase
			.from('households')
			.update({ claude_api_key: claudeKey.trim() })
			.eq('id', household.id);

		if (err) error = err.message;
		else saved = true;
		saving = false;
	}
</script>

<svelte:head><title>Settings — SmartPantry</title></svelte:head>

<h1 class="text-2xl font-bold mb-6">Settings</h1>

{#if !household}
	<p class="text-gray-500 text-sm">You need to be in a household to configure settings.</p>
{:else}
	<div class="bg-white rounded-xl border border-gray-200 p-6 max-w-lg">
		<h2 class="font-semibold text-lg mb-1">Claude API Key</h2>
		<p class="text-sm text-gray-500 mb-4">
			Required for importing recipes from URLs and PDFs. Each household uses their own key.
			Get one at <a href="https://console.anthropic.com/settings/keys" target="_blank"
				class="underline text-gray-700">console.anthropic.com</a>.
		</p>

		{#if error}
			<p class="text-red-600 text-sm mb-3 bg-red-50 rounded-lg px-3 py-2">{error}</p>
		{/if}
		{#if saved}
			<p class="text-green-700 text-sm mb-3 bg-green-50 rounded-lg px-3 py-2">API key saved.</p>
		{/if}

		<div class="space-y-3">
			<div>
				<label for="claude-key" class="block text-sm font-medium text-gray-700 mb-1">
					API Key <span class="text-gray-400 font-normal">(starts with sk-ant-…)</span>
				</label>
				<input
					id="claude-key"
					type="password"
					bind:value={claudeKey}
					placeholder="sk-ant-api03-…"
					class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gray-900"
				/>
			</div>
			<button
				onclick={saveKey}
				disabled={saving || !claudeKey.trim()}
				class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50"
			>
				{saving ? 'Saving…' : 'Save Key'}
			</button>
		</div>
	</div>
{/if}
