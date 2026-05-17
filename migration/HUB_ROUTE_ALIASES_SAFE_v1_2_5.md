# HUB ASTORIE APP – v1.3.0 Hub Route Aliases Safe

## Co opravuje
OpenAPI ukázalo, že aplikace obsahuje staré route:
- `/hub/calculators-old-v083`
- `/hub/forms-old-v083`
- `/hub/stats-old-v083`
- `/hub/help-old-v083`
- `/hub/new-tip-old-v085`

ale menu odkazuje na nové URL:
- `/hub/calculators`
- `/hub/forms`
- `/hub/stats`
- `/hub/help`
- `/hub/new-tip`

Proto vznikalo `{"detail":"Nenalezen"}`.

## Bezpečnost
- Nemění databázi.
- Nemaže staré route.
- Nesahá na sekci Partneři.
- Pouze přidává stabilní aliasy pro nové URL.

## Ověření
- `/api/release-1-2-5/status`
- `/hub/calculators`
- `/hub/forms`
- `/hub/stats`
- `/hub/help`
- `/hub/new-tip`
- `/hub/partners?selected=KOOP&tab=contacts`
