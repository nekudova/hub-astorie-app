# HUB ASTORIE – v1.2.3 import-relationship-fix

## Opravená chyba

Import podsekcí padal na:

`null value in column "section_id" of relation "subsections" violates not-null constraint`

Příčina:
Excel a import pracují se `section_code`, ale databáze má u `subsections` povinný technický sloupec `section_id`.

## Oprava

- import podsekcí při INSERTu doplňuje `section_id` automaticky:
  `SELECT id FROM sections WHERE section_code = :section_code`
- existující podsekce bez `section_id` se opraví zpětně
- přidán preflight:
  `/api/import/hub-xlsx/preflight`
- přidána oprava vazeb:
  `/api/import/hub-xlsx/repair-relationships`

## Doporučený rychlý postup

1. Nasadit v1.2.3.
2. Otevřít `/api/import/hub-xlsx/repair-database`.
3. Otevřít `/api/import/hub-xlsx/repair-relationships`.
4. Otevřít `/api/import/hub-xlsx/preflight`.
5. Pokud `ok=true`, spustit import XLSX.
6. Pokud preflight vrátí issues, řešit je najednou podle seznamu.
