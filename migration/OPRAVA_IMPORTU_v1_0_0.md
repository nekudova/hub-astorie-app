# HUB ASTORIE – v1.2.6 full-import-schema-fix

## Problém
Import padal proto, že produkční databáze vznikala postupně ve starších verzích.
Import už posílal data správně, ale tabulky `sections`, `subsections`, `partners` a další neměly všechny sloupce, které import používá.

Typická chyba:
`column "created_at" of relation "sections" does not exist`

## Oprava
Tato verze před importem sjednotí schéma přesně těch tabulek, do kterých XLSX import zapisuje:

- users
- sections
- subsections
- hub_sections
- hub_subsections
- specialists
- partners
- partner_contacts
- partner_links
- partner_products
- commission_rates
- tips
- audit_log

Doplní:
- id
- created_at
- updated_at
- chybějící business sloupce
- defaulty pro timestampy
- bezpečné indexy

## Postup po nasazení
1. Ověřit `/version`
2. Otevřít `/api/import/hub-xlsx/repair-database`
3. Otevřít `/api/admin/summary`
4. Spustit import na `/admin/import/hub-xlsx`
5. První import bez zaškrtnutí aktualizace existujících záznamů.
