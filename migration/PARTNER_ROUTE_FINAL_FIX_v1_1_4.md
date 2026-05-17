# HUB ASTORIE APP – v1.2.0 Partner Route Final Fix

## Co opravuje
- `/hub/partners` už neskončí na `Interní chyba serveru`.
- Route vždy definuje `dashboard`, `partner_history`, `partner_requests`, `contacts`, `links`, `products`, `faqs`.
- Data se berou z admin tabulek: `partners`, `partner_contacts`, `partner_links`, `partner_products`, `partner_faq`.
- Pokud nastane chyba, stránka se načte v bezpečném režimu a nezpůsobí 500.

## Ověření
1. `/version`
2. `/api/partner-safe-route/status`
3. `/hub/partners`
4. `/hub/partners?selected=ALLIANZ&tab=contacts`
