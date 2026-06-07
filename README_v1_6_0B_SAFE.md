# HUB ASTORIE APP – v1.6.0B VERSION + EMAIL STATUS CLEANUP SAFE

Bezpečná mikroverze po zprovoznění SMTP/Brevo.

## Co mění
- sjednocuje verzi aplikace v UI na `v1.6.0B`,
- doplňuje `/api/version`,
- doplňuje `/api/release-1-6-0b/status`,
- zachovává kompatibilní `/api/release-1-6-0/status`,
- zpřehledňuje e-mailový status: aktuální SMTP konfigurace, poslední úspěch, poslední chyba, počty logů.

## Co nemění
- SMTP odesílací logiku,
- databázová business data,
- TIPy, Partnery, Kontakty, Odkazy, Produkty, Sazebník, Výpovědi, Importy, Login, Oprávnění.

## Kontrola po nasazení
- `/api/version`
- `/api/release-1-6-0b/status`
- `/admin/email` → testovací e-mail
