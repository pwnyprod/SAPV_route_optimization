# Listen zum Speichern von Kunden und Fahrzeugen
patients = []
vehicles = []

class Entity:
    def __init__(self, name, lat=None, lon=None):
        self.id = None  # Wird später gesetzt
        self.name = name
        self.lat = lat
        self.lon = lon

    def __str__(self):
        return f"{self.name} ({self.lat}, {self.lon})"


class Patient(Entity):
    def __init__(self, name, address, visit_type, lat=None, lon=None):
        super().__init__(name, lat, lon)
        self.id = len(patients) + 1  # Eindeutige ID basierend auf der Liste der Kunden
        self.address = address
        self.visit_type = visit_type

    def __str__(self):
        return f"Customer: {self.name}, {self.address} ({self.lat}, {self.lon})"


class Vehicle(Entity):
    def __init__(self, name, start_address, lat=None, lon=None, stellenumfang=100):
        """
        Erweitertes Vehicle mit Stellenumfang:
          - stellenumfang: Zahl im Bereich 0..100, entspricht 0..100% (also 0..8h)
        """
        super().__init__(name, lat, lon)
        self.id = len(vehicles) + 1  # Eindeutige ID basierend auf der Liste der Fahrzeuge
        self.start_address = start_address
        self.stellenumfang = stellenumfang  # NEU: Attribut für Stellenumfang

    def __str__(self):
        return (f"Vehicle: {self.name}, {self.start_address} "
                f"({self.lat}, {self.lon}), Stellenumfang={self.stellenumfang}")
