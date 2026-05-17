# v1.4.2 Specialist Badge + Rates Data Fix SAFE

Tento release opravuje dvě izolované oblasti:

1. **Nový TIP – karta specialisty**
   - před výběrem se zobrazuje stav `PŘIJÍMÁ TIPY` nebo `NEPŘIJÍMÁ TIPY`,
   - `DOPORUČENO` se zobrazí až po ručním výběru specialisty,
   - nepřijímající specialista zůstává zneaktivněný a nejde vybrat.

2. **Kalkulačky / Sazebník provizí**
   - opravena ztráta hodnot ve sloupcích Typ / Produkt / Sazba,
   - backend posílá explicitní aliasy pro zobrazení,
   - doplněn filtr Produkt,
   - limit načítání sazebníku zvýšen na 2000 položek.

Databáze se nemění.
