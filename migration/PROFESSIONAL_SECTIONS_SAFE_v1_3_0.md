# HUB ASTORIE APP – v1.3.0 Professional Sections Safe

Tato verze nahrazuje nouzový redirect bridge za skutečné funkční stránky.

## Bezpečnost
- Nemění databázi.
- Nemění import.
- Sekce Partneři se nemění.
- Staré route `-old-v083` zůstávají jako záloha.
- Nové route `/hub/...` jsou skutečné stránky, ne redirect.

## Opravené sekce
- `/hub/calculators`: kompaktní kalkulačky + sazebník s fulltextem a filtry.
- `/hub/contacts`: skupiny kontaktů.
- `/hub/new-tip`: čisté sekce bez duplicit, podsekce, upozornění na specialisty.
- `/hub/help`: rozdělení ASTORIE / partnerské odkazy.
- `/hub/forms`: zachované formuláře s partnery.
- `/hub/stats`: základní provozní přehled.

## Ověření
- `/api/release-1-3-0/status`
- `/api/release-1-3-0/router-status`
- `/hub/calculators`
- `/hub/contacts`
- `/hub/new-tip`
- `/hub/help`
- `/hub/partners?selected=KOOP&tab=contacts`
