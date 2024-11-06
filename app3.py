import os
from flask import Flask, render_template, request, jsonify
from google.cloud import optimization_v1
import googlemaps
from config import *

# Setze die Umgebungsvariable für Google Cloud Service Account
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_CREDENTIALS

app = Flask(__name__)

# Google Maps Client initialisieren
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


class Customer:
    def __init__(self, name, address, lat=None, lon=None):
        self.name = name
        self.address = address
        self.lat = lat
        self.lon = lon


class Vehicle:
    def __init__(self, name, start_address, lat=None, lon=None):
        self.name = name
        self.start_address = start_address
        self.lat = lat
        self.lon = lon


# In-Memory Storage (in einer realen Anwendung würde man eine Datenbank verwenden)
customers = []
vehicles = []

def geocode_address(address):
    """Konvertiert eine Adresse in Koordinaten mittels Google Maps API"""
    try:
        result = gmaps.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            return location['lat'], location['lng']
        return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None


@app.route('/')
def index():
    return render_template('index3.html', customers=customers, vehicles=vehicles)


@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.json
    name = data.get('name')
    address = data.get('address')

    lat, lon = geocode_address(address)
    if lat and lon:
        customer = Customer(name, address, lat, lon)
        customers.append(customer)
        return jsonify({'status': 'success', 'message': 'Customer added successfully'})
    return jsonify({'status': 'error', 'message': 'Could not geocode address'})


@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    data = request.json
    name = data.get('name')
    start_address = data.get('start_address')

    lat, lon = geocode_address(start_address)
    if lat and lon:
        vehicle = Vehicle(name, start_address, lat, lon)
        vehicles.append(vehicle)
        return jsonify({'status': 'success', 'message': 'Vehicle added successfully'})
    return jsonify({'status': 'error', 'message': 'Could not geocode address'})


@app.route('/optimize_route', methods=['POST'])
def optimize_route():
    # Cloud Optimization Client initialisieren
    optimization_client = optimization_v1.FleetRoutingClient()

    if not customers or not vehicles:
        return jsonify({'status': 'error', 'message': 'Need at least one customer and one vehicle'})

    # Fleet Routing Request erstellen
    fleet_routing_request = optimization_v1.OptimizeToursRequest(
        parent=f"projects/routenplanung-sapv",
        vehicles=[
            optimization_v1.Vehicle(
                start_location=optimization_v1.Location(
                    latitude=vehicle.lat,
                    longitude=vehicle.lon
                ),
                end_location=optimization_v1.Location(
                    latitude=vehicle.lat,
                    longitude=vehicle.lon
                )
            ) for vehicle in vehicles
        ],
        shipments=[
            optimization_v1.Shipment(
                pickup=optimization_v1.Pickup(
                    location=optimization_v1.Location(
                        latitude=customer.lat,
                        longitude=customer.lon
                    )
                )
            ) for customer in customers
        ]
    )

    try:
        # Optimierungsanfrage senden
        response = optimization_client.optimize_tours(fleet_routing_request)

        # Routen aus der Antwort extrahieren
        routes = []
        for route in response.routes:
            route_info = {
                "vehicle": vehicles[route.vehicle_index].name,
                "stops": []
            }

            for visit in route.visits:
                customer_index = visit.shipment_index
                if customer_index >= 0:
                    route_info["stops"].append({
                        "customer": customers[customer_index].name,
                        "address": customers[customer_index].address
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