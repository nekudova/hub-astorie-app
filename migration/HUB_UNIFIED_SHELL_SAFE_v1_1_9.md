# HUB ASTORIE APP – v1.1.9 Unified HUB Shell Safe

## Smysl verze
Sjednocení uživatelského rozhraní HUBu bez zásahu do backendu:
- levé menu zůstává hlavním místem identity,
- velká pravá hero hlavička se v uživatelských sekcích skrývá,
- každá stránka má kompaktní stránkovou hlavičku,
- sekce Partneři zůstává funkčně navázaná na v1.1.8,
- kontakty a kalkulačky mají profesionálnější kompaktní rozložení,
- globální loading indikátor „Načítám data…“.

## Co verze nemění
- databázi,
- import,
- login,
- TIP workflow,
- partner workflow,
- admin workflow,
- e-mail workflow.

## Poznámka k interním kontaktům ASTORIE
Pokud se v `/hub/contacts` stále nezobrazí žádné kontakty, nejde o CSS ani layout, ale o backend datové napojení dané route na tabulku/list s interními kontakty. Tato verze připravuje UI pro proměnné `contacts` nebo `global_contacts`, ale nemění datový backend.

## Ověření
1. `/version`
2. `/api/hub-shell-unified/status`
3. `/hub/partners?selected=KOOP&tab=contacts`
4. `/hub/partners?selected=KOOP&tab=products`
5. `/hub/contacts`
6. `/hub/calculators`
7. `/hub/my-tips`
8. `/hub/new-tip`
