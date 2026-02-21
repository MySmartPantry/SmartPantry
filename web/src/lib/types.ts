export interface Household {
	id: string;
	name: string;
	invite_code: string;
	role?: string;
}

export interface PantryItem {
	id: string;
	household_id: string;
	specific_name: string;
	quantity: number;
	unit: string;
}

export interface Substitution {
	id: string;
	household_id: string;
	ingredient_a: string;
	ingredient_b: string;
}

export interface Recipe {
	id: string;
	title: string;
	source_url: string | null;
	image_url: string | null;
	instructions: string | null;
	servings: number | null;
}

export interface RecipeIngredient {
	id: string;
	recipe_id: string;
	specific_name: string;
	quantity: number | null;
	unit: string | null;
	note: string | null;
}
