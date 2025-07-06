import hydra
from omegaconf import DictConfig, OmegaConf
import os
from hydra.utils import instantiate
import json
import re
from datetime import datetime
import yaml

def save_to_markdown(data, output_dir):
    """
    수집된 단일 데이터를 마크다운 파일로 저장합니다.
    """
    # 파일명으로 사용하기 부적절한 문자 제거
    filename = re.sub(r'[\\/:"*?<>|]+', '', data['title']) + '.md'
    filepath = os.path.join(output_dir, filename)

    # YAML Frontmatter 생성
    frontmatter = "---\n"
    for key, value in data.items():
        if key != 'body':
            # 날짜 객체는 ISO 형식 문자열로 변환하여 저장
            if isinstance(value, datetime):
                # Ensure datetime is tz-naive before saving
                if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
                    value = value.replace(tzinfo=None)
                frontmatter += f"{key}: {value.isoformat()}\n"
            else:
                frontmatter += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
    frontmatter += "---\n\n"

    # 본문 내용
    body = data.get('body', '')

    # 파일 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter + body)
    print(f"Saved: {filepath}")

def create_metadata_index(markdown_dir, output_file):
    """
    마크다운 파일들로부터 메타데이터 인덱스를 생성합니다.
    """
    metadata_list = []
    for filename in os.listdir(markdown_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(markdown_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # YAML Frontmatter 추출
                match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if match:
                    try:
                        metadata = yaml.safe_load(match.group(1))
                        metadata['filepath'] = filepath
                        metadata_list.append(metadata)
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML in {filename}: {e}")

    # published_at 기준으로 최신 날짜순으로 정렬
    # published_at이 없는 경우를 대비하여 기본값 설정
    metadata_list.sort(key=lambda x: x.get('published_at', '1970-01-01T00:00:00'), reverse=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=4)
    print(f"Metadata index created: {output_file}")

def run_collection(cfg: DictConfig):
    all_scraped_data = []
    for source_name, source_cfg in cfg.sources.items():
        source = instantiate(source_cfg)
        print(f"'{source.name}'에서 데이터 수집 중...")
        scraped_data = source.scrape()
        all_scraped_data.extend(scraped_data)
    return all_scraped_data

def run_summarization(cfg: DictConfig, data_to_process: list):
    if cfg.processing.summarize.enabled:
        print("요약 기능 활성화됨. 데이터 처리 중...")
        summarizer = instantiate(cfg.processing.summarize)
        # Pass the selected_prompt_name from config to summarize_data
        processed_data = summarizer.summarize_data(data_to_process, cfg.processing.summarize.selected_prompt_name)
        return processed_data
    else:
        print("요약 기능이 비활성화되어 있습니다.")
        return data_to_process

@hydra.main(config_path="configs", config_name="config", version_base=None)
def cli_main(cfg: DictConfig) -> None:
    output_dir = os.path.join(os.getcwd(), 'results')
    markdown_dir = os.path.join(output_dir, 'markdown')
    os.makedirs(markdown_dir, exist_ok=True)
    metadata_path = os.path.join(output_dir, 'metadata.json')

    mode = cfg.cli.mode
    input_path = cfg.cli.input

    if mode == "collect" or mode == "all":
        print("Collecting data...")
        scraped_data = run_collection(cfg)
        for data in scraped_data:
            save_to_markdown(data, markdown_dir)

    if mode == "summarize":
        if not input_path:
            print("Error: 'input' parameter is required for 'summarize' mode in config.yaml or as a command-line override.")
            return
        
        data_to_summarize = []
        if os.path.isdir(input_path):
            for filename in os.listdir(input_path):
                if filename.endswith('.md'):
                    filepath = os.path.join(input_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                        if match:
                            metadata = yaml.safe_load(match.group(1))
                            body = content[match.end():].strip()
                            metadata['body'] = body
                            data_to_summarize.append(metadata)
        elif os.path.isfile(input_path) and input_path.endswith('.md'):
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if match:
                    metadata = yaml.safe_load(match.group(1))
                    body = content[match.end():].strip()
                    metadata['body'] = body
                    data_to_summarize.append(metadata)
        else:
            print(f"Error: Invalid input for summarize mode: {input_path}. Must be a .md file or a directory containing .md files.")
            return

        summarized_data = run_summarization(cfg, data_to_summarize)
        # 요약된 내용을 다시 마크다운 파일에 저장
        for data in summarized_data:
            save_to_markdown(data, markdown_dir)

    if mode == "index" or mode == "all":
        print("Creating metadata index...")
        create_metadata_index(markdown_dir, metadata_path)

    print("Omni-Collector 작업 완료.")

if __name__ == "__main__":
    cli_main()

