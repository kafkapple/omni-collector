import os
import glob
from .base_source import BaseSource
from datetime import datetime

class ObsidianSource(BaseSource):
    def __init__(self, name, posts_to_scrape=-1, filter_keywords=None, vault_path=None, folder_paths=None, **kwargs):
        super().__init__(name, None, posts_to_scrape, None, None, filter_keywords=filter_keywords, **kwargs)
        self.vault_path = vault_path
        self.folder_paths = folder_paths if folder_paths is not None else []

    def scrape(self):
        if not self.vault_path or not os.path.isdir(self.vault_path):
            print(f"Error: Obsidian vault path '{self.vault_path}' is invalid or not found.")
            return []

        markdown_files = []
        limit = self.posts_to_scrape if self.posts_to_scrape != -1 else float('inf')
        count = 0

        target_dirs = []
        if not self.folder_paths: # folder_paths가 비어있으면 전체 볼트 스캔
            target_dirs.append(self.vault_path)
        else:
            for folder in self.folder_paths:
                target_dir = os.path.join(self.vault_path, folder)
                if os.path.isdir(target_dir):
                    target_dirs.append(target_dir)
                else:
                    print(f"Warning: Obsidian folder path '{target_dir}' is invalid or not found. Skipping.")
        
        if not target_dirs:
            print("Error: No valid Obsidian folders to scan.")
            return []

        for target_dir in target_dirs:
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
                            continue
                        
                        # 파일의 수정 시간을 발행일로 사용
                        modified_time = os.path.getmtime(file_path)
                        published_at = datetime.fromtimestamp(modified_time).isoformat()

                        markdown_files.append({
                            'title': os.path.splitext(file)[0],
                            'url': f"file://{file_path}", # 로컬 파일 경로를 URL 형태로 저장
                            'source': self.name,
                            'body': content,
                            'file_path': file_path,
                            'published_at': published_at
                        })
                        count += 1
                        if count >= limit:
                            break
                if count >= limit:
                    break
            if count >= limit:
                break

        return self._apply_filters(markdown_files)
