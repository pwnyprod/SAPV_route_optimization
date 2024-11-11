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

# Liste zum Speichern der Kunden
customers = []

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

        if 'file' not in request.files:
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # CSV-Datei einlesen
                df = pd.read_csv(filepath, encoding='utf-8')
                
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
                flash(f'Fehler beim Verarbeiten der CSV-Datei: {str(e)}')
                return redirect(request.url)
            
    return render_template('csv_import_template.html', today=WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende"))

@app.route('/customers')
def show_customers():
    current_weekday = WEEKDAY_MAPPING.get(get_current_weekday(), "Wochenende")
    return render_template('csv_customers_template.html',
                           customers=customers,
                           today=current_weekday)

if __name__ == '__main__':
    app.run(debug=True)
