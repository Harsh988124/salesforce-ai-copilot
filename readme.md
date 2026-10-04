# Salesforce Agentic AI Copilot

An enterprise-grade AI Copilot integrating a custom Salesforce Lightning Web Component (LWC) with a Python FastAPI backend. This system orchestrates multiple AI agents to analyze Customer 360 data, prioritize cases, and propose actionable CRM insights directly within the Salesforce UI.

## Architecture & Workflow

The system operates on a decoupled architecture, separating the Salesforce CRM frontend from the Python-based AI orchestration engine.

1. **Authentication:** The user logs in via Salesforce OAuth 2.0 (PKCE flow). The FastAPI backend securely stores the session and sets a cross-origin cookie (`samesite="none"`, `secure=True`).
2. **Trigger:** A Salesforce user clicks "Analyze Customer" on the Account Record Page, which fires a client-side LWC `fetch()` POST request to the backend.
3. **Data Retrieval:** FastAPI validates the Account ID and fetches the raw Customer 360 data (Accounts, Cases, Opportunities, Tasks) via the Salesforce REST API.
4. **Agent Orchestration:** The backend routes the data through deterministic AI agents:
   * **Case Agent:** Identifies high-priority, unresolved support tickets.
   * **Sales Agent:** Flags high-value opportunities nearing their close date.
   * **Task Agent:** Detects overdue follow-ups.
5. **UI Rendering:** The orchestrated insights are returned as a structured JSON payload and rendered reactively inside the Salesforce LWC dashboard.

## Directory & Tree Map

```text
salesforce-ai-copilot/
├── app/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── case_investigation.py    # Analyzes high-priority and unresolved cases
│   │   ├── customer_insights.py     # Base logic for generating CRM insights
│   │   ├── follow_up.py             # Detects overdue follow-up tasks
│   │   └── sales_agent.py           # Evaluates opportunity closing risks
│   ├── audit/
│   │   ├── __init__.py
│   │   └── audit_service.py         # Tracks executed actions and history
│   ├── services/
│   │   ├── __init__.py
│   │   ├── action_service.py        # Proposes and executes Salesforce actions
│   │   └── orchestrator.py          # Central router unifying agent outputs
│   ├── config.py                    # Environment variable management
│   ├── main.py                      # FastAPI application and route definitions
│   └── salesforce_client.py         # OAuth 2.0 and Salesforce REST API integration
├── force-app/main/default/lwc/copilotDashboard/
│   ├── copilotDashboard.html        # LWC frontend template (UI)
│   ├── copilotDashboard.js          # LWC client-side logic and fetch requests
│   └── copilotDashboard.js-meta.xml # LWC Salesforce metadata and visibility config
├── tests/                           # Unit and integration test suite
│   ├── test_agents.py               # Tests for individual deterministic agents
│   ├── test_orchestrator.py         # Copilot logic and routing tests
│   └── test_salesforce_client.py    # API mocking and error handling tests
├── .env.example                     # Template for required environment variables
├── .dockerignore                    # Excludes virtual environments from builds
├── Dockerfile                       # Containerization configuration
├── requirements.txt                 # Python dependencies
└── README.md                        # Project documentation
```

## Setup & Installation Manual

### 1. Prerequisites
* A Salesforce Developer Edition Org.
* Salesforce CLI (`sf` / `sfdx`) installed and authenticated to your org.
* Docker Desktop installed and running.
* Python 3.12 (if running locally without Docker).

### 2. Salesforce Configuration
1. **Create a Connected App:** In Salesforce Setup, create a Connected App with OAuth enabled. Add the callback URL `http://localhost:8001/oauth/callback`. Grant full API access scopes.
2. **Configure CSP Trusted Sites:** In Salesforce Setup, go to **CSP Trusted Sites**. Add `http://localhost:8001` and check the box to allow `connect-src` to permit client-side fetch requests.
3. **Deploy the Frontend:** Run the following command in your terminal to push the LWC to your org:
   ```bash
   sf project deploy start -d force-app/main/default/lwc/copilotDashboard
   ```
4. **Add to Page Layout:** Open an Account record in Salesforce, click the Gear icon > **Edit Page**, and drag the "Agentic Copilot" custom component onto the page layout. Save and activate.

### 3. Backend Environment Setup
1. Clone the repository and navigate to the project root.
2. Create a `.env` file based on the template:
   ```bash
   cp .env.example .env
   ```
3. Add your Salesforce Connected App Client ID to the `.env` file.

### 4. Running the Backend (Docker)
Build and run the application in an isolated container:
```bash
docker build -t salesforce-copilot-api .
docker run -p 8001:8001 --env-file .env salesforce-copilot-api
```
*(Verify the container is running by visiting `http://localhost:8001/health` in your browser).*

## How to Test

1. **Authenticate:** Open a new browser tab and navigate to `http://localhost:8001/oauth/login`. Complete the Salesforce login flow to generate your secure session cookie.
2. **Navigate to CRM:** Open your Salesforce Org and navigate to any Account record page (e.g., "Acme Technologies").
3. **Run Copilot:** Locate the "Agentic Copilot" card on the page. The Account ID will auto-populate. Click the **Analyze Customer** button.
4. **Observe Background Processing:** Check your terminal. You will see the `POST /copilot/analyze/{account_id}` request come in, followed by the backend executing the Customer 360 data fetch.

## Expected Results

Upon a successful test, the LWC UI will reactively update to display the structured AI insights. 

**Successful UI Output Example:**
*   **High Priority Unresolved Case: 00001026** 
    *   *Description:* Integration failure
    *   *Action:* Investigate and escalate if necessary.
*   **Opportunity Closing Soon: Enterprise Renewal**
    *   *Description:* Closing in 6 days. Amount: 500000.0
    *   *Action:* Follow up with the primary contact to secure the deal.
*   **Overdue Task: Email**
    *   *Description:* Task was due on 2026-09-21
    *   *Action:* Complete the task or reschedule.

**API Response Logging:**
The FastAPI terminal will output a `200 OK` status for the `POST` request. If the browser's privacy shields block the cross-origin cookie, the backend will log: `INFO: Cookie blocked by browser. Using active local dev session fallback.` and successfully process the request anyway.

## Limitations & Technical Notes
* **Browser Privacy Shields:** Strict browsers (like Brave) natively block cross-origin cookies between `force.com` and `localhost`. The backend includes a Local Dev Override in `main.py` that utilizes the most recent in-memory session if the cookie is dropped.
* **In-Memory Sessions:** For demonstration purposes, OAuth sessions are stored in an in-memory dictionary. In a production deployment, this should be migrated to Redis or a relational database.
* **HTTPS/SSL:** In a production cloud environment, the backend must be served over HTTPS to comply strictly with modern browser `secure=True` cookie policies without relying on localhost exemptions.

---
*Developed by Harsh Kaley*