# HUB ASTORIE APP – v1.1.5 Partner Advisor UI Premium Compact

## Co verze mění
Pouze uživatelskou sekci `/hub/partners` – UI/UX.

## Co verze nemění
- import XLSX,
- databázové tabulky,
- admin číselníky,
- workflow požadavků,
- e-mail workflow,
- TIP modul.

## Přidáno
- kompaktní premium layout podle schváleného vizuálu,
- menší písmo,
- kompaktní seznam partnerů,
- sticky detail partnera,
- menší decentní tlačítko `+ Návrh`,
- loading hláška vpravo dole `Načítám data…`,
- kompaktní taby,
- kontakty ve 2 sloupcích,
- produkty v accordionu,
- FAQ accordion,
- požadavky timeline,
- historie timeline,
- bezpečné fallbacky.

## Ověření po nasazení
1. `/version`
2. `/api/partner-advisor-ui/status`
3. `/hub/partners`
4. `/hub/partners?selected=ALLIANZ&tab=contacts`
5. `/hub/partners?selected=ALLIANZ&tab=products`
6. `/admin/partner-requests`
