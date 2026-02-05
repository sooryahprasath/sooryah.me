lucide.createIcons();

const ui = {
    toggleTheme: () => {
        const isDark = document.documentElement.classList.toggle('dark');
        if (mapLayer.active) map.removeLayer(mapLayer.active);
        setTimeout(() => { mapLayer.active = L.tileLayer(isDark ? mapLayer.dark : mapLayer.light, { maxZoom: 19 }).addTo(map); }, 10);
    },
    
    // LEFT SIDEBAR LOGIC
    toggleTacticalMode: () => {
        // Force Close Right Sidebar if open
        ui.closeSidebar();
        
        const body = document.body;
        const btn = document.getElementById('view-btn-text');
        
        if (body.classList.contains('tactical-active')) {
            body.classList.remove('tactical-active', 'ui-hidden'); 
            btn.innerText = "LIVE TELEMETRY VIEW";
            map.dragging.disable();
            map.flyTo(DEFAULT_CENTER, DEFAULT_ZOOM, { duration: 1.5 });
        } else {
            body.classList.add('tactical-active', 'ui-hidden'); 
            btn.innerText = "EXIT TELEMETRY VIEW";
            map.dragging.enable(); map.invalidateSize();
        }
    },

    // RIGHT SIDEBAR LOGIC
    openFlightSidebar: (data) => {
        // FORCE CLOSE LEFT SIDEBAR if open
        const body = document.body;
        if (body.classList.contains('tactical-active')) {
            body.classList.remove('tactical-active'); // Keep ui-hidden if you want
            document.getElementById('view-btn-text').innerText = "LIVE TELEMETRY VIEW";
        }

        document.body.style.overflow = 'hidden'; // SCROLL LOCK
        document.getElementById('sidebar-title').innerText = "LIVE FLIGHT TELEMETRY";
        document.getElementById('detail-sidebar').classList.add('open');
        selectedHex = data.hex;
        
        const val = (v, unit='') => v !== undefined && v !== null ? `${v}${unit}` : 'N/A';
        document.getElementById('sidebar-content').innerHTML = `
            <div class="p-5 rounded-xl bg-gradient-to-br from-black/10 to-transparent border border-theme">
                <div class="flex justify-between items-start">
                    <div><div class="text-xs text-muted mb-1 font-mono">CALLSIGN</div><div class="text-4xl font-bold text-accent font-mono tracking-tight">${data.flightno || data.callsign || 'N/A'}</div></div>
                    <div class="text-right"><div class="text-xs text-muted mb-1 font-mono">REGISTRATION</div><div class="text-xl font-bold font-mono text-main">${data.reg || 'N/A'}</div></div>
                </div>
                <div class="mt-6 pt-4 border-t border-white/10 flex justify-between items-center">
                    <div><div class="text-xs text-muted mb-1 font-mono">ROUTE</div><div class="text-lg font-bold">${data.route || 'Unknown'}</div></div>
                    <div class="text-right"><div class="text-xs text-muted mb-1 font-mono">TYPE</div><div class="text-lg font-bold font-mono">${data.type || 'N/A'}</div></div>
                </div>
            </div>
            <h3 class="text-xs font-bold text-muted uppercase tracking-widest mt-2">Live Position</h3>
            <div class="tech-grid">
                <div class="tech-item"><div class="tech-label">Altitude</div><div class="tech-val">${val(data.altitude, ' ft')}</div></div>
                <div class="tech-item"><div class="tech-label">Ground Speed</div><div class="tech-val">${val(data.speed, ' kts')}</div></div>
                <div class="tech-item"><div class="tech-label">Heading</div><div class="tech-val">${val(data.heading, '°')}</div></div>
                <div class="tech-item"><div class="tech-label">Latitude</div><div class="tech-val">${val(data.lat)}</div></div>
            </div>
            <div class="p-4 bg-black/5 dark:bg-white/5 rounded border border-theme text-[10px] font-mono text-muted text-center mt-4">HEX: ${data.hex}</div>
        `;
    },
    
    closeSidebar: () => {
        document.body.style.overflow = ''; // UNLOCK SCROLL
        document.getElementById('detail-sidebar').classList.remove('open');
        selectedHex = null;
    },
    
    openAnalyticsModal: () => { document.getElementById('analytics-modal').classList.remove('hidden'); charts.loadAll(); },
    closeAnalyticsModal: () => { document.getElementById('analytics-modal').classList.add('hidden'); }
};

