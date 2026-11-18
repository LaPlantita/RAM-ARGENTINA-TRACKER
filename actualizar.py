import json
import re
import statistics
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9"
}

def obtener_dolar_blue():
    """Consulta cotización de venta desde dolarapi.com."""
    try:
        resp = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=10)
        if resp.status_code == 200:
            return float(resp.json().get("venta", 1400))
    except Exception as e:
        print(f"Error consultando dolarapi: {e}")
    return None

def clasificar_modulo_escritorio(titulo: str):
    """
    Devuelve 'ddr4_8gb', 'ddr5_8gb', 'ddr4_16gb' o 'ddr5_16gb' si es un módulo individual
    UDIMM de escritorio. Descarta kits (2x8, 2x16) y memorias de notebook (SODIMM).
    """
    t = titulo.lower()
    excluidos = ["2x8", "2 x 8", "2x16", "2 x 16", "2x32", "kit", "sodimm", "so-dimm", "notebook", "laptop", "ecc"]
    if any(palabra in t for palabra in excluidos):
        return None

    es_ddr4 = "ddr4" in t
    es_ddr5 = "ddr5" in t
    if not (es_ddr4 or es_ddr5):
        return None

    es_8gb = bool(re.search(r"\b8\s*gb\b", t))
    es_16gb = bool(re.search(r"\b16\s*gb\b", t))

    if es_ddr4 and es_8gb:
        return "ddr4_8gb"
    if es_ddr5 and es_8gb:
        return "ddr5_8gb"
    if es_ddr4 and es_16gb:
        return "ddr4_16gb"
    if es_ddr5 and es_16gb:
        return "ddr5_16gb"
    return None

def limpiar_precio(texto: str) -> int:
    solo_nums = re.sub(r"[^\d,]", "", texto).split(",")[0]
    return int(solo_nums) if solo_nums.isdigit() else 0

def scrapear_tiendas():
    urls = [
        "https://www.maximus.com.ar/Productos/Memorias-RAM/DDR4/maximus.aspx",
        "https://www.maximus.com.ar/Productos/Memorias-RAM/DDR5/maximus.aspx",
        "https://www.fullh4rd.com.ar/cat/c/18-memorias-ram",
        "https://www.gezatek.com.ar/tienda/memorias-ram/",
        "https://compragamer.com/productos?cate=15"
    ]
    recolectado = {"ddr4_8gb": [], "ddr5_8gb": [], "ddr4_16gb": [], "ddr5_16gb": []}
    rangos_validos = {
        "ddr4_8gb": (70000, 260000),
        "ddr5_8gb": (110000, 380000),
        "ddr4_16gb": (180000, 620000),
        "ddr5_16gb": (260000, 780000),
    }

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for card in soup.find_all(["div", "article", "li"], class_=re.compile(r"(product|item|card)", re.I)):
                texto = card.get_text(" ", strip=True)
                categoria = clasificar_modulo_escritorio(texto)
                if categoria:
                    match_precio = re.search(r"\$\s*([\d\.]{5,10})", texto)
                    if match_precio:
                        valor = limpiar_precio(match_precio.group(1))
                        min_p, max_p = rangos_validos[categoria]
                        if min_p <= valor <= max_p:
                            recolectado[categoria].append(valor)
        except Exception as e:
            print(f"Error en {url}: {e}")
    return recolectado

def main():
    with open("datos.json", "r", encoding="utf-8") as f:
        datos = json.load(f)

    dolar_hoy = obtener_dolar_blue()
    if dolar_hoy:
        datos["dolar_referencia"] = int(dolar_hoy)

    muestras = scrapear_tiendas()
    dolar = datos["dolar_referencia"]

    for cat in ["ddr4_8gb", "ddr5_8gb", "ddr4_16gb", "ddr5_16gb"]:
        valores = list(set(muestras[cat]))
        if valores:
            mediana = int(statistics.median(valores))
            datos["actual_promedio_ars"][cat] = mediana
            datos["historico"][f"ars_{cat}"][4] = mediana
            datos["historico"][f"usd_{cat}"][4] = round(mediana / dolar)

    datos["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d")

    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print("datos.json actualizado correctamente.")

if __name__ == "__main__":
    main()
