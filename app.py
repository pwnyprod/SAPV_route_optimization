import os
from flask import Flask, render_template, request, jsonify, session
from google.maps import routeoptimization_v1
from backend.FileHandler import *
from backend.RouteHandler import get_start_time, get_end_time
from config import *


# Setze die Umgebungsvariable für Google Cloud Service Account zur Authentifikation
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_CREDENTIALS

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY





@app.route('/update-weekday', methods=['POST'])
def update_weekday():
    data = request.get_json()
    selected_weekday = data.get('weekday')

    # Speichern des Wochentags in der Sitzung
    session['selected_weekday'] = selected_weekday

    return jsonify({"status": "success", "weekday": selected_weekday})



@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')

        if upload_type == 'patients':
            return handle_patient_upload(request)
        elif upload_type == 'vehicles':
            return handle_vehicle_upload(request)

    # GET-Anfrage: Rendert die Seite mit den erforderlichen Daten
    return render_template(
        'index.html',
        patients=patients,
        vehicles=vehicles,
        google_maps_api_key=GOOGLE_MAPS_API_KEY
    )


@app.route('/get_markers', methods=['GET'])
def get_markers():
    markers = {
        'patients': [{'name': c.name, 'lat': c.lat, 'lng': c.lon} for c in patients],
        'vehicles': [{'name': v.name, 'lat': v.lat, 'lng': v.lon} for v in vehicles]
    }
    return jsonify(markers)



@app.route('/patients', methods=['GET', 'POST'])
def show_patients():
    selected_weekday = get_selected_weekday()

    return render_template('show_patient.html',
                           patients=patients,
                           weekday=selected_weekday)



@app.route('/vehicles')
def show_vehicles():
    return render_template('show_vehicle.html', vehicles=vehicles)


@app.route('/optimize_route', methods=['POST'])
def optimize_route():
    print(get_start_time(get_selected_weekday()))
    print(get_end_time(get_selected_weekday()))

    optimization_client = routeoptimization_v1.RouteOptimizationClient()

    if not patients or not vehicles:
        return jsonify({'status': 'error', 'message': 'Need at least one patient and one vehicle'})

    # Fleet Routing Request erstellen
    fleet_routing_request = routeoptimization_v1.OptimizeToursRequest(
        {
            "parent": "projects/routenplanung-sapv",
            "model": {
                "shipments": [
                    {
                        "pickups": [
                            {
                                "arrival_location": {
                                    "latitude": patient.lat,
                                    "longitude": patient.lon
                                },
                                "duration": (
                                    # Ist nur beispielhaft
                                    "2100s" if patient.visit_type == "HB" else # 35 Minuten
                                    "7200s" if patient.visit_type == "Neuaufnahme" else # 120 Minuten
                                    "0s" if patient.visit_type == "TK" else
                                    "150s"
                                )
                            }
                        ]
                    }
                    for patient in patients
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
                        }
                    }
                    for vehicle in vehicles
                ],
                "global_start_time": get_start_time(get_selected_weekday()),
                "global_end_time": get_end_time(get_selected_weekday()),
                "global_duration_cost_per_hour": 1
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
                patient_index = visit.shipment_index
                if patient_index >= 0:
                    route_info["stops"].append({
                        "patient": patients[patient_index].name,
                        "address": patients[patient_index].address,
                        "location": {
                            "lat": patients[patient_index].lat,
                            "lng": patients[patient_index].lon
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