1. Functionality
Nexus Flow is a self-hosted traffic orchestration engine built with Flask. It allows developers to generate, route, and monitor HTTP requests from a local environment with granular control over identity and network paths.

Traffic Orchestration: Execute concurrent HTTP/S requests with customizable methods, headers, payloads, and user-agents.

Advanced Proxy Management: Built-in logic for proxy rotation, direct connections, or hybrid ("My IP + Proxy") modes, complete with success/failure scoring for every proxy used.

Browser Automation: Integrated Playwright support to execute tasks in a headless Chromium environment when standard HTTP requests aren't enough.

Request Chaining: Define multi-step workflows (e.g., Login -> Get Token -> Fetch Data) using JSON-based chains.

Real-Time Monitoring: A "Cyberpunk" dashboard featuring live logs, status visualization, and Three.js globe animations, all updated via low-latency polling.

2. Project Structure
The project is a lightweight Flask application with a single-file backend and a responsive frontend:

nexus-flow/
├── app.py              # Core logic: Worker threads, proxy rotation, and Playwright engine
├── templates/
│   └── index.html      # The "Control Panel" dashboard UI
├── static/
│   ├── main.js         # Frontend logic: State polling, IndexedDB history, and Three.js
│   └── style.css       # Neon/Cyberpunk styling
└── requirements.txt    # (See requirements below)

3. Requirements
Python 3.8+

Core Libraries: Flask, requests

Optional (for Browser Mode): playwright (plus playwright install chromium)

Frontend: Modern browser (uses vanilla JS + Three.js CDN)
