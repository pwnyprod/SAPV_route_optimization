from backend.src.Customer.model import Customer, Vehicle


class CustomerFacadeInterface:
    def generateCustomer(self, id: int, lat: str|None, lon: str|None, name: str, address: str, visit_type: str):
        pass


class CustomerFacade(CustomerFacadeInterface):
    def generateCustomer(self, lat, lon, name, address, visit_type):
        return Customer(name, address, visit_type, lat, lon)
    
    def generateVehicle(self, name: str, start_address: str, lat=None, lon=None):
        return Vehicle(name, start_address, lat, lon)
    

    # TBD