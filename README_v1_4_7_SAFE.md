# HUB ASTORIE APP v1.4.7 – Výpovědi PDF Archive + Evidence SAFE

Izolovaná oprava modulu Výpovědi.

## Změněno
- Profesionální náhled výpovědi bez chybných znaků `\n`.
- Po vytvoření náhledu se dokument automaticky uloží do DB archivu.
- Přidána centrální evidence výpovědí v Adminu.
- Detail uložené výpovědi lze znovu otevřít a vytisknout / uložit jako PDF.
- Poradenská část zůstává dostupná v HUBu.

## DB změna
Pouze aditivní: vytvoří se tabulka `termination_documents`, pokud neexistuje.
Žádná stávající tabulka se nemaže ani nepřepisuje.

## Beze změny
Nový TIP, Moje TIPy, Partneři, Sazebník, Kontakty, Produkty, Odkazy.

## Kontrola po nasazení
/api/release-1-4-7/status
