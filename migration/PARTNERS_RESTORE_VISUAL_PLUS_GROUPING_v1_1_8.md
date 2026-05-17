# HUB ASTORIE APP – v1.2.2 Partners Restore Visual + Grouping

## Cíl opravy
Tato verze vrací vizuální koncept sekce Partneři zpět k původnímu workspace vzhledu z v1.2.2 a doplňuje pouze požadované funkční členění.

## Co verze opravuje
- Neodstraňuje uživatelskou hlavičku ani původní ovládací prvky.
- Zachovává původní vizuál partner detailu.
- Kontakty jsou rozdělené do rozklikávacích kategorií:
  - VIP / TOP kontakty – otevřeno automaticky,
  - Osobní kontakty,
  - Metodika,
  - Infolinky / podpora,
  - Ostatní.
- Produkty jsou seskupené podle sekcí:
  - Auto,
  - Flotily,
  - Majetek,
  - Odpovědnost,
  - Podnikatel,
  - Život,
  - Cestování,
  - Ostatní.
- Odkazy se řadí abecedně.
- Fulltext zůstává pro partnery, kontakty, produkty a odkazy.
- Sdílení partnera kopíruje aktuální URL nebo používá nativní sdílení prohlížeče.

## Co verze nemění
- import,
- databázi,
- routy TIPů,
- login,
- admin workflow,
- e-mail workflow,
- tabulky.

## Ověření
1. `/version`
2. `/api/partners-restore-visual/status`
3. `/hub/partners?selected=KOOP&tab=overview`
4. `/hub/partners?selected=KOOP&tab=contacts`
5. `/hub/partners?selected=KOOP&tab=products`
6. `/hub/partners?selected=KOOP&tab=links`