// --- MAP & DATA LOGIC ---
const DEFAULT_CENTER = [12.98, 77.6];
const DEFAULT_ZOOM = 8.4;
const map = L.map('map-container', { zoomControl: false, attributionControl: false, zoomSnap: 0.1, boxZoom: false, doubleClickZoom: false, dragging: false, scrollWheelZoom: false }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
const mapLayer = { dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', light: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', active: null };
mapLayer.active = L.tileLayer(mapLayer.dark, { maxZoom: 19 }).addTo(map);

const markers = {}, polylines = {}, trails = {};
let selectedHex = null;

function getIcon(h, f, r, a, s) {
    return L.divIcon({ className: 'plane-icon-wrapper', html: `<div style="transform: rotate(${h}deg);"><svg width="24" height="24" viewBox="0 0 24 24" fill="#3b82f6" stroke="white" stroke-width="1.5" style="filter: drop-shadow(0 0 4px #000);"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg></div><div class="plane-label"><div class="pl-flight">${f||'N/A'}</div><div class="pl-data">${Math.round(a/100)} | ${Math.round(s)}kt</div></div>`, iconSize: [30, 30], iconAnchor: [15, 15] });
}

async function fetchRadar() {
    try {
        const res = await fetch('/api/live');
        const data = await res.json();
        if (!data || !data.aircraft) return;
        const planes = Object.entries(data.aircraft).map(([h, p]) => ({...p, hex: h})).filter(p => p.lat && p.lon);
        
        document.getElementById('plane-count').innerText = planes.length;
        document.getElementById('status-text').innerText = "SYSTEM ONLINE";
        
        // Mock Stats
        const msgRate = (planes.length * 1.8).toFixed(1);
        document.getElementById('net-rate').innerText = `${msgRate} msg/s`;
        document.getElementById('net-bw').innerText = `${(msgRate * 0.12).toFixed(2)} KB/s`;
        
        // Insight Calculation (Carrier)
        const counts = {};
        planes.forEach(p => { 
            const c = (p.flightno || p.callsign || 'UNK').substring(0,3); 
            if(c !== 'UNK' && c.length === 3) counts[c] = (counts[c]||0)+1; 
        });
        // FIX: Handle empty array gracefully
        const top = Object.keys(counts).length > 0 ? Object.keys(counts).reduce((a,b)=>counts[a]>counts[b]?a:b) : "WAITING...";
        document.getElementById('insight-carrier').innerText = top;
        
        // FIX: Force Integer Math for Average Speed
        const speeds = planes.map(p => parseInt(p.speed || 0)).filter(s => s > 0);
        const avgSpeed = speeds.length ? Math.round(speeds.reduce((a,b)=>a+b, 0)/speeds.length) : 0;
        document.getElementById('insight-speed').innerText = `${avgSpeed} kts`;

        const alts = planes.map(p => p.altitude).filter(a => a);
        const avgAlt = alts.length ? Math.round(alts.reduce((a,b)=>a+b)/alts.length) : 0;
        document.getElementById('insight-alt').innerText = `${avgAlt} ft`;

        if (selectedHex) { const p = planes.find(x => x.hex === selectedHex); if (p) ui.openFlightSidebar(p); }
        
        const currentHexes = new Set();
        planes.forEach(p => {
            currentHexes.add(p.hex);
            const latlng = [p.lat, p.lon];
            const name = p.flightno || p.callsign || p.hex;
            
            if (!trails[p.hex]) trails[p.hex] = [];
            trails[p.hex].push(latlng);
            if (trails[p.hex].length > 60) trails[p.hex].shift();
            if (polylines[p.hex]) polylines[p.hex].setLatLngs(trails[p.hex]);
            else polylines[p.hex] = L.polyline(trails[p.hex], { color: '#3b82f6', weight: 1, opacity: 0.3 }).addTo(map);

            if (markers[p.hex]) { markers[p.hex].setLatLng(latlng); markers[p.hex].setIcon(getIcon(p.heading, name, p.route, p.altitude, p.speed)); }
            else { 
                const m = L.marker(latlng, { icon: getIcon(p.heading, name, p.route, p.altitude, p.speed) }).addTo(map);
                m.on('click', () => ui.openFlightSidebar(p));
                markers[p.hex] = m; 
            }
        });
        Object.keys(markers).forEach(hex => { if(!currentHexes.has(hex)) { map.removeLayer(markers[hex]); delete markers[hex]; } });
    } catch (e) {}
}
setInterval(fetchRadar, 2000); fetchRadar();

// --- CHARTS ---
let chartInstances = {};
const commonOpts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } } };

