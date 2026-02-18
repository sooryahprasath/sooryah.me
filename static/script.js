lucide.createIcons();

const ui = {
    toggleTheme: () => {
        const isDark = document.documentElement.classList.toggle('dark');
        if (mapLayer.active) map.removeLayer(mapLayer.active);
        setTimeout(() => { mapLayer.active = L.tileLayer(isDark ? mapLayer.dark : mapLayer.light, { maxZoom: 19 }).addTo(map); }, 10);
    },
    
    toggleTacticalMode: () => {
        ui.closeSidebar(); 
        const body = document.body;
        const btn = document.getElementById('view-btn-text');
        
        if (body.classList.contains('tactical-active')) {
            body.classList.remove('tactical-active', 'ui-hidden'); 
            btn.innerText = "LIVE TELEMETRY VIEW";
            map.scrollWheelZoom.disable();
            map.flyTo(DEFAULT_CENTER, DEFAULT_ZOOM, { duration: 1.5 });
        } else {
            body.classList.add('tactical-active', 'ui-hidden'); 
            btn.innerText = "EXIT TELEMETRY VIEW";
            map.dragging.enable(); 
            map.scrollWheelZoom.enable();
            map.invalidateSize(); 
        }
    },

    openFlightSidebar: (data) => {
        if (document.body.classList.contains('tactical-active')) {
            document.getElementById('view-btn-text').innerText = "LIVE TELEMETRY VIEW";
        }
        document.body.classList.add('overflow-hidden');
        document.getElementById('sidebar-title').innerText = "LIVE FLIGHT TELEMETRY";
        document.getElementById('detail-sidebar').classList.add('open');
        selectedHex = data.hex;
        
        const val = (v, unit='') => v !== undefined && v !== null ? `${v}${unit}` : 'N/A';
        document.getElementById('sidebar-content').innerHTML = `
            <div class="p-5 rounded-xl bg-gradient-to-br from-black/10 to-transparent border border-theme">
                <div class="flex justify-between items-start mb-3">
                    <div><div class="text-xs text-muted mb-1 font-mono">CALLSIGN</div><div class="text-3xl font-bold text-accent font-mono tracking-tight leading-none">${data.flightno || data.callsign || 'N/A'}</div></div>
                    <div class="text-right"><div class="text-xs text-muted mb-1 font-mono">REGISTRATION</div><div class="text-xl font-bold font-mono text-main leading-none">${data.reg || 'N/A'}</div></div>
                </div>
                <div class="flex justify-between items-center border-t border-white/10 pt-3">
                    <div><div class="text-xs text-muted font-mono">ROUTE</div><div class="text-base font-bold">${data.route || 'Unknown'}</div></div>
                    <div class="text-right"><div class="text-xs text-muted font-mono">TYPE</div><div class="text-base font-bold font-mono">${data.type || 'N/A'}</div></div>
                </div>
            </div>
            <div class="space-y-2 mt-2">
                <h3 class="text-xs font-bold text-muted uppercase tracking-widest">Dynamics</h3>
                <div class="tech-grid gap-3">
                    <div class="tech-item p-3"><div class="tech-label">Altitude</div><div class="tech-val text-accent text-lg">${val(data.altitude, ' ft')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Vert Rate</div><div class="tech-val text-lg">${val(data.vert_rate, ' fpm')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Ground Speed</div><div class="tech-val text-lg">${val(data.speed, ' kts')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Track</div><div class="tech-val text-lg">${val(data.track_angle, '°')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Distance</div><div class="tech-val text-lg">${val(data.polar_distance, ' nm')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Lat/Lon</div><div class="tech-val text-sm">${val(data.lat).substring(0,6)} / ${val(data.lon).substring(0,6)}</div></div>
                </div>
            </div>
            <div class="space-y-2 mt-2">
                <h3 class="text-xs font-bold text-muted uppercase tracking-widest">Sensors</h3>
                <div class="tech-grid gap-3">
                    <div class="tech-item p-3"><div class="tech-label">Squawk</div><div class="tech-val text-accent text-lg">${val(data.squawk)}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Category</div><div class="tech-val text-lg">${val(data.category)}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Air Temp</div><div class="tech-val text-lg">${val(data.oat, '°C')}</div></div>
                    <div class="tech-item p-3"><div class="tech-label">Wind</div><div class="tech-val text-lg">${val(data.wind_speed, ' kts')}</div></div>
                </div>
            </div>
            <div class="p-3 bg-black/5 dark:bg-white/5 rounded border border-theme text-[10px] font-mono text-muted text-center mt-4">HEX: ${data.hex} | MSG AGE: ${data.age || 0}s</div>
        `;
    },
    
    closeSidebar: () => {
        document.body.classList.remove('overflow-hidden'); 
        document.getElementById('detail-sidebar').classList.remove('open');
        selectedHex = null;
        if (document.body.classList.contains('tactical-active')) {
            document.getElementById('view-btn-text').innerText = "EXIT TELEMETRY VIEW";
        } else {
            document.getElementById('view-btn-text').innerText = "LIVE TELEMETRY VIEW";
        }
    },
    
    openProjectSidebar: (key) => { 
        const data = PROJECT_DATA[key];
        document.getElementById('sidebar-title').innerText = "PROJECT ARCHITECTURE";
        let specsHtml = data.specs.map(s => `<div class="flex justify-between items-center py-2 border-b border-white/5"><span class="text-xs text-muted font-mono uppercase">${s.label}</span><span class="text-sm font-bold text-right">${s.value}</span></div>`).join('');
        document.getElementById('sidebar-content').innerHTML = `<div><h2 class="text-2xl font-bold text-accent mb-1">${data.title}</h2><p class="text-xs font-mono text-muted border-b border-theme pb-4">${data.subtitle}</p></div><div class="text-sm leading-relaxed text-main/80 bg-black/5 dark:bg-white/5 p-4 rounded-lg border border-theme">${data.description}</div><div class="flex flex-col gap-1 mt-2">${specsHtml}</div>`;
        const footer = document.getElementById('sidebar-footer');
        if(data.link) { footer.innerHTML = `<a href="${data.link}" target="_blank" class="w-full btn-glass py-3 rounded-lg flex justify-center items-center gap-2 font-bold hover:bg-accent hover:text-white transition">OPEN LIVE VIEW <i data-lucide="external-link" class="w-4 h-4"></i></a>`; footer.classList.remove('hidden'); } else { footer.classList.add('hidden'); }
        document.getElementById('detail-sidebar').classList.add('open');
    },
    openAnalyticsModal: () => { document.getElementById('analytics-modal').classList.remove('hidden'); charts.loadAll(); },
    closeAnalyticsModal: () => { document.getElementById('analytics-modal').classList.add('hidden'); },

    // APPENDED: Traffic Modal
    openTrafficModal: () => { 
        document.getElementById('traffic-modal').classList.remove('hidden'); 
        // This sets the src of our new <img> tag
        document.getElementById('traffic-stream').src = "https://traffic.sooryah.me/video_feed";
        charts.loadTrafficHistory(); 
    },
    closeTrafficModal: () => { 
        document.getElementById('traffic-modal').classList.add('hidden'); 
        // clear src to save bandwidth when closed
        document.getElementById('traffic-stream').src = ""; 
    }
};

