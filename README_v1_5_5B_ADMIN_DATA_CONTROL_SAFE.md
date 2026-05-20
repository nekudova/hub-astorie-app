# HUB ASTORIE APP v1.5.5b – Admin Data Control CRUD SAFE

Bezpečná mikroverze navazující na v1.5.5a / stabilní v1.5.4.

## Účel
Doplnit v Adminu praktickou možnost ručně opravovat data bez importu a bez zásahu do produkčních modulů.

## Změněno pouze
- Admin → Kontakty: řádková editace, archivace, smazání.
- Admin → Role kontaktů: řádková editace, vypnutí/zapnutí, smazání.
- Admin → Odkazy: řádková editace, zdroj odkazu ASTORIE/Kalkulačka/Partner, archivace, smazání.
- Admin → Produkty: řádková editace, fulltext, archivace, smazání.
- Admin → Sekce / Podsekce: doplněna archivace jako bezpečná deaktivace.
- Admin → Partneři: rychlá změna stavu aktivní/pozastaveno/ukončeno a archivace.

## Výslovně beze změny
- produkční HUB routy a zobrazení pro poradce,
- TIPy,
- uživatelé,
- oprávnění,
- SMTP/e-maily,
- výpovědi,
- sazebník datově,
- importy,
- login.

## Bezpečnost
- Žádný automatický import.
- Žádné automatické mazání dat.
- Mazání probíhá pouze ruční akcí v Adminu po potvrzení.
- U kritické taxonomie Sekce/Podsekce je primárně použita archivace/deaktivace, ne hromadný destruktivní zásah.

## Kontrola po nasazení
Otevřít:
`/api/release-1-5-5b/status`
