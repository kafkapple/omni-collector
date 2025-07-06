import os
from dotenv import load_dotenv

class RaindropAuthenticator:
    def __init__(self):
        load_dotenv()
        self.access_token = os.getenv("RAINDROP_ACCESS_TOKEN")
        if not self.access_token:
            print("Warning: RAINDROP_ACCESS_TOKEN not found in .env. Raindrop API calls will fail.")

    def get_headers(self):
        if not self.access_token:
            return {}
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
