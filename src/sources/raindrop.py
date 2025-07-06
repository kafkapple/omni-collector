import requests
from bs4 import BeautifulSoup
from .base_source import BaseSource
from src.auth.raindrop_auth import RaindropAuthenticator

class RaindropSource(BaseSource):
    def __init__(self, name, posts_to_scrape, filter_keywords=None, collection_ids=None, **kwargs):
        super().__init__(name, None, posts_to_scrape, None, None, filter_keywords=filter_keywords, **kwargs)
        self.authenticator = RaindropAuthenticator()
        self.base_api_url = "https://api.raindrop.io/rest/v1/"
        self.collection_ids = collection_ids if collection_ids is not None else []

    def get_collections(self):
        headers = self.authenticator.get_headers()
        if not headers:
            print("Raindrop API authentication failed. Cannot fetch collections.")
            return {}
        
        url = f"{self.base_api_url}collections"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            collections = {item['_id']: item['title'] for item in data.get('items', [])}
            return collections
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Raindrop collections: {e}")
            return {}

    def scrape(self):
        headers = self.authenticator.get_headers()
        if not headers:
            print("Raindrop API authentication failed. Skipping scrape.")
            return []

        all_raindrops = []
        target_collection_ids = self.collection_ids if self.collection_ids else [None] # None이면 모든 컬렉션

        for col_id in target_collection_ids:
            params = {
                "perpage": self.posts_to_scrape if self.posts_to_scrape != -1 else 50, # Max 50 per page for Raindrop
                "sort": "-created"
            }
            
            if col_id:
                url = f"{self.base_api_url}raindrops/{col_id}"
            else:
                url = f"{self.base_api_url}raindrops"

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('items', []):
                    raindrop = {
                        'title': item.get('title'),
                        'url': item.get('link'),
                        'source': self.name,
                        'body': item.get('note', ''), # Raindrop의 note 필드를 본문으로 사용
                        'published_at': item.get('created'), # ISO 8601 형식으로 가정
                        'tags': item.get('tags', [])
                    }
                    
                    # Raindrop note가 비어있을 경우, 웹 페이지에서 본문 스크랩 시도
                    if not raindrop['body'] and raindrop['url']:
                        raindrop['body'] = self._get_web_content_body(raindrop['url'])

                    all_raindrops.append(raindrop)
                
            except requests.exceptions.RequestException as e:
                print(f"Error scraping Raindrop collection {col_id if col_id else 'all'}: {e}")
                continue # 다음 컬렉션으로 넘어감

        return self._apply_filters(all_raindrops)

    def _get_web_content_body(self, url):
        """
        주어진 URL에서 웹 콘텐츠의 본문을 스크랩합니다.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # 웹 페이지의 주요 본문 내용을 추출하는 일반적인 선택자들
            # 이 부분은 웹사이트마다 다를 수 있으므로, 필요에 따라 조정해야 합니다.
            body_elements = soup.select('article, .entry-content, .post-content, .article-body, .main-content')
            if body_elements:
                return body_elements[0].get_text(strip=True)
            return ""
        except Exception as e:
            print(f"Error fetching web content body from {url}: {e}")
            return ""
