# HUB ASTORIE APP – v0.2.4 CLEAN START

Čistý stabilizační balíček pro první deploy na Render.

## Důležité

Tato verze NEPOUŽÍVÁ:
- passlib
- bcrypt
- SQLAlchemy Mapped typování

Kontrolní endpointy:
- `/`
- `/health`
- `/api/admin/summary`
- `/docs`


## Hotfix v0.2.5

Endpoint `/api/admin/summary` je převedený na bezpečné PostgreSQL dotazy.
Nespadne ani v případě, že některá tabulka ještě chybí nebo má odlišné schéma.
