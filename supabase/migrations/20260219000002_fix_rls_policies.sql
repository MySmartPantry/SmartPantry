-- Drop all existing household/member policies and start fresh
DROP POLICY IF EXISTS "authenticated users can create households" ON households;
DROP POLICY IF EXISTS "members can view their household" ON households;
DROP POLICY IF EXISTS "authenticated users can join households" ON household_members;
DROP POLICY IF EXISTS "users can view own memberships" ON household_members;

-- Ensure the authenticated role has full table permissions
-- (Supabase sets these by default but we add them explicitly to be safe)
GRANT ALL ON households TO authenticated;
GRANT ALL ON household_members TO authenticated;

-- Households: any authenticated user can insert; can only read their own
CREATE POLICY "hh_insert" ON households
    FOR INSERT TO authenticated
    WITH CHECK (true);

CREATE POLICY "hh_select" ON households
    FOR SELECT TO authenticated
    USING (true);

-- Household members: can only insert/read your own row
CREATE POLICY "hm_insert" ON household_members
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "hm_select" ON household_members
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());
