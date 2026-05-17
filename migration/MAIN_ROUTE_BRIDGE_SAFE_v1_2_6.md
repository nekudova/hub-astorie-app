# HUB ASTORIE APP – v1.2.6 Main Route Bridge Safe

## Proč tato verze vznikla
Endpoint `/api/release-1-2-5/status` fungoval, ale `/hub/calculators` stále vracel `Nenalezen`.
To znamená, že routerový status byl načtený, ale veřejné HUB routy nebyly spolehlivě obsloužené.

## Co verze dělá
Přidává pevné aliasy přímo do `app/main.py` před `include_router(...)`.

Alias:
- `/hub/calculators` -> `/hub/calculators-old-v083`
- `/hub/forms` -> `/hub/forms-old-v083`
- `/hub/stats` -> `/hub/stats-old-v083`
- `/hub/help` -> `/hub/help-old-v083`
- `/hub/new-tip` -> `/hub/new-tip-old-v085`

## Co verze nedělá
- Nemění databázi.
- Nemění import.
- Nemění sekci Partneři.
- Nemaže žádné staré route.
- Nepřepisuje šablony.

## Ověření
1. `/api/release-1-2-6/status`
2. `/hub/calculators`
3. `/hub/forms`
4. `/hub/new-tip`
5. `/hub/partners?selected=KOOP&tab=contacts`
