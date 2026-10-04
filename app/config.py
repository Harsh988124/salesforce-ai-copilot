import os
from dotenv import load_dotenv

load_dotenv()

SF_CLIENT_ID = os.getenv("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET")

SF_REDIRECT_URI = os.getenv(
    "SF_REDIRECT_URI",
    "http://localhost:8001/oauth/callback"
)

SF_DOMAIN = os.getenv("SF_DOMAIN", "login")

SF_API_VERSION = os.getenv("SF_API_VERSION", "v65.0")