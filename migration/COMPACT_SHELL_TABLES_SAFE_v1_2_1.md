# HUB ASTORIE APP – v1.3.0 Compact Shell Tables Safe

## Co tato verze řeší
- Schová širokou petrolejovou hero hlavičku na pravé straně uživatelského HUBu.
- Nechává identitu v levém menu.
- Nechává kompaktní hlavičky jednotlivých sekcí, zejména sekci Partneři.
- Nepřepisuje funkční šablony jednotlivých sekcí.
- Přidává bezpečný fulltext nad dlouhé tabulky, například Sazebník provizí.

## Co se nemění
- DB,
- import,
- TIP workflow,
- specialisté,
- partner workflow,
- admin workflow,
- e-mail workflow,
- konkrétní šablony Kalkulačky, Nový TIP, Moje TIPy, Kontakty, Formuláře.

## Ověření po nasazení
1. `/version`
2. `/api/compact-shell-tables/status`
3. `/hub/partners?selected=KOOP&tab=contacts`
4. `/hub/calculators` – ověřit, že nahoře není široká hero hlavička a Sazebník má fulltext
5. `/hub/new-tip` – ověřit, že nahoře není široká hero hlavička a funkce zůstaly
6. `/hub/forms`
7. `/hub/contacts`

## Poznámka
Pokud se v Nový TIP stále negenerují všechny sekce/podsekce nebo specialisté, je to backend/datový problém route/API, nikoliv vizuální shell. Tato verze záměrně backend nemění.
