import requests
from .base_source import BaseSource
from src.auth.youtube_auth import YouTubeAuthenticator
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import time

class YouTubeSource(BaseSource):
    def __init__(self, name, posts_to_scrape, filter_keywords=None, channel_ids=None, playlist_ids=None, delay_between_requests=5, **kwargs):
        super().__init__(name, None, posts_to_scrape, None, None, filter_keywords=filter_keywords, **kwargs)
        self.authenticator = YouTubeAuthenticator()
        self.channel_ids = channel_ids if channel_ids is not None else []
        self.playlist_ids = playlist_ids if playlist_ids is not None else []
        self.delay_between_requests = delay_between_requests

    def scrape(self):
        youtube = self.authenticator.get_youtube_service()
        if not youtube:
            print("YouTube API authentication failed. Skipping scrape.")
            return []

        video_ids = []
        
        # 채널 ID 리스트 처리
        for channel_id in self.channel_ids:
            try:
                channel_response = youtube.channels().list(
                    id=channel_id,
                    part='contentDetails'
                ).execute()
                
                if 'items' in channel_response and len(channel_response['items']) > 0:
                    uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    self.playlist_ids.append(uploads_playlist_id) # 업로드 플레이리스트 ID 추가
                else:
                    print(f"Error: Could not retrieve channel details for ID {channel_id}. Check channel ID or API key/permissions.")
            except Exception as e:
                print(f"Error fetching channel {channel_id} details: {e}")

        # 플레이리스트 ID 리스트 처리
        for playlist_id in self.playlist_ids:
            playlist_items = []
            next_page_token = None
            while True:
                try:
                    playlist_response = youtube.playlistItems().list(
                        playlistId=playlist_id,
                        part='snippet',
                        maxResults=50, # 최대 50개
                        pageToken=next_page_token
                    ).execute()
                    playlist_items.extend(playlist_response['items'])
                    next_page_token = playlist_response.get('nextPageToken')
                    if not next_page_token or (self.posts_to_scrape != -1 and len(playlist_items) >= self.posts_to_scrape):
                        break
                except Exception as e:
                    print(f"Error fetching playlist {playlist_id} items: {e}")
                    break # 오류 발생 시 현재 플레이리스트 처리 중단
            
            for item in playlist_items:
                video_ids.append(item['snippet']['resourceId']['videoId'])
                if self.posts_to_scrape != -1 and len(video_ids) >= self.posts_to_scrape:
                    break

        videos_data = []
        if video_ids:
            # 비디오 상세 정보 가져오기
            # API 할당량 고려하여 50개씩 끊어서 요청
            for i in range(0, len(video_ids), 50):
                batch_video_ids = video_ids[i:i+50]
                try:
                    video_response = youtube.videos().list(
                        id=",".join(batch_video_ids),
                        part='snippet,statistics'
                    ).execute()
                    
                    for item in video_response['items']:
                        video = {
                            'title': item['snippet']['title'],
                            'url': f"https://www.youtube.com/watch?v={item['id']}",
                            'source': self.name,
                            'channel_title': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'view_count': item['statistics'].get('viewCount', 0),
                            'like_count': item['statistics'].get('likeCount', 0),
                            'comment_count': item['statistics'].get('commentCount', 0),
                            'video_id': item['id']
                        }
                        # 자막 가져오기 (재시도 및 딜레이 로직 추가)
                        retries = 3
                        for i in range(retries):
                            try:
                                # 각 요청 사이에 딜레이 추가
                                if i > 0:
                                    time.sleep(self.delay_between_requests)
                                    
                                transcript_list = YouTubeTranscriptApi.list_transcripts(item['id'])
                                transcript = transcript_list.find_transcript(['ko', 'en'])
                                transcript_data = transcript.fetch()
                                video['body'] = " ".join([entry['text'] for entry in transcript_data])
                                break # 성공하면 루프 종료
                            except NoTranscriptFound:
                                video['body'] = ""
                                print(f"No transcript found for video: {video['title']}")
                                break # 자막이 없으면 더 이상 재시도하지 않음
                            except TranscriptsDisabled:
                                video['body'] = ""
                                print(f"Transcripts are disabled for video: {video['title']}")
                                break # 자막이 비활성화되어 있으면 더 이상 재시도하지 않음
                            except Exception as e:
                                video['body'] = ""
                                # IP 차단 메시지 개선
                                if "YouTube is blocking requests from your IP" in str(e):
                                    print(f"Warning: YouTube IP ban detected for video: {video['title']}. See README for solutions.")
                                else:
                                    print(f"Error fetching transcript for {video['title']}: {e}")
                                
                                if i < retries - 1:
                                    time.sleep(2 ** i) # 지수 백오프
                                else:
                                    print(f"Failed to fetch transcript for {video['title']} after {retries} retries.")

                        videos_data.append(video)
                        # 다음 비디오 처리를 위해 딜레이 추가
                        time.sleep(self.delay_between_requests)
                except Exception as e:
                    print(f"Error fetching video details for batch: {e}")

        return self._apply_filters(videos_data)