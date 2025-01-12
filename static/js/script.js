/**************************************************************************
 * Globale Variablen
 **************************************************************************/
let map;                        // Google Map-Objekt
let markers = [];               // Array aller aktuell geladenen Marker
let directionsRenderers = [];   // Array aller DirectionsRenderer für Routen
let optimized_routes = [];      // Globale Variable für optimierte Routen

// Feste Farbpalette (Beispiel: 20 Farben)
const COLORS = [
  "#FF0000","#0000FF","#008000","#FFD700","#FF00FF","#00CED1","#FFA500",
  "#800080","#8B4513","#000000","#C71585","#6495ED","#DC143C","#B8860B",
  "#008B8B","#696969","#708090","#F08080","#808000","#00FF00"
];

window.onload = initMap();
/**************************************************************************
 * 1) initMap():
 *    - Erstellt Google Map
 *    - Lädt Marker
 **************************************************************************/
function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    center: { lat: 51.0237509, lng: 7.535209399 },
    zoom: 9,
    streetViewControl: false,
    mapTypeControl: false
  });
  loadMarkers();
}

/**************************************************************************
 * 2) Marker vom Server laden
 **************************************************************************/
async function loadMarkers() {
  clearMarkers();
  try {
    const response = await fetch('/get_markers');
    const data = await response.json();

    // Patienten: rote Marker
    data.patients.forEach(p => {
      const marker = new google.maps.Marker({
        position: { lat: p.lat, lng: p.lng },
        map: map,
        title: p.name,
        icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
      });
      markers.push(marker);
    });

    // Fahrzeuge: grüne Marker
    data.vehicles.forEach(v => {
      const marker = new google.maps.Marker({
        position: { lat: v.lat, lng: v.lng },
        map: map,
        title: v.name,
        icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
      });
      markers.push(marker);
    });
  } catch (error) {
    console.error("Fehler beim Laden der Marker:", error);
  }
}

/**************************************************************************
 * 3) Marker löschen
 **************************************************************************/
function clearMarkers() {
  markers.forEach(marker => marker.setMap(null));
  markers = [];
}

/**************************************************************************
 * 4) Routen löschen
 **************************************************************************/
function clearRoutes() {
  directionsRenderers.forEach(renderer => renderer.setMap(null));
  directionsRenderers = [];
}

/**************************************************************************
 * 5) calculateRoute():
 *    - Promise-basierte Funktion für DirectionsService
 **************************************************************************/
function calculateRoute(request, directionsRenderer) {
  return new Promise((resolve, reject) => {
    const directionsService = new google.maps.DirectionsService();
    directionsService.route(request, (result, status) => {
      if (status === "OK") {
        directionsRenderer.setDirections(result);
        resolve(result);
      } else {
        console.error("Fehler bei der Routenberechnung:", status);
        reject(status);
      }
    });
  });
}

/**************************************************************************
 * 6) Klick auf "Route optimieren"
 **************************************************************************/
document.getElementById('optimizeButton').addEventListener('click', async () => {
  clearRoutes(); // Alte Routen entfernen
  try {
    const response = await fetch('/optimize_route', { method: 'POST' });
    const data = await response.json();

    if (data.status === 'success') {
      // Wir haben 'data.routes' (nur HB/Neuaufnahme) und 'data.tk_patients' (nur TK)
      displayRoutes(data);
      document.getElementById('resultsSection').style.display = 'block';
    } else {
      alert(data.message || "Fehler bei der Routenoptimierung");
    }
  } catch (error) {
    console.error("Fehler bei /optimize_route:", error);
    alert("Fehler bei /optimize_route. Siehe Konsole.");
  }
});

/**************************************************************************
 * 7) Weitere DOM-Events (Wochentag, etc.)
 **************************************************************************/
