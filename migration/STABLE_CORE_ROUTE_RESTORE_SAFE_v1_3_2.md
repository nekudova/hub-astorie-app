# HUB ASTORIE APP v1.3.2 – Stable Core Route Restore Safe

Tato verze je bezpečný stabilizační balíček po rozbití verze 1.3.0.

## Základ
- vychází z funkčního jádra v1.2.6, které obsahuje kompletní TIP routy, Moje TIPy, detail TIPu a specialistické TIPy,
- zachovává funkční sekci Partneři,
- zachovává Sazebník/Kalkulačku z v1.2.6 včetně fulltextového vyhledávání,
- nemění databázové modely, importy ani tabulky.

## Oprava
- odstraněny nouzové redirecty v main.py, které přepisovaly přímé HUB routy a vracely staré obrazovky,
- vráceno řízení rout do app/routers/admin_ui.py, kde jsou kompletní funkční šablony.

## Kontrolní URL po nasazení
- /version
- /api/release-1-3-2/status
- /hub/new-tip
- /hub/my-tips
- /hub/calculators
- /hub/partners
- /hub/contacts
- /hub/forms
- /hub/stats
- /hub/help
