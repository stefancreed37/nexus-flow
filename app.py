import random
import time
import threading
import json
from collections import deque, defaultdict

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
)

# Optional Playwright support
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    PLAYWRIGHT_AVAILABLE = False

app = Flask(__name__)
# CHANGE THIS IN YOUR LOCAL COPY
app.secret_key = "CHANGE_ME_SUPER_SECRET"
MASTER_PASSWORD = "nexusflow"  # simple login password, change locally

# --------------------------------------------------------------------
# Runtime state
# --------------------------------------------------------------------
state_lock = threading.Lock()
runtime_state = {
    "running": False,
    "config": {},
    "stats": {
        "total": 0,
        "success": 0,
        "failed": 0,
        "last_status": "-",
        "last_error": "-",
        "last_proxy": "-",
        "start_time": None,
    },
    "proxy_scores": defaultdict(lambda: {"success": 0, "failed": 0}),
    "logs": deque(maxlen=300),
    "max_requests": 0,
}


def add_log(message, ok=None):
    """Append a log entry to the ring buffer.

    ok = True  -> success
    ok = False -> failure
    ok = None  -> info
    """
    with state_lock:
        runtime_state["logs"].append(
            {
                "ts": time.time(),
                "msg": message,
                "ok": ok,
            }
        )


def parse_headers(text: str):
    headers = {}
    if not text:
        return headers
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


def parse_body(text: str):
    if not text or not text.strip():
        return None
    stripped = text.strip()
    # Try JSON first
    try:
        return json.loads(stripped)
    except Exception:
        # Raw string fallback
        return stripped


def parse_proxies(text: str):
    proxies = []
    if not text:
        return proxies
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        proxies.append(line)
    return proxies


def parse_user_agents(text: str):
    uas = []
    if not text:
        return uas
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        uas.append(line)
    return uas


def parse_request_chain(text: str):
    if not text or not text.strip():
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        add_log(f"Request chain JSON error: {e}", ok=False)
        return []


def choose_user_agent(user_agents):
    if not user_agents:
        return None
    return random.choice(user_agents)


def choose_proxy(proxies, proxy_mode="rotate"):
    """Choose which proxy (or direct) to use.

    proxy_mode:
      - "direct"            -> always use your real IP (no proxy)
      - "rotate"            -> pick random proxy each time
      - "my_ip_plus_proxy"  -> mix direct + proxies
    """
    if proxy_mode == "direct":
        return None

    if not proxies:
        return None

    if proxy_mode == "my_ip_plus_proxy":
        # 50% direct, 50% proxy
        if random.random() < 0.5:
            return None

    # default: rotate
    return random.choice(proxies)


def normalize_proxy(proxy_str):
    """Return (requests_proxies_dict, proxy_url_for_playwright)."""
    if not proxy_str:
        return None, None

    if proxy_str.startswith(("socks5://", "socks4://", "http://", "https://")):
        proxy_url = proxy_str
    else:
        # Guess socks for typical ports, otherwise HTTP
        if any(proxy_str.endswith(f":{p}") for p in ["1080", "9050", "10800"]):
            proxy_url = f"socks5://{proxy_str}"
        else:
            proxy_url = f"http://{proxy_str}"

    proxies = {"http": proxy_url, "https": proxy_url}
    return proxies, proxy_url


def update_stats_after_request(ok, status_code, parsed_kind, error_msg, proxy_str):
    with state_lock:
        stats = runtime_state["stats"]
        stats["total"] += 1

        if ok:
            stats["success"] += 1
            stats["last_status"] = f"{status_code} ({parsed_kind})"
            stats["last_error"] = "-"
        else:
            stats["failed"] += 1
            stats["last_status"] = f"{status_code or 'ERR'}"
            stats["last_error"] = error_msg or f"HTTP {status_code}"

        stats["last_proxy"] = proxy_str or "-"

        if proxy_str:
            proxy_scores = runtime_state["proxy_scores"]
            if ok:
                proxy_scores[proxy_str]["success"] += 1
            else:
                proxy_scores[proxy_str]["failed"] += 1


