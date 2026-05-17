# HUB ASTORIE – v1.2.4 import-user-id-fix

## Opraveno
Import padal na:
`null value in column "id" of relation "users" violates not-null constraint`.

Příčina:
SQLAlchemy model má Python default `uuid.uuid4`, ale raw SQL `INSERT INTO users (...)` jej nepoužije. Starší PostgreSQL tabulka zároveň neměla serverový DEFAULT na `users.id`.

## Co verze opravuje
- XLSX upsert automaticky doplňuje UUID `id` pro hlavní UUID tabulky.
- Doplněn endpoint `/api/import/hub-xlsx/repair-users`, který nastaví `gen_random_uuid()` jako serverový default.
- Excel ID jako `501.0` se převádí na čisté `501`.
- Import po chybě provádí rollback, aby se nezablokovala další část importu.

## Postup
1. Nasadit v1.2.4.
2. Ověřit `/version`.
3. Otevřít `/api/import/hub-xlsx/repair-users`.
4. Otevřít `/api/import/hub-xlsx/repair-schema`.
5. Spustit import na `/admin/import/hub-xlsx`.
6. První import bez zaškrtnutí aktualizace existujících záznamů.
