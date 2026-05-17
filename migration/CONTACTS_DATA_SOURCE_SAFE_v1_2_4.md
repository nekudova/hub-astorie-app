# v1.3.0 Contacts Data Source Safe

Oprava po kontrole statusu v1.2.3:
- v1.2.3 hlásila technical ok, ale global_contacts_count byl 0.
- v1.3.0 rozlišuje technical_ok a provozní ok.
- Kontakty ASTORIE umí číst i fallback z partner_links, pokud global_contacts není naplněná.
- Sekce Partneři zůstává beze změny.

Ověření:
- /api/release-1-2-4/status
- /hub/contacts
- /hub/calculators
- /hub/partners?selected=KOOP&tab=contacts
