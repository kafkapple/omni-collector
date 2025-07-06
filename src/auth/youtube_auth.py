import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

class YouTubeAuthenticator:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            print("Warning: YOUTUBE_API_KEY not found in .env. YouTube API calls will fail.")
        self.youtube_service = None

    def get_youtube_service(self):
        if not self.api_key:
            return None
        if self.youtube_service is None:
            self.youtube_service = build("youtube", "v3", developerKey=self.api_key)
        return self.youtube_service
