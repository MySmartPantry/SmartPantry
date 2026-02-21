import { ChatAnthropic } from '@langchain/anthropic';
import { HumanMessage } from '@langchain/core/messages';
import { z } from 'zod';

// ── Schemas ──────────────────────────────────────────────────

const IngredientSchema = z.object({
	name: z.string().describe('The ingredient name, e.g. "chicken breast"'),
	quantity: z.number().nullable().describe('Numeric quantity, or null if unspecified'),
	unit: z.string().nullable().describe('Unit of measure (cups, oz, lbs…), or null'),
	note: z.string().nullable().describe('Prep notes like "finely chopped", or null')
});

const RecipeSchema = z.object({
	title: z.string().describe('The recipe title'),
	servings: z.number().nullable().describe('Number of servings, or null if unknown'),
	image_url: z.string().nullable().describe('Image URL if found, or null'),
	instructions: z.array(z.string()).describe('Step-by-step cooking instructions'),
	ingredients: z.array(IngredientSchema).describe('List of ingredients')
});

// Anthropic tool use requires top-level z.object — wrap the array
const IngredientsWrapperSchema = z.object({
	ingredients: z.array(IngredientSchema).describe('List of parsed ingredients')
});

export type ParsedRecipe = z.infer<typeof RecipeSchema> & {
	source_url: string | null;
};

export type ParsedIngredient = z.infer<typeof IngredientSchema>;

// ── Helpers ──────────────────────────────────────────────────

function makeModel(apiKey: string) {
	return new ChatAnthropic({
		model: 'claude-haiku-4-5-20251001',
		anthropicApiKey: apiKey,
		maxTokens: 2048
	});
}

// ── Parse raw ingredient strings into structured objects ─────

export async function parseIngredientStrings(
	apiKey: string,
	ingredients: string[]
): Promise<ParsedIngredient[]> {
	const model = makeModel(apiKey);
	const structured = model.withStructuredOutput(IngredientsWrapperSchema);
	const result = await structured.invoke(
		`Parse these recipe ingredient strings into structured data:\n\n${ingredients.join('\n')}`
	);
	return result.ingredients;
}

// ── Extract a full recipe from page text ─────────────────────

export async function extractRecipeFromText(
	apiKey: string,
	pageText: string,
	sourceUrl: string
): Promise<ParsedRecipe> {
	const model = makeModel(apiKey);
	const structured = model.withStructuredOutput(RecipeSchema);
	const trimmed = pageText.slice(0, 12000);
	const result = await structured.invoke(
		`Extract the recipe from this webpage text:\n\n${trimmed}`
	);
	return { ...result, source_url: sourceUrl };
}

// ── Extract a full recipe from a PDF (base64) ───────────────

export async function extractRecipeFromPdf(
	apiKey: string,
	base64Data: string
): Promise<ParsedRecipe> {
	const model = makeModel(apiKey);
	const structured = model.withStructuredOutput(RecipeSchema);
	const result = await structured.invoke([
		new HumanMessage({
			content: [
				{
					type: 'image_url',
					image_url: { url: `data:application/pdf;base64,${base64Data}` }
				},
				{ type: 'text', text: 'Extract the recipe from this PDF.' }
			]
		})
	]);
	return { ...result, source_url: null };
}
