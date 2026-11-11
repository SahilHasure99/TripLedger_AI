# 🏆 PayPal AI Hackathon Official Submission

## Project Name: **TripLedger AI** (TravelMate Enhanced Edition)
### Tagline: *From Multi-Agent AI Itineraries to Cryptographically Verified PayPal Group Checkouts in One Click.*

---

## 📌 Executive Summary

Planning group trips is notoriously frustrating: itineraries live in chats, bookings in emails, and shared expenses in messy spreadsheets where someone always gets shortchanged. 

**TripLedger AI** bridges the gap between **autonomous generative AI travel planning** and **enterprise-grade PayPal payments**. 

Using a coordinated multi-agent AI architecture (Flights, Accommodations, Real-Time Weather, and Google Gemini Itinerary Agents), TripLedger AI dynamically plans personalized travel, budgets realistic allocations across 7 global currencies, and connects directly to the **PayPal REST API v2**. Travelers can toggle instant **Group Funding Pools**, initiate PayPal Sandbox checkouts, and verify captures server-side with an **immutable transaction ledger**.

---

## 🎯 The Problem We Solved

1. **The Disconnect Between AI Planning & Payment:** Travelers generate AI itineraries on ChatGPT or travel tools, but have to leave the app, manually calculate costs, and collect money on separate apps.
2. **Group Travel Payment Friction:** Splitting travel bookings across multiple participants is prone to errors, delayed reimbursements, and payment disputes.
3. **Client-Side Financial Vulnerabilities:** Many travel webapps trust browser-side payment amounts or client-reported capture callbacks, leaving them vulnerable to tampering.
4. **Unreliable LLM Failures:** Pure LLM travel apps break when rate-limited or offline.

---

## 💡 What TripLedger AI Does

* 🤖 **Multi-Agent AI Travel Concierge:** Orchestrates 4 specialized agents (`FlightAgent`, `HotelAgent`, `WeatherAgent`, and `ItineraryAgent` powered by Google Gemini with deterministic offline fallback) to construct customized, weather-aware, day-by-day travel itineraries.
* 💳 **1-Click Plan-to-Checkout Bridge:** Converts AI-generated itinerary budgets into formal travel records in the database and pre-configures a PayPal checkout order in one click.
* 👥 **Dynamic Group Funding Pool:** Automatically calculates per-person payment shares for multi-traveler groups with real-time visual pool indicators.
* 🛡️ **Zero-Client-Trust PayPal Sandbox Checkout:** All order creation and capture logic is strictly handled server-side via FastAPI. Browser clients cannot tamper with amounts, currencies, or capture status.
* 🔁 **Idempotent Order Management:** Cryptographically hashed `PayPal-Request-Id` and client idempotency keys prevent double-charging or race conditions during network retries.
* 📒 **Auditable Transaction Ledger:** Every completed PayPal transaction is recorded in an immutable ledger with unique PayPal order/capture IDs, timestamping, status badges, and formula-injection-safe CSV exports.
* 🎨 **Interactive Dual-Navigation UI:** A glassmorphic top navigation bar + synchronized sidebar with instant judge demo auto-login mode.

---

## 🛠️ PayPal Integration Deep Dive

TripLedger AI integrates deeply with the **PayPal REST API v2**:

### 1. Secure OAuth 2.0 Client Authentication
* Authenticates against `https://api-m.sandbox.paypal.com/v1/oauth2/token` using sandbox credentials stored strictly on the server (`.env`). Credentials are never exposed to the browser.

### 2. Orders API v2 (`POST /v2/checkout/orders`)
* Generates PayPal orders with `intent: "CAPTURE"`, `user_action: "PAY_NOW"`, and `shipping_preference: "NO_SHIPPING"`.
* Dynamically extracts PayPal checkout approval links supporting both `rel: "payer-action"` and `rel: "approve"`, with a zero-downtime sandbox fallback URL.
* Enforces currency minor-unit precision across 7 global currencies (including zero-decimal JPY and two-decimal USD, EUR, GBP, SGD, AUD, CAD).

### 3. Server-Side Capture & Integrity Verification (`POST /v2/checkout/orders/{id}/capture`)
* Independent server-side capture: The FastAPI backend calls PayPal directly to capture the order.
* Verifies that the captured amount and currency code returned by PayPal match the saved database trip budget to the exact penny.

### 4. Idempotency & Concurrency Safety
* Every checkout order derives a unique `PayPal-Request-Id` using `sha256(idempotency_key)[:32]`.
* Reused keys safely return the existing order along with the verified checkout `approval_url`, preventing duplicate orders on double-clicks.

### 5. Webhook Signature Verification (`POST /v1/notifications/verify-webhook-signature`)
* Built-in support for verifying PayPal transmission signatures (`PAYPAL_WEBHOOK_ID`, `paypal-transmission-sig`, `paypal-cert-url`) to protect against spoofed webhooks.

---

