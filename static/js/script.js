let map;
let markers = [];
let routePolylines = [];

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
    routePolylines.forEach(polyline => polyline.setMap(null));
    routePolylines = [];
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

// Initialisiere Event Listener für bestehende Lösch-Buttons
document.querySelectorAll('.deleteCustomer').forEach(button => {
    button.addEventListener('click', handleDeleteCustomer);
});

document.querySelectorAll('.deleteVehicle').forEach(button => {
    button.addEventListener('click', handleDeleteVehicle);
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
        data.routes.forEach((route, index) => {
            const routeColor = getRandomColor();

            // HTML für die Routenliste
            routesHtml += `<h3>Fahrzeug: ${route.vehicle}</h3><ul>`;
            route.stops.forEach(stop => {
                routesHtml += `<li>${stop.customer} - ${stop.address}</li>`;
            });
            routesHtml += '</ul>';

            // Route auf der Karte zeichnen
            const waypoints = [
                { lat: route.vehicle_start.lat, lng: route.vehicle_start.lng },
                ...route.stops.map(stop => ({ lat: stop.location.lat, lng: stop.location.lng })),
                { lat: route.vehicle_start.lat, lng: route.vehicle_start.lng } // Zurück zum Start
            ];

            const polyline = new google.maps.Polyline({
                path: waypoints,
                geodesic: true,
                strokeColor: routeColor,
                strokeOpacity: 1.0,
                strokeWeight: 2
            });

            polyline.setMap(map);
            routePolylines.push(polyline);
        });

        document.getElementById('routeResults').innerHTML = routesHtml;
        document.getElementById('resultsSection').style.display = 'block';
    } else {
        alert(data.message);
    }
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