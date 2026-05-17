# HUB ASTORIE APP – v1.2.0 Safe Rollback Visual Shell

## Důvod verze
Verze v1.1.9 přepsala některé konkrétní šablony uživatelských sekcí. To mohlo způsobit ztrátu funkčních prvků, například v Kalkulačkách nebo dalších sekcích.

Tato verze je opravná:
- vrací základ na stabilní v1.1.8,
- nepřepisuje funkční šablony jednotlivých sekcí,
- doplňuje pouze bezpečnou globální vizuální vrstvu,
- zachovává sekci Partneři z v1.1.8 včetně rozdělení kontaktů a produktů,
- nemění databázi, import ani workflow.

## Co se nemění
- DB struktura,
- import,
- TIP workflow,
- specialisté,
- admin,
- e-maily,
- partner workflow,
- původní šablony Kalkulaček, TIPů, Kontaktů a dalších sekcí.

## Co se mění
- číslo verze,
- přidán globální loader „Načítám data…“,
- jemně sjednocené radiusy, stíny a formulářové prvky,
- přidán kontrolní endpoint.

## Kontrola po nasazení
1. `/version`
2. `/api/safe-rollback-visual-shell/status`
3. `/hub/calculators` – zkontrolovat, že se vrátila i Kalkulačka provizí
4. `/hub/new-tip` – zkontrolovat načtení sekcí/podsekcí
5. `/hub/my-tips`
6. `/hub/partners?selected=KOOP&tab=contacts`
7. `/hub/partners?selected=KOOP&tab=products`

## Důležitá poznámka k TIPům
Pokud se v Novém TIPu negenerují všechny sekce/podsekce nebo se nenapojují specialisté, není to problém vizuální šablony, ale datového napojení route/API na tabulky:
- sections,
- subsections,
- specialists.

Tato verze to záměrně neopravuje destruktivně, aby nedošlo k dalšímu poškození funkčních částí. Pro opravu TIP workflow je potřeba samostatná bezpečná backend verze s diagnostikou API.
