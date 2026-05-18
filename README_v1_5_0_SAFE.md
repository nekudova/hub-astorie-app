# HUB ASTORIE APP v1.5.0 – User Multi-role Permissions SAFE

Změněno pouze:
- Admin → Poradci / uživatelé
- Admin → Oprávnění menu

Doplněno:
- uživatel může mít více rolí současně: IF, PS, ADMIN, BO, VEDENI,
- oprávnění menu se řídí součtem povolených modulů pro role uživatele,
- opravené ukládání nového uživatele,
- opravené ukládání/reset hesla pro UUID i textové ID,
- přidána aditivní DB tabulka module_permissions.

Neměněno:
- Partneři
- Kontakty partnerů
- Role kontaktů
- Sazebník
- Výpovědi
- TIP workflow
- E-mail core

Kontrola po deployi:
/api/release-1-5-0/status
