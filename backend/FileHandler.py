import io
import pandas as pd
from flask import flash, redirect, url_for, session
import googlemaps
from config import GOOGLE_MAPS_API_KEY
from backend.entities import Patient, Vehicle, patients, vehicles

# Google Maps Client initialisieren
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_selected_weekday():
    # Zugriff auf den Wochentag in der Sitzung
    return session.get('selected_weekday', 'Kein Wochentag gesetzt')

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

# Konfiguration für File Upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            # CSV-Datei direkt aus dem Speicher lesen
            file_stream = io.StringIO(file.stream.read().decode('utf-8-sig'))  # Datei im Speicher lesen
            df = pd.read_csv(file_stream, sep=';')

            # Überprüfen ob alle erforderlichen Spalten vorhanden sind
            required_columns = ['Nachname', 'Vorname', 'Straße', 'Ort', 'PLZ'] + list(WEEKDAY_MAPPING.values())
            if not all(col in df.columns for col in required_columns):
                flash('CSV-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            # Filtern der Daten für den ausgewählten Wochentag
            df_filtered = df[df[get_selected_weekday()].isin(VALID_VISIT_TYPES)].copy()

            # Daten in Customer-Objekte umwandeln
            patients.clear()  # Liste leeren, um Duplikate zu vermeiden
            for _, row in df_filtered.iterrows():
                name = f"{row['Vorname']} {row['Nachname']}"
                address = f"{row['Straße']}, {row['PLZ']} {row['Ort']}"
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
            # CSV-Datei direkt aus dem Speicher lesen
            file_stream = io.StringIO(file.stream.read().decode('utf-8-sig'))  # Datei im Speicher lesen
            df = pd.read_csv(file_stream, encoding='utf-8-sig', sep=';')

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
