import base64
import hashlib
import requests
from urllib.parse import urlencode

from app.config import (
    SF_CLIENT_ID,
    SF_CLIENT_SECRET,
    SF_REDIRECT_URI,
    SF_DOMAIN,
    SF_API_VERSION,
)

def generate_code_challenge(code_verifier: str) -> str:
    """Generate an S256 PKCE code challenge."""
    digest = hashlib.sha256(
        code_verifier.encode("ascii")
    ).digest()

    return (
        base64.urlsafe_b64encode(digest)
        .rstrip(b"=")
        .decode("ascii")
    )

def get_authorization_url(state: str, code_challenge: str) -> str:
    """Build the Salesforce OAuth authorization URL."""
    base_url = (
        f"https://{SF_DOMAIN}.salesforce.com"
        "/services/oauth2/authorize"
    )

    params = {
        "response_type": "code",
        "client_id": SF_CLIENT_ID,
        "redirect_uri": SF_REDIRECT_URI,
        "scope": "api refresh_token",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{base_url}?{urlencode(params)}"

def exchange_code_for_token(code: str, code_verifier: str) -> dict:
    """Exchange the authorization code for OAuth tokens."""
    token_url = (
        f"https://{SF_DOMAIN}.salesforce.com"
        "/services/oauth2/token"
    )

    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": SF_CLIENT_ID,
            "client_secret": SF_CLIENT_SECRET,
            "redirect_uri": SF_REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()

def execute_salesforce_query(access_token: str, instance_url: str, query: str) -> list:
    """Execute any SOQL query against the Salesforce REST API."""
    response = requests.get(
        f"{instance_url}/services/data/{SF_API_VERSION}/query",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        params={"q": query},
        timeout=30,
    )

    response.raise_for_status()
    return response.json().get("records", [])

def get_salesforce_accounts(access_token: str, instance_url: str) -> list:
    """Fetch up to 10 Salesforce Accounts through REST API."""
    query = """
        SELECT Id, Name, Industry, Type, Phone
        FROM Account
        ORDER BY Name
        LIMIT 10
    """
    return execute_salesforce_query(access_token, instance_url, query)


def get_customer_360(
    access_token: str,
    instance_url: str,
    account_id: str,
):
    """Collect CRM information related to one Account."""

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    def run_query(query: str):
        response = requests.get(
            f"{instance_url}/services/data/v65.0/query",
            headers=headers,
            params={"q": query},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("records", [])

    # Account ID is validated by the API endpoint
    # before it reaches this function.
    account_records = run_query(
        f"""
        SELECT Id, Name, Industry, Type, Phone, Website,
               BillingCity, BillingCountry, Description
        FROM Account
        WHERE Id = '{account_id}'
        LIMIT 1
        """
    )

    if not account_records:
        return None

    contacts = run_query(
        f"""
        SELECT Id, FirstName, LastName, Email, Phone, Title
        FROM Contact
        WHERE AccountId = '{account_id}'
        LIMIT 100
        """
    )

    opportunities = run_query(
        f"""
        SELECT Id, Name, StageName, Amount, CloseDate, Probability
        FROM Opportunity
        WHERE AccountId = '{account_id}'
        LIMIT 100
        """
    )

    cases = run_query(
        f"""
        SELECT Id, CaseNumber, Subject, Status, Priority,
               CreatedDate, Description
        FROM Case
        WHERE AccountId = '{account_id}'
        LIMIT 100
        """
    )

    tasks = run_query(
        f"""
        SELECT Id, Subject, Status, Priority, ActivityDate,
               Description, OwnerId
        FROM Task
        WHERE WhatId = '{account_id}'
        LIMIT 100
        """
    )

    return {
        "account": account_records[0],
        "contacts": contacts,
        "opportunities": opportunities,
        "cases": cases,
        "tasks": tasks,
        "summary": {
            "contacts_count": len(contacts),
            "opportunities_count": len(opportunities),
            "cases_count": len(cases),
            "tasks_count": len(tasks),
        },
    }

# Add this to the bottom of app/salesforce_client.py
def create_salesforce_record(access_token: str, instance_url: str, object_name: str, data: dict):
    """
    Creates a new record in Salesforce via the REST API.
    """
    # Note: Adjust v60.0 to match the API version you are using in your other client functions
    url = f"{instance_url}/services/data/v60.0/sobjects/{object_name}/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    import requests
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code in (200, 201):
        return response.json()
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=502, 
            detail=f"Salesforce API Error: {response.text}"
        )