-- Allow households to store their own Claude API key
ALTER TABLE households ADD COLUMN IF NOT EXISTS claude_api_key TEXT;

-- Allow recipe ingredients to store a raw name (for imported recipes)
-- ingredient_type_id becomes optional so we don't need a taxonomy match on import
ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE recipe_ingredients ALTER COLUMN ingredient_type_id DROP NOT NULL;

-- Allow household members to update their household (e.g. to save Claude API key)
CREATE POLICY hh_update ON households
    FOR UPDATE USING (id = my_household_id()) WITH CHECK (id = my_household_id());
