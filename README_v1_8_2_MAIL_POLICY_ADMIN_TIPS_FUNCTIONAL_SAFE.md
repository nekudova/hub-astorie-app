# HUB ASTORIE APP v1.8.2 – MAIL POLICY + ADMIN TIPS FUNCTIONAL SAFE

Bezpečná provozní verze pro opravu mailového modulu a správu TIPů.

## Změny
- Opraveno načítání pravidel mailového modulu podle sekcí.
- Pravidla se nyní garantovaně vytvoří ve `hub_email_policy` i v případě, že historické tabulky sekcí mají jinou strukturu.
- Opravena administrace pravidel v `/admin/email` – formuláře v tabulce jsou funkční a ukládají změny.
- Doplněny admin akce u TIPů:
  - Archivovat TIP
  - Smazat TIP
- Smazání TIPu je pouze ruční akce administrátora a vyžaduje potvrzení.
- Archivace nemaže data.

## Co se nemění
- SMTP nastavení
- odesílání přes Brevo
- partneři
- kontakty
- odkazy
- produkty
- sazby
- výpovědi
- přihlášení
- oprávnění
- produkční čtení dat

## Ověření po nasazení
1. `/api/release-1-8-2/status`
2. Zkontrolovat `policy_count` – musí být větší než 0.
3. `/admin/email` – v tabulce musí být sekce a musí jít uložit změna.
4. `/admin/tips` – u TIPů musí být akce Detail / Archiv / Smazat.
5. Založit testovací TIP a ověřit e-mailové logy.
