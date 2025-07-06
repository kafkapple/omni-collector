import requests
from bs4 import BeautifulSoup
from .base_source import BaseSource
from datetime import datetime

class PyTorchKRSource(BaseSource):
    def __init__(self, name, url, posts_to_scrape, selectors, output_fields, filter_keywords=None, **kwargs):
        super().__init__(name, url, posts_to_scrape, selectors, output_fields, filter_keywords=filter_keywords, **kwargs)

    def scrape(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            posts = []
            limit = self.posts_to_scrape if self.posts_to_scrape != -1 else None

            for item in soup.select(self.selectors.post_item)[:limit]:
                title = item.get_text(strip=True)
                post_url = item['href']
                if not post_url.startswith('http'):
                    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=requests.utils.urlparse(self.url))
                    post_url = base_url + post_url
                posts.append({'title': title, 'url': post_url, 'source': self.name})
            
            # 각 게시글의 상세 정보(본문, 작성자 등)를 가져오는 로직 추가
            for post in posts:
                details = self._get_post_details(post['url'])
                post.update(details)

            return self._apply_filters(posts)
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {self.name}: {e}")
            return []

    def _get_post_details(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {}
            # 본문
            body_element = soup.select_one(self.selectors.post_body)
            details['body'] = body_element.get_text(strip=True) if body_element else ""

            # 작성일
            try:
                # Discourse 포럼의 일반적인 시간 요소 셀렉터
                time_element = soup.select_one('.crawler-post-infos .post-time')
                if time_element and time_element.has_attr('title'):
                    # 'title' 속성에 더 정확한 시간이 있는 경우가 많음
                    details['published_at'] = datetime.fromisoformat(time_element['title'].replace('Z', '+00:00')).isoformat()
                elif time_element:
                    details['published_at'] = time_element.get_text(strip=True)
                else:
                    details['published_at'] = datetime.now().isoformat() # Fallback
            except Exception:
                details['published_at'] = datetime.now().isoformat() # Fallback

            # 조회수
            try:
                views_element = soup.select_one('.topic-views .number')
                details['view_count'] = int(views_element.get_text(strip=True).replace(',', '')) if views_element else 0
            except (ValueError, AttributeError):
                details['view_count'] = 0

            # 추천수 (좋아요)
            try:
                likes_element = soup.select_one('.likes .count')
                details['like_count'] = int(likes_element.get_text(strip=True).replace(',', '')) if likes_element else 0
            except (ValueError, AttributeError):
                details['like_count'] = 0

            return details
        except Exception as e:
            print(f"Error fetching post details from {url}: {e}")
            return {'body': '', 'published_at': datetime.now().isoformat(), 'view_count': 0, 'like_count': 0}
