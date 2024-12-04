import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from google.cloud import optimization_v1
import googlemaps
from config import *
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

# Setze die Umgebungsvariable für Google Cloud Service Account
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_CREDENTIALS

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Konfiguration für File Upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Google Maps Client initialisieren
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Listen zum Speichern von Kunden und Fahrzeugen
customers = []
vehicles = []

# Definition der erlaubten Besuchsarten
VALID_VISIT_TYPES = {'HB', 'TK', 'Neuaufnahme'}

# Mapping von Wochentagen (0 = Montag, 6 = Sonntag) zu Spaltennamen
WEEKDAY_MAPPING = {
    0: 'Montag',
    1: 'Dienstag',
    2: 'Mittwoch',
    3: 'Donnerstag',
    4: 'Freitag'
}


class Customer:
    def __init__(self, name, address, visit_type, lat=None, lon=None):
        self.id = len(customers) + 1
        self.name = name
        self.address = address
        self.visit_type = visit_type
        self.lat = lat
        self.lon = lon

class Vehicle:
    def __init__(self, name, start_address, lat=None, lon=None):
        self.id = len(vehicles) + 1  # Eindeutige ID basierend auf der Länge der Liste
        self.name = name
        self.start_address = start_address
        self.lat = lat
        self.lon = lon


# Konvertiert eine Adresse in Koordinaten
def geocode_address(address):
    try:
        result = gmaps.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            return location['lat'], location['lng']
        return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_weekday():
    return datetime.now().weekday()


def get_tomorrow_weekday():
    return (datetime.now() + timedelta(days=1)).weekday()


def is_weekend():
    return get_current_weekday() > 4


