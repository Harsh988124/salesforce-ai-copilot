import logging
import secrets
import re
from typing import List

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Cookie,
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import SF_CLIENT_ID
from app.salesforce_client import (
    get_authorization_url,
    exchange_code_for_token,
    generate_code_challenge,
    get_salesforce_accounts,
    get_customer_360,
    execute_salesforce_query,
)

from app.agents.customer_insights import analyze_customer_360, Insight
from app.services.orchestrator import run_copilot, CopilotResponse
from app.services.action_service import (
    propose_action, get_action, approve_action, execute_action, 
    ActionRequest, ActionProposal
)
from app.audit.audit_service import get_audit_logs, AuditEvent

# --------------------------------------------------
# Logging & Setup
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Salesforce AI Copilot API",
    description="Agentic AI assistant for Salesforce CRM operations",
    version="0.1.0",
)

# 2. Add the CORS Middleware immediately after the FIRST app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://orgfarm-7513724dbb-dev-ed.develop.lightning.force.com"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary OAuth Storage (In-memory for development)
oauth_states = {}
oauth_sessions = {}

def get_session(session_id: str | None):
    """
    Retrieves the OAuth session. 
    Includes a Local Dev Override to bypass strict browser cookie blockers (like Brave Shields).
    """
    # 1. Normal flow: Try to get the session using the cookie ID
    if session_id and session_id in oauth_sessions:
        return oauth_sessions[session_id]
        
    # 2. LOCAL DEV OVERRIDE: If the browser blocked the cookie, but we have 
    # an active login in memory, automatically use the most recent one.
    if oauth_sessions:
        logger.info("Cookie blocked by browser. Using active local dev session fallback.")
        return list(oauth_sessions.values())[-1]
        
    return None

