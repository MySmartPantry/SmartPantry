<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import type { SupabaseClient } from '@supabase/supabase-js';

	const supabase = getContext<SupabaseClient>('supabase');

	let tab = $state<'login' | 'signup'>('login');
	let email = $state('');
	let password = $state('');
	let householdName = $state('');
	let error = $state('');
	let message = $state('');
	let loading = $state(false);

	async function signIn() {
		loading = true;
		error = '';
		const { error: err } = await supabase.auth.signInWithPassword({ email, password });
		if (err) { error = err.message; }
		else { goto('/'); }
		loading = false;
	}

	async function signUp() {
		loading = true;
		error = '';
		const { error: err } = await supabase.auth.signUp({
			email,
			password,
			options: { data: { pending_household_name: householdName } }
		});
		if (err) { error = err.message; }
		else { message = `Account created for ${email}! Check your email for a confirmation link.`; }
		loading = false;
	}
</script>

<svelte:head><title>SmartPantry — Sign In</title></svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 p-4">
	<div class="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
		<h1 class="text-3xl font-bold text-center mb-2">🍎 SmartPantry</h1>
		<p class="text-center text-gray-500 mb-6 text-sm">Plan meals, manage your pantry, order groceries.</p>

		<div class="flex rounded-lg overflow-hidden border border-gray-200 mb-6">
			<button class="flex-1 py-2 text-sm font-medium transition-colors {tab === 'login' ? 'bg-gray-900 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
				onclick={() => { tab = 'login'; error = ''; message = ''; }}>Sign In</button>
			<button class="flex-1 py-2 text-sm font-medium transition-colors {tab === 'signup' ? 'bg-gray-900 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
				onclick={() => { tab = 'signup'; error = ''; message = ''; }}>Create Account</button>
		</div>

		{#if error}
			<p class="text-red-600 text-sm mb-4 bg-red-50 rounded-lg px-3 py-2">{error}</p>
		{/if}
		{#if message}
			<p class="text-green-700 text-sm mb-4 bg-green-50 rounded-lg px-3 py-2">{message}</p>
		{/if}

		{#if tab === 'login'}
			<form onsubmit={(e) => { e.preventDefault(); signIn(); }} class="space-y-4">
				<div>
					<label for="li-email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
					<input id="li-email" type="email" bind:value={email} required autocomplete="email"
						class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				</div>
				<div>
					<label for="li-pw" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
					<input id="li-pw" type="password" bind:value={password} required autocomplete="current-password"
						class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				</div>
				<button type="submit" disabled={loading}
					class="w-full bg-gray-900 text-white py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50">
					{loading ? 'Signing in…' : 'Sign In'}
				</button>
			</form>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); signUp(); }} class="space-y-4">
				<div>
					<label for="su-email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
					<input id="su-email" type="email" bind:value={email} required autocomplete="email"
						class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				</div>
				<div>
					<label for="su-pw" class="block text-sm font-medium text-gray-700 mb-1">Password (min 6 characters)</label>
					<input id="su-pw" type="password" bind:value={password} required minlength="6" autocomplete="new-password"
						class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				</div>
				<div>
					<label for="su-hh" class="block text-sm font-medium text-gray-700 mb-1">Household name</label>
					<input id="su-hh" type="text" bind:value={householdName} placeholder="e.g. The Parisi House"
						class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900" />
				</div>
				<button type="submit" disabled={loading}
					class="w-full bg-gray-900 text-white py-2 rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50">
					{loading ? 'Creating account…' : 'Create Account'}
				</button>
			</form>
		{/if}
	</div>
</div>