// --- MAP ENGINE ---
const DEFAULT_CENTER = [12.98, 77.6];
const DEFAULT_ZOOM = 8.4;
const map = L.map('map-container', { 
    zoomControl: false, attributionControl: false, zoomSnap: 0.1, boxZoom: false, 
    doubleClickZoom: true, dragging: true, scrollWheelZoom: true 
}).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

const mapLayer = { dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', light: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', active: null };
mapLayer.active = L.tileLayer(mapLayer.dark, { maxZoom: 19 }).addTo(map);

const markers = {}, polylines = {}, trails = {};
let selectedHex = null;

function getIcon(h, f, r, a, s) { return L.divIcon({ className: 'plane-icon-wrapper', html: `<div style="transform: rotate(${h}deg);"><svg width="24" height="24" viewBox="0 0 24 24" fill="#3b82f6" stroke="white" stroke-width="1.5" style="filter: drop-shadow(0 0 4px #000);"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg></div><div class="plane-label"><div class="pl-flight">${f||'N/A'}</div><div class="pl-data">${Math.round(a/100)} | ${Math.round(s)}kt</div></div>`, iconSize: [30, 30], iconAnchor: [15, 15] }); }

async function fetchRadar() {
    try {
        const res = await fetch('/api/live');
        const data = await res.json();
        const aircraft = data.aircraft || {};
        const planes = Object.entries(aircraft).map(([h, p]) => ({...p, hex: h})).filter(p => p.lat && p.lon);
        document.getElementById('plane-count').innerText = planes.length;
        
        const statusText = document.getElementById('status-text');
        const statusDot = document.getElementById('status-dot');
        if (planes.length > 0) { statusText.innerText = "SYSTEM ONLINE"; statusDot.className = "w-2 h-2 rounded-full bg-green-500 animate-pulse"; } 
        else { statusText.innerText = "WAITING FOR TRAFFIC"; statusDot.className = "w-2 h-2 rounded-full bg-amber-500 animate-pulse"; }

        const msgRate = (planes.length * 1.8).toFixed(1);
        document.getElementById('net-rate').innerText = `${msgRate} msg/s`;
        document.getElementById('net-bw').innerText = `${(msgRate * 0.12).toFixed(2)} KB/s`;
        
        const counts = {};
        planes.forEach(p => { let c = (p.flightno || p.callsign || '').substring(0,3); if (c && c.length === 3) counts[c] = (counts[c]||0)+1; });
        const top = Object.keys(counts).length > 0 ? Object.keys(counts).reduce((a,b)=>counts[a]>counts[b]?a:b) : "WAITING...";
        document.getElementById('insight-carrier').innerText = top;
        
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
            
            // MEMORY LIMIT: 3-minute limit for map trails (90 points @ 2s interval)
            if (!trails[p.hex]) trails[p.hex] = []; 
            trails[p.hex].push(latlng); 
            if (trails[p.hex].length > 90) trails[p.hex].shift(); 

            if (polylines[p.hex]) polylines[p.hex].setLatLngs(trails[p.hex]); 
            else polylines[p.hex] = L.polyline(trails[p.hex], { color: '#3b82f6', weight: 1, opacity: 0.3 }).addTo(map);
            
            if (markers[p.hex]) { markers[p.hex].setLatLng(latlng); markers[p.hex].setIcon(getIcon(p.heading, name, p.route, p.altitude, p.speed)); }
            else { const m = L.marker(latlng, { icon: getIcon(p.heading, name, p.route, p.altitude, p.speed) }).addTo(map); m.on('click', () => ui.openFlightSidebar(p)); markers[p.hex] = m; }
        });
        Object.keys(markers).forEach(hex => { if(!currentHexes.has(hex)) { map.removeLayer(markers[hex]); delete markers[hex]; } });
    } catch (e) {}
}
setInterval(fetchRadar, 2000); fetchRadar();

