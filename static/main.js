let logColorIndex = 0;
let lastLogCount = 0;
let db = null;

function $(id) {
    return document.getElementById(id);
}

function collectForm() {
    return {
        method: $("method").value,
        url: $("url").value,
        body: $("body").value,
        headers: $("headers").value,
        proxies: $("proxies").value,
        user_agents: $("user_agents").value,
        interval_ms: parseInt($("interval_ms").value || "1000", 10),
        timeout: parseFloat($("timeout").value || "10"),
        concurrency: parseInt($("concurrency").value || "1", 10),
        max_requests: parseInt($("max_requests").value || "0", 10),
        request_chain: $("request_chain").value,
        mode: $("mode").value,
        proxy_mode: $("proxy_mode").value,
    };
}

function setMethodBehavior() {
    const method = $("method").value.toUpperCase();
    const body = $("body");
    if (method === "GET") {
        body.disabled = true;
        body.classList.add("disabled");
    } else {
        body.disabled = false;
        body.classList.remove("disabled");
    }
}

async function startWorker() {
    const payload = collectForm();
    try {
        const res = await fetch("/api/start", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!data.ok) {
            alert("Start failed: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        alert("Network error: " + e);
    }
}

async function stopWorker() {
    try {
        await fetch("/api/stop", { method: "POST" });
    } catch (e) {
        console.error(e);
    }
}

function updateStats(data) {
    const stats = data.stats || {};
    $("stat-total").textContent = stats.total ?? 0;
    $("stat-success").textContent = stats.success ?? 0;
    $("stat-failed").textContent = stats.failed ?? 0;
    $("stat-last-status").textContent = stats.last_status ?? "-";
    $("stat-last-proxy").textContent = stats.last_proxy ?? "-";
    $("stat-last-error").textContent = stats.last_error ?? "-";
    $("stat-uptime").textContent = stats.uptime ?? 0;

    const stateText = data.running ? "RUNNING" : "IDLE";
    $("stat-state").textContent = stateText;
    const pill = $("state-pill");
    pill.textContent = "STATE: " + stateText;
    if (data.running) {
        pill.classList.add("running");
    } else {
        pill.classList.remove("running");
    }

    // Proxy scores
    const body = $("proxy-body");
    body.innerHTML = "";
    const scores = data.proxy_scores || {};
    Object.keys(scores)
        .sort()
        .forEach((proxy) => {
            const s = scores[proxy].success || 0;
            const f = scores[proxy].failed || 0;
            const score = s - f;
            const row = document.createElement("div");
            row.className = "proxy-row";
            const scoreClass = score >= 0 ? "proxy-score-good" : "proxy-score-bad";
            row.innerHTML = `
                <span>${proxy}</span>
                <span>${s}</span>
                <span>${f}</span>
                <span class="${scoreClass}">${score}</span>
            `;
            body.appendChild(row);
        });

    // Warning panel logic
    const alertPanel = $("alert-panel");
    const alertMessage = $("alert-message");
    if ((stats.failed || 0) > (stats.success || 0) * 2 || stats.last_error !== "-") {
        alertMessage.textContent = `Errors rising: ${stats.last_error}`;
        alertPanel.classList.remove("hidden");
    } else {
        alertPanel.classList.add("hidden");
    }

    // Save proxy history to local DB
    if (stats.last_proxy && stats.last_proxy !== "-") {
        saveProxyRecord(stats.last_proxy, stats.last_error === "-");
    }
}

function updateLogs(data) {
    const logWin = $("log-window");
    const logs = data.logs || [];

    if (logs.length === lastLogCount) {
        return;
    }
    lastLogCount = logs.length;

    logWin.innerHTML = "";
    logs.forEach((entry) => {
        const div = document.createElement("div");
        let cls = "log-line info";
        if (entry.ok === true) cls = "log-line success";
        else if (entry.ok === false) cls = "log-line fail";
        const colorClass = "color-" + (logColorIndex % 5);
        logColorIndex++;
        div.className = `${cls} ${colorClass}`;
        const ts = new Date(entry.ts * 1000).toISOString().split("T")[1].slice(0, 8);
        div.textContent = `[${ts}] ${entry.msg}`;
        logWin.appendChild(div);
    });

    logWin.scrollTop = logWin.scrollHeight;
}

async function pollStatus() {
    try {
        const [sRes, lRes] = await Promise.all([
            fetch("/api/status"),
            fetch("/api/logs"),
        ]);
        const statusData = await sRes.json();
        const logData = await lRes.json();
        if (statusData.ok) updateStats(statusData);
        if (logData.ok) updateLogs(logData);
    } catch (e) {
        console.error("poll error", e);
    }
}

function hookPresetButtons() {
    $("load-from-preset").addEventListener("click", () => {
        try {
            const obj = JSON.parse($("preset-dump").value);
            if (obj.method) $("method").value = obj.method;
            if (obj.url) $("url").value = obj.url;
            if (obj.body) $("body").value = obj.body;
            if (obj.headers) $("headers").value = obj.headers;
            if (obj.proxies) $("proxies").value = obj.proxies;
            if (obj.user_agents) $("user_agents").value = obj.user_agents;
            if (obj.interval_ms) $("interval_ms").value = obj.interval_ms;
            if (obj.timeout) $("timeout").value = obj.timeout;
            if (obj.concurrency) $("concurrency").value = obj.concurrency;
            if (obj.max_requests) $("max_requests").value = obj.max_requests;
            if (obj.request_chain) $("request_chain").value = obj.request_chain;
            if (obj.mode) $("mode").value = obj.mode;
            if (obj.proxy_mode) $("proxy_mode").value = obj.proxy_mode;
            setMethodBehavior();
        } catch (e) {
            alert("Invalid preset JSON");
        }
    });

    $("dump-from-form").addEventListener("click", () => {
        const cfg = collectForm();
        $("preset-dump").value = JSON.stringify(cfg, null, 2);
    });
}

// IndexedDB for proxy history
function initDB() {
    const req = indexedDB.open("nexusflow-db", 1);
    req.onupgradeneeded = (e) => {
        db = e.target.result;
        db.createObjectStore("proxyHistory", { keyPath: "id", autoIncrement: true });
    };
    req.onsuccess = (e) => {
        db = e.target.result;
    };
    req.onerror = (e) => {
        console.error("IndexedDB error", e);
    };
}

function saveProxyRecord(proxy, ok) {
    if (!db) return;
    const tx = db.transaction("proxyHistory", "readwrite");
    const store = tx.objectStore("proxyHistory");
    store.add({
        ts: Date.now(),
        proxy: proxy,
        ok: ok,
    });
}

// Three.js globe
function initGlobe() {
    const canvas = document.getElementById("globe");
    if (!canvas || !window.THREE) return;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true });
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.z = 3;

    const geo = new THREE.SphereGeometry(1, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
        wireframe: true,
        color: 0x00eaff,
        transparent: true,
        opacity: 0.4,
    });
    const sphere = new THREE.Mesh(geo, mat);
    scene.add(sphere);

    function resize() {
        const size = Math.min(window.innerWidth, window.innerHeight) * 0.25;
        canvas.width = size;
        canvas.height = size;
        renderer.setSize(size, size, false);
    }
    resize();
    window.addEventListener("resize", resize);

    function animate() {
        sphere.rotation.y += 0.002;
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }
    animate();
}

document.addEventListener("DOMContentLoaded", () => {
    $("method").addEventListener("change", setMethodBehavior);
    setMethodBehavior();

    $("start-btn").addEventListener("click", startWorker);
    $("stop-btn").addEventListener("click", stopWorker);

    hookPresetButtons();
    initDB();
    initGlobe();

    setInterval(pollStatus, 1000);
});
