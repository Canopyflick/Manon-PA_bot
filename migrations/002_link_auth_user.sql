-- Link Ben's existing Supabase Auth user (lovable-envars project) to the Manon account.
UPDATE manon_users
SET auth_user_id = 'fd49e0b9-d548-4a54-b6df-4ba9ff44869d'
WHERE user_id = 1875436366
  AND chat_id = 1875436366
  AND auth_user_id IS NULL;
