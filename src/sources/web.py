import requests
from bs4 import BeautifulSoup
from .base_source import BaseSource
from datetime import datetime

class WebSource(BaseSource):
    def __init__(self, name, url, filter_keywords=None, **kwargs):
        super().__init__(name, url, 1, None, None, filter_keywords=filter_keywords, **kwargs) # posts_to_scrape is always 1 for a single URL

    def scrape(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else self.url
            body = self._get_web_content_body(self.url, soup)
            
            # Use current time as published_at for generic web scraping
            published_at = datetime.now().isoformat()

            return [{
                'title': title,
                'url': self.url,
                'source': self.name,
                'body': body,
                'published_at': published_at
            }]
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {self.url}: {e}")
            return []

    def _get_web_content_body(self, url, soup):
        """
        주어진 URL의 BeautifulSoup 객체에서 웹 콘텐츠의 본문을 스크랩합니다.
        """
        try:
            # 웹 페이지의 주요 본문 내용을 추출하는 일반적인 선택자들
            # 이 부분은 웹사이트마다 다를 수 있으므로, 필요에 따라 조정해야 합니다.
            body_elements = soup.select('article, .entry-content, .post-content, .article-body, .main-content, #content, .content')
            if body_elements:
                return body_elements[0].get_text(strip=True)
            return ""
        except Exception as e:
            print(f"Error fetching web content body from {url}: {e}")
            return ""
