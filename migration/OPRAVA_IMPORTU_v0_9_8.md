# HUB ASTORIE – v1.2.0 import-timestamps-fix

Oprava chyby:
`null value in column "created_at" of relation "users" violates not-null constraint`

Opraveno:
- INSERT do `users` posílá `created_at = NOW()` a `updated_at = NOW()`.
- Při UPDATE se nastaví `updated_at = NOW()`.
- Přidán endpoint `/api/import/hub-xlsx/repair-users-timestamps`.

Postup:
1. `/version` = `1.2.0-safe-rollback-visual-shell`
2. `/api/import/hub-xlsx/repair-users-timestamps`
3. `/api/import/hub-xlsx/repair-schema`
4. `/admin/import/hub-xlsx`
5. Import bez zaškrtnutí aktualizace existujících záznamů.
