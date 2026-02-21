import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockInvoke = vi.fn();
const mockWithStructuredOutput = vi.fn(() => ({ invoke: mockInvoke }));

// Mock @langchain/anthropic — ChatAnthropic must be a class
vi.mock('@langchain/anthropic', () => ({
	ChatAnthropic: class {
		withStructuredOutput = mockWithStructuredOutput;
		constructor() {}
	}
}));

import {
	parseIngredientStrings,
	extractRecipeFromText,
	extractRecipeFromPdf
} from './recipe_parser';

describe('parseIngredientStrings', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should return structured ingredients from raw strings', async () => {
		const ingredients = [
			{ name: 'chicken breast', quantity: 2, unit: 'lbs', note: 'boneless' },
			{ name: 'olive oil', quantity: 2, unit: 'tbsp', note: null }
		];
		mockInvoke.mockResolvedValueOnce({ ingredients });

		const result = await parseIngredientStrings('sk-test-key', [
			'2 lbs chicken breast, boneless',
			'2 tbsp olive oil'
		]);

		expect(result).toEqual(ingredients);
		expect(mockInvoke).toHaveBeenCalledOnce();
		const prompt = mockInvoke.mock.calls[0][0];
		expect(prompt).toContain('2 lbs chicken breast, boneless');
		expect(prompt).toContain('2 tbsp olive oil');
	});

	it('should pass a z.object schema with ingredients key to withStructuredOutput', async () => {
		mockInvoke.mockResolvedValueOnce({ ingredients: [] });

		await parseIngredientStrings('sk-test-key', ['1 cup flour']);

		expect(mockWithStructuredOutput).toHaveBeenCalledOnce();
		const schema = mockWithStructuredOutput.mock.calls[0][0];
		// Schema must be a Zod object (not array) with an ingredients property
		expect(schema.shape).toBeDefined();
		expect(schema.shape.ingredients).toBeDefined();
	});

	it('should unwrap the ingredients array from the wrapper object', async () => {
		const ingredients = [{ name: 'flour', quantity: 1, unit: 'cup', note: null }];
		mockInvoke.mockResolvedValueOnce({ ingredients });

		const result = await parseIngredientStrings('sk-test-key', ['1 cup flour']);
		expect(result).toEqual(ingredients);
	});

	it('should handle empty ingredient list', async () => {
		mockInvoke.mockResolvedValueOnce({ ingredients: [] });

		const result = await parseIngredientStrings('sk-test-key', []);
		expect(result).toEqual([]);
	});
});

describe('extractRecipeFromText', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should return a full recipe with source_url added', async () => {
		mockInvoke.mockResolvedValueOnce({
			title: 'Pomegranate Chicken Salad',
			servings: 4,
			image_url: 'https://example.com/img.jpg',
			instructions: ['Mix ingredients', 'Serve cold'],
			ingredients: [{ name: 'chicken', quantity: 1, unit: 'lb', note: null }]
		});

		const result = await extractRecipeFromText(
			'sk-test-key',
			'Some page text about pomegranate chicken...',
			'https://example.com/recipe'
		);

		expect(result.title).toBe('Pomegranate Chicken Salad');
		expect(result.source_url).toBe('https://example.com/recipe');
		expect(result.ingredients).toHaveLength(1);
		expect(result.instructions).toHaveLength(2);
	});

	it('should truncate page text to 12000 chars', async () => {
		mockInvoke.mockResolvedValueOnce({
			title: 'Test', servings: null, image_url: null,
			instructions: [], ingredients: []
		});

		const longText = 'x'.repeat(20000);
		await extractRecipeFromText('sk-test-key', longText, 'https://example.com');

		const prompt = mockInvoke.mock.calls[0][0];
		expect(prompt.length).toBeLessThan(13000); // ~12000 + prompt prefix
	});

	it('should use a z.object schema for withStructuredOutput', async () => {
		mockInvoke.mockResolvedValueOnce({
			title: 'Test', servings: null, image_url: null,
			instructions: [], ingredients: []
		});

		await extractRecipeFromText('sk-test-key', 'text', 'url');

		expect(mockWithStructuredOutput).toHaveBeenCalledOnce();
		const schema = mockWithStructuredOutput.mock.calls[0][0];
		// RecipeSchema should be a Zod object with title, ingredients, etc.
		expect(schema.shape).toBeDefined();
		expect(schema.shape.title).toBeDefined();
		expect(schema.shape.ingredients).toBeDefined();
	});
});

describe('extractRecipeFromPdf', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should return a recipe with source_url = null', async () => {
		mockInvoke.mockResolvedValueOnce({
			title: 'PDF Recipe',
			servings: 6,
			image_url: null,
			instructions: ['Step 1'],
			ingredients: [{ name: 'sugar', quantity: 2, unit: 'cups', note: null }]
		});

		const result = await extractRecipeFromPdf('sk-test-key', 'base64pdfdata');

		expect(result.title).toBe('PDF Recipe');
		expect(result.source_url).toBeNull();
		expect(result.ingredients).toHaveLength(1);
	});

	it('should pass base64 PDF data in message content', async () => {
		mockInvoke.mockResolvedValueOnce({
			title: 'Test', servings: null, image_url: null,
			instructions: [], ingredients: []
		});

		await extractRecipeFromPdf('sk-test-key', 'AABASE64DATA==');

		const messages = mockInvoke.mock.calls[0][0];
		expect(Array.isArray(messages)).toBe(true);
	});
});
