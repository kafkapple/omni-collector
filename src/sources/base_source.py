from abc import ABC, abstractmethod

class BaseSource(ABC):
    def __init__(self, name, url, posts_to_scrape, selectors, output_fields, filter_keywords=None, **kwargs):
        self.name = name
        self.url = url
        self.posts_to_scrape = posts_to_scrape
        self.selectors = selectors
        self.output_fields = output_fields
        self.filter_keywords = [kw.lower() for kw in filter_keywords] if filter_keywords else []

    @abstractmethod
    def scrape(self):
        pass

    def _apply_filters(self, posts):
        if not self.filter_keywords:
            return posts
        
        filtered_posts = []
        for post in posts:
            # 제목과 본문(body)에 키워드가 포함되어 있는지 확인
            # 본문이 없는 경우를 대비하여 get() 사용
            content_to_check = (post.get('title', '') + " " + post.get('body', '')).lower()
            if any(keyword in content_to_check for keyword in self.filter_keywords):
                filtered_posts.append(post)
        return filtered_posts