# HUB ASTORIE APP v1.3.6 – New TIP Visual Correction SAFE

Bezpečný opravný balíček po v1.3.5.

## Změněno
- pouze `app/templates/hub_new_tip.html` – vizuál sekce Nový TIP podle schváleného návrhu;
- `app/main.py` – číslo verze;
- `app/routers/admin_ui.py` – pouze kontrolní endpoint `/api/release-1-3-6/status`.

## Nemění se
- databáze;
- API logika TIPů;
- routy;
- Partneři;
- Kalkulačky/Sazebník;
- Moje TIPy;
- Administrace;
- Specialisté/Sekce/Podsekce v backendu.

## Kontrola po deployi
1. `/api/release-1-3-6/status`
2. `/hub/new-tip` – výběr oblasti, podsekce, specialisty a zadání TIPu
3. `/hub/my-tips`
4. `/hub/partners`
5. `/hub/calculators`