// --- CHART ENGINE ---
let chartInstances = {};
const commonOpts = { 
    responsive: true, 
    maintainAspectRatio: false, 
    plugins: { legend: { display: false } }, 
    interaction: { mode: 'index', intersect: false }, 
    scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } } 
};

const charts = {
    currentRange: '24h',

    loadAll: async () => {
        const getData = async (ep) => (await fetch(ep)).json();
        const kpi = await getData('/api/kpi');
        document.getElementById('kpi-unique').innerText = kpi.unique !== undefined ? kpi.unique : '--';
        document.getElementById('kpi-speed').innerText = kpi.speed || '--';
        document.getElementById('kpi-alt').innerText = kpi.alt || '--';

        if(!chartInstances.daily) {
            const d = await getData('/api/daily');
            chartInstances.daily = new Chart(document.getElementById('chart-daily'), { type: 'bar', data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: '#3b82f6', borderRadius: 4 }] }, options: commonOpts });
        }
        charts.loadVolume('24h');
        if(!chartInstances.altitude) {
            const d = await getData('/api/altitude');
            chartInstances.altitude = new Chart(document.getElementById('chart-altitude'), { type: 'bar', data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: '#8b5cf6', borderRadius: 4 }] }, options: commonOpts });
        }
        if(!chartInstances.scatter) {
            const d = await getData('/api/scatter');
            chartInstances.scatter = new Chart(document.getElementById('chart-scatter'), { type: 'scatter', data: { datasets: [{ data: d, backgroundColor: 'rgba(245, 158, 11, 0.6)' }] }, options: commonOpts });
        }
        if(!chartInstances.polar) {
            const d = await getData('/api/direction');
            chartInstances.polar = new Chart(document.getElementById('chart-polar'), { type: 'polarArea', data: { labels: ['N','NE','E','SE','S','SW','W','NW'], datasets: [{ data: d.data, backgroundColor: ['#ef4444','#3b82f6','#eab308','#10b981','#8b5cf6','#f97316','#9ca3af','#6366f1'] }] }, options: commonOpts });
        }
    },

    changeResolution: (range) => { charts.currentRange = range; charts.loadVolume(range); },

    loadVolume: async (range) => {
        const d = await (await fetch(`/api/history?range_type=${range}`)).json();
        document.getElementById('volume-title').innerText = `Traffic Volume (${range})`;
        if(!chartInstances.volume) {
            chartInstances.volume = new Chart(document.getElementById('chart-volume'), { type: 'line', data: { labels: d.labels, datasets: [{ data: d.data, borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.4, pointRadius: 0 }] }, options: commonOpts });
        } else {
            chartInstances.volume.data.labels = d.labels;
            chartInstances.volume.data.datasets[0].data = d.data;
            chartInstances.volume.update();
        }
    }
};

// APPENDED: Traffic Polling
// Global variable to store last log so we don't repeat
let lastLogMsg = "";

let lastLogMsg = ""; // Keep track of the last log to avoid duplicates

