# HUB ASTORIE – v1.0.3 import-index-fix

## Opraveno
V předchozí verzi zůstala stará přímá tvorba indexu uvnitř importní funkce:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_specialists_import_key
ON specialists (advisor_id, section_code, subsection_code, email)
```

Pokud byl předtím v transakci jakýkoliv SQL problém, PostgreSQL import zablokoval chybou:

```text
current transaction is aborted, commands ignored until end of transaction block
```

## Co v1.0.3 mění
- Inline tvorba indexu uvnitř importní funkce je odstraněna.
- Struktura pro specialisty se opravuje před importem.
- Před importem se provádí rollback/čištění transakce.
- Pokud se index specialistů nepodaří vytvořit, import pokračuje dál bez pádu.
- Přidán diagnostický endpoint:
  - `/api/import/hub-xlsx/repair-schema`

## Postup
1. Nasadit v1.0.3.
2. Ověřit `/version`.
3. Otevřít `/api/import/hub-xlsx/repair-schema`.
4. Potom spustit import na `/admin/import/hub-xlsx`.
5. První import bez zaškrtnutí aktualizace existujících záznamů.
