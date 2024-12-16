from backend.src.Customer.model import AbstractModel

class Vehicle(AbstractModel):
    name: str
    start_address: str
    
    def __init__(self, name: str, start_address: str, lat=None, lon=None):
        self.id = 1
        self.name = name
        self.start_address = start_address
        self.lat = lat
        self.lon = lon