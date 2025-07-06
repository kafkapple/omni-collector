import requests
from bs4 import BeautifulSoup
from .base_source import BaseSource

class GPTERSNewsSource(BaseSource):
    def __init__(self, name, url, posts_to_scrape, selectors, output_fields, filter_keywords=None, **kwargs):
        super().__init__(name, url, posts_to_scrape, selectors, output_fields, filter_keywords=filter_keywords, **kwargs)

    def scrape(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            posts = []
            limit = self.posts_to_scrape if self.posts_to_scrape != -1 else None

            # GPTERS.org 뉴스 페이지의 게시글 선택자 (예시, 실제 확인 필요)
            # 실제 웹사이트 구조에 따라 선택자를 조정해야 합니다.
            for item in soup.select(self.selectors.post_item)[:limit]:
                title_element = item.select_one(self.selectors.title)
                url_element = item.select_one(self.selectors.url)
                
                if title_element and url_element:
                    title = title_element.get_text(strip=True)
                    post_url = url_element['href']
                    posts.append({'title': title, 'url': post_url, 'source': self.name})
            
            # 각 게시글의 상세 정보(본문, 작성자 등)를 가져오는 로직 추가
            for post in posts:
                post['body'] = self._get_post_body(post['url'])
                # author, date 등 추가 정보 수집 로직은 향후 구현

            return self._apply_filters(posts)
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {self.name}: {e}")
            return []

    def _get_post_body(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # GPTERS.org 뉴스 페이지의 본문 선택자 (예시, 실제 확인 필요)
            body = soup.select_one(self.selectors.post_body).get_text(strip=True)
            return body
        except Exception as e:
            print(f"Error fetching post body from {url}: {e}")
            return ""