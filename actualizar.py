import json
import urllib.request
import re
from datetime import datetime

# Función para consultar cotización del dólar blue (Argentina)
def obtener_dolar_blue():
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return float(data.get('venta', 1200))
    except Exception:
        return 1200.0

# Función genérica para buscar precios usando motores de búsqueda filtrando por tiendas de computación (incluyendo Mexx y Venex)
def buscar_precio_web(query_base):
    precios = []
    # Sitios objetivo en Argentina incluyendo Mexx y Venex
    tiendas = [
        "mercadolibre.com.ar",
        "venex.com.ar",
        "mexx.com.ar",
        "compragamer.com",
        "fullh4rd.com.ar",
        "maximus.com.ar",
        "gezatek.com.ar"
    ]
    
    for tienda in tiendas:
        try:
            # Construimos la consulta acotada a la tienda
            query_completa = f"{query_base} site:{tienda}"
            url_busqueda = f"https://html.duckduckgo.com/html/?q={urllib.request.quote(query_completa)}"
            
            req = urllib.request.Request(
                url_busqueda, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Buscamos patrones de precios en ARS (ej: $ 410.000 o 410000)
                # Filtramos para evitar valores irrelevantes o de cuotas
                encontrados = re.findall(r'\$\s*([1-9]\d{1,2}(?:\.\d{3})+)', html)
                for p_str in encontrados:
                    p_limpio = float(p_str.replace('.', ''))
                    # Rango lógico para un módulo individual de RAM en Argentina (entre 80k y 900k ARS)
                    if 80000 <= p_limpio <= 900000:
                        precios.append(p_limpio)
        except Exception:
            continue
            
    if precios:
        # Retornamos el promedio de los precios válidos hallados en las tiendas
        return round(sum(precios) / len(precios), 2)
    return None

def actualizar_datos():
    hoy = datetime.now().strftime("%Y-%m-%d")
    dolar_blue = obtener_dolar_blue()
    
    print(f"[{hoy}] Consultando cotización Dólar Blue: ${dolar_blue}")
    
    # Consultas específicas para aislar módulos individuales (1x8GB y 1x16GB) evitando kits
    categorias = {
        "ddr4_8gb": "memoria ram 8gb ddr4 3200 udimm",
        "ddr5_8gb": "memoria ram 8gb ddr5 udimm",
        "ddr4_16gb": "memoria ram 16gb ddr4 3200 udimm",
        "ddr5_16gb": "memoria ram 16gb ddr5 udimm"
    }
    
    nuevos_precios = {}
    
    for cat, query in categorias.items():
        precio_hallado = buscar_precio_web(query)
        if precio_hallado:
            nuevos_precios[cat] = precio_hallado
            print(f" -> {cat}: ${precio_hallado} ARS")
        else:
            print(f" -> {cat}: No se pudo actualizar, manteniendo histórico reciente.")

    # Cargamos el archivo datos.json existente
    try:
        with open('datos.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {"historial": []}
        
    # Verificamos si ya existe una entrada para el día de hoy para actualizarla o agregar una nueva
    historial = data.get("historial", [])
    entrada_hoy = next((item for item in historial if item["fecha"] == hoy), None)
    
    if entrada_hoy:
        # Actualizamos con los nuevos datos frescos
        for cat in categorias:
            if cat in nuevos_precios:
                entrada_hoy[cat] = nuevos_precios[cat]
        entrada_hoy["dolar"] = dolar_blue
    else:
        # Creamos una nueva entrada diaria
        # Si alguna categoría falló hoy, heredamos el último valor conocido para evitar baches en el gráfico
        ultimo = historial[-1] if historial else {
            "ddr4_8gb": 145000, "ddr5_8gb": 220000, "ddr4_16gb": 410000, "ddr5_16gb": 480000
        }
        
        nueva_entrada = {
            "fecha": hoy,
            "ddr4_8gb": nuevos_precios.get("ddr4_8gb", ultimo.get("ddr4_8gb", 145000)),
            "ddr5_8gb": nuevos_precios.get("ddr5_8gb", ultimo.get("ddr5_8gb", 220000)),
            "ddr4_16gb": nuevos_precios.get("ddr4_16gb", ultimo.get("ddr4_16gb", 410000)),
            "ddr5_16gb": nuevos_precios.get("ddr5_16gb", ultimo.get("ddr5_16gb", 480000)),
            "dolar": dolar_blue
        }
        historial.append(nueva_entrada)
        
    data["historial"] = historial
    
    # Guardamos el archivo actualizado
    with open('datos.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print("¡datos.json actualizado con éxito incluyendo Mexx y Venex!")

if __name__ == "__main__":
    actualizar_datos()
