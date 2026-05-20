# HUB ASTORIE APP v1.5.5a – LINK SOURCE + HELP + CRUD SAFE

Bezpečný patch nad stabilním základem v1.5.4 / v1.5.2.

## Cíl
- Oddělit produkční čtení odkazů:
  - `/hub/links` = pouze Odkazy ASTORIE.
  - `/hub/calculators` = pouze Online kalkulačky + Sazebník.
  - Detail partnera → záložka Odkazy = pouze odkazy daného partnera.
- Vytvořit samostatnou Nápovědu `/hub/help`.
- Doplnit základní bezpečné admin akce: archivace/smazání u odkazů, produktů, rolí kontaktů a archivace sekcí/podsekcí/partnera.

## Bezpečnost
- Žádný import.
- Žádný hromadný cleanup.
- Žádné mazání dat automaticky.
- Žádný zásah do TIPů, uživatelů, oprávnění, SMTP, výpovědí ani sazebníku.
- DB změna je pouze bezpečné doplnění metadat u `partner_links`, pokud sloupce chybí:
  - `source_type`
  - `is_archived`
  - `visibility`

## Source type logika
- `ASTORIE_LINK` – interní odkazy ASTORIE.
- `ONLINE_CALCULATOR` – online kalkulačky.
- `PARTNER_LINK` – odkazy konkrétních partnerů.

Pokud u starých dat `source_type` chybí, patch jej doplní fallback pravidlem bez mazání záznamů.

## Kontrola po deployi
Otevřít:
`/api/release-1-5-5a/status`

Pak zkontrolovat:
- `/hub/links`
- `/hub/help`
- `/hub/calculators`
- detail partnera → Odkazy
- Admin → Odkazy
- Admin → Produkty
