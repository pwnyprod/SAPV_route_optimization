from flask import Flask, render_template, jsonify, request
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import googlemaps
from datetime import datetime, timedelta

app = Flask(__name__)

# Fügen Sie hier Ihren Google Maps API-Schlüssel ein
GOOGLE_MAPS_API_KEY = 'AIzaSyCQsBRlgxruIcymhmMtJPjFCW9mS7uKhl0'  # Hier deinen API-Schlüssel einfügen
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


class DeliveryProblem:
    def __init__(self, addresses, time_windows, service_times):
        self.addresses = addresses
        self.time_windows = time_windows
        self.service_times = service_times
        self.locations = self.geocode_addresses()

    def geocode_addresses(self):
        locations = []
        for addr in self.addresses:
            geocode_result = gmaps.geocode(addr)
            if geocode_result:
                locations.append(geocode_result[0]['geometry']['location'])
            else:
                locations.append(None)  # Fallback für ungültige Adressen
        return locations

    def get_distance_matrix(self):
        size = len(self.locations)
        matrix = np.zeros((size, size))

        for i in range(size):
            for j in range(i + 1, size):
                result = gmaps.distance_matrix(
                    self.addresses[i],
                    self.addresses[j],
                    mode="driving"
                )
                duration = result['rows'][0]['elements'][0]['duration']['value'] // 60  # Convert to minutes
                matrix[i][j] = duration
                matrix[j][i] = duration

        return matrix.astype(int)


def create_data_model():
    """Erstellt das Datenmodell für das Routing-Problem."""
    data = {}

    # Beispieladressen (Berlin)
    addresses = [
        "Alexanderplatz, Berlin",  # Depot 1
        "Kurfürstendamm 234, Berlin",  # Depot 2
        "Friedrichstraße 100, Berlin",  # Kunde 1
        "Potsdamer Platz, Berlin",  # Kunde 2
        "Brandenburger Tor, Berlin",  # Kunde 3
        "East Side Gallery, Berlin",  # Kunde 4
        "Checkpoint Charlie, Berlin",  # Kunde 5
        "Hackescher Markt, Berlin",  # Kunde 6
        "Berliner Dom, Berlin",  # Kunde 7
        "Schloss Charlottenburg, Berlin",  # Kunde 8
        "Gendarmenmarkt, Berlin",  # Kunde 9
        "Olympiastadion Berlin",  # Kunde 10
    ]

    # Zeitfenster für jeden Standort (früher Start, später Start) in Minuten seit 8:00
    time_windows = [
        (0, 480),  # Depot 1: 8:00-16:00
        (0, 480),  # Depot 2: 8:00-16:00
        (60, 120),  # Kunde 1: 9:00-10:00
        (120, 180),  # Kunde 2: 10:00-11:00
        (180, 240),  # Kunde 3: 11:00-12:00
        (120, 240),  # Kunde 4: 10:00-12:00
        (240, 300),  # Kunde 5: 12:00-13:00
        (180, 360),  # Kunde 6: 11:00-14:00
        (300, 360),  # Kunde 7: 13:00-14:00
        (60, 420),  # Kunde 8: 9:00-15:00
        (180, 420),  # Kunde 9: 11:00-15:00
        (240, 480),  # Kunde 10: 12:00-16:00
    ]

    # Besuchsdauer in Minuten für jeden Standort
    service_times = [0, 0, 15, 30, 20, 25, 15, 30, 20, 25, 15, 30]

    problem = DeliveryProblem(addresses, time_windows, service_times)

    data['distance_matrix'] = problem.get_distance_matrix()
    data['time_windows'] = problem.time_windows
    data['service_times'] = problem.service_times
    data['num_vehicles'] = 2
    data['depot'] = 0  # Erstes Depot als Hauptdepot
    data['starts'] = [0, 1]  # Fahrzeug 1 startet von Depot 1, Fahrzeug 2 von Depot 2
    data['ends'] = [0, 1]  # Fahrzeuge kehren zu ihren Startdepots zurück

    return data, problem


def solve_routing_problem():
    """Löst das Vehicle Routing Problem mit Zeitfenstern."""
    data, problem = create_data_model()

    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['starts'],
        data['ends'])

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = data['distance_matrix'][from_node][to_node]
        return travel_time + data['service_times'][from_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_callback_index,
        30,  # Allow waiting time
        480,  # Maximum time per vehicle
        False,  # Don't force start cumul to zero
        'Time')

    time_dimension = routing.GetDimensionOrDie('Time')

    # Zeitfenster hinzufügen
    for location_idx, time_window in enumerate(data['time_windows']):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Lösungsstrategie festlegen
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 30

    # Lösung finden
    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None

    routes = []
    for vehicle_id in range(data['num_vehicles']):
        route = []
        index = routing.Start(vehicle_id)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            route.append({
                'location': node,
                'address': problem.addresses[node],
                'coords': problem.locations[node],  # Füge die Koordinaten hinzu
                'arrival_time': solution.Min(time_var),
                'departure_time': solution.Min(time_var) + data['service_times'][node]
            })
            index = solution.Value(routing.NextVar(index))
        node = manager.IndexToNode(index)
        time_var = time_dimension.CumulVar(index)
        route.append({
            'location': node,
            'address': problem.addresses[node],
            'coords': problem.locations[node],  # Füge die Koordinaten hinzu
            'arrival_time': solution.Min(time_var),
            'departure_time': solution.Min(time_var)
        })
        routes.append(route)

    return routes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/optimize', methods=['POST'])
def optimize():
    # In einer vollständigen Implementierung würden Sie hier die vom Benutzer eingegebenen Daten verarbeiten
    # Für dieses Beispiel verwenden wir weiterhin die vordefinierten Daten
    routes = solve_routing_problem()
    if routes:
        return jsonify({'success': True, 'routes': routes})
    return jsonify({'success': False, 'message': 'Keine Lösung gefunden'})


if __name__ == '__main__':
    app.run(debug=True)