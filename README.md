# Nexus Flow

> **Local Traffic Orchestration & Proxy Management Engine**
>
> *Control your network footprint with a cyberpunk-themed dashboard.*

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0%2B-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-active-neon.svg)

---

## About The Project

**Nexus Flow** is a self-hosted orchestration engine designed to streamline HTTP traffic generation, proxy management, and browser automation. Unlike standard request tools, Nexus Flow runs locally but acts globally—routing traffic through complex proxy chains or executing headless browser tasks via Playwright.

The interface features a **real-time, neon-styled dashboard** with live logging, traffic stats, and 3D visualizations, giving you full visibility into every request leaving your machine.

---

## Key Features

### 🎮 **Traffic Orchestration**
* **Multi-Threaded Execution:** Run concurrent requests with adjustable concurrency limits.
* **Request Chaining:** Define complex workflows (e.g., *Login* → *Get Token* → *Scrape Data*) using JSON-based chains.
* **Custom Payloads:** Full control over Methods (GET/POST/PUT/DELETE), Headers, Body, and User-Agents.

### **Advanced Proxy Logic**
* **Smart Rotation:** Automatically rotate through a list of proxies for every request.
* **Hybrid Mode:** Use "My IP + Proxy" mode to blend direct traffic with proxied requests.
* **Scoring System:** Tracks success/failure rates for every proxy in real-time to identify bad nodes.

### **Browser Automation**
* **Playwright Integration:** Seamlessly switch from HTTP requests to a headless Chromium browser for JavaScript-heavy targets.
* **Pre-Flight Checks:** Validates connectivity before launching browser contexts to save resources.

### **Live Monitoring**
* **Real-Time Logs:** Color-coded status logs stream instantly to the dashboard.
* **Visual Analytics:** View uptime, total requests, and error rates at a glance.
* **State Persistence:** Saves proxy history locally using IndexedDB.

---

## Project Structure

The project is built as a lightweight Flask application with a single-file backend and a responsive frontend.

```text
nexus-flow/
├── app.py              # Core Engine: Worker threads, proxy logic, Playwright
├── templates/
│   └── index.html      # Dashboard: The main control panel UI
├── static/
│   ├── main.js         # Logic: Polling, stats, and Three.js visualization
│   └── style.css       # Styling: Neon variables and responsive layout
└── requirements.txt    # Dependencies
