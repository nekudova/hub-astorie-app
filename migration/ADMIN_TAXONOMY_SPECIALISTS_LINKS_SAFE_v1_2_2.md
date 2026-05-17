# HUB ASTORIE APP – v1.2.3 Admin Taxonomy Specialists Links Safe

## Řešené problémy
1. Duplicitní zobrazení sekcí v Novém TIPu
   - Sekce se nemažou z databáze.
   - Pro poradce se při zobrazení provede bezpečná deduplikace podle názvu/aliasu.
   - Kontrola: `/api/admin/taxonomy-health`.

2. Specialisté
   - V adminu lze specialistu založit výběrem z existujících uživatelů.
   - Už není nutné ručně opisovat jméno/e-mail/telefon.
   - Ruční zadání zůstává dostupné jako pokročilá volba.

3. Sekce a podsekce
   - Existující sekce a podsekce lze upravovat přímo v tabulce.
   - Ukládá se název, aktivita, pořadí, poznámka, ikona a vazba podsekce na sekci.

4. Odkazy
   - Admin sekce Odkazy je rozdělena na:
     - interní odkazy ASTORIE,
     - partnerské odkazy.
   - Kontrola: `/api/admin/links-health`.

5. Kontakty ASTORIE
   - Neopravováno destruktivně. Pokud nejsou naimportované, lze je zadat ručně podle domluvy.

## Co se nemění
- Import XLSX.
- DB data se nemažou.
- Partner workspace.
- TIP workflow kromě bezpečné deduplikace sekcí pro zobrazení.
- E-maily.

## Ověření po nasazení
- `/version`
- `/api/release-1-2-2/status`
- `/api/admin/taxonomy-health`
- `/api/admin/links-health`
- `/admin/sections`
- `/admin/specialists`
- `/admin/links`
- `/hub/new-tip`
- `/hub/help`
