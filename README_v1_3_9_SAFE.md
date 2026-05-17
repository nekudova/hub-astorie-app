# HUB ASTORIE APP v1.3.9 – New TIP Business Fix SAFE

Rozsah změny je záměrně omezený na sekci Nový TIP a workflow založení TIPu.

## Opravy
- Specialisté se zobrazují až po výběru podsekce.
- Bez vybraného specialisty nelze TIP založit.
- Formulář hlídá povinné položky: klient, kontakt, identifikace, odhad potenciálu, smlouva č., popis případu.
- Karty specialistů jsou upravené blíže schválené šabloně.
- Interní kódy nejsou zobrazované uživateli v kartách sekcí/podsekcí.
- Při založení TIPu se zapíše systémová zpráva do historie TIPu.
- Pokud je nastavené SMTP, odešle se potvrzení poradci a notifikace specialistovi.
- Administrace obsahuje odkaz Správa TIPů.

## Bezpečnost
- Partneři, Kalkulačky/Sazebník, Kontakty, Formuláře a ostatní poradenské sekce nejsou měněné.
- Databáze se rozšiřuje pouze bezpečnými ALTER TABLE ADD COLUMN IF NOT EXISTS a CREATE TABLE IF NOT EXISTS pro historii TIPů.
