# HUB ASTORIE APP v1.8.0 – HUB MAIL ENGINE PROFESSIONAL SAFE

Bezpečná verze zaměřená na profesionální e-mailový modul.

## Co se mění
- Centrální mail engine pro odesílání šablon.
- Additivní tabulka `hub_email_policy` pro pravidla e-mailů podle sekcí.
- Admin → E-maily / SMTP: možnost zapnout/vypnout kopii BackOffice po založení TIPu pro každou sekci.
- Nový TIP respektuje e-mailovou politiku sekce.
- Výchozí bezpečné chování: poradce + specialista + BackOffice.
- Selhání e-mailu nesmí zrušit uložený TIP.

## Co se nemění
- SMTP konfigurace v Renderu.
- Data TIPů.
- Partneři, kontakty, odkazy, produkty, sazby, výpovědi.
- Přihlášení a oprávnění.

## Ověření
- `/api/release-1-8-0/status`
- `/admin/email`
- založit nový TIP a zkontrolovat e-mail poradci, specialistovi a volitelně BO podle nastavení sekce.