def handle_customer_upload(request):
    if 'customer_file' not in request.files:
        flash('Keine Kundendatei ausgewählt')
        return redirect(request.url)

    file = request.files['customer_file']
    if file.filename == '':
        flash('Keine Kundendatei ausgewählt')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # CSV-Datei einlesen
            df = pd.read_csv(filepath, encoding='utf-8-sig', sep=';')

            # Überprüfen ob alle erforderlichen Spalten vorhanden sind
            required_columns = ['Nachname', 'Vorname', 'Straße', 'Ort', 'PLZ'] + list(WEEKDAY_MAPPING.values())
            if not all(col in df.columns for col in required_columns):
                flash('CSV-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            # Aktuellen Wochentag ermitteln
            current_weekday = get_current_weekday()
            current_weekday_name = WEEKDAY_MAPPING.get(current_weekday)

            if current_weekday_name is None:
                flash('Heute ist Wochenende. Keine Datenverarbeitung möglich.')
                return redirect(request.url)

            # Filtern der Daten für den aktuellen Wochentag
            # Nur Zeilen berücksichtigen, wo für den aktuellen Tag ein gültiger Besuchstyp eingetragen ist
            df_filtered = df[df[current_weekday_name].isin(VALID_VISIT_TYPES)].copy()

            # Daten in Customer-Objekte umwandeln
            customers.clear()  # Liste leeren, um Duplikate zu vermeiden
            for _, row in df_filtered.iterrows():
                name = f"{row['Vorname']} {row['Nachname']}"
                address = f"{row['Straße']}, {row['PLZ']} {row['Ort']}"
                visit_type = row[current_weekday_name]
                lat, lon = geocode_address(address)
                customer = Customer(name=name, address=address, visit_type=visit_type, lat=lat, lon=lon)
                customers.append(customer)

            if len(customers) == 0:
                flash(f'Keine Termine für {current_weekday_name} gefunden.')
            else:
                flash(f'{len(customers)} Kunden für {current_weekday_name} erfolgreich importiert')
            return redirect(url_for('show_customers'))

        except Exception as e:
            flash(f'Fehler beim Verarbeiten der Kundendatei: {str(e)}')
            return redirect(request.url)


def handle_vehicle_upload(request):
    if 'vehicle_file' not in request.files:
        flash('Keine Fahrzeugdatei ausgewählt')
        return redirect(request.url)

    file = request.files['vehicle_file']
    if file.filename == '':
        flash('Keine Fahrzeugdatei ausgewählt')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # CSV-Datei einlesen
            df = pd.read_csv(filepath, encoding='utf-8-sig', sep=';')

            # Überprüfen ob alle erforderlichen Spalten vorhanden sind
            required_columns = ['Nachname', 'Vorname', 'Straße', 'Ort', 'PLZ']
            if not all(col in df.columns for col in required_columns):
                flash('CSV-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            # Daten in Vehicle-Objekte umwandeln
            vehicles.clear()  # Liste leeren, um Duplikate zu vermeiden
            for _, row in df.iterrows():
                lat, lon = geocode_address(f"{row['Straße']}, {row['PLZ']} {row['Ort']}")
                vehicle = Vehicle(
                    name=f"{row['Vorname']} {row['Nachname']}",
                    start_address=f"{row['Straße']}, {row['PLZ']} {row['Ort']}",
                    lat=lat,
                    lon=lon
                )
                vehicles.append(vehicle)

            if len(vehicles) == 0:
                flash('Keine Fahrzeuge importiert')
            else:
                flash(f'{len(vehicles)} Fahrzeuge erfolgreich importiert')
            return redirect(url_for('show_vehicles'))

        except Exception as e:
            flash(f'Fehler beim Verarbeiten der Fahrzeugdatei: {str(e)}')
            return redirect(request.url)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Überprüfen, ob es ein Wochenende ist
        if is_weekend():
            flash('An Wochenenden können keine Daten importiert werden.')
            return redirect(request.url)

        upload_type = request.form.get('upload_type')

        if upload_type == 'customers':
            return handle_customer_upload(request)
        elif upload_type == 'vehicles':
            return handle_vehicle_upload(request)

    # GET-Anfrage: Rendert die Seite mit den erforderlichen Daten
    return render_template(
        'index.html',
        customers=customers,
        vehicles=vehicles,
        today=WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende"),
        google_maps_api_key=GOOGLE_MAPS_API_KEY
    )


@app.route('/get_markers', methods=['GET'])
def get_markers():
    markers = {
        'customers': [{'name': c.name, 'lat': c.lat, 'lng': c.lon} for c in customers],
        'vehicles': [{'name': v.name, 'lat': v.lat, 'lng': v.lon} for v in vehicles]
    }
    return jsonify(markers)


@app.route('/customers')
def show_customers():
    current_weekday = WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende")
    return render_template('show_customer.html',
                           customers=customers,
                           today=current_weekday)


@app.route('/vehicles')
def show_vehicles():
    return render_template('show_vehicle.html', vehicles=vehicles)


@app.route('/optimize_route', methods=['POST'])
def optimize_route():
    optimization_client = optimization_v1.FleetRoutingClient()

    if not customers or not vehicles:
        return jsonify({'status': 'error', 'message': 'Need at least one customer and one vehicle'})

    # Fleet Routing Request erstellen
    fleet_routing_request = optimization_v1.OptimizeToursRequest(
        {
            "parent": "projects/routenplanung-sapv",
            "model": {
                "shipments": [
                    {
                        "pickups": [
                            {
                                "arrival_location": {
                                    "latitude": customer.lat,
                                    "longitude": customer.lon
                                },
                                "duration": (
                                # Ist nur beispielhaft
                                "10s" if customer.visit_type == "HB" else
                                "20s" if customer.visit_type == "Neuaufnahme" else
                                "30s" if customer.visit_type == "TK" else
                                "150s"  # Fallback-Dauer, falls kein `visittype` definiert ist
                            )
                            }
                        ],
                        # Jeder Stopp zählt als 1 Einheit
                        "demands": [
                            {
                                "type": "visits",
                                "value": "1"
                            }
                        ]
                    }
                    for customer in customers
                ],
                "vehicles": [
                    {
                        "start_location": {
                            "latitude": vehicle.lat,
                            "longitude": vehicle.lon
                        },
                        "end_location": {
                            "latitude": vehicle.lat,
                            "longitude": vehicle.lon
                        },
                        # Maximale Anzahl Stopps pro Fahrzeug
                        "capacities": [
                            {
                                "type": "visits",
                                # Ceil(Gesamtanzahl Stopps / Anzahl Fahrzeuge)
                                "value": str(-(-(len(customers)) // len(vehicles)))
                            }
                        ]
                    }
                    for vehicle in vehicles
                ]
            }
        }
    )

    try:
        response = optimization_client.optimize_tours(fleet_routing_request)

        # Routen aus der Antwort extrahieren
        routes = []
        for route in response.routes:
            route_info = {
                "vehicle": vehicles[route.vehicle_index].name,
                "vehicle_start": {
                    "lat": vehicles[route.vehicle_index].lat,
                    "lng": vehicles[route.vehicle_index].lon
                },
                "stops": []
            }

            for visit in route.visits:
                customer_index = visit.shipment_index
                if customer_index >= 0:
                    route_info["stops"].append({
                        "customer": customers[customer_index].name,
                        "address": customers[customer_index].address,
                        "location": {
                            "lat": customers[customer_index].lat,
                            "lng": customers[customer_index].lon
                        }
                    })

            routes.append(route_info)

        return jsonify({
            'status': 'success',
            'routes': routes
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


if __name__ == '__main__':
    app.run(debug=True)