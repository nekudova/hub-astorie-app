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


## v0.5.2 Audit & History Core

Přidáno:
- Auditní tabulka `audit_history`.
- Bezpečný audit helper, který nerozbije hlavní operaci.
- Stránka `/admin/audit-history`.
- Historie změn v detailu partnera.
- První auditování úprav partnera.


## v0.5.3 Advisors Fix + User Admin

Opraveno:
- Sekce Poradci / uživatelé je přepracovaná tak, aby nespadla kvůli rozdílům ve struktuře DB.

Přidáno:
- Založení poradce / uživatele.
- Inline úprava jména, e-mailu, telefonu, role a aktivity.
- Zapnutí/vypnutí uživatele.
- Reset PINu.
- Audit změn uživatele.
- Kompatibilní redirect `/admin/users` → `/admin/advisors`.

## v0.5.4 Specialisté Core

Přidáno:
- Správa specialistů.
- Jeden specialista může mít více odborností.
- Sekce, podsekce, region, role, IF/PS podíly.
- Dostupnost / důvod nedostupnosti.
- Aktivní/neaktivní specialista.
- API `/api/specialists/search` pro budoucí routing TIPů.
- Audit změn specialistů.


## v0.5.5 Routing & Taxonomy Core

Opraveno:
- Sekce/podsekce už nemají padat na interní chybu.
- `/admin/subsections` je bezpečně přesměrováno na `/admin/sections`.

Přidáno:
- Samostatná taxonomie `hub_sections` a `hub_subsections`.
- Zakládání sekcí včetně ikony a URL obrázku.
- Zakládání podsekcí navázaných na sekci.
- Specialisté vybírají sekci a podsekci z nabídky, nikoli ručním psaním.
- Můj profil specialisty pro vlastní správu dostupnosti.
- Routing API `/api/routing/specialists`.


## v0.5.6 Performance & Safe UX

Přidáno:
- Bezpečné výkonové indexy pro partnery, kontakty, odkazy, produkty, specialisty, taxonomii a audit.
- Endpoint `/admin/performance/upgrade` pro doplnění indexů bez mazání dat.
- Endpoint `/api/performance/status`.
- Sticky hlavičky tabulek.
- Loading stav tlačítek při ukládání.
- Meta `notranslate`, aby Google Translate méně zasahoval do adminu.
- Snížení těžkých výpisů na bezpečnější limity.

Poznámka:
- Verze nic nemaže a nemění existující business data.


## v0.6.0 Admin Productivity Pack

Větší vývojová verze zaměřená na rychlost práce administrace.

Přidáno:
- Modul Produktivita administrace.
- CSV export partnerů.
- CSV export specialistů.
- CSV export sekcí a podsekcí.
- Hromadná změna partnerů podle kódů.
- Duplikace partnera jako náhrada kopírování řádku v tabulce.
- Rychlý přístup k výkonovým indexům.
- Příprava na bulk operace pro kontakty, odkazy a produkty.

Poznámka:
- Verze je nedestruktivní: nemaže data, pouze přidává nástroje a endpointy.


## v0.8.5 User HUB Core

Větší vývojový krok – začátek reálné poradenské části HUBu.

Přidáno:
- Uživatelský portál `/hub`.
- Nový TIP `/hub/new-tip`.
- Moje TIPy `/hub/my-tips`.
- Kalkulačky `/hub/calculators`.
- Partneři `/hub/partners`.
- Kontakty `/hub/contacts`.
- Formuláře `/hub/forms`.
- Statistiky `/hub/stats`.
- Nápověda `/hub/help`.
- Samostatný firemní vizuál pro poradce.
- TIPy se ukládají do DB tabulky `tips`.
- Výběr sekce/podsekce/specialisty je napojený na taxonomii a specialisty.
- Partner detail zobrazuje kontakty, odkazy a produkty.

Poznámka:
- Přihlašování poradce je zatím vývojově fixované na testovací identitu. V další verzi se napojí na uživatele/session.


## v0.8.5 Specialist Profile & Sections Fix

Opraveno:
- V profilu specialisty jsou nově viditelné dostupné sekce HUBu.
- Profil specialisty už není prázdná slepá stránka, pokud ještě nemá založenou odbornost.
- Lze si přímo přidat odbornost do profilu specialisty.
- Výchozí sekce/podsekce lze bezpečně doplnit tlačítkem.
- Nový TIP automaticky doplní výchozí taxonomii, pokud je prázdná.

Přidáno:
- Výchozí sekce: Flotily, Majetek, Život, Podnikatelé, Penze, Úvěry, Obnova, Investice, Zlato, Zvíře.


## v0.8.5 Visible Sections Fix

Opraveno:
- Sekce jsou nově viditelné přímo v poradenské části `/hub/new-tip` jako dlaždice.
- Výchozí sekce se automaticky doplní při otevření Nového TIPu.
- Není nutné ručně čekat na profil specialisty, aby byly sekce vidět.
- Přidán kontrolní endpoint `/api/taxonomy/visible-sections`.

Přidáno:
- Dlaždice sekcí v Nový TIP.
- Chytré filtrování podsekcí podle vybrané sekce.
- Chytré filtrování specialistů podle sekce/podsekce.
