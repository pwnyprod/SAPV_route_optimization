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
    optimization_client = routeoptimization_v1.RouteOptimizationClient()

    if not patients or not vehicles:
        return jsonify({'status': 'error', 'message': 'Need at least one patient and one vehicle'})

    # 1) Patienten nach visit_type trennen
    non_tk_patients = [p for p in patients if p.visit_type in ["Neuaufnahme", "HB"]]
    tk_patients = [p for p in patients if p.visit_type == "TK"]

    # 2) Baue das Request-Model **nur** mit non_tk_patients
    fleet_routing_request = routeoptimization_v1.OptimizeToursRequest({
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
                                "2100s" if patient.visit_type == "HB" else
                                "7200s" if patient.visit_type == "Neuaufnahme" else
                                # Falls du einen sonstigen Fallback willst:
                                "0s"
                            )
                        }
                    ]
                }
                for patient in non_tk_patients
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
                    "cost_per_hour": 1
                }
                for vehicle in vehicles
            ],
            "global_start_time": get_start_time(get_selected_weekday()),
            "global_end_time": get_end_time(get_selected_weekday())
        }
    })

    try:
        response = optimization_client.optimize_tours(fleet_routing_request)

        # Routen aus der Antwort extrahieren
        routes = []
        for route in response.routes:
            v_index = route.vehicle_index
            route_info = {
                "vehicle": vehicles[v_index].name,
                "vehicle_start": {
                    "lat": vehicles[v_index].lat,
                    "lng": vehicles[v_index].lon
                },
                "stops": []
            }

            for visit in route.visits:
                patient_index = visit.shipment_index  # => Index in non_tk_patients
                if patient_index >= 0:
                    p = non_tk_patients[patient_index]
                    route_info["stops"].append({
                        "patient": p.name,
                        "address": p.address,
                        "visit_type": p.visit_type,
                        "location": {
                            "lat": p.lat,
                            "lng": p.lon
                        }
                    })

            routes.append(route_info)

        # 3) Hier hängen wir alle TK-Patient*innen **einfach** ans Ende der Antwort
        #    - Sie werden NICHT geroutet, sondern nur aufgelistet
        tk_list = [
            {
                "patient": tk.name,
                "address": tk.address,
                "visit_type": tk.visit_type
            }
            for tk in tk_patients
        ]

        return jsonify({
            'status': 'success',
            'routes': routes,
            'tk_patients': tk_list 
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)