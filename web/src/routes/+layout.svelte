<script lang="ts">
	import '../app.css';
	import { createClient } from '$lib/supabase';
	import { setContext } from 'svelte';

	let { children, data } = $props();

	const supabase = createClient();
	setContext('supabase', supabase);
	setContext('session', () => data.session);
</script>

{@render children()}
