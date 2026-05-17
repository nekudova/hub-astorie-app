# HUB ASTORIE APP v1.3.3 – Emergency Rollback Safe

Tato verze řeší stav, kdy po nasazení v1.3.2 fungovala jen sekce Partneři a ostatní poradenské sekce hlásily interní chybu.

## Co se změnilo
- Vráceno stabilní jádro z v1.2.6.
- Přímé routy v `app/main.py` se registrují před `admin_ui.py`, takže obejdou rozbité nové routy.
- Přidán nouzový bridge pro `/hub/my-tips` a `/hub/contacts`.
- Zachovány původní bridge pro `/hub/new-tip`, `/hub/calculators`, `/hub/forms`, `/hub/stats`, `/hub/help`.

## Co se nemění
- Databáze se nemění.
- Importy se nemění.
- Partneři se nemění.

## Kontrola po deployi
Otevřít: `/api/release-1-3-3/status`
