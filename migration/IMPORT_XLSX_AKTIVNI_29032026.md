# Import skutečného souboru Aktivní_29032026_ASTORIE HUB.xlsx

Verze v1.2.5 umí nahrát přímo XLSX export ze stávajícího Google Sheetu.

## Důležité

- Původní Google Sheet se nemění.
- Výchozí režim je bezpečný: existující číselníkové záznamy v nové DB se nepřepisují.
- TIPy se importují jako nové záznamy, aby bylo možné testovat workflow bez rizika ztráty historických dat.

## Postup

1. Nasaďte ZIP v1.2.5.
2. Otevřete `/admin/import/hub-xlsx`.
3. Nahrajte soubor `Aktivní_29032026_ASTORIE HUB.xlsx`.
4. Nechte nezaškrtnuté „Aktualizovat existující číselníkové záznamy“ pro první test.
5. Po importu ověřte:
   - `/admin/tips`
   - `/hub/my-tips`
   - `/admin/partners`
   - `/hub/partners`
   - `/hub/new-tip`

## Očekávané listy

Poradci, Sekce, Podsekce, Specialisté, Import_Partners, Vypovedi_Pojistovny, Import_Partner_Contacts,
Import_Partner_Links, Import_Online kalkulacky_Links, Import_Astorie_Links, Import_Products, Provize_TIPHub, Tipy.
