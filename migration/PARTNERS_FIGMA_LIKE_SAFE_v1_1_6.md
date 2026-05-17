# HUB ASTORIE APP – v1.2.5 Partners Figma-like Safe

## Cíl
Přiblížit uživatelskou sekci Partneři odsouhlasenému vizuálu č. 2.

## Bezpečnost
- backend route zůstává postavená na bezpečné v1.2.5,
- import se nemění,
- databázové workflow se nemění,
- mění se hlavně template a CSS sekce `/hub/partners`,
- fallback proměnné zůstávají.

## Ověření
1. `/version`
2. `/api/partner-figma-ui/status`
3. `/hub/partners`
4. `/hub/partners?selected=ALLIANZ&tab=overview`
5. `/hub/partners?selected=ALLIANZ&tab=contacts`
