from datetime import datetime, timedelta

def get_next_weekday(weekday_name: str) -> datetime:
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
        raise ValueError("Ungültiger Wochentag.")

    # Zielwochentag
    target_weekday = weekdays[weekday_name]

    # Differenz zwischen dem aktuellen Wochentag und dem Zielwochentag berechnen
    days_difference = (target_weekday - current_weekday) % 7

    # Datum für den nächsten Zielwochentag berechnen
    return current_date + timedelta(days=days_difference)


# Funktion für die Startzeit
def get_start_time(weekday_name: str) -> str:
    target_date = get_next_weekday(weekday_name)
    start_time = datetime(target_date.year, target_date.month, target_date.day, 8, 0, 0)
    return start_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


# Funktion für die Endzeit
def get_end_time(weekday_name: str) -> str:
    target_date = get_next_weekday(weekday_name)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 16, 0, 0)
    return end_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