# --------------------------------------------------
# Home Page & Health Checks
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <body style="display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; background-color: #f4f6f9;">
            <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2>Salesforce AI Copilot</h2>
                <p style="margin-bottom: 20px; color: #555;">Connect your Salesforce account to continue.</p>
                <a href="/oauth/login" style="padding: 12px 24px; background-color: #00A1E0; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Log In with Salesforce
                </a>
            </div>
        </body>
    </html>
    """

@app.get("/health")
def health():
    return {
        "status": "running",
        "service": "Salesforce AI Copilot API",
    }

@app.get("/salesforce/health")
def salesforce_health(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected. Open / first.")

    try:
        records = get_salesforce_accounts(session["access_token"], session["instance_url"])
        return {"status": "connected", "records_checked": len(records)}
    except Exception:
        logger.exception("Salesforce REST API health check failed.")
        raise HTTPException(status_code=502, detail="Salesforce REST API request failed.")

# --------------------------------------------------
# Salesforce OAuth Login & Callback
# --------------------------------------------------

@app.get("/oauth/login")
def oauth_login():
    if not SF_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Salesforce OAuth configuration is missing.")

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = generate_code_challenge(code_verifier)

    oauth_states[state] = {"code_verifier": code_verifier}

    authorization_url = get_authorization_url(state=state, code_challenge=code_challenge)

    response = RedirectResponse(url=authorization_url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=600,
    )
    return response # <--- This forces the browser to actually redirect

@app.get("/oauth/callback")
def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None),
):
    if error:
        logger.warning("Salesforce OAuth authorization failed.")
        raise HTTPException(status_code=400, detail="Salesforce authorization failed. Restart login.")

    if not code or not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state. Start again at /.")

    stored = oauth_states.pop(state, None)
    if not stored:
        raise HTTPException(status_code=400, detail="OAuth session expired. Start again at /.")

    try:
        token_data = exchange_code_for_token(code=code, code_verifier=stored["code_verifier"])
        session_id = secrets.token_urlsafe(32)

        oauth_sessions[session_id] = {
            "access_token": token_data["access_token"],
            "instance_url": token_data["instance_url"],
        }

        response = RedirectResponse(url="/accounts", status_code=303)
        response.delete_cookie("oauth_state")
        response.set_cookie(
            key="copilot_session",
            value=session_id,
            httponly=True,
            samesite="none",
            secure=True,
            max_age=3600,
        )
        return response # <--- This finishes the login and saves the secure cookie

    except Exception:
        logger.exception("Salesforce OAuth token exchange failed.")
        raise HTTPException(status_code=502, detail="OAuth token exchange failed. Check logs.")
    
# --------------------------------------------------
# Salesforce Data Endpoints
# --------------------------------------------------

@app.get("/accounts")
def accounts(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected. Open / first.")

    try:
        records = get_salesforce_accounts(session["access_token"], session["instance_url"])
        return {"total": len(records), "records": records}
    except Exception:
        logger.exception("Salesforce Accounts query failed.")
        raise HTTPException(status_code=502, detail="Could not retrieve Accounts.")


@app.get("/contacts")
def contacts(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected.")

    query = """
        SELECT Id, Name, Email, Phone, Title, Account.Name 
        FROM Contact 
        ORDER BY CreatedDate DESC 
        LIMIT 10
    """
    try:
        records = execute_salesforce_query(session["access_token"], session["instance_url"], query)
        return {"total": len(records), "records": records}
    except Exception:
        logger.exception("Salesforce Contacts query failed.")
        raise HTTPException(status_code=502, detail="Could not retrieve Contacts.")


@app.get("/opportunities")
def opportunities(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected.")

    query = """
        SELECT Id, Name, StageName, Amount, CloseDate, IsWon 
        FROM Opportunity 
        ORDER BY CreatedDate DESC 
        LIMIT 10
    """
    try:
        records = execute_salesforce_query(session["access_token"], session["instance_url"], query)
        return {"total": len(records), "records": records}
    except Exception:
        logger.exception("Salesforce Opportunities query failed.")
        raise HTTPException(status_code=502, detail="Could not retrieve Opportunities.")


@app.get("/cases")
def cases(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected.")

    query = """
        SELECT Id, CaseNumber, Subject, Status, Priority, CreatedDate 
        FROM Case 
        ORDER BY CreatedDate DESC 
        LIMIT 10
    """
    try:
        records = execute_salesforce_query(session["access_token"], session["instance_url"], query)
        return {"total": len(records), "records": records}
    except Exception:
        logger.exception("Salesforce Cases query failed.")
        raise HTTPException(status_code=502, detail="Could not retrieve Cases.")


@app.get("/tasks")
def tasks(copilot_session: str | None = Cookie(default=None)):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected.")

    query = """
        SELECT Id, Subject, Status, Priority, ActivityDate 
        FROM Task 
        ORDER BY ActivityDate DESC NULLS LAST 
        LIMIT 10
    """
    try:
        records = execute_salesforce_query(session["access_token"], session["instance_url"], query)
        return {"total": len(records), "records": records}
    except Exception:
        logger.exception("Salesforce Tasks query failed.")
        raise HTTPException(status_code=502, detail="Could not retrieve Tasks.")


# --------------------------------------------------
# Customer 360 API
# --------------------------------------------------

@app.get("/customer-360/{account_id}")
def customer_360(
    account_id: str,
    copilot_session: str | None = Cookie(default=None),
):
    if not re.fullmatch(r"[A-Za-z0-9]{15}([A-Za-z0-9]{3})?", account_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid Salesforce Account ID format.",
        )

    session = get_session(copilot_session)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not connected. Open /oauth/login first.",
        )

    try:
        customer_data = get_customer_360(
            access_token=session["access_token"],
            instance_url=session["instance_url"],
            account_id=account_id,
        )

        if customer_data is None:
            raise HTTPException(
                status_code=404,
                detail="Salesforce Account not found.",
            )

        return customer_data

    except HTTPException:
        raise
    except Exception:
        logger.exception("Customer 360 request failed.")
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve Customer 360 data.",
        )

@app.post("/agents/customer-insights/{account_id}", response_model=List[Insight])
def get_customer_insights(
    account_id: str,
    copilot_session: str | None = Cookie(default=None),
):
    if not re.fullmatch(r"[A-Za-z0-9]{15}([A-Za-z0-9]{3})?", account_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid Salesforce Account ID format.",
        )

    session = get_session(copilot_session)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not connected. Open /oauth/login first.",
        )

    try:
        customer_data = get_customer_360(
            access_token=session["access_token"],
            instance_url=session["instance_url"],
            account_id=account_id,
        )

        if customer_data is None:
            raise HTTPException(
                status_code=404,
                detail="Salesforce Account not found.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Customer insights CRM request failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Could not retrieve Customer 360 data for insights: {str(e)}",
        )

    insights = analyze_customer_360(customer_data)
    return insights

@app.post("/copilot/analyze/{account_id}", response_model=CopilotResponse)
def analyze_customer(
    account_id: str,
    copilot_session: str | None = Cookie(default=None),
):
    if not re.fullmatch(r"[A-Za-z0-9]{15}([A-Za-z0-9]{3})?", account_id):
        raise HTTPException(status_code=400, detail="Invalid Salesforce Account ID format.")

    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected. Open /oauth/login first.")

    try:
        customer_data = get_customer_360(
            access_token=session["access_token"],
            instance_url=session["instance_url"],
            account_id=account_id,
        )
        if customer_data is None:
            raise HTTPException(status_code=404, detail="Salesforce Account not found.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Copilot orchestration CRM request failed.")
        raise HTTPException(status_code=502, detail=f"Could not retrieve Customer 360 data: {str(e)}")

    copilot_response = run_copilot(account_id, customer_data)
    return copilot_response

@app.post("/actions/propose", response_model=ActionProposal)
def create_proposed_action(request: ActionRequest):
    return propose_action(request)

@app.get("/actions/{action_id}", response_model=ActionProposal)
def retrieve_action(action_id: str):
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")
    return action

@app.post("/actions/{action_id}/approve", response_model=ActionProposal)
def confirm_action(action_id: str):
    action = approve_action(action_id)
    if not action:
        raise HTTPException(
            status_code=400, 
            detail="Action not found or already processed."
        )
    return action

@app.post("/actions/{action_id}/execute", response_model=ActionProposal)
def run_action(
    action_id: str, 
    copilot_session: str | None = Cookie(default=None)
):
    session = get_session(copilot_session)
    if not session:
        raise HTTPException(status_code=401, detail="Not connected. Open /oauth/login first.")
    
    try:
        action = execute_action(
            action_id=action_id, 
            access_token=session["access_token"], 
            instance_url=session["instance_url"]
        )
        if not action:
            raise HTTPException(status_code=404, detail="Action not found.")
        return action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audit-logs", response_model=List[AuditEvent])
def retrieve_audit_logs():
    return get_audit_logs()