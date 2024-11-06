document.getElementById('customerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const response = await fetch('/add_customer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: document.getElementById('customerName').value,
            address: document.getElementById('customerAddress').value
        })
    });
    const data = await response.json();
    if (data.status === 'success') {
        location.reload();
    } else {
        alert(data.message);
    }
});

document.getElementById('vehicleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const response = await fetch('/add_vehicle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: document.getElementById('vehicleName').value,
            start_address: document.getElementById('startAddress').value
        })
    });
    const data = await response.json();
    if (data.status === 'success') {
        location.reload();
    } else {
        alert(data.message);
    }
});

document.querySelectorAll('.deleteCustomer').forEach(button => {
    button.addEventListener('click', async (e) => {
        const customerId = e.target.getAttribute('data-id');
        const response = await fetch(`/delete_customer/${customerId}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (data.status === 'success') {
            location.reload();
        } else {
            alert(data.message);
        }
    });
});

document.querySelectorAll('.deleteVehicle').forEach(button => {
    button.addEventListener('click', async (e) => {
        const vehicleId = e.target.getAttribute('data-id');
        const response = await fetch(`/delete_vehicle/${vehicleId}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (data.status === 'success') {
            location.reload();
        } else {
            alert(data.message);
        }
    });
});

document.getElementById('optimizeButton').addEventListener('click', async () => {
    const response = await fetch('/optimize_route', {
        method: 'POST',
    });
    const data = await response.json();
    if (data.status === 'success') {
        let routesHtml = '';
        data.routes.forEach(route => {
            routesHtml += `<h3>Fahrzeug: ${route.vehicle}</h3><ul>`;
            route.stops.forEach(stop => {
                routesHtml += `<li>${stop.customer} - ${stop.address}</li>`;
            });
            routesHtml += '</ul>';
        });
        document.getElementById('routeResults').innerHTML = routesHtml;
        document.getElementById('resultsSection').style.display = 'block';
    } else {
        alert(data.message);
    }
});