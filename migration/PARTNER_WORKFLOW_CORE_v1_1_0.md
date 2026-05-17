# HUB ASTORIE APP – v1.1.9 Partner Workflow Core

Přidáno:
- partner_change_requests
- partner_request_comments
- partner_audit_log
- partner_history
- partner_favorites
- administrace `/admin/partner-requests`
- odeslání požadavků z HUB partnerů do BO workflow
- e-mail BO a potvrzení poradci, pokud je SMTP nastavené
- bezpečný fallback: bez SMTP se požadavek uloží a workflow nespadne

Ověření po nasazení:
1. `/version` = `1.1.9-unified-hub-shell-safe`
2. `/api/partner-workflow/status`
3. `/admin/partner-requests`
4. test z `/hub/partners` přes Navrhnout doplnění / Nahlásit změnu.