## 🏗️ System Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│              Streamlit UI (Port 8501)                  │
│  • Top Glassmorphism Nav & Synchronized Sidebar        │
│  • Anime Guide Search & Google Maps Integration        │
│  • Group Funding Pool Widget & 1-Click Bridge          │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (JWT Auth)
┌───────────────────────────▼────────────────────────────┐
│              FastAPI Backend (Port 8000)               │
│  • PBKDF2 Password Hashing & Cryptographic JWT Vault   │
│  • SQLite / PostgreSQL Storage with Strict Minor Units │
│  • Strict Budget Match & Anti-Tamper Middlewares       │
└─────────────┬────────────────────────────┬─────────────┘
              │ REST API v2                │ AI Pipeline
┌─────────────▼───────────────┐ ┌──────────▼───────────────┐
│     PayPal REST API         │ │ Multi-Agent Coordinator  │
│  • OAuth 2.0 Token Exchange │ │  • Flight Search Agent   │
│  • Orders v2 (PAY_NOW)      │ │  • Hotel Search Agent    │
│  • Capture & Verification   │ │  • Open-Meteo Weather    │
│  • Webhook Signature Auth   │ │  • Google Gemini LLM     │
└─────────────────────────────┘ └──────────────────────────┘
```

* **Frontend:** Streamlit, Custom CSS3 Motion Layer, SVG Anime Character, BaseWeb Components.
* **Backend:** Python 3.12+, FastAPI, Uvicorn, SQLite/PostgreSQL, Pydantic v2.
* **Payments:** PayPal REST API v2 (Orders, Capture, Webhooks).
* **AI & Multi-Agent:** Google Gemini Flash (`google-generativeai`), Open-Meteo Weather API, Multi-Agent Coordinator.
* **Exports & Utilities:** ReportLab (PDF), python-docx (Word), JSON, CSV.
* **Testing:** Pytest (59/59 automated tests passing), Requests, TestClient.

---

## 🧪 Comprehensive Testing & Verification

TripLedger AI underwent rigorous testing with **100% pass rate**:

| Test Suite / Phase | Score | Verification Details |
|---|:---:|---|
| **Pytest Automated Suite** | **59 / 59 PASSED** | Agent pipelines, coordinator, travel features, backend security, regression tests. |
| **PayPal Sandbox Order Creation** | **VERIFIED** | Successfully exchanges OAuth tokens and generates valid sandbox orders. |
| **PayPal Approval URL Resolution** | **VERIFIED** | Correctly maps both `payer-action` and `approve` links. |
| **Financial Anti-Tamper Defense** | **VERIFIED** | Any budget/amount mismatch between frontend request and saved trip yields `HTTP 409 Conflict`. |
| **Idempotency Protection** | **VERIFIED** | Rapid duplicate requests return original order ID and active checkout URL without duplicates. |
| **Multi-Agent Fallback System** | **VERIFIED** | Automatically falls back to deterministic planning if Gemini API quota or network is unavailable. |

---

## 🚀 Quickstart & Demo Guide (For Judges)

### 1. Prerequisites
* Python 3.12 or later installed.
* PowerShell or Windows Command Prompt / Terminal.

### 2. Run the Backend & Frontend

**Terminal 1 (Backend):**
```powershell
cd "TripLedger_AI\TravelMate_Original_UI_Enhanced"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```powershell
cd "TripLedger_AI\TravelMate_Original_UI_Enhanced"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

### 3. Step-by-Step 2-Minute Judge Walkthrough
1. Open **`http://localhost:8501`** in your browser.
2. Click **`👤 Account`** on the top navigation bar.
3. Click **`🧪 Auto-Fill Demo Judge Credentials`** to instantly authenticate without typing.
4. Click **`🌍 Planner`**, select a curated destination (e.g. *Bali, Indonesia* or *Kyoto, Japan*) or enter your own, and click **`✦ Generate travel plan`**.
5. Review the coordinated flight options, hotel recommendations, weather forecast, and Gemini AI day-by-day itinerary.
6. Scroll down to the **TripLedger Bridge**, select your currency (*USD*), and click **`✨ Save Trip & Proceed to PayPal Checkout ➔`**.
7. In **`💳 Payments`**, toggle the **`👥 Enable Group Split`** checkbox to inspect per-traveler funding pool shares.
8. Click **`🚀 Launch PayPal Sandbox Checkout`** — a verified PayPal Sandbox Order ID and clickable checkout link will appear immediately!
9. View the immutable record in **`📒 Ledger`** and click **`Download ledger CSV`**.

---

## 🔮 What's Next for TripLedger AI

1. **Multi-Payer Group Escrow:** Allowing each traveler in a group to approve and fund their individual split share directly through PayPal before the master booking is executed.
2. **Automated Merchant Payouts:** Using PayPal Payouts API to disburse funds automatically to airlines and hotels once the trip pool is 100% funded.
3. **Real-Time FX Settlement:** Utilizing PayPal's dynamic currency conversion APIs to settle multi-currency group expenses in real time.

---

## 👥 Hackathon Team & Acknowledgments

* **Project:** TripLedger AI
* **Event:** PayPal AI Hackathon 2026
* Built with passion for seamless travel experiences and secure fintech automation.

