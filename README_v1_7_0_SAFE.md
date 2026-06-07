# HUB ASTORIE APP v1.7.0 – TIP WORKFLOW MAIL AUTOMATION SAFE

Bezpečná aditivní verze pro napojení e-mailů na reálné TIP workflow.

## Mění pouze
- e-mailové notifikace při založení TIPu,
- e-mailové notifikace při změně TIPu z BackOffice,
- e-mailové notifikace při aktualizaci TIPu specialistou,
- audit/logování e-mailů,
- release status endpoint.

## Nemění
- SMTP jádro,
- Render ENV,
- databázová data,
- partnery,
- kontakty,
- odkazy,
- produkty,
- sazby,
- výpovědi,
- oprávnění,
- importy,
- produkční čtení dat.

## Ověření po nasazení
- /api/release-1-7-0/status
- /admin/email – testovací e-mail
- /hub/new-tip – založit testovací TIP
- /hub/my-tips – ověřit uložení TIPu
- Brevo / Transactional / Logs – ověřit e-mailové notifikace

## Bezpečnost
Selhání e-mailu nikdy nesmí zablokovat uložení TIPu ani změnu stavu. Chyba se pouze zapíše do historie/e-mail logu.
