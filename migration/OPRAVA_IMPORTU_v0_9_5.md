# HUB ASTORIE – oprava importu v0.9.9

## Opravená chyba

Chyba:
`psycopg2.errors.InFailedSqlTransaction: current transaction is aborted`

Vznikala tak, že před vytvořením indexu na tabulce `specialists` spadl některý předchozí SQL příkaz.
PostgreSQL pak zablokoval všechny další příkazy v rámci stejné transakce.

## Oprava

- Každý přípravný SQL blok má samostatný `commit` / `rollback`.
- Před indexem se bezpečně doplňují chybějící sloupce tabulky `specialists`.
- Importní struktury se připravují robustně i nad dříve založenou databází.
- Původní Google Sheet se nemění.

## Postup po nasazení

1. Nasadit ZIP `v0.9.9`.
2. Na Renderu zvolit `Clear build cache & deploy`.
3. Ověřit `/version` = `0.9.9-import-schema-canonical-fix`.
4. Ověřit `/api/admin/summary`.
5. Otevřít `/admin/import/hub-xlsx`.
6. Nahrát XLSX.
7. První import spustit bez zaškrtnutí aktualizace existujících záznamů.
