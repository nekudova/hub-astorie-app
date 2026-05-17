# HUB ASTORIE APP – v1.1.7 Partners Workspace Pro Safe

## Co verze řeší
- odstranění dvojité HUB hlavičky v sekci Partneři,
- plnohodnotné fulltextové filtrování v seznamu partnerů,
- fulltext v kontaktech, produktech a odkazech,
- automatické rozdělení kontaktů na:
  - VIP / TOP kontakty,
  - osobní kontakty,
  - pobočky / hotline / metodika / servisní kontakty,
- abecední řazení kontaktů, produktů a odkazů v prohlížeči,
- seskupení produktů podle sekcí:
  - Auto,
  - Flotily,
  - Majetek,
  - Odpovědnost,
  - Podnikatel,
  - Život,
  - Cestování,
  - Ostatní,
- kompaktnější layout,
- zachování loading hlášky „Načítám data…“.

## Bezpečnost
- import XLSX se nemění,
- databáze se nemění,
- workflow požadavků se nemění,
- route zůstává bezpečně navázaná na v1.1.4,
- změny jsou převážně template/CSS/JS.

## Ověření po nasazení
1. `/version`
2. `/api/partners-workspace-pro/status`
3. `/hub/partners`
4. `/hub/partners?selected=KOOP&tab=contacts`
5. `/hub/partners?selected=KOOP&tab=products`
6. `/admin/partner-requests`
