# HUB ASTORIE APP v1.4.4 – Admin Sazebník DB Core SAFE

Tato verze přidává administraci Sazebníku provizí a nastavuje databázi jako jediný ostrý zdroj pro poradenský sazebník.

## Změněno
- Admin menu: nová sekce `Sazebník provizí`.
- DB kontrola struktury `commission_rates` přes bezpečné `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- Přehled sazeb v adminu: Sekce, Oblast, Partner, Produkt, Základ, Provize, Stav.
- Ruční přidání sazby.
- Editace sazby.
- Aktivní / neaktivní sazba.
- Audit změn do `audit_log`.
- Kontrolní endpoint `/api/release-1-4-4/status`.

## Nezměněno
- Nový TIP
- Moje TIPy
- Partneři
- Kontakty
- Specialisté
- Login
- Datový model TIPů

## Důležité
Google Sheets už nemá být ostrý runtime zdroj pro sazebník. Slouží pouze jako importní podklad přes existující XLSX import.
