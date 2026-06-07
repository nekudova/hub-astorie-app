# HUB ASTORIE APP v1.8.1 – MAIL POLICY SECTIONS FUNCTIONAL SAFE

Bezpečný hotfix mailového modulu.

## Řeší
- Admin → E-maily / SMTP: pravidla podle sekcí už nejsou jen prázdná vizuální tabulka.
- Vytvoří chybějící řádky pravidel pro sekce z `hub_sections`, `sections`, existujících TIPů a bezpečného fallback seznamu.
- U každé sekce lze zapnout/vypnout kopii BO.

## Nemění
- SMTP nastavení
- data TIPů
- partnery
- kontakty
- odkazy
- produkty
- sazby
- přihlášení
- oprávnění

## Ověření
- `/api/release-1-8-1/status`
- `/admin/email`
