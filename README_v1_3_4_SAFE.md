# HUB ASTORIE APP v1.3.4 SAFE

Tato verze vychází ze stabilní verze v1.2.2, kterou uživatel označil jako nejlepší funkční základ.

## Co je změněno
- `app/templates/hub_calculators.html` – profesionálnější zobrazení kalkulaček + fulltextové filtrování sazebníku přímo v tabulce.
- `app/main.py` – pouze číslo verze.
- `app/routers/admin_ui.py` – pouze kontrolní endpoint `/api/release-1-3-4/status`.

## Co se záměrně nemění
- databáze, migrace, importy, Partneři, TIPy, Moje TIPy, Sekce, Podsekce, Specialisté.

## Kontrola po nasazení
1. `/version`
2. `/api/release-1-3-4/status`
3. `/hub/new-tip`
4. `/hub/my-tips`
5. `/hub/calculators`
6. `/hub/partners`
7. `/admin/sections`
8. `/admin/specialists`
