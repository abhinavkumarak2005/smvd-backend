-- ─── Supabase Auth → users table sync trigger ────────────────────────────────
-- Run this in Supabase SQL Editor (once, in your production project).
-- This creates a trigger on auth.users that automatically inserts a row
-- into your public users table whenever a new auth user is created.

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, phone, role, is_active)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    NEW.phone,
    'devotee',   -- default role; change to 'admin' or 'super_admin' manually after creation
    true
  )
  ON CONFLICT (id) DO NOTHING;  -- safe to re-run if user already exists
  RETURN NEW;
END;
$$;

-- Attach trigger to auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();

-- ─── Also backfill your 2 existing auth users into the users table ──────────
-- This inserts the 2 users that already exist in auth.users but aren't in public.users
INSERT INTO public.users (id, email, full_name, phone, role, is_active)
SELECT
  id,
  email,
  COALESCE(raw_user_meta_data->>'full_name', split_part(email, '@', 1)),
  phone,
  'devotee',
  true
FROM auth.users
ON CONFLICT (id) DO NOTHING;
