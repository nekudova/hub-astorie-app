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


## v0.3.7 ARES Partner Registry

Přidáno:
- napojení na ARES podle IČO
- rozšíření číselníku partnerů o IČO, DIČ, datovou schránku, e-mail/podatelnu a adresu
- tlačítko ARES při zakládání partnera
- možnost aktualizovat detail partnera z ARES
- příprava dat pro formuláře a výpovědi pojistných smluv


## v0.3.8 Partner Registry UX

Přidáno / upraveno:
- Seznam partnerů jako hlavní full-width pracovní plocha.
- Formulář Nový partner je schovaný za tlačítkem.
- Fulltextové hledání partnerů podle kódu, názvu, IČO, DS, e-mailu, města a adresy.
- Detail partnera má návratové tlačítko nahoře.
- Rychlé akce z detailu: kontakty, odkazy, produkty, aktualizace z ARES.
- Kopírování partnera jako náhrada práce s řádky v Excelu.


## v0.3.9 Partner Edit + Forms Ready

Přidáno:
- Úprava partnera přímo v detailu.
- Aktivní/neaktivní stav partnera.
- JSON endpoint `/api/partners/{partner_code}/registry` pro budoucí formuláře a výpovědi.
- Blok „Připraveno pro formuláře“ v detailu partnera.


## v0.4.0 Partner Detail CRUD

Přidáno:
- Rychlé přidání kontaktu, odkazu a produktu přímo z detailu partnera.
- Inline editace kontaktů, odkazů a produktů.
- Kopírování řádků.
- Zapnutí/vypnutí záznamů bez mazání dat.
- Detail partnera se mění na hlavní pracovní prostor pro správu master dat.


## v0.4.1 Partner Search API + Form Data Bridge

Přidáno:
- `/api/partners/search?q=...` pro našeptávač partnerů.
- `/api/partners/{partner_code}/form-source` pro předvyplnění výpovědí a formulářů.
- Admin stránka „Napojení formulářů“.
- Detail partnera zobrazuje API zdroje připravené pro formuláře.

## v0.4.2 Výpovědi Core

Přidáno:
- Modul `/admin/terminations`.
- Výběr partnera přes našeptávač.
- Dotahování údajů partnera z číselníku.
- Náhled textu výpovědi.
- Tisk / uložení jako PDF přes prohlížeč.


## v0.4.3 Navigation & Module Structure

Přidáno:
- Rozšířené levé menu rozdělené na Přehled, TIP HUB, Číselníky, Dokumenty a Systém.
- Nová stránka `/admin/modules` – mapa modulů.
- Viditelné připravené položky pro budoucí migraci uživatelského TIP Hubu.
- Funkční moduly zůstávají zachovány.


## v0.4.4 Navigation Fix

Opraveno:
- Levé menu vráceno do jednotného firemního vizuálu.
- Funkční a připravené moduly jsou jasně oddělené.
- Připravené položky nevedou na chybové stránky, ale na mapu modulů.
- Vizuálně stabilizován sidebar, topbar a verze.

## v0.5.0 Smart Select + Fulltext Core

Přidáno:
- Společný JS základ `/static/hub-smart.js`.
- Našeptávač partnerů pro kontakty, odkazy, produkty a výpovědi.
- Rychlé filtrování tabulek.
- Ovládání našeptávače klávesnicí.
- Základ pro další datagrid workflow a náhradu práce v Google Sheets.

## v0.5.1 Partner Registry Engine

Přidáno: provozní metadata partnera, VIP a segmenty, onboarding/smlouva, auditní poznámka, filtry v seznamu partnerů a bezpečný upgrade DB.
