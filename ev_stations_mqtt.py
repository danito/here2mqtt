import os
import time
import json
import requests
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
HERE_API_KEY = os.getenv("HERE_API_KEY")
LAT = os.getenv("LAT")
LON = os.getenv("LON")
RADIUS = os.getenv("RADIUS")

# Intervalle de mise à jour : 5 minutes (300 secondes)
UPDATE_INTERVAL = 300 

HERE_URL = f"https://ev-v2.cc.api.here.com/ev/stations.json?prox={LAT},{LON},{RADIUS}&connectortype=31&apiKey={HERE_API_KEY}"

# Configuration de l'appareil unique pour regrouper les capteurs
DEVICE_INFO = {
    "identifiers": ["here_ev_group_brussels"],
    "name": "Bornes de recharge HERE",
    "model": "EV Station Monitor",
    "manufacturer": "HERE Technologies"
}

def get_price(connector):
    """Extrait le prix de manière sécurisée si disponible."""
    try:
        details = connector.get("connectorDetails", {})
        pricing = details.get("pricing", [])
        if pricing:
            price_data = pricing[0].get("price", {})
            value = price_data.get("value")
            currency = price_data.get("currency", "EUR")
            if value is not None:
                return f"{round(float(value), 3)} {currency}/kWh"
    except Exception:
        pass
    return "Non spécifié"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connecté au broker MQTT avec succès.")
    else:
        print(f"Erreur de connexion MQTT, code : {rc}")

# Initialisation du client MQTT
client = mqtt.Client()
if os.getenv("MQTT_USER"):
    client.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWORD"))

client.on_connect = on_connect
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

def update_stations():
    try:
        print(f"Requête API HERE en cours... ({time.strftime('%H:%M:%S')})")
        response = requests.get(HERE_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        stations = data.get("evStations", {}).get("evStation", [])

        for station in stations:
            # Création d'un identifiant propre
            raw_id = station["id"]
            clean_id = "".join(e for e in raw_id if e.isalnum())
            
            name = station["name"]
            street = station["address"].get("street", "Rue inconnue")
            number = station["address"].get("streetNumber", "")
            address_short = f"{street} {number}".strip()
            
            # Analyse de la disponibilité et du prix
            connectors = station.get("connectors", {}).get("connector", [])
            available = 0
            price_attr = "Non spécifié"
            
            if connectors:
                first_conn = connectors[0]
                available = first_conn.get("chargingPoint", {}).get("numberOfAvailable", 0)
                price_attr = get_price(first_conn)

            # Définition des Topics MQTT
            base_topic = f"homeassistant/sensor/here_ev_{clean_id}"
            config_topic = f"{base_topic}/config"
            state_topic = f"{base_topic}/state"
            attr_topic = f"{base_topic}/attributes"

            # Payload de Configuration (Discovery)
            config_payload = {
                "name": f"{name} ({address_short})",
                "unique_id": f"sensor_here_ev_{clean_id}",
                "state_topic": state_topic,
                "unit_of_measurement": "libres",
                "json_attributes_topic": attr_topic,
                "icon": "mdi:ev-station",
                "device": DEVICE_INFO
            }
            
            # Payload des Attributs
            attr_payload = {
                "latitude": station["position"]["latitude"],
                "longitude": station["position"]["longitude"],
                "adresse_complete": station["address"]["unparsedAddress"],
                "prix": price_attr,
                "distance_metres": station.get("distance"),
                "derniere_maj_api": station["lastUpdateTimestamp"]
            }

            # Envois vers MQTT
            client.publish(config_topic, json.dumps(config_payload), retain=True)
            client.publish(state_topic, available)
            client.publish(attr_topic, json.dumps(attr_payload))

        print(f"Succès : {len(stations)} stations mises à jour.")

    except Exception as e:
        print(f"Erreur lors de la mise à jour : {e}")

# Boucle principale avec attente de 5 minutes
try:
    while True:
        update_stations()
        time.sleep(UPDATE_INTERVAL)
except KeyboardInterrupt:
    print("\nArrêt du script par l'utilisateur...")
    client.loop_stop()
    client.disconnect()
