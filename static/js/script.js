/**************************************************************************
 * Globale Variablen
 **************************************************************************/
let map;                        // Google Map-Objekt
let markers = [];               // Array aller aktuell geladenen Marker
let directionsRenderers = [];   // Array aller DirectionsRenderer für Routen

// Feste Farbpalette (Beispiel: 20 Farben)
const COLORS = [
  "#FF0000","#0000FF","#008000","#FFD700","#FF00FF","#00CED1","#FFA500",
  "#800080","#8B4513","#000000","#C71585","#6495ED","#DC143C","#B8860B",
  "#008B8B","#696969","#708090","#F08080","#808000","#00FF00"
];

/**************************************************************************
 * 1) initMap():
 *    - Erstellt Google Map
 *    - Lädt Marker
 **************************************************************************/
function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    center: { lat: 51.1657, lng: 10.4515 }, // Deutschland-Mitte
    zoom: 6,
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
      let routesHtml = '';

      // Schleife über alle Routen (für HB/Neuaufnahme)
      for (let i = 0; i < data.routes.length; i++) {
        const route = data.routes[i];
        const routeColor = COLORS[i % COLORS.length];

        // HTML-Ausgabe: Fahrzeug + Stopps
        routesHtml += `<h3>Fahrzeug: ${route.vehicle}</h3><ul>`;
        (route.stops || []).forEach(stop => {
          routesHtml += `<li>${stop.patient} - ${stop.address} (${stop.visit_type || ''})</li>`;
        });
        routesHtml += `</ul>`;

        // Falls Stopps existieren => Route zeichnen
        if (route.stops && route.stops.length > 0) {
          // Wegpunkte
          const waypoints = route.stops.map(s => ({
            location: new google.maps.LatLng(s.location.lat, s.location.lng),
            stopover: true
          }));

          // Start- & End-Ort (selbes Fahrzeug)
          const origin = new google.maps.LatLng(route.vehicle_start.lat, route.vehicle_start.lng);
          const destination = origin; // Fahrzeug kehrt zum Start zurück

          // DirectionsRenderer
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

          // DirectionsRequest
          const request = {
            origin: origin,
            destination: destination,
            waypoints: waypoints,
            travelMode: google.maps.TravelMode.DRIVING,
            optimizeWaypoints: false
          };

          try {
            await calculateRoute(request, directionsRenderer);
          } catch (err) {
            console.error("Fehler bei der Routenberechnung:", err);
          }
        }
      }

      // TK-Patienten anzeigen (werden nicht geroutet)
      if (data.tk_patients && data.tk_patients.length > 0) {
        routesHtml += `<h3>Alle TK-Fälle (nicht geroutet)</h3><ul>`;
        data.tk_patients.forEach(tk => {
          routesHtml += `<li>${tk.patient} - ${tk.address} (${tk.visit_type})</li>`;
        });
        routesHtml += `</ul>`;
      }

      document.getElementById('routeResults').innerHTML = routesHtml;
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
