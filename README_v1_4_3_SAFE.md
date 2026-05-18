# v1.4.3 Rates Column Mapping SAFE

Izolovaná oprava pouze pro sekci Kalkulačky / Sazebník provizí.

## Změny
- Sloupce v sazebníku jsou nyní: Sekce, Oblast, Partner, Produkt, Základ, Provize.
- Produkt = importní sloupec `Druh obchodu`.
- Základ = importní sloupec `Typ_obchodu`.
- Provize = importní sloupec `Sazba_provize_%`.
- Nemění databázi.
- Nemění Nový TIP, Moje TIPy, Partnery ani Admin TIPů.

Kontrola po deployi: `/api/release-1-4-3/status`.