const charts = {
    currentOffset: 0,
    loadAll: async () => {
        const getData = async (ep) => (await fetch(ep)).json();
        
        // KPIs
        const kpi = await getData('/api/kpi');
        document.getElementById('kpi-unique').innerText = kpi.unique_planes_24h || '--';
        document.getElementById('kpi-speed').innerText = kpi.max_speed_24h || '--';
        document.getElementById('kpi-alt').innerText = kpi.max_alt_24h || '--';

        // 1. Daily Bar
        if(!chartInstances.daily) {
            const d = await getData('/api/daily');
            const ctx = document.getElementById('chart-daily');
            chartInstances.daily = new Chart(ctx, { type: 'bar', data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: '#3b82f6', borderRadius: 4 }] }, options: { ...commonOpts, onClick: (e, els) => { if(els.length) { charts.currentOffset = d.labels.length - 1 - els[0].index; charts.loadVolume(charts.currentOffset, '30m'); } } } });
        }
        
        charts.loadVolume(0, '30m');

        if(!chartInstances.altitude) {
            const d = await getData('/api/altitude');
            chartInstances.altitude = new Chart(document.getElementById('chart-altitude'), { type: 'bar', data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: '#8b5cf6', borderRadius: 4 }] }, options: commonOpts });
        }

        if(!chartInstances.scatter) {
            const d = await getData('/api/scatter');
            chartInstances.scatter = new Chart(document.getElementById('chart-scatter'), { type: 'scatter', data: { datasets: [{ data: d, backgroundColor: 'rgba(245, 158, 11, 0.6)' }] }, options: { ...commonOpts, scales: { x: { min: -80, max: 65, grid: { color: 'rgba(255,255,255,0.05)' } }, y: { min: 0, max: 70000, grid: { color: 'rgba(255,255,255,0.05)' } } } } });
        }

        if(!chartInstances.polar) {
            const d = await getData('/api/direction');
            chartInstances.polar = new Chart(document.getElementById('chart-polar'), { type: 'polarArea', data: { labels: ['N','NE','E','SE','S','SW','W','NW'], datasets: [{ data: d.data, backgroundColor: ['#ef4444','#3b82f6','#eab308','#10b981','#8b5cf6','#f97316','#9ca3af','#6366f1'] }] }, options: { ...commonOpts, scales: { r: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { display: false } } } } });
        }
    },

    changeResolution: (res) => { charts.loadVolume(charts.currentOffset, res); },

    loadVolume: async (offset, bucket) => {
        const d = await (await fetch(`/api/history?offset=${offset}&bucket=${bucket}`)).json();
        const dateStr = offset === 0 ? "Today" : `-${offset} Days`;
        document.getElementById('volume-title').innerText = `Traffic Volume (${dateStr})`;
        
        if(!chartInstances.volume) {
            chartInstances.volume = new Chart(document.getElementById('chart-volume'), { type: 'line', data: { labels: d.labels, datasets: [{ data: d.data, borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.4, pointRadius: 0 }] }, options: commonOpts });
        } else {
            chartInstances.volume.data.labels = d.labels;
            chartInstances.volume.data.datasets[0].data = d.data;
            chartInstances.volume.update();
        }
    }
};