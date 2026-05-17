# HUB ASTORIE – v1.1.2 uuid-relationship-fix

## Opravená chyba

`section_id` je v produkční databázi typu UUID.
Předchozí kontrola používala:

```sql
section_id = ''
```

To je u UUID neplatné a PostgreSQL vracel:

```text
invalid input syntax for type uuid: ""
```

## Oprava

- všechny kontroly `section_id = ''` byly odstraněny,
- používá se pouze `section_id IS NULL`,
- vazba se doplňuje podle:
  `subsections.section_code = sections.section_code`,
- přidán endpoint:
  `/api/import/hub-xlsx/repair-uuid-relationships`.

## Postup

1. `/version` = `1.1.2-partner-hotfix-safe-ui`
2. `/api/import/hub-xlsx/repair-database`
3. `/api/import/hub-xlsx/repair-uuid-relationships`
4. `/api/import/hub-xlsx/preflight`
5. import XLSX
