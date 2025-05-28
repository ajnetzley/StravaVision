from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env into os.environ

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
