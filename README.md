🌐 Nexus Flow
Local Traffic Orchestration & Proxy Management Engine

Control your network footprint with a cyberpunk-themed dashboard.

⚡ About The Project
Nexus Flow is a self-hosted orchestration engine designed to streamline HTTP traffic generation, proxy management, and browser automation. Unlike standard request tools, Nexus Flow runs locally but acts globally—routing traffic through complex proxy chains or executing headless browser tasks via Playwright.

The interface features a real-time, neon-styled dashboard with live logging, traffic stats, and 3D visualizations, giving you full visibility into every request leaving your machine.

🚀 Key Features
🎮 Traffic Orchestration
Multi-Threaded Execution: Run concurrent requests with adjustable concurrency limits.

Request Chaining: Define complex workflows (e.g., Login → Get Token → Scrape Data) using JSON-based chains.

Custom Payloads: Full control over Methods (GET/POST/PUT/DELETE), Headers, Body, and User-Agents.

🛡️ Advanced Proxy Logic
Smart Rotation: Automatically rotate through a list of proxies for every request.

Hybrid Mode: Use "My IP + Proxy" mode to blend direct traffic with proxied requests.

Scoring System: Tracks success/failure rates for every proxy in real-time, helping you identify bad nodes.

🤖 Browser Automation
Playwright Integration: Seamlessly switch from HTTP requests to a headless Chromium browser for JavaScript-heavy targets.

Pre-Flight Checks: Validates proxy connectivity before launching browser contexts to save resources.

📊 Live Monitoring
Real-Time Logs: Color-coded status logs (Success/Fail/Info) stream instantly to the dashboard.

Visual Analytics: View uptime, total requests, and error rates at a glance.

State Persistence: Saves proxy history locally using IndexedDB.

🛠️ Project Structure
The project is built as a lightweight Flask application with a single-file backend and a responsive frontend.

Plaintext

nexus-flow/
├── app.py              # 🧠 Core Engine: Worker threads, proxy logic, Playwright
├── templates/
│   └── index.html      # 🖥️ Dashboard: The main control panel UI
├── static/
│   ├── main.js         # ⚙️ Logic: Polling, stats, and Three.js visualization
│   └── style.css       # 🎨 Styling: Neon variables and responsive layout
└── requirements.txt    # 📦 Dependencies
💻 Installation & Usage
1. Prerequisites
Python 3.8+

(Optional) Playwright for browser mode

2. Setup
Clone the repository and install dependencies:

Bash

git clone https://github.com/yourusername/nexus-flow.git
cd nexus-flow
pip install flask requests playwright
playwright install chromium  # Only if you need browser mode
3. Running the Engine
Start the Flask server:

Bash

python app.py
Access the Dashboard: Open http://localhost:5000 in your browser.

Login: The default password is nexusflow.

Note: Change MASTER_PASSWORD in app.py for security.

🎛️ How to Use
Basic HTTP Request
Select Method: Choose GET, POST, etc.

Target URL: Enter the API endpoint (e.g., https://api.ipify.org?format=json).

Proxies: Paste your proxy list (one per line, host:port).

Concurrency: Set how many threads you want running.

Click START.

Using Playwright Mode
If a target requires JavaScript rendering:

Change Engine Mode to Playwright Browser.

The engine will launch a headless Chromium instance for each task.

Note: This consumes more system resources than standard HTTP requests.

Request Chaining
To perform a sequence of actions, use the Request Chain box with a JSON array:

JSON

[
  {
    "method": "POST",
    "url": "https://example.com/login",
    "data": {"user": "admin", "pass": "1234"}
  },
  {
    "mode": "playwright",
    "url": "https://example.com/dashboard"
  }
]
🎨 Cyberpunk UI
The interface is designed with a "Neon/Dark Mode" aesthetic:

Neon Wires: CSS animations simulate data flow in the background.

3D Globe: A Three.js wireframe globe visualizes global connectivity.

Alert System: Visual warnings appear if error rates spike.

📝 License
Distributed under the MIT License.
