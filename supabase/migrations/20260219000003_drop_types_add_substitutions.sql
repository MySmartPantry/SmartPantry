-- Make pantry_items.ingredient_type_id optional — we're switching to name-based matching
ALTER TABLE pantry_items DROP CONSTRAINT IF EXISTS pantry_items_ingredient_type_id_fkey;
ALTER TABLE pantry_items ALTER COLUMN ingredient_type_id DROP NOT NULL;

-- Substitution pairs: user-defined "A is interchangeable with B"
-- household_id NULL = global/built-in; non-null = household-specific
CREATE TABLE ingredient_substitutions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES households(id) ON DELETE CASCADE,
    ingredient_a TEXT NOT NULL,
    ingredient_b TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(household_id, ingredient_a, ingredient_b)
);

GRANT ALL ON ingredient_substitutions TO authenticated;
ALTER TABLE ingredient_substitutions ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read all substitutions
CREATE POLICY "subs_select" ON ingredient_substitutions
    FOR SELECT TO authenticated USING (true);

-- Users can only insert substitutions for their own household
CREATE POLICY "subs_insert" ON ingredient_substitutions
    FOR INSERT TO authenticated
    WITH CHECK (
        household_id = (
            SELECT household_id FROM household_members
            WHERE user_id = auth.uid() LIMIT 1
        )
    );

-- Users can only delete their own household's substitutions
CREATE POLICY "subs_delete" ON ingredient_substitutions
    FOR DELETE TO authenticated
    USING (
        household_id = (
            SELECT household_id FROM household_members
            WHERE user_id = auth.uid() LIMIT 1
        )
    );
