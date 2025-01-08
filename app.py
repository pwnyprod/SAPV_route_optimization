import os
from flask import Flask, render_template, request, jsonify, session
from google.maps import routeoptimization_v1
from datetime import datetime
from backend.FileHandler import *
from backend.RouteHandler import get_start_time, get_end_time
from config import *

# Setze die Umgebungsvariable für Google Cloud Service Account zur Authentifikation
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_CREDENTIALS

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

def get_selected_weekday():
    return session.get('selected_weekday', 'Montag')

@app.route('/update-weekday', methods=['POST'])
def update_weekday():
    data = request.get_json()
    selected_weekday = data.get('weekday')
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
    """
    1) Trenne TK/Non-TK
    2) Fleet Routing Request nur für Non-TK
    3) Berücksichtige Stellenumfang als max. Routenzeit
    4) Gebe TK-Fälle separat zurück
    5) Drucke Zeiten im Terminal (falls du magst)
    """
    optimization_client = routeoptimization_v1.RouteOptimizationClient()

    if not patients or not vehicles:
        return jsonify({'status': 'error', 'message': 'Need at least one patient and one vehicle'})

    # 1) Patienten nach visit_type trennen
    non_tk_patients = [p for p in patients if p.visit_type in ("Neuaufnahme", "HB")]
    tk_patients    = [p for p in patients if p.visit_type == "TK"]

    # 2) Shipments nur für Non-TK
    shipments = []
    for patient in non_tk_patients:
        duration_seconds = 0
        if patient.visit_type == "HB":
            duration_seconds = 2100  # 35 min
        elif patient.visit_type == "Neuaufnahme":
            duration_seconds = 7200  # 120 min
        # sonst -> 0s

        pickups = [{
            "arrival_location": {
                "latitude": patient.lat,
                "longitude": patient.lon
            },
            "duration": f"{duration_seconds}s"
        }]
        shipments.append({"pickups": pickups})

    # 3) Fahrzeuge: Berücksichtige Stellenumfang
    #    Stellenumfang = 0..100 -> 0..8 h
    #    => max_duration.seconds
    vehicles_model = []
    for v in vehicles:
        # Falls Stellenumfang nicht gesetzt ist, default=100
        stellenumfang = getattr(v, 'Stellenumfang', 100) or 100  
        # Umwandeln in Sekunden
        max_seconds = int((stellenumfang / 100.0) * 8 * 3600)

        vehicle_model = {
            "start_location": {
                "latitude": v.lat,
                "longitude": v.lon
            },
            "end_location": {
                "latitude": v.lat,
                "longitude": v.lon
            },
            "cost_per_hour": 1,
            "route_duration_limit": {
                # Nur setzen, wenn > 0 (sonst "verboten" / 0s)
                "max_duration": {
                    "seconds": max_seconds
                }
            }
        }
        vehicles_model.append(vehicle_model)

    # Request zusammenstellen
    fleet_routing_request = routeoptimization_v1.OptimizeToursRequest({
        "parent": "projects/routenplanung-sapv",
        "model": {
            "shipments": shipments,
            "vehicles": vehicles_model,
            "global_start_time": get_start_time(get_selected_weekday()),
            "global_end_time": get_end_time(get_selected_weekday())
        }
    })

    try:
        # 4) Aufruf der Optimierung
        response = optimization_client.optimize_tours(fleet_routing_request)

        # Routen extrahieren
        routes = []
        for i, route in enumerate(response.routes):
            start_dt = route.vehicle_start_time
            end_dt   = route.vehicle_end_time

            # Debug im Terminal
            if start_dt and end_dt:
                duration_sec = (end_dt - start_dt).total_seconds()
                duration_hrs = duration_sec / 3600.0
                print(f"Fahrzeug {i} => "
                      f"Start: {start_dt}, Ende: {end_dt}, "
                      f"Dauer: {duration_hrs:.2f} h, "
                      f"Name: {vehicles[route.vehicle_index].name}")
            else:
                print(f"Fahrzeug {i} => None start/end (nicht genutzt?)")

            v_index = route.vehicle_index
            route_info = {
                "vehicle": vehicles[v_index].name,
                "vehicle_start": {
                    "lat": vehicles[v_index].lat,
                    "lng": vehicles[v_index].lon
                },
                "stops": []
            }

            # Besuche => non_tk_patients
            for visit in route.visits:
                p_idx = visit.shipment_index
                if p_idx >= 0:
                    p = non_tk_patients[p_idx]
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

        # 5) TK-Fälle als Liste
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
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
