import os
import json
import requests
from datetime import datetime, timedelta

# 1. Cargamos las credenciales seguras de GitHub
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

HISTORIAL_FILE = 'history.json'
RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"

# Diccionario para traducir meses al español de forma simple
MESES = {
    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre"
}

def buscar_vuelos(origen, destino):
    """Busca el vuelo más barato ida y vuelta usando la API Air Scraper"""
    # Usamos la versión 2 de búsqueda que es la más estable para rutas fijas
    url = f"https://{RAPIDAPI_HOST}/api/v2/flights/searchFlights"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    # Definimos fechas de ejemplo automáticas para buscar (ej: dentro de 60 días)
    fecha_ida_dt = datetime.now() + timedelta(days=60)
    fecha_vuelta_dt = fecha_ida_dt + timedelta(days=12) # Viaje de 12 días
    
    fecha_ida_str = fecha_ida_dt.strftime('%Y-%m-%d')
    fecha_vuelta_str = fecha_vuelta_dt.strftime('%Y-%m-%d')

    # Obtenemos los meses en español para armar el mensaje descriptivo
    mes_texto = MESES[fecha_ida_dt.strftime('%m')]
    fechas_texto = f"{fecha_ida_dt.strftime('%d')} al {fecha_vuelta_dt.strftime('%d')} de {mes_texto}"

    # Parámetros requeridos por Air Scraper (Sky Scrapper)
    # Nota: Esta API requiere códigos de entidad internos de Skyscanner. 
    # Para Miami (MIA) el ID suele ser "MIA", para Buenos Aires "BUE", para Montevideo "MVD"
    querystring = {
        "originSkyId": origen,
        "destinationSkyId": destino,
        "date": fecha_ida_str,
        "returnDate": fecha_vuelta_str,
        "cabinClass": "economy",
        "adults": "1",
        "currency": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        # Procesamos la respuesta estándar de la API de Skyscanner
        if data.get('status') is True and 'data' in data:
            itinerarios = data['data'].get('itineraries', [])
            if itinerarios:
                # El primero siempre es el más barato debido al ordenamiento nativo
                vuelo_mas_barato = itinerarios[0]
                precio = int(vuelo_mas_barato['price']['raw'])
                return precio, fechas_texto
                
        return float('inf'), ""
    except Exception as e:
        print(f"Error consultando ruta {origen} -> {destino}: {e}")
        return float('inf'), ""

def clasificar_precio(precio):
    """Aplica tus reglas de negocio exactas para catalogar los precios"""
    if precio < 300: return "💎 Error tarifario o precio extraordinario", "🔥 Precio excepcional."
    elif precio < 400: return "🔴 Súper oferta", "🔥 Precio increíble."
    elif precio < 500: return "🟡 Muy buena oferta", "Aprovechá este precio."
    elif precio < 650: return "🟢 Buena oferta", "Buen precio para considerar."
    return None, None

def enviar_telegram(texto):
    """Envía la alerta directo a tu Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": texto})

def main():
    print("Iniciando escaneo diario de tarifas en Air Scraper...")
    
    # Realizamos las búsquedas para ambos orígenes hacia Miami
    precio_mvd, fechas_mvd = buscar_vuelos("MVD", "MIA")
    precio_bue, fechas_bue = buscar_vuelos("BUE", "MIA")
    
    print(f"Resultados obtenidos -> MVD: USD {precio_mvd} | BUE: USD {precio_bue}")
    
    mejor_precio = min(precio_mvd, precio_bue)
    
    if mejor_precio == float('inf'):
        print("No se encontraron vuelos válidos en esta ejecución.")
        return
        
    if precio_bue < precio_mvd:
        origen_ganador = "Buenos Aires"
        fechas_ganadoras = fechas_bue
    else:
        origen_ganador = "Montevideo"
        fechas_ganadoras = fechas_mvd

    # Clasificamos la tarifa encontrada
    categoria, subtitulo = clasificar_precio(mejor_precio)
    
    if not categoria:
        print(f"Tarifa normal (USD {mejor_precio}). No se emite alerta.")
        return

    # Cargamos la memoria para evitar spam de alertas idénticas
    with open(HISTORIAL_FILE, 'r') as f:
        historial = json.load(f)
        
    if historial.get('ultimo_precio') == mejor_precio and historial.get('ultima_fecha') == fechas_ganadoras:
        print("Alerta repetida detectada. Omitiendo mensaje para cuidar el feed.")
        return

    # Construimos el formato exacto del mensaje que pediste
    mensaje = f"🚨 {categoria.upper()} DETECTADA\n\n"
    mensaje += f"✈️ {origen_ganador} → Miami\n"
    mensaje += f"💵 USD {mejor_precio}\n"
    mensaje += f"📅 {fechas_ganadoras}\n\n"
    mensaje += f"{subtitulo}"
    
    # Comparativa inteligente entre aeropuertos cercanos
    if origen_ganador == "Buenos Aires" and precio_mvd != float('inf'):
        ahorro = precio_mvd - precio_bue
        if ahorro > 0:
            mensaje += f"\n\n💡 Conviene salir desde Buenos Aires.\nAhorrás USD {ahorro}."

    # Enviamos la notificación
    enviar_telegram(mensaje)
    
    # Actualizamos el estado de memoria del JSON
    with open(HISTORIAL_FILE, 'w') as f:
        json.dump({"ultimo_precio": mejor_precio, "ultima_fecha": fechas_ganadoras}, f)
        
    print("¡Proceso completado con éxito!")

if __name__ == "__main__":
    main()
