// Initialize Leaflet Map
const map = L.map('map').setView([39.8283, -98.5795], 4); // Center of US

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// State
let routeLayer = null;
let markers = [];

// DOM Elements
const form = document.getElementById('routeForm');
const startInput = document.getElementById('startInput');
const finishInput = document.getElementById('finishInput');
const submitBtn = document.getElementById('submitBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsArea = document.getElementById('resultsArea');
const errorArea = document.getElementById('errorArea');
const errorMsg = document.getElementById('errorMsg');
const stopsList = document.getElementById('stopsList');
const totalDistEl = document.getElementById('totalDist');
const totalCostEl = document.getElementById('totalCost');

// Icons
const stationIcon = L.divIcon({
    className: 'custom-div-icon',
    html: `<div style="background-color: #3b82f6; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6]
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const start = startInput.value.trim();
    const finish = finishInput.value.trim();

    if (!start || !finish) return;

    // UI Updates
    resultsArea.classList.add('hidden');
    errorArea.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-75');

    // Clear Map
    if (routeLayer) map.removeLayer(routeLayer);
    markers.forEach(m => map.removeLayer(m));
    markers = [];

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/route/?start=${encodeURIComponent(start)}&finish=${encodeURIComponent(finish)}&t=${Date.now()}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to calculate route.');
        }

        renderResults(data);
    } catch (err) {
        errorMsg.textContent = err.message;
        errorArea.classList.remove('hidden');
    } finally {
        loadingIndicator.classList.add('hidden');
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-75');
    }
});

function renderResults(data) {
    // 1. Draw Route
    routeLayer = L.geoJSON(data.route_geometry, {
        style: {
            color: '#4f46e5', // indigo-600
            weight: 5,
            opacity: 0.8
        }
    }).addTo(map);

    // Fit map bounds to route
    map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });

    // 2. Render Stops
    stopsList.innerHTML = '';
    
    if (data.fuel_stops && data.fuel_stops.length > 0) {
        data.fuel_stops.forEach((stop, index) => {
            // Draw marker
            const lat = stop.coords[1];
            const lon = stop.coords[0];
            const marker = L.marker([lat, lon], { icon: stationIcon }).addTo(map);
            marker.bindPopup(`<b>${stop.name}</b><br/>$${stop.price_per_gal} / gal`);
            markers.push(marker);

            // Add to list
            const stopEl = document.createElement('div');
            stopEl.className = 'bg-white p-4 rounded-xl shadow-sm border border-slate-100 relative hover:shadow-md transition-shadow cursor-pointer';
            stopEl.innerHTML = `
                <div class="absolute -left-2 -top-2 bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm">
                    ${index + 1}
                </div>
                <h4 class="font-bold text-slate-800 text-sm mb-1">${stop.name}</h4>
                <div class="flex justify-between items-end text-xs text-slate-500">
                    <div>
                        <p>Route Dist: <span class="font-medium text-slate-700">${stop.route_dist} mi</span></p>
                        <p>Price: <span class="font-medium text-slate-700">$${stop.price_per_gal}/gal</span></p>
                    </div>
                    <div class="text-right">
                        <p class="font-bold text-green-600 text-sm">+$${stop.leg_cost}</p>
                        <p>${stop.gallons_purchased} gal</p>
                    </div>
                </div>
            `;
            
            // Pan map on click
            stopEl.addEventListener('click', () => {
                map.setView([lat, lon], 13);
                marker.openPopup();
            });
            
            stopsList.appendChild(stopEl);
        });
    } else {
        stopsList.innerHTML = `<p class="text-sm text-slate-500 italic">No fuel stops needed for this trip!</p>`;
    }

    // 3. Update Stats
    totalDistEl.textContent = `${Math.round(data.total_distance_miles).toLocaleString()} mi`;
    totalCostEl.textContent = `$${data.total_fuel_cost.toFixed(2)}`;

    // Show Results
    resultsArea.classList.remove('hidden');
}
