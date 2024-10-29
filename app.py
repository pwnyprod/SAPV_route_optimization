from flask import Flask, render_template, jsonify
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import requests
import time
from datetime import datetime, timedelta

app = Flask(__name__)


class DeliveryProblem:
    def __init__(self):
        # Beispiel-Adressen für 2 Depots und 10 Kunden
        self.locations = [
            {
                "address": "Hauptstraße 1, 10115 Berlin",  # Depot 1
                "coordinates": None  # Wird durch Geocoding gefüllt
            },
            {
                "address": "Musterstraße 50, 10117 Berlin",  # Depot 2
                "coordinates": None
            },
            # Kunden
            {
                "address": "Friedrichstraße 100, 10117 Berlin",
                "coordinates": None
            },
            # ... weitere Kunden-Adressen ...
        ]

        # Zeitfenster für jeden Standort (Start, Ende) in Minuten seit 8:00
        self.time_windows = [
            (0, 480),  # Depot 1: 8:00-16:00
            (0, 480),  # Depot 2: 8:00-16:00
            (60, 120),  # Kunde 1: 9:00-10:00
            # ... weitere Zeitfenster ...
        ]

        self.service_times = [
            0,  # Depot 1
            0,  # Depot 2
            15,  # Kunde 1
            # ... weitere Service-Zeiten ...
        ]

    def geocode_addresses(self):
        """Wandelt alle Adressen in Koordinaten um."""
        for location in self.locations:
            if location["coordinates"] is None:
                # Hier würden Sie einen Geocoding-Service wie Google Maps, Nominatim, etc. verwenden
                # Beispiel mit Nominatim (OpenStreetMap):
                response = requests.get(
                    f"https://nominatim.openstreetmap.org/search",
                    params={
                        "q": location["address"],
                        "format": "json"
                    },
                    headers={"User-Agent": "YourApp/1.0"}
                )

                if response.status_code == 200 and response.json():
                    result = response.json()[0]
                    location["coordinates"] = (float(result["lat"]), float(result["lon"]))
                    # Wichtig: Rate-Limiting beachten
                    time.sleep(1)
                else:
                    raise ValueError(f"Konnte Adresse nicht geocodieren: {location['address']}")

    def get_distance_matrix(self):
        """Berechnet die Entfernungsmatrix zwischen allen Standorten mit echten Fahrzeiten."""
        if any(loc["coordinates"] is None for loc in self.locations):
            self.geocode_addresses()

        size = len(self.locations)
        matrix = np.zeros((size, size))

        for i in range(size):
            for j in range(size):
                if i != j:
                    # Hier würden Sie einen Routing-Service verwenden
                    # Beispiel mit OSRM (Open Source Routing Machine):
                    lat1, lon1 = self.locations[i]["coordinates"]
                    lat2, lon2 = self.locations[j]["coordinates"]

                    response = requests.get(
                        f"http://router.project-osrm.org/route/v1/driving/"
                        f"{lon1},{lat1};{lon2},{lat2}",
                        params={"overview": "false"}
                    )

                    if response.status_code == 200:
                        # Fahrtzeit in Sekunden zu Minuten umrechnen
                        duration = response.json()["routes"][0]["duration"] / 60
                        matrix[i][j] = int(duration)
                    else:
                        # Fallback auf Luftlinie wenn Routing-Service nicht verfügbar
                        matrix[i][j] = self._calculate_euclidean_distance(
                            self.locations[i]["coordinates"],
                            self.locations[j]["coordinates"]
                        )

                    # Rate-Limiting beachten
                    time.sleep(0.1)

        return matrix.astype(int)

    def _calculate_euclidean_distance(self, coord1, coord2):
        """Berechnet die Luftlinie zwischen zwei Koordinaten."""
        from math import radians, cos, sin, asin, sqrt

        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Haversine-Formel für Entfernungsberechnung auf der Erdkugel
        R = 6371  # Erdradius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = R * c

        # Geschätzte Fahrzeit: 2 Minuten pro Kilometer
        return int(km * 2)


def format_time(minutes):
    """Formatiert Minuten seit 8:00 in lesbare Uhrzeit."""
    base_time = datetime.strptime("8:00", "%H:%M")
    actual_time = base_time + timedelta(minutes=minutes)
    return actual_time.strftime("%H:%M")


@app.route('/optimize')
def optimize():
    # Routing-Logik wie zuvor, aber mit zusätzlichen Adressinformationen in der Ausgabe
    routes = solve_routing_problem()

    if routes:
        formatted_routes = []
        for route in routes:
            formatted_route = []
            for stop in route:
                formatted_stop = {
                    'address': problem.locations[stop['location']]['address'],
                    'coordinates': problem.locations[stop['location']]['coordinates'],
                    'arrival_time': format_time(stop['arrival_time']),
                    'departure_time': format_time(stop['departure_time'])
                }
                formatted_route.append(formatted_stop)
            formatted_routes.append(formatted_route)

        return jsonify({
            'success': True,
            'routes': formatted_routes
        })

    return jsonify({
        'success': False,
        'message': 'Keine Lösung gefunden'
    })


if __name__ == '__main__':
    app.run(debug=True)