import re
from typing import Any

import requests


ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


def normalize_ico(ico: str) -> str:
    return re.sub(r"\D", "", ico or "")


def format_address(data: dict[str, Any]) -> dict[str, str]:
    adresa = data.get("sidlo") or data.get("adresaDorucovaci") or {}

    text = adresa.get("textovaAdresa") or ""
    street = ""
    city = ""
    zip_code = ""

    # ARES vrací různé kombinace polí podle typu subjektu.
    if adresa:
        street_parts = []
        if adresa.get("nazevUlice"):
            street_parts.append(str(adresa.get("nazevUlice")))
        if adresa.get("cisloDomovni"):
            house = str(adresa.get("cisloDomovni"))
            if adresa.get("cisloOrientacni"):
                house += "/" + str(adresa.get("cisloOrientacni"))
            street_parts.append(house)

        street = " ".join(street_parts).strip()
        city = str(adresa.get("nazevObce") or adresa.get("nazevMestskeCastiObvodu") or "")
        zip_code = str(adresa.get("psc") or "")

    return {
        "street": street,
        "city": city,
        "zip_code": zip_code,
        "address_full": text,
    }


def fetch_ares_subject(ico: str) -> dict[str, Any]:
    clean_ico = normalize_ico(ico)
    if not re.fullmatch(r"\d{8}", clean_ico):
        return {"ok": False, "error": "IČO musí mít přesně 8 číslic."}

    url = f"{ARES_BASE_URL}/{clean_ico}"

    try:
        response = requests.get(url, timeout=10)
    except Exception as exc:
        return {"ok": False, "error": f"ARES není dostupný: {exc}"}

    if response.status_code == 404:
        return {"ok": False, "error": "Subjekt nebyl v ARES nalezen."}

    if response.status_code >= 400:
        return {"ok": False, "error": f"ARES vrátil chybu HTTP {response.status_code}."}

    try:
        data = response.json()
    except Exception:
        return {"ok": False, "error": "ARES nevrátil platnou JSON odpověď."}

    address = format_address(data)

    # Datová schránka v ARES bývá v poli datovaSchranka nebo datoveSchranky podle verze odpovědi.
    data_box = ""
    if data.get("datovaSchranka"):
        data_box = str(data.get("datovaSchranka") or "")
    elif isinstance(data.get("datoveSchranky"), list) and data["datoveSchranky"]:
        first = data["datoveSchranky"][0] or {}
        data_box = str(first.get("idDatoveSchranky") or first.get("datovaSchranka") or "")

    legal_form = ""
    pf = data.get("pravniForma")
    if isinstance(pf, str):
        legal_form = pf
    elif isinstance(pf, dict):
        legal_form = str(pf.get("nazev") or pf.get("kod") or "")

    result = {
        "ok": True,
        "ico": clean_ico,
        "dic": str(data.get("dic") or ""),
        "name": str(data.get("obchodniJmeno") or data.get("nazev") or ""),
        "data_box": data_box,
        "legal_form": legal_form,
        "street": address["street"],
        "city": address["city"],
        "zip_code": address["zip_code"],
        "address_full": address["address_full"],
        "source": "ARES",
    }

    return result