document.addEventListener('DOMContentLoaded', function() {
  // Falls du initMap() hier manuell aufrufen willst (keine callback=initMap)
  initMap();

  const weekdaySelect = document.getElementById('weekdaySelect');
  const tomorrowBtn = document.getElementById('tomorrowBtn');

  // Array der Wochentage
  const weekdays = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];

  // Dropdown -> Server
  weekdaySelect.addEventListener('change', function() {
    fetch('/update-weekday', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ weekday: this.value })
    })
    .then(res => res.json())
    .then(data => console.log("Server Response:", data))
    .catch(err => console.error("Error updating weekday:", err));
  });

  // Button "Morgen"
  tomorrowBtn.addEventListener('click', function() {
    const today = new Date();
    const todayIndex = today.getDay();
    const tomorrowIndex = (todayIndex + 1) % 7;
    weekdaySelect.value = weekdays[tomorrowIndex];
    // Trigger 'change'
    weekdaySelect.dispatchEvent(new Event('change'));
  });
});

function displayRoutes(data) {
    clearRoutes();
    const routeResults = document.getElementById('routeResults');
    routeResults.innerHTML = '';
    
    const routesContainer = document.createElement('div');
    routesContainer.className = 'routes-container';
    
    // Routen erstellen
    data.routes.forEach((route, index) => {
        const routeColor = COLORS[index % COLORS.length];
        const routeCard = document.createElement('div');
        routeCard.className = 'route-card';
        routeCard.style.borderColor = routeColor;
        
        // Fahrzeug-Header
        const vehicleHeader = document.createElement('h3');
        vehicleHeader.textContent = `Fahrzeug: ${route.vehicle}`;
        routeCard.appendChild(vehicleHeader);
        
        // Container für verschiebbare Stopps
        const stopsContainer = document.createElement('div');
        stopsContainer.className = 'stops-container';
        stopsContainer.setAttribute('data-vehicle', route.vehicle);
        
        // Filtere TK-Stopps für die Route aus
        const regularStops = route.stops.filter(stop => stop.visit_type !== 'TK');
        
        // Nur reguläre Stopps für die Wegpunkte und Route verwenden
        if (regularStops.length > 0) {
            const waypoints = regularStops.map(s => ({
                location: new google.maps.LatLng(s.location.lat, s.location.lng),
                stopover: true
            }));

            // Route berechnen und anzeigen
            const origin = new google.maps.LatLng(route.vehicle_start.lat, route.vehicle_start.lng);
            const destination = origin;

            const directionsRenderer = new google.maps.DirectionsRenderer({
                map: map,
                suppressMarkers: true,
                preserveViewport: true,
                polylineOptions: {
                    strokeColor: routeColor,
                    strokeOpacity: 0.8,
                    strokeWeight: 4
                }
            });
            directionsRenderers.push(directionsRenderer);

            const request = {
                origin: origin,
                destination: destination,
                waypoints: waypoints,
                travelMode: google.maps.TravelMode.DRIVING,
                optimizeWaypoints: false
            };

            calculateRoute(request, directionsRenderer).catch(err => {
                console.error("Fehler bei der Routenberechnung:", err);
            });
        }

        // Alle Stopps anzeigen
        route.stops.forEach((stop, stopIndex) => {
            const stopCard = document.createElement('div');
            stopCard.className = `stop-card${stop.visit_type === 'TK' ? ' tk-stop' : ''}`;
            stopCard.draggable = true;
            stopCard.innerHTML = `
                ${stop.visit_type !== 'TK' ? `<div class="stop-number">${stopIndex + 1}</div>` : ''}
                <div class="patient-info">
                    <strong>${stop.patient}</strong>
                    <div>${stop.address}</div>
                    <div class="visit-type">${stop.visit_type || ''}</div>
                    <div style="display:none" data-lat="${stop.location.lat}" data-lng="${stop.location.lng}"></div>
                </div>
            `;
            
            stopCard.addEventListener('dragstart', handleDragStart);
            stopCard.addEventListener('dragend', handleDragEnd);
            
            stopsContainer.appendChild(stopCard);
        });
        
        routeCard.appendChild(stopsContainer);
        routesContainer.appendChild(routeCard);
    });
    
    // Nicht zugeordnete TK-Patienten separat anzeigen
    if (data.tk_patients && data.tk_patients.length > 0) {
        const tkCard = document.createElement('div');
        tkCard.className = 'route-card tk-card';
        
        const tkHeader = document.createElement('h3');
        tkHeader.textContent = 'Nicht zugeordnete TK-Fälle';
        tkCard.appendChild(tkHeader);
        
        const tkContainer = document.createElement('div');
        tkContainer.className = 'stops-container';
        tkContainer.setAttribute('data-vehicle', 'tk');
        
        data.tk_patients.forEach(tk => {
            const tkStop = document.createElement('div');
            tkStop.className = 'stop-card tk-stop';
            tkStop.draggable = true;
            tkStop.innerHTML = `
                <div class="patient-info">
                    <strong>${tk.patient}</strong>
                    <div>${tk.address}</div>
                    <div class="visit-type">TK</div>
                    <div style="display:none" data-lat="${tk.location?.lat}" data-lng="${tk.location?.lng}"></div>
                </div>
            `;
            
            tkStop.addEventListener('dragstart', handleDragStart);
            tkStop.addEventListener('dragend', handleDragEnd);
            
            tkContainer.appendChild(tkStop);
        });
        
        tkCard.appendChild(tkContainer);
        routesContainer.appendChild(tkCard);
    }
    
    routeResults.appendChild(routesContainer);
    
    document.querySelectorAll('.stops-container').forEach(container => {
        container.addEventListener('dragover', handleDragOver);
        container.addEventListener('drop', handleDrop);
    });
}

