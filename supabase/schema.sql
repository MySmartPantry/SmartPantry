-- ============================================================
-- SmartPantry Database Schema
-- Run this in the Supabase SQL Editor (supabase.com > your project > SQL Editor)
-- ============================================================

-- ── Households ───────────────────────────────────────────────
CREATE TABLE households (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    invite_code TEXT UNIQUE NOT NULL DEFAULT substr(md5(random()::text), 1, 8),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Links Supabase Auth users to households
CREATE TABLE household_members (
    user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    household_id UUID REFERENCES households(id) ON DELETE CASCADE,
    role         TEXT NOT NULL DEFAULT 'member', -- 'owner' or 'member'
    joined_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, household_id)
);

-- ── Ingredient Taxonomy ───────────────────────────────────────
-- Canonical ingredient types (e.g., "Milk", "Pasta", "Chicken")
CREATE TABLE ingredient_types (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name     TEXT UNIQUE NOT NULL,  -- canonical name, e.g. "Milk"
    category TEXT NOT NULL          -- e.g. "Dairy", "Grain", "Protein", "Vegetable", "Fruit", "Oil", "Spice", "Other"
);

-- Specific variants that map to a canonical type
-- e.g., "Goat Milk" -> Milk, "Oat Milk" -> Milk, "Whole Milk" -> Milk
CREATE TABLE ingredient_aliases (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alias              TEXT NOT NULL,
    ingredient_type_id UUID NOT NULL REFERENCES ingredient_types(id) ON DELETE CASCADE,
    UNIQUE(alias)
);

-- ── Pantry ────────────────────────────────────────────────────
CREATE TABLE pantry_items (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id       UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    ingredient_type_id UUID NOT NULL REFERENCES ingredient_types(id),
    specific_name      TEXT NOT NULL,  -- what they actually have, e.g. "Goat Milk"
    quantity           NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit               TEXT NOT NULL DEFAULT 'count', -- "cups", "oz", "lbs", "count", etc.
    updated_at         TIMESTAMPTZ DEFAULT now()
);

-- ── Recipes ───────────────────────────────────────────────────
CREATE TABLE recipes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title        TEXT NOT NULL,
    source_url   TEXT,
    image_url    TEXT,
    instructions TEXT,
    servings     INTEGER DEFAULT 4,
    created_by   UUID REFERENCES auth.users(id),  -- NULL = from TheMealDB
    is_public    BOOLEAN DEFAULT true,
    external_id  TEXT,  -- TheMealDB meal ID, for deduplication
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE recipe_ingredients (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id          UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_type_id UUID NOT NULL REFERENCES ingredient_types(id),
    quantity           NUMERIC(10,2),
    unit               TEXT,
    note               TEXT  -- "finely chopped", "divided", optional
);

-- ── Meal Plans ────────────────────────────────────────────────
CREATE TABLE meal_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    start_date   DATE NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE meal_plan_recipes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_plan_id UUID NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    recipe_id    UUID NOT NULL REFERENCES recipes(id),
    meal_date    DATE NOT NULL,
    meal_type    TEXT NOT NULL DEFAULT 'dinner',  -- 'breakfast', 'lunch', 'dinner', 'snack'
    servings     INTEGER DEFAULT 4,
    cooked_at    TIMESTAMPTZ  -- set when user marks as cooked
);

-- ── Shopping Lists ────────────────────────────────────────────
CREATE TABLE shopping_list_items (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id       UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    meal_plan_id       UUID REFERENCES meal_plans(id),  -- nullable for ad-hoc items
    ingredient_type_id UUID NOT NULL REFERENCES ingredient_types(id),
    specific_name      TEXT,  -- suggested product name, optional
    quantity_needed    NUMERIC(10,2),
    unit               TEXT,
    is_checked         BOOLEAN DEFAULT false,
    ordered_at         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT now()
);

-- ── Chrome Extension Import Queue ─────────────────────────────
CREATE TABLE pending_imports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES auth.users(id),
    source_url   TEXT NOT NULL,
    raw_data     JSONB,  -- JSON-LD schema.org/Recipe data from extension
    status       TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'processed', 'failed'
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Row Level Security (RLS)
-- Users can only see their own household's data
-- ============================================================
ALTER TABLE households          ENABLE ROW LEVEL SECURITY;
ALTER TABLE household_members   ENABLE ROW LEVEL SECURITY;
ALTER TABLE pantry_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plans          ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plan_recipes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopping_list_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_imports     ENABLE ROW LEVEL SECURITY;

