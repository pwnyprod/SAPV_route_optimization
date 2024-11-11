let map;
let markers = [];
let directionsRenderers = [];

// Initialisiere Google Maps
function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: 51.1657, lng: 10.4515 }, // Zentrum von Deutschland
        zoom: 6
    });
    loadMarkers();
}

// Lade alle existierenden Marker
async function loadMarkers() {
    clearMarkers();
    const response = await fetch('/get_markers');
    const data = await response.json();

    // Füge Kunden-Marker hinzu
    data.customers.forEach(customer => {
        const marker = new google.maps.Marker({
            position: { lat: customer.lat, lng: customer.lng },
            map: map,
            title: customer.name,
            icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
        });
        markers.push(marker);
    });

    // Füge Fahrzeug-Marker hinzu
    data.vehicles.forEach(vehicle => {
        const marker = new google.maps.Marker({
            position: { lat: vehicle.lat, lng: vehicle.lng },
            map: map,
            title: vehicle.name,
            icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
        });
        markers.push(marker);
    });
}

// Aktualisiere die Kundenliste
function updateCustomerList(customer, customerId) {
    const customerList = document.getElementById('customerList');
    const li = document.createElement('li');
    li.innerHTML = `
        ${customer.name} - ${customer.address}
        <button class="deleteCustomer" data-id="${customerId}">
            <i class="fas fa-trash"></i>
        </button>
    `;

    // Event Listener für den neuen Lösch-Button
    const deleteButton = li.querySelector('.deleteCustomer');
    deleteButton.addEventListener('click', handleDeleteCustomer);

    customerList.appendChild(li);
}

// Aktualisiere die Fahrzeugliste
function updateVehicleList(vehicle, vehicleId) {
    const vehicleList = document.getElementById('vehicleList');
    const li = document.createElement('li');
    li.innerHTML = `
        ${vehicle.name} - ${vehicle.start_address}
        <button class="deleteVehicle" data-id="${vehicleId}">
            <i class="fas fa-trash"></i>
        </button>
    `;

    // Event Listener für den neuen Lösch-Button
    const deleteButton = li.querySelector('.deleteVehicle');
    deleteButton.addEventListener('click', handleDeleteVehicle);

    vehicleList.appendChild(li);
}

// Handler für das Löschen eines Kunden
async function handleDeleteCustomer(e) {
    const customerId = e.target.closest('.deleteCustomer').getAttribute('data-id');
    const response = await fetch(`/delete_customer/${customerId}`, {
        method: 'DELETE',
    });
    const data = await response.json();
    if (data.status === 'success') {
        e.target.closest('li').remove();
        loadMarkers(); // Aktualisiere die Marker
    } else {
        alert(data.message);
    }
}

// Handler für das Löschen eines Fahrzeugs
async function handleDeleteVehicle(e) {
    const vehicleId = e.target.closest('.deleteVehicle').getAttribute('data-id');
    const response = await fetch(`/delete_vehicle/${vehicleId}`, {
        method: 'DELETE',
    });
    const data = await response.json();
    if (data.status === 'success') {
        e.target.closest('li').remove();
        loadMarkers(); // Aktualisiere die Marker
    } else {
        alert(data.message);
    }
}

// Lösche alle Marker von der Karte
function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}

// Lösche alle Routen von der Karte
function clearRoutes() {
    directionsRenderers.forEach(renderer => renderer.setMap(null));
    directionsRenderers = [];
}

// Promise-basierte Funktion für die Routenberechnung
function calculateRoute(request, directionsRenderer) {
    return new Promise((resolve, reject) => {
        const directionsService = new google.maps.DirectionsService();

        directionsService.route(request, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
                resolve(result);
            } else {
                console.error('Fehler bei der Routenberechnung:', status);
                reject(status);
            }
        });
    });
}

