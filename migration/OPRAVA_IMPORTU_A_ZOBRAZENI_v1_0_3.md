# HUB ASTORIE – v1.1.3 import-cleanup-partner-ui

## Co tato verze řeší

1. Opakovaný import nahrál duplicitní záznamy.
   - Přidán endpoint `/api/import/hub-xlsx/cleanup-duplicates`.
   - Deduplikuje kontakty partnerů, odkazy, produkty, provizní sazby, globální kontakty a FAQ.

2. Sekce Kontakty v uživatelském HUBu zobrazovala kontakty partnerů.
   - Nově menu `Kontakty` zobrazuje pouze `Import_Astorie_Contacts`.
   - Kontakty partnerů zůstávají v detailu partnera na záložce `Kontakty`.

3. Partner detail nebyl kompletní.
   - Doplněna záložka FAQ.
   - Produkty jsou rozklikávací přes accordion.
   - Kontakty zobrazují více údajů: role, území/region, specifikace, poznámka, telefon, e-mail.

4. Poradce musí umět navrhnout změnu/doplnění.
   - Přidána tabulka `data_suggestions`.
   - V detailu partnera je tlačítko `+ Navrhnout doplnění`.
   - V každé záložce partnera je návrhové tlačítko.
   - U každého kontaktu je `Nahlásit změnu`.

## Postup po nasazení

1. Ověřit `/version`.
2. Otevřít `/api/import/hub-xlsx/repair-display-data`.
3. Otevřít `/api/import/hub-xlsx/cleanup-duplicates`.
4. Zkontrolovat `/hub/partners`.
5. Zkontrolovat `/hub/contacts`.
