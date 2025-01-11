import io
import pandas as pd
from flask import flash, redirect, url_for, session
import googlemaps
import os
from werkzeug.utils import secure_filename

from config import GOOGLE_MAPS_API_KEY
from backend.entities import Patient, Vehicle, patients, vehicles

# Google Maps Client initialisieren
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_selected_weekday():
    return session.get('selected_weekday', 'Kein Wochentag gesetzt')

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

# Konfiguration für File Upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Definition der erlaubten Besuchsarten
VALID_VISIT_TYPES = {'HB', 'TK', 'Neuaufnahme'}

# Mapping von Wochentagen
WEEKDAY_MAPPING = {
    0: 'Montag',
    1: 'Dienstag',
    2: 'Mittwoch',
    3: 'Donnerstag',
    4: 'Freitag'
}

def handle_patient_upload(request):
    if 'patient_file' not in request.files:
        flash('Keine Kundendatei ausgewählt')
        return redirect(request.url)

    file = request.files['patient_file']
    if file.filename == '':
        flash('Keine Kundendatei ausgewählt')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        try:
            df = pd.read_excel(file)

            required_columns = ['Nachname', 'Vorname', 'Strasse', 'Ort', 'PLZ'] + list(WEEKDAY_MAPPING.values())
            if not all(col in df.columns for col in required_columns):
                flash('Excel-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            df_filtered = df[df[get_selected_weekday()].isin(VALID_VISIT_TYPES)].copy()

            patients.clear()
            for _, row in df_filtered.iterrows():
                name = f"{row['Vorname']} {row['Nachname']}"
                address = f"{row['Strasse']}, {row['PLZ']} {row['Ort']}"
                visit_type = row[get_selected_weekday()]
                lat, lon = geocode_address(address)
                patient = Patient(name=name, address=address, visit_type=visit_type, lat=lat, lon=lon)
                patients.append(patient)

            if len(patients) == 0:
                flash(f'Keine Termine für {get_selected_weekday()} gefunden.')
            else:
                flash(f'{len(patients)} Kunden für {get_selected_weekday()} erfolgreich importiert')
            return redirect(url_for('show_patients'))

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
        try:
            df = pd.read_excel(file)

            required_columns = ['Nachname', 'Vorname', 'Strasse', 'Ort', 'PLZ', 'Stellenumfang']
            if not all(col in df.columns for col in required_columns):
                flash('Excel-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            vehicles.clear()
            for _, row in df.iterrows():
                lat, lon = geocode_address(f"{row['Strasse']}, {row['PLZ']} {row['Ort']}")
                
                try:
                    stellenumfang_val = float(row['Stellenumfang'])
                except:
                    stellenumfang_val = 100.0

                if stellenumfang_val < 0:  
                    stellenumfang_val = 0
                elif stellenumfang_val > 100:
                    stellenumfang_val = 100

                vehicle = Vehicle(
                    name=f"{row['Vorname']} {row['Nachname']}",
                    start_address=f"{row['Strasse']}, {row['PLZ']} {row['Ort']}",
                    lat=lat,
                    lon=lon,
                    stellenumfang=stellenumfang_val
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