// Drag & Drop Funktionen
function handleDragStart(e) {
    e.target.classList.add('dragging');
    e.dataTransfer.setData('text/plain', e.target.innerHTML);
    // Speichere den Typ des gezogenen Elements
    e.dataTransfer.setData('type', e.target.classList.contains('tk-stop') ? 'tk' : 'regular');
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    const container = e.target.closest('.stops-container');
    if (!container) return;

    const draggingElement = document.querySelector('.dragging');
    if (!draggingElement) return;

    const isTKContainer = container.getAttribute('data-vehicle') === 'tk';
    const isTKStop = draggingElement.classList.contains('tk-stop');
    
    // TK-Container akzeptiert nur TK-Stopps
    if (isTKContainer && !isTKStop) {
        e.dataTransfer.dropEffect = 'none';
        return;
    }
    
    e.dataTransfer.dropEffect = 'move';

    // Entferne vorhandene Drop-Indikatoren
    container.querySelectorAll('.drop-indicator').forEach(el => el.remove());

    const stops = [...container.querySelectorAll('.stop-card:not(.dragging)')];
    const afterElement = getDropPosition(container, e.clientY, isTKStop);
    
    if (afterElement) {
        // Füge Drop-Indikator ein
        const indicator = document.createElement('div');
        indicator.className = 'drop-indicator';
        afterElement.before(indicator);
    } else if (!isTKStop) {
        // Am Ende einfügen (nur für nicht-TK-Stopps)
        const indicator = document.createElement('div');
        indicator.className = 'drop-indicator';
        container.appendChild(indicator);
    }
}

