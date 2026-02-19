-- Allow authenticated users to insert new households
CREATE POLICY "authenticated users can create households" ON households
    FOR INSERT TO authenticated
    WITH CHECK (true);

-- Allow users to view households they belong to
CREATE POLICY "members can view their household" ON households
    FOR SELECT TO authenticated
    USING (id = my_household_id());

-- Allow household owners/members to insert themselves into household_members
CREATE POLICY "authenticated users can join households" ON household_members
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Allow users to view their own membership rows
CREATE POLICY "users can view own memberships" ON household_members
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());