// Event Listener für das Kundenformular
document.getElementById('customerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const customerName = document.getElementById('customerName').value;
    const customerAddress = document.getElementById('customerAddress').value;

    const response = await fetch('/add_customer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: customerName,
            address: customerAddress
        })
    });
    const data = await response.json();
    if (data.status === 'success') {
        // Formular zurücksetzen
        document.getElementById('customerForm').reset();

        // Liste und Marker aktualisieren
        updateCustomerList({name: customerName, address: customerAddress}, data.customerId);
        loadMarkers();
    } else {
        alert(data.message);
    }
});

// Event Listener für das Fahrzeugformular
document.getElementById('vehicleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const vehicleName = document.getElementById('vehicleName').value;
    const startAddress = document.getElementById('startAddress').value;

    const response = await fetch('/add_vehicle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: vehicleName,
            start_address: startAddress
        })
    });
    const data = await response.json();
    if (data.status === 'success') {
        // Formular zurücksetzen
        document.getElementById('vehicleForm').reset();

        // Liste und Marker aktualisieren
        updateVehicleList({name: vehicleName, start_address: startAddress}, data.vehicleId);
        loadMarkers();
    } else {
        alert(data.message);
    }
});

// Event Listener für Route optimieren
document.getElementById('optimizeButton').addEventListener('click', async () => {
    clearRoutes();
    const response = await fetch('/optimize_route', {
        method: 'POST',
    });
    const data = await response.json();
    if (data.status === 'success') {
        let routesHtml = '';

        // Erstelle für jede Route einen eigenen DirectionsService und DirectionsRenderer
        for (let routeIndex = 0; routeIndex < data.routes.length; routeIndex++) {
            const route = data.routes[routeIndex];
            const routeColor = getRandomColor();

            // HTML für die Routenliste
            routesHtml += `<h3>Fahrzeug: ${route.vehicle}</h3><ul>`;
            route.stops.forEach(stop => {
                routesHtml += `<li>${stop.customer} - ${stop.address}</li>`;
            });
            routesHtml += '</ul>';

            // Erstelle einen neuen DirectionsRenderer für diese Route
            const directionsRenderer = new google.maps.DirectionsRenderer({
                map: map,
                suppressMarkers: true, // Unterdrücke die Standard-Marker
                preserveViewport: true, // Behalte den aktuellen Kartenausschnitt
                polylineOptions: {
                    strokeColor: routeColor,
                    strokeOpacity: 0.8,
                    strokeWeight: 4
                }
            });

            directionsRenderers.push(directionsRenderer);

            // Erstelle Wegpunkte für die Route
            const waypoints = route.stops.map(stop => ({
                location: new google.maps.LatLng(stop.location.lat, stop.location.lng),
                stopover: true
            }));

            // Erstelle die Routenanfrage
            const request = {
                origin: new google.maps.LatLng(route.vehicle_start.lat, route.vehicle_start.lng),
                destination: new google.maps.LatLng(route.vehicle_start.lat, route.vehicle_start.lng), // Zurück zum Startpunkt
                waypoints: waypoints,
                travelMode: google.maps.TravelMode.DRIVING,
                optimizeWaypoints: false // Da die Optimierung bereits serverseitig erfolgt ist
            };

            // Nutze eine Promise-basierte Funktion für die Routenberechnung
            try {
                await calculateRoute(request, directionsRenderer);
            } catch (error) {
                console.error('Fehler bei Route', routeIndex + 1, ':', error);
            }
        }

        document.getElementById('routeResults').innerHTML = routesHtml;
        document.getElementById('resultsSection').style.display = 'block';
    } else {
        alert(data.message);
    }
});

// Initialisiere Event Listener für bestehende Lösch-Buttons
document.querySelectorAll('.deleteCustomer').forEach(button => {
    button.addEventListener('click', handleDeleteCustomer);
});

document.querySelectorAll('.deleteVehicle').forEach(button => {
    button.addEventListener('click', handleDeleteVehicle);
});

// Zufällige Farbe für Routen generieren
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}