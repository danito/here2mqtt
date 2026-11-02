# here2mqtt

Polls the [HERE EV Charge Points API](https://developer.here.com/) every 5 minutes for charging stations around a location and publishes them to MQTT with Home Assistant discovery.

Each station becomes a sensor (number of free charging points), grouped under a single "Bornes de recharge HERE" device, with attributes for position, address, price and distance.

## Setup

```sh
pip install -r requirements.txt
cp .env.example .env   # then fill in your values
python3 ev_stations_mqtt.py
```

## Configuration (`.env`)

| Variable | Description |
|---|---|
| `MQTT_HOST`, `MQTT_PORT` | MQTT broker |
| `MQTT_USER`, `MQTT_PASSWORD` | Optional broker credentials |
| `HERE_API_KEY` | HERE API key |
| `LAT`, `LON` | Search centre |
| `RADIUS` | Search radius in metres |

## Run as a service

Edit the user and paths in `ev_stations.service`, then:

```sh
sudo cp ev_stations.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ev_stations.service
journalctl -u ev_stations.service -f
```
