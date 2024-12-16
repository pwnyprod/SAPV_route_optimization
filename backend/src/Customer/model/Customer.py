from backend.src.Customer.model import AbstractModel

class Customer(AbstractModel):
    name: str
    address: str
    visit_type: str

    def __init__(self, name: str, address: str, visit_type: str, lat=None, lon=None):
        self.id = 1
        self.name = name
        self.address = address
        self.visit_type = visit_type
        self.lat = lat
        self.lon = lon