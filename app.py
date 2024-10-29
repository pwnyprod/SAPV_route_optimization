from flask import Flask, render_template, request, jsonify
import google.auth
from google.auth.transport.requests import Request
import requests
import json

app = Flask(__name__)

# Beispiel-Kundendaten (mit Adressen)
customers = [
    {"name": "Kunde 1", "address": "Adresse 1, Saarbrücken, Deutschland", "time_window_start": "09:00", "time_window_end": "10:00", "visit_duration": 1800},
    {"name": "Kunde 2", "address": "Adresse 2, Saarbrücken, Deutschland", "time_window_start": "11:00", "time_window_end": "12:00", "visit_duration": 1200},
]

# Mitarbeiter Start- und Endpunkte (mit Adressen)
employees = [
    {"name": "Mitarbeiter 1", "address": "Startpunkt 1, Saarbrücken, Deutschland"},
    {"name": "Mitarbeiter 2", "address": "Startpunkt 2, Saarbrücken, Deutschland"},
    {"name": "Mitarbeiter 3", "address": "Startpunkt 3, Saarbrücken, Deutschland"}
]

# Funktion, um Adressen in Längen- und Breitengrade umzuwandeln (Google Geocoding API)
def geocode_address(address):
    api_key = "AIzaSyCQsBRlgxruIcymhmMtJPjFCW9mS7uKhl0"  # Google Maps API-Schlüssel
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"

    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        if result['status'] == 'OK':
            location = result['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, f"Fehler: {result['status']}"
    else:
        return None, f"Fehler bei der Anfrage: {response.status_code}"

# Funktion, um die Route mit Zeitfenstern und Besuchsdauer zu optimieren
def optimize_route_with_time_windows():
    # Google Cloud Authentication
    credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

    if credentials.expired or not credentials.valid:
        credentials.refresh(Request())

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    url = f"https://cloudoptimization.googleapis.com/v1/projects/{project}/locations/global:optimizeTours"

    # Erstelle Fahrzeuge (Mitarbeiter) und Jobs (Kunden)
    vehicles = []
    for employee in employees:
        lat, lng = geocode_address(employee["address"])  # Adresse in lat/lng umwandeln
        vehicles.append({
            "start_time": "08:00",  # Startzeit des Arbeitstages
            "end_time": "18:00",    # Endzeit des Arbeitstages
            "start_location": {"lat": lat, "lng": lng},
            "end_location": {"lat": lat, "lng": lng}
        })

    jobs = []
    for customer in customers:
        lat, lng = geocode_address(customer["address"])  # Adresse in lat/lng umwandeln
        jobs.append({
            "location": {"lat": lat, "lng": lng},
            "time_windows": [{
                "start": customer["time_window_start"],
                "end": customer["time_window_end"]
            }],
            "visit_duration": f"{customer['visit_duration']}s"
        })

    # Erstelle das Model für die Optimierung
    body = {
        "model": {
            "vehicles": vehicles,
            "jobs": jobs
        }
    }

    # Sende die Anfrage an die Google Cloud Optimization API
    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        return response.json()  # Optimierte Route
    else:
        return None, f"Fehler bei der Optimierung: {response.status_code}, {response.text}"

@app.route('/')
def index():
    return render_template('index.html', customers=customers, employees=employees)

@app.route('/optimize', methods=['POST'])
def optimize_routes():
    # Berechne die optimierte Route unter Berücksichtigung von Zeitfenstern und Besuchsdauer
    result, error = optimize_route_with_time_windows()

    if result is not None:
        # Extrahiere die optimierte Route und die geplanten Besuchszeiten
        optimized_routes = {}
        for i, vehicle in enumerate(result['routes']):
            employee_name = employees[i]['name']
            optimized_routes[employee_name] = []
            for stop in vehicle['visits']:
                job_index = stop['job']
                customer = customers[job_index]
                arrival_time = stop['arrival_time']
                optimized_routes[employee_name].append({
                    "customer": customer['name'],
                    "address": customer['address'],
                    "arrival_time": arrival_time
                })

        # Antwort mit den optimierten Routen
        response = {
            "optimized_routes": optimized_routes
        }
        return jsonify(response)
    else:
        return jsonify({"error": error}), 500

if __name__ == '__main__':
    app.run(debug=True)