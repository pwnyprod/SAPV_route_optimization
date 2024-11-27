# app.py
from flask import Flask, render_template, request, flash, redirect, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Konfiguration für File Upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_weekday():
    return datetime.now().weekday()


def is_weekend():
    return get_current_weekday() > 4


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Überprüfen ob es ein Wochenende ist
        if is_weekend():
            flash('An Wochenenden können keine Daten importiert werden.')
            return redirect(request.url)

        upload_type = request.form.get('upload_type')

        if upload_type == 'customers':
            return handle_customer_upload(request)
        elif upload_type == 'vehicles':
            return handle_vehicle_upload(request)

    return render_template('csv_import_template.html', today=WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende"))


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
            df = pd.read_csv(filepath, encoding='utf-8-sig')

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
                customer = Customer(name=name, address=address, visit_type=visit_type)
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
            df = pd.read_csv(filepath, encoding='utf-8-sig')

            # Überprüfen ob alle erforderlichen Spalten vorhanden sind
            required_columns = ['Nachname', 'Vorname', 'Straße', 'Ort', 'PLZ']
            if not all(col in df.columns for col in required_columns):
                flash('CSV-Datei hat nicht alle erforderlichen Spalten')
                return redirect(request.url)

            # Daten in Vehicle-Objekte umwandeln
            vehicles.clear()  # Liste leeren, um Duplikate zu vermeiden
            for _, row in df.iterrows():
                vehicle = Vehicle(
                    name=f"{row['Vorname']} {row['Nachname']}",
                    start_address=f"{row['Straße']}, {row['PLZ']} {row['Ort']}"
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


@app.route('/customers')
def show_customers():
    current_weekday = WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende")
    return render_template('csv_customers_template.html',
                           customers=customers,
                           today=current_weekday)


@app.route('/vehicles')
def show_vehicles():
    return render_template('csv_vehicles_template.html', vehicles=vehicles)


if __name__ == '__main__':
    app.run(debug=True)