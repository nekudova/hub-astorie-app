# HUB ASTORIE APP v1.5.4 – EMERGENCY ROLLBACK SAFE

Nouzový rollback po chybě ve v1.5.3.

Základ: v1.5.2, poslední potvrzená funkční verze před zásahem do /admin/modules a /hub/stats.

Cíl:
- okamžitě obnovit běh aplikace,
- neprovádět žádné nové změny databáze,
- vrátit stabilní stav adminu a poradenských sekcí.

Poznámka:
- v1.5.3 se nesmí dále používat.
- Opravu /admin/modules a /hub/stats je nutné řešit až následně jako samostatný patch nad funkčním základem.
