# HUB ASTORIE – oprava importu v1.2.2

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

1. Nasadit ZIP `v1.2.2`.
2. Na Renderu zvolit `Clear build cache & deploy`.
3. Ověřit `/version` = `1.2.2-admin-taxonomy-specialists-links-safe`.
4. Ověřit `/api/admin/summary`.
5. Otevřít `/admin/import/hub-xlsx`.
6. Nahrát XLSX.
7. První import spustit bez zaškrtnutí aktualizace existujících záznamů.
