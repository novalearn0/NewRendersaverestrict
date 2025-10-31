# Gpt-save-restricted-

## New premium & admin features added
- `/status` (admin-only): shows uptime, users, premium count, python version.
- `/grantpremium <user_id> <days>` (admin-only): grant premium.
- `/revokepremium <user_id>` (admin-only): revoke premium.
- `/mypremium` (users): check your premium status and quota.

Database now stores `premium_until` datetime and `quota` per user. Use `db.set_quota(user_id, amount)` to set user quota.
