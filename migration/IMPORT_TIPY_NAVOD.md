# HUB ASTORIE – import TIPů ze stávající aplikace

## Doporučený postup

1. Ve staré aplikaci nebo zdrojové Google tabulce vyexportujte TIPy do CSV.
2. V nové aplikaci otevřete `/admin/import/legacy-tips`.
3. Stáhněte vzor CSV.
4. Upravte export tak, aby měl doporučené sloupce.
5. Nejdříve spusťte náhled importu.
6. Pokud náhled sedí, spusťte ostrý import.
7. Ověřte data v:
   - `/admin/tips`
   - `/hub/my-tips`
   - `/hub/my-tips?tab=work`
   - `/hub/my-tips?tab=archive`

## Doporučené sloupce

ID; Klient; Kontakt klienta; RČ/IČO; Poradce; E-mail poradce; ID poradce; Specialista; E-mail specialista; Sekce; Podsekce; Stav; Smlouva; Potenciál; Poznámka; Datum

## Poznámka

Import v této verzi nepřepisuje existující záznamy. Přidává nové záznamy do nové databáze.