-- Helper: get the household_id for the current user
CREATE OR REPLACE FUNCTION my_household_id()
RETURNS UUID AS $$
    SELECT household_id FROM household_members WHERE user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER;

-- Pantry: users see only their household's items
CREATE POLICY "household pantry access" ON pantry_items
    USING (household_id = my_household_id());

-- Meal plans: users see only their household's plans
CREATE POLICY "household meal plan access" ON meal_plans
    USING (household_id = my_household_id());

CREATE POLICY "household meal plan recipes access" ON meal_plan_recipes
    USING (meal_plan_id IN (SELECT id FROM meal_plans WHERE household_id = my_household_id()));

-- Shopping list: users see only their household's list
CREATE POLICY "household shopping list access" ON shopping_list_items
    USING (household_id = my_household_id());

-- Pending imports: users see only their own
CREATE POLICY "own pending imports" ON pending_imports
    USING (user_id = auth.uid());

-- ingredient_types and ingredient_aliases are public (no RLS needed)
-- recipes are public if is_public = true, or owned by the user
CREATE POLICY "public or own recipes" ON recipes
    USING (is_public = true OR created_by = auth.uid());

-- ============================================================
-- Seed Data: Ingredient Types + Aliases
-- ============================================================
INSERT INTO ingredient_types (name, category) VALUES
-- Dairy
('Milk',           'Dairy'),
('Butter',         'Dairy'),
('Cheese',         'Dairy'),
('Cream',          'Dairy'),
('Yogurt',         'Dairy'),
('Sour Cream',     'Dairy'),
('Cream Cheese',   'Dairy'),
('Eggs',           'Dairy'),
-- Proteins
('Chicken',        'Protein'),
('Beef',           'Protein'),
('Pork',           'Protein'),
('Salmon',         'Protein'),
('Tuna',           'Protein'),
('Shrimp',         'Protein'),
('Tofu',           'Protein'),
('Bacon',          'Protein'),
('Sausage',        'Protein'),
-- Grains
('Pasta',          'Grain'),
('Rice',           'Grain'),
('Bread',          'Grain'),
('Flour',          'Grain'),
('Oats',           'Grain'),
('Breadcrumbs',    'Grain'),
('Tortillas',      'Grain'),
-- Vegetables
('Onion',          'Vegetable'),
('Garlic',         'Vegetable'),
('Tomato',         'Vegetable'),
('Spinach',        'Vegetable'),
('Broccoli',       'Vegetable'),
('Carrots',        'Vegetable'),
('Celery',         'Vegetable'),
('Bell Pepper',    'Vegetable'),
('Mushrooms',      'Vegetable'),
('Corn',           'Vegetable'),
('Potatoes',       'Vegetable'),
('Zucchini',       'Vegetable'),
('Kale',           'Vegetable'),
('Green Beans',    'Vegetable'),
('Peas',           'Vegetable'),
('Cucumber',       'Vegetable'),
('Lettuce',        'Vegetable'),
-- Fruits
('Lemon',          'Fruit'),
('Lime',           'Fruit'),
('Apple',          'Fruit'),
('Banana',         'Fruit'),
('Avocado',        'Fruit'),
('Tomatoes',       'Fruit'),
-- Legumes
('Black Beans',    'Legume'),
('Chickpeas',      'Legume'),
('Lentils',        'Legume'),
('Kidney Beans',   'Legume'),
-- Oils & Fats
('Olive Oil',      'Oil'),
('Vegetable Oil',  'Oil'),
('Coconut Oil',    'Oil'),
-- Sauces & Condiments
('Soy Sauce',      'Condiment'),
('Hot Sauce',      'Condiment'),
('Ketchup',        'Condiment'),
('Mustard',        'Condiment'),
('Mayonnaise',     'Condiment'),
('Vinegar',        'Condiment'),
('Worcestershire Sauce', 'Condiment'),
('Tomato Sauce',   'Condiment'),
('Salsa',          'Condiment'),
-- Broths & Stocks
('Chicken Broth',  'Broth'),
('Beef Broth',     'Broth'),
('Vegetable Broth','Broth'),
-- Spices & Herbs
('Salt',           'Spice'),
('Black Pepper',   'Spice'),
('Cumin',          'Spice'),
('Paprika',        'Spice'),
('Chili Powder',   'Spice'),
('Garlic Powder',  'Spice'),
('Onion Powder',   'Spice'),
('Oregano',        'Spice'),
('Basil',          'Spice'),
('Thyme',          'Spice'),
('Rosemary',       'Spice'),
('Cinnamon',       'Spice'),
('Turmeric',       'Spice'),
('Ginger',         'Spice'),
('Cayenne',        'Spice'),
-- Sweeteners & Baking
('Sugar',          'Baking'),
('Brown Sugar',    'Baking'),
('Honey',          'Baking'),
('Maple Syrup',    'Baking'),
('Baking Soda',    'Baking'),
('Baking Powder',  'Baking'),
('Vanilla Extract','Baking'),
('Cocoa Powder',   'Baking'),
('Chocolate',      'Baking'),
-- Nuts & Seeds
('Almonds',        'Nut'),
('Walnuts',        'Nut'),
('Peanuts',        'Nut'),
('Peanut Butter',  'Nut'),
('Sesame Seeds',   'Nut');