def perform_request(base_cfg, task_overrides, proxy_str):
    method = (task_overrides.get("method") or base_cfg.get("method") or "GET").upper()
    url = task_overrides.get("url") or base_cfg.get("url")
    timeout = float(base_cfg.get("timeout", 10))

    headers = {}
    headers.update(base_cfg.get("headers", {}))
    headers.update(task_overrides.get("headers", {}))

    ua = choose_user_agent(base_cfg.get("user_agents", []))
    if ua:
        headers.setdefault("User-Agent", ua)

    data = task_overrides.get("data", base_cfg.get("body"))

    # VIEW MODE: GET -> disable body, add browser-like defaults
    if method == "GET":
        headers.setdefault(
            "User-Agent",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        )
        headers.setdefault(
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        headers.setdefault("Connection", "keep-alive")
        data = None

    if proxy_str:
        proxies, _ = normalize_proxy(proxy_str)
    else:
        proxies = None

    start = time.time()
    ok = False
    status_code = None
    parsed_kind = "unknown"
    error_msg = ""

    try:
        if isinstance(data, dict) and method != "GET":
            response = requests.request(
                method,
                url,
                headers=headers,
                json=data,
                proxies=proxies,
                timeout=timeout,
            )
        else:
            response = requests.request(
                method,
                url,
                headers=headers,
                data=data,
                proxies=proxies,
                timeout=timeout,
            )
        elapsed_ms = (time.time() - start) * 1000.0
        status_code = response.status_code

        content_type = response.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            try:
                _ = response.json()
                parsed_kind = "json"
            except Exception:
                parsed_kind = "text"
        elif "text/html" in content_type:
            parsed_kind = "html"
        else:
            try:
                _ = response.json()
                parsed_kind = "json"
            except Exception:
                parsed_kind = "text"

        ok = 200 <= status_code < 400

        msg = (
            f"[{status_code}] {method} {url} via {proxy_str or 'direct'} "
            f"in {elapsed_ms:.0f} ms ({parsed_kind})"
        )
        add_log(msg, ok=ok)

    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000.0
        error_msg = str(e)
        msg = (
            f"[ERROR] {method} {url} via {proxy_str or 'direct'} "
            f"failed after {elapsed_ms:.0f} ms: {error_msg}"
        )
        add_log(msg, ok=False)

    update_stats_after_request(ok, status_code, parsed_kind, error_msg, proxy_str)


def perform_playwright(base_cfg, task_overrides, proxy_str):
    """Browser mode using Playwright (Chromium)."""
    url = task_overrides.get("url") or base_cfg.get("url")
    timeout = float(base_cfg.get("timeout", 10))

    start = time.time()
    ok = False
    status_code = None
    parsed_kind = "html"
    error_msg = ""

    if not PLAYWRIGHT_AVAILABLE:
        error_msg = (
            "Playwright not installed. Run: "
            "pip install playwright && playwright install chromium"
        )
        add_log(f"[PLAYWRIGHT ERROR] {url}: {error_msg}", ok=False)
        update_stats_after_request(False, status_code, parsed_kind, error_msg, proxy_str)
        return

    _, proxy_url = normalize_proxy(proxy_str) if proxy_str else (None, None)

    try:
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if proxy_url:
                launch_kwargs["proxy"] = {"server": proxy_url}

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context()
            page = context.new_page()

            response = page.goto(url, timeout=timeout * 1000)
            page.wait_for_timeout(1000)

            status_code = response.status if response else 0

            ok = 200 <= status_code < 400
            elapsed_ms = (time.time() - start) * 1000.0
            msg = (
                f"[{status_code}] PLAYWRIGHT {url} via {proxy_str or 'direct'} "
                f"in {elapsed_ms:.0f} ms (html)"
            )
            add_log(msg, ok=ok)

            browser.close()
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000.0
        error_msg = str(e)
        msg = (
            f"[PLAYWRIGHT ERROR] {url} via {proxy_str or 'direct'} "
            f"failed after {elapsed_ms:.0f} ms: {error_msg}"
        )
        add_log(msg, ok=False)

    update_stats_after_request(ok, status_code, parsed_kind, error_msg, proxy_str)


def worker_loop():
    while True:
        time.sleep(0.01)
        with state_lock:
            running = runtime_state["running"]
            cfg = runtime_state["config"]
            stats = runtime_state["stats"]
            max_requests = runtime_state["max_requests"]
            total_so_far = stats["total"]

        if not running:
            continue

        if max_requests > 0 and total_so_far >= max_requests:
            with state_lock:
                runtime_state["running"] = False
            add_log("Max requests reached, stopping worker.", ok=None)
            continue

        interval_ms = int(cfg.get("interval_ms", 1000))
        concurrency = int(cfg.get("concurrency", 1))
        proxies = cfg.get("proxies", [])
        proxy_mode = cfg.get("proxy_mode", "rotate")
        request_chain = cfg.get("request_chain", []) or [{}]

        for _ in range(concurrency):
            for chain_step in request_chain:
                proxy_str = choose_proxy(proxies, proxy_mode)
                step_mode = chain_step.get("mode") or cfg.get("mode", "http")
                if step_mode == "playwright":
                    target_fn = perform_playwright
                else:
                    target_fn = perform_request

                threading.Thread(
                    target=target_fn,
                    args=(cfg, chain_step, proxy_str),
                    daemon=True,
                ).start()

        time.sleep(max(interval_ms / 1000.0, 0.01))


worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()

# --------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------
@app.before_request
def require_login():
    # allow login + static files unauthenticated
    if request.path.startswith("/static"):
        return
    if request.path == "/login":
        return
    if not session.get("auth"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == MASTER_PASSWORD:
            session["auth"] = True
            return redirect(url_for("index"))
        return "Wrong password", 403
    # simple inline HTML, UI is not important here
    return """<!doctype html>
<html><head><title>NexusFlow Login</title></head>
<body style="background:#050014;color:#f5f5ff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;">
<form method="POST" style="background:#090020;border:1px solid #00f6ff;padding:20px;border-radius:10px;min-width:260px;">
    <h2 style="margin-top:0;margin-bottom:10px;">NexusFlow Login</h2>
    <input type="password" name="password" placeholder="Password" style="width:100%;padding:8px;margin-bottom:10px;background:#000;color:#f5f5ff;border:1px solid #333;border-radius:6px;">
    <button style="width:100%;padding:8px;background:#00f6ff;color:#050014;border:none;border-radius:6px;cursor:pointer;">Enter</button>
</form>
</body></html>"""


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(force=True)

    method = data.get("method", "GET").upper()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"ok": False, "error": "Target URL is required."}), 400

    body_text = data.get("body", "")
    headers_text = data.get("headers", "")
    proxies_text = data.get("proxies", "")
    user_agents_text = data.get("user_agents", "")
    chain_text = data.get("request_chain", "")

    headers = parse_headers(headers_text)
    body = parse_body(body_text)
    proxies = parse_proxies(proxies_text)
    user_agents = parse_user_agents(user_agents_text)
    request_chain = parse_request_chain(chain_text)

    interval_ms = int(data.get("interval_ms", 1000))
    timeout = float(data.get("timeout", 10))
    concurrency = int(data.get("concurrency", 1))
    max_requests = int(data.get("max_requests", 0))

    mode = data.get("mode", "http")  # "http" or "playwright"
    proxy_mode = data.get("proxy_mode", "rotate")  # "direct", "rotate", "my_ip_plus_proxy"

    cfg = {
        "method": method,
        "url": url,
        "body": body,
        "headers": headers,
        "proxies": proxies,
        "user_agents": user_agents,
        "interval_ms": interval_ms,
        "timeout": timeout,
        "concurrency": concurrency,
        "request_chain": request_chain,
        "mode": mode,
        "proxy_mode": proxy_mode,
    }

    # --------- PLAYWRIGHT PRE-TEST -----------
    if mode == "playwright":
        test_proxy = choose_proxy(proxies, proxy_mode)
        _, proxy_url = normalize_proxy(test_proxy) if test_proxy else (None, None)
        try:
            if not PLAYWRIGHT_AVAILABLE:
                return jsonify({"ok": False, "error": "Playwright not installed"}), 400

            with sync_playwright() as p:
                launch_kwargs = {"headless": True}
                if proxy_url:
                    launch_kwargs["proxy"] = {"server": proxy_url}
                browser = p.chromium.launch(**launch_kwargs)
                page = browser.new_page()
                r = page.goto(url, timeout=timeout * 1000)
                if not r or r.status >= 400:
                    browser.close()
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": f"Pre-test failed: HTTP {getattr(r, 'status', '0')}",
                            }
                        ),
                        400,
                    )
                browser.close()
        except Exception as e:
            return jsonify({"ok": False, "error": f"Pre-test error: {e}"}), 500
    # -----------------------------------------

    with state_lock:
        runtime_state["config"] = cfg
        runtime_state["running"] = True
        runtime_state["max_requests"] = max_requests
        stats = runtime_state["stats"]
        stats["total"] = 0
        stats["success"] = 0
        stats["failed"] = 0
        stats["last_status"] = "-"
        stats["last_error"] = "-"
        stats["last_proxy"] = "-"
        stats["start_time"] = time.time()
        runtime_state["proxy_scores"] = defaultdict(lambda: {"success": 0, "failed": 0})
        runtime_state["logs"].clear()

    add_log("Worker started.", ok=None)

    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    with state_lock:
        runtime_state["running"] = False
    add_log("Worker stopped.", ok=None)
    return jsonify({"ok": True})


@app.route("/api/status")
def api_status():
    with state_lock:
        stats = dict(runtime_state["stats"])
        running = runtime_state["running"]
        proxy_scores = {
            proxy: dict(scores) for proxy, scores in runtime_state["proxy_scores"].items()
        }
        start_time = stats.get("start_time")
    uptime = 0
    if start_time:
        uptime = int(time.time() - start_time)
    stats["uptime"] = uptime
    return jsonify(
        {
            "ok": True,
            "running": running,
            "stats": stats,
            "proxy_scores": proxy_scores,
        }
    )


@app.route("/api/logs")
def api_logs():
    with state_lock:
        logs = list(runtime_state["logs"])
    return jsonify({"ok": True, "logs": logs})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, load_dotenv=False)