function getDropPosition(container, y, isTKStop) {
    const draggableElements = [...container.querySelectorAll('.stop-card:not(.dragging)')];
    
    if (isTKStop) {
        // TK-Stopps immer ans Ende
        return null;
    }

    // Finde das erste TK-Element
    const firstTKStop = draggableElements.find(el => el.classList.contains('tk-stop'));
    if (firstTKStop) {
        // Filtere TK-Stopps aus
        draggableElements.splice(draggableElements.indexOf(firstTKStop));
    }

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function handleDrop(e) {
    e.preventDefault();
    const draggingElement = document.querySelector('.dragging');
    
    if (draggingElement) {
        const container = e.target.closest('.stops-container');
        if (container) {
            const isTKContainer = container.getAttribute('data-vehicle') === 'tk';
            const isTKStop = draggingElement.classList.contains('tk-stop');
            
            if (isTKContainer && !isTKStop) {
                return;
            }

            // Entferne Drop-Indikatoren
            container.querySelectorAll('.drop-indicator').forEach(el => el.remove());
            
            if (isTKStop) {
                container.appendChild(draggingElement);
            } else {
                const afterElement = getDropPosition(container, e.clientY, isTKStop);
                if (afterElement) {
                    afterElement.before(draggingElement);
                } else {
                    const tkStops = container.querySelectorAll('.tk-stop');
                    if (tkStops.length > 0) {
                        tkStops[0].before(draggingElement);
                    } else {
                        container.appendChild(draggingElement);
                    }
                }
            }
            updateStopNumbers();
            updateOptimizedRoutes();
        }
    }
}

// Neue Funktion zur Aktualisierung der Nummerierung
function updateStopNumbers() {
    document.querySelectorAll('.stops-container').forEach(container => {
        // Nur Nicht-TK-Stopps nummerieren
        const regularStops = container.querySelectorAll('.stop-card:not(.tk-stop)');
        regularStops.forEach((stop, index) => {
            let numberDiv = stop.querySelector('.stop-number');
            if (!numberDiv) {
                numberDiv = document.createElement('div');
                numberDiv.className = 'stop-number';
                stop.insertBefore(numberDiv, stop.firstChild);
            }
            numberDiv.textContent = index + 1;
        });
    });
}

// Neue Funktion zur Aktualisierung der optimierten Routen
function updateOptimizedRoutes() {
    const optimized_routes = [];
    const assigned_tk_stops = new Set(); // Sammle zugewiesene TK-Stopps
    
    // Sammle alle regulären Routen und ihre TK-Stopps
    document.querySelectorAll('.stops-container:not([data-vehicle="tk"])').forEach((container) => {
        const vehicleName = container.getAttribute('data-vehicle');
        const routeInfo = {
            vehicle: vehicleName,
            vehicle_start: null,
            stops: []
        };
        
        // Sammle alle Stopps
        container.querySelectorAll('.stop-card').forEach(stop => {
            const locationDiv = stop.querySelector('[data-lat]');
            const isTKStop = stop.classList.contains('tk-stop');
            
            const stopInfo = {
                patient: stop.querySelector('strong').textContent,
                address: stop.querySelector('.patient-info div').textContent,
                visit_type: isTKStop ? "TK" : stop.querySelector('.visit-type').textContent,
                location: locationDiv ? {
                    lat: parseFloat(locationDiv.dataset.lat),
                    lng: parseFloat(locationDiv.dataset.lng)
                } : null
            };
            
            // Füge den Stopp zu stops hinzu
            routeInfo.stops.push(stopInfo);
            
            // Merke dir zugewiesene TK-Stopps
            if (isTKStop) {
                assigned_tk_stops.add(stopInfo.patient);
            }
        });
        
        optimized_routes.push(routeInfo);
    });
    
    // Sammle nicht zugewiesene TK-Stopps
    const unassigned_tk_stops = [];
    document.querySelector('.stops-container[data-vehicle="tk"]')?.querySelectorAll('.stop-card').forEach(stop => {
        const patient = stop.querySelector('strong').textContent;
        if (!assigned_tk_stops.has(patient)) {
            const locationDiv = stop.querySelector('[data-lat]');
            unassigned_tk_stops.push({
                patient: patient,
                address: stop.querySelector('.patient-info div').textContent,
                visit_type: "TK",
                location: locationDiv ? {
                    lat: parseFloat(locationDiv.dataset.lat),
                    lng: parseFloat(locationDiv.dataset.lng)
                } : null
            });
        }
    });

    fetch('/update_routes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            optimized_routes: optimized_routes,
            unassigned_tk_stops: unassigned_tk_stops
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            clearRoutes();
            displayRoutes(data);
        }
    })
    .catch(error => console.error('Error updating routes:', error));
}
