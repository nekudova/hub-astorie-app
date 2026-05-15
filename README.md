# HUB ASTORIE APP – v0.3.0 ADMIN CORE

První administrační verze nového HUBu v Pythonu.

## Co obsahuje

- Firemní ASTORIE layout
- Admin dashboard
- Správa poradců
- Správa sekcí
- Správa podsekcí
- Správa partnerů
- Základ audit logu
- Safe PostgreSQL bootstrap
- API dokumentace `/docs`
- Kontrola běhu `/health`

## Důležité

Tato verze je první Admin Core. Uživatelský TIP workflow se zatím nepřepisuje.
Cílem je začít nahrazovat administraci v Google Sheets.


## v0.3.1 admin-route-fix

Opravný balíček pro ověření, že Render skutečně nasadil Admin Core.

Kontrolní URL:
- `/version`
- `/admin-test`
- `/admin`
- `/api/admin/summary`

Pokud `/version` nevrací `0.3.1-admin-route-fix`, Render neběží z této verze.


## v0.3.2 Import Admin

Přidán bezpečný CSV import:
- poradci / uživatelé
- sekce
- podsekce
- partneři

Nová URL:
- `/admin/import`

Kontrolní URL:
- `/version`


## v0.3.3 Contacts & Links

Nové administrační moduly:
- /admin/contacts
- /admin/links

Funkce:
- správa kontaktů partnerů
- správa odkazů partnerů
- PostgreSQL persistence
- připraveno pro napojení do poradenského HUBu


## v0.3.4 Partner Products

Oprava:
- `contact_models.py` používá správně `app.core.database.Base`.

Nové funkce:
- `/admin/products`
- detail partnera `/admin/partners/{partner_code}`
- správa produktů partnerů
- souhrn kontaktů, odkazů a produktů v detailu partnera


## v0.3.5 Import Partner Data

Přidáno:
- import kontaktů partnerů
- import odkazů partnerů
- import produktů partnerů
- automatické vytváření tabulek `partner_contacts`, `partner_links`, `partner_products`

Doporučené pořadí importu:
1. Sekce
2. Podsekce
3. Partneři
4. Kontakty partnerů
5. Odkazy partnerů
6. Produkty partnerů
7. Poradci


## v0.3.6 Data Admin UX

Přidáno:
- fulltextové hledání pro kontakty, odkazy a produkty
- našeptávač partnera přes datalist
- nové údaje kontaktu: druh kontaktu, územní platnost/region, VIP/TOP
- rychlé kopírování záznamu
- bezpečné doplnění sloupců do PostgreSQL bez mazání dat
