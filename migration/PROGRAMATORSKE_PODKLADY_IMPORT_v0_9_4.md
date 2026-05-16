# ASTORIE HUB – programátorské podklady pro import XLSX v0.9.5

## Cíl
Zprovoznit bezpečný import dat ze staženého Google Sheetu do nové PostgreSQL databáze aplikace HUB ASTORIE.

## Zásadní pravidlo
Import NESMÍ měnit původní Google Sheet. Pracuje pouze s nahraným XLSX souborem a zapisuje do nové databáze aplikace.

## Nové / opravené routy

### UI
- `GET /admin/import/hub-xlsx`
- `POST /admin/import/hub-xlsx`
- `GET /admin/import/hub-xlsx/` alias
- `POST /admin/import/hub-xlsx/` alias
- `GET /admin/import/xlsx` alias

### API
- `GET /api/admin/summary`
- `GET /api/import/hub-xlsx/expected-sheets`
- `POST /api/import/hub-xlsx`
- `GET /api/import/hub-xlsx/status`
- `GET /api/import/hub-xlsx/summary`

## UX importu
Stránka `/admin/import/hub-xlsx` obsahuje:
- upload XLSX
- bezpečný režim bez přepisu existujících záznamů
- volitelný checkbox pro aktualizaci existujících číselníků
- loader overlay po kliknutí na import
- deaktivaci tlačítka při odeslání formuláře
- výsledek importu po dokončení
- odkaz na kontrolní `/api/admin/summary`

## Kontrola po deploy
1. `/version` musí vrátit `0.9.5-import-transaction-fix`
2. `/api/admin/summary` musí vrátit JSON s `ok: true`
3. `/api/import/hub-xlsx/expected-sheets` musí vrátit seznam listů
4. `/admin/import/hub-xlsx` musí zobrazit formulář pro upload
5. Po kliknutí na import se musí zobrazit loader

## Bezpečnostní režim
Výchozí režim: `safe_insert_only`
- existující číselníkové záznamy nepřepisovat
- duplicity přeskočit
- nové záznamy vložit

Checkbox `update_existing=1`:
- použít až po prvním testovacím importu
- může aktualizovat existující číselníkové záznamy v nové DB
- stále nemění původní Google Sheet

## Důležitá poznámka
Tato verze je synchronní import. Pro velké soubory může import trvat. Loader uživateli jasně ukáže, že systém pracuje. Async import s progress barem je další fáze.
