from datetime import datetime, timedelta

def get_next_weekday(weekday_name: str) -> str:
    # Wochentagszuordnung mit großgeschriebenem Anfangsbuchstaben
    weekdays = {
        'Montag': 0,
        'Dienstag': 1,
        'Mittwoch': 2,
        'Donnerstag': 3,
        'Freitag': 4,
        'Samstag': 5,
        'Sonntag': 6
    }

    # Aktuelles Datum abrufen
    current_date = datetime.utcnow()

    # Wochentag des aktuellen Datums (0 = Montag, 6 = Sonntag)
    current_weekday = current_date.weekday()

    # Überprüfen, ob der eingegebene Wochentag gültig ist
    if weekday_name not in weekdays:
        return "Ungültiger Wochentag."

    # Zielwochentag
    target_weekday = weekdays[weekday_name]

    # Differenz zwischen dem aktuellen Wochentag und dem Zielwochentag berechnen
    days_difference = (target_weekday - current_weekday) % 7

    # Datum für den nächsten Zielwochentag berechnen
    target_date = current_date + timedelta(days=days_difference)

    # Datum im gewünschten Format zurückgeben (RFC3339 mit "Z")
    return target_date.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def get_start_time(weekday_name: str) -> str:
    target_date = get_next_weekday(weekday_name)
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    return start_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

# Funktion für die Endzeit (20:00 Uhr)
def get_end_time(weekday_name: str) -> str:
    target_date = get_next_weekday(weekday_name)
    end_time = target_date.replace(hour=20, minute=0, second=0, microsecond=0)
    return end_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

# Beispiele:
print(get_start_time('Montag'))   # Gibt die Startzeit für den nächsten Montag (08:00 Uhr) zurück.
print(get_end_time('Montag'))     # Gibt die Endzeit für den nächsten Montag (20:00 Uhr) zurück.