async function syncTrafficStats() {
    try {
        // 1. Fetch the data
        const res = await fetch('https://traffic.sooryah.me/api/stats');
        const data = await res.json();
        
        let totalCount = 0;
        let gridHTML = '';
        
        // 2. Loop through the JSON data
        for (const [key, value] of Object.entries(data)) {
            
            // SKIP the "log" key (it's text, not a count)
            if (key === 'log') continue;

            // Process Numbers (CAR: 1, PERSON: 2)
            if (typeof value === 'number' && value > 0) {
                totalCount += value;
                
                // Create a glass-morphism box for each detection
                gridHTML += `
                    <div class="bg-emerald-900/30 border border-emerald-500/30 rounded px-2 py-2 flex flex-col items-center justify-center animate-pulse">
                        <span class="text-xl font-bold text-white leading-none">${value}</span>
                        <span class="text-[8px] font-bold text-emerald-400 uppercase mt-1 tracking-wider">${key}</span>
                    </div>
                `;
            }
        }

        // 3. Update the Big Total Number
        const totalEl = document.getElementById('modal-live-cars');
        if (totalEl) totalEl.innerText = totalCount;

        // 4. Update the Breakdown Grid
        const gridEl = document.getElementById('traffic-breakdown');
        if (gridEl) {
            if (totalCount === 0) {
                gridEl.innerHTML = `<div class="col-span-3 text-center text-[10px] text-gray-500 font-mono py-2">-- SCANNING SECTOR --</div>`;
            } else {
                gridEl.innerHTML = gridHTML;
            }
        }

        // 5. Update the "Chat" Log (Only if it changed)
        if (data.log && data.log !== lastLogMsg) {
            lastLogMsg = data.log;
            const logContainer = document.getElementById('traffic-log');
            if (logContainer) {
                const newEntry = document.createElement('div');
                // Matrix style green text
                newEntry.className = "text-emerald-400/90 border-b border-emerald-500/10 py-1 truncate hover:whitespace-normal transition-all";
                newEntry.innerText = `> ${data.log}`;
                
                // Add to top
                logContainer.prepend(newEntry);
                
                // Keep history clean (max 10 items)
                if (logContainer.children.length > 10) {
                    logContainer.removeChild(logContainer.lastChild);
                }
            }
        }

    } catch (e) {
        // console.error("Sync Error:", e); // Uncomment for debugging
    }
}

// Poll every 1 second (1000ms)
setInterval(syncTrafficStats, 1000);


const PROJECT_DATA = {
    adsb: { 
        title: "RF & IoT Sensor Networks", 
        subtitle: "Station ID: CustardLev | Bengaluru", 
        description: `
            <p class="mb-4"><strong>Operational since 2016.</strong> My journey into RF started with a generic DVB-T dongle and a 6.9cm quarter-wave antenna (my first attempt at tuning). Over the years, I iterated through Spider and Cantenna designs to optimize gain.</p>
            <p class="mb-4">Today, the station runs on a custom-built <strong>2ft Collinear Coaxial (CoCo)</strong> antenna mounted 50ft AGL on my roof, providing 360° horizon visibility.</p>
            <p>It feeds real-time flight data to FlightRadar24, FlightAware, and this portfolio.</p>
        `, 
        specs: [
            { label: "Host", value: "Raspberry Pi 2 Model B" }, 
            { label: "Radio", value: "RTL-SDR Blog V3 TCXO" },
            { label: "LNA / Filter", value: "Nooelec ADS-B (SAW+LNA)" },
            { label: "Antenna", value: "Custom 2ft Coaxial Collinear" },
            { label: "Software", value: "Dump1090-fa, Piaware" },
            { label: "Range", value: "~180 Nautical Miles" }
        ], 
        link: "https://planes.custardlev.uk" 
    },
    telemetry: { 
        title: "Enterprise Telemetry Pipeline", 
        subtitle: "Data Engineering", 
        description: "Centralized pipeline utilizing Apache Airflow and Azure SQL to ingest real-time data from 150+ global sites, feeding dynamic Power BI dashboards.", 
        specs: [
            { label: "Orchestration", value: "Apache Airflow" },
            { label: "Database", value: "Azure SQL (Managed Instance)" },
            { label: "Language", value: "Python (Pandas, PyODBC)" },
            { label: "Visualization", value: "Power BI Pro" },
            { label: "Latency", value: "< 2 Minutes End-to-End" }
        ], 
        link: null 
    },
    cloud: { 
        title: "Private Cloud Cluster", 
        subtitle: "Homelab", 
        description: "Production-grade home infrastructure. A 3-node Proxmox cluster running Kubernetes (K3s), automation pools, and storage nodes.", 
        specs: [
            { label: "Hypervisor", value: "Proxmox VE 8.1" }, 
            { label: "Orchestrator", value: "Kubernetes (K3s)" },
            { label: "Storage", value: "ZFS RaidZ1 Pool" },
            { label: "Networking", value: "Tailscale Mesh VPN" },
            { label: "Ingress", value: "Traefik + Cloudflare Tunnel" }
        ], 
        link: null 
    }
};