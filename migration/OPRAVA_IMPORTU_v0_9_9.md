# HUB ASTORIE – v1.1.5 import-schema-canonical-fix

## Problém
Import už posílal `created_at` a `updated_at`, ale starší tabulky v produkční DB tyto sloupce vůbec neměly.

Z logu:
- `hub_sections.updated_at` neexistuje
- `hub_subsections.updated_at` neexistuje
- `partners.created_at` neexistuje

## Oprava
Tato verze sjednocuje schéma všech importovaných tabulek před importem:

- doplní `created_at`
- doplní `updated_at`
- nastaví default `NOW()`
- doplní chybějící importní sloupce pro:
  - hub_sections
  - hub_subsections
  - partners
  - partner_contacts
  - partner_links
  - partner_products
  - commission_rates
  - tips
- opraví transakce přes rollback/commit po jednotlivých DDL krocích
- import se před spuštěním pokusí schéma opravit automaticky

## Nový endpoint
`/api/import/hub-xlsx/repair-all`

## Postup
1. Nasadit ZIP.
2. Ověřit `/version` = `1.1.5-partner-advisor-ui-premium-compact`.
3. Otevřít `/api/import/hub-xlsx/repair-all`.
4. Otevřít `/api/admin/summary`.
5. Spustit import na `/admin/import/hub-xlsx`.
6. První import bez zaškrtnutí aktualizace existujících číselníků.