-- Milk aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Whole Milk'),
    ('2% Milk'),
    ('Skim Milk'),
    ('1% Milk'),
    ('Goat Milk'),
    ('Sheep Milk'),
    ('Oat Milk'),
    ('Almond Milk'),
    ('Soy Milk'),
    ('Coconut Milk'),
    ('Cashew Milk'),
    ('Rice Milk'),
    ('Half and Half'),
    ('Heavy Cream'),
    ('Evaporated Milk'),
    ('Condensed Milk')
) AS aliases(alias)
WHERE ingredient_types.name = 'Milk';

-- Butter aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Salted Butter'),
    ('Unsalted Butter'),
    ('Vegan Butter'),
    ('Ghee'),
    ('Clarified Butter')
) AS aliases(alias)
WHERE ingredient_types.name = 'Butter';

-- Cheese aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Cheddar'),
    ('Cheddar Cheese'),
    ('Mozzarella'),
    ('Mozzarella Cheese'),
    ('Parmesan'),
    ('Parmesan Cheese'),
    ('Parmigiano-Reggiano'),
    ('Feta'),
    ('Feta Cheese'),
    ('Goat Cheese'),
    ('Brie'),
    ('Swiss Cheese'),
    ('Gouda'),
    ('Ricotta'),
    ('Cottage Cheese'),
    ('Monterey Jack'),
    ('Pepper Jack'),
    ('Colby Jack'),
    ('Provolone'),
    ('Gruyere'),
    ('Cream Cheese'),
    ('Velveeta'),
    ('American Cheese')
) AS aliases(alias)
WHERE ingredient_types.name = 'Cheese';

-- Pasta aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Spaghetti'),
    ('Penne'),
    ('Linguine'),
    ('Fettuccine'),
    ('Rigatoni'),
    ('Fusilli'),
    ('Farfalle'),
    ('Gluten Free Pasta'),
    ('Whole Wheat Pasta'),
    ('Orzo'),
    ('Rotini'),
    ('Lasagna Noodles'),
    ('Angel Hair'),
    ('Egg Noodles')
) AS aliases(alias)
WHERE ingredient_types.name = 'Pasta';

-- Rice aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('White Rice'),
    ('Brown Rice'),
    ('Jasmine Rice'),
    ('Basmati Rice'),
    ('Wild Rice'),
    ('Arborio Rice'),
    ('Long Grain Rice'),
    ('Short Grain Rice')
) AS aliases(alias)
WHERE ingredient_types.name = 'Rice';

-- Chicken aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Chicken Breast'),
    ('Chicken Thighs'),
    ('Chicken Legs'),
    ('Chicken Wings'),
    ('Whole Chicken'),
    ('Rotisserie Chicken'),
    ('Ground Chicken'),
    ('Chicken Tenders'),
    ('Chicken Drumsticks')
) AS aliases(alias)
WHERE ingredient_types.name = 'Chicken';

-- Beef aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Ground Beef'),
    ('Hamburger'),
    ('Hamburger Meat'),
    ('Steak'),
    ('Ribeye'),
    ('Sirloin'),
    ('Chuck Roast'),
    ('Brisket'),
    ('Ground Chuck'),
    ('Beef Chuck'),
    ('Flank Steak'),
    ('Skirt Steak'),
    ('Short Ribs')
) AS aliases(alias)
WHERE ingredient_types.name = 'Beef';

-- Olive Oil aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Extra Virgin Olive Oil'),
    ('EVOO'),
    ('Light Olive Oil')
) AS aliases(alias)
WHERE ingredient_types.name = 'Olive Oil';

-- Chickpeas aliases
INSERT INTO ingredient_aliases (alias, ingredient_type_id)
SELECT alias, id FROM ingredient_types, (VALUES
    ('Garbanzo Beans'),
    ('Garbanzo')
) AS aliases(alias)
WHERE ingredient_types.name = 'Chickpeas';
