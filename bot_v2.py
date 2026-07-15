import os
import asyncio
import aiohttp
import aiosqlite
from datetime import datetime, timedelta

# 1. Configuración de variables (se cargan desde tu entorno)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"
DB_NAME = "vuelos_itinerario.db"

# 2. Configuración de la Base de Datos
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS historial 
                            (id INTEGER PRIMARY KEY, total_precio REAL, itinerario_fechas TEXT)''')
        await db.commit()

# 3. Función para buscar un tramo (la pieza fundamental del motor)
async def buscar_tramo(session, origen, destino, fecha):
    url = f"https://{RAPIDAPI_HOST}/api/v2/flights/searchFlights"
    params = {
        "originSkyId": origen,
        "destinationSkyId": destino,
        "date": fecha,
        "adults": "1",
        "currency": "USD",
        "cabinClass": "economy"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    
    try:
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            # Obtenemos el precio del primer vuelo (el más barato)
            if data.get('status') and 'data' in data and data['data'].get('itineraries'):
                return int(data['data']['itineraries'][0]['price']['raw'])
    except Exception as e:
        print(f"Error consultando {origen} -> {destino} en {fecha}: {e}")
    return float('inf') # Retorna infinito si no hay vuelos, para que la suma falle

# 4. Función principal que orquestará todo el viaje
async def main():
    await init_db()
    print("Bot inicializado. El motor de búsqueda está listo para ejecutarse.")
    
    # Aquí es donde pondremos la lógica de las fechas martes/miércoles
    # que definiremos en el siguiente paso.

if __name__ == "__main__":
    asyncio.run(main())

