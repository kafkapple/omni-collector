import streamlit as st
import pandas as pd
import json
import os
import re
import yaml
import hydra
from omegaconf import DictConfig, OmegaConf
from hydra.core.global_hydra import GlobalHydra
from hydra.utils import instantiate

# Initialize Hydra and load the base configuration
GlobalHydra.instance().clear()
hydra.initialize(config_path="./configs", job_name="omni_collector_app")
base_cfg = hydra.compose(config_name="config")

# Import functions from main.py
from main import run_collection, run_summarization, create_metadata_index, save_to_markdown

# Import specific sources for their methods (e.g., Raindrop collections)
from src.sources.raindrop import RaindropSource
from src.sources.youtube import YouTubeSource
from src.sources.obsidian import ObsidianSource
from src.sources.web import WebSource # Import WebSource

all_available_sources = list(base_cfg.sources.keys())

# 데이터 로드 함수
@st.cache_data
def load_data(metadata_path):
    if not os.path.exists(metadata_path):
        return pd.DataFrame()
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    # published_at 컬럼을 datetime으로 변환하여 정렬 가능하게 함
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', format='ISO8601')

        # Ensure all valid datetimes are tz-naive
        def make_tz_naive(ts):
            if pd.isna(ts):
                return ts
            if ts.tz is not None:
                return ts.tz_localize(None)
            return ts

        df['published_at'] = df['published_at'].apply(make_tz_naive)

        df = df.sort_values(by='published_at', ascending=False)
    
    # 'rating' 컬럼이 없으면 0으로 초기화
    if 'rating' not in df.columns:
        df['rating'] = 0

    return df

def load_markdown_content(filepath):
    if not os.path.exists(filepath):
        return ""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        # YAML Frontmatter 제거
        match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if match:
            return content[match.end():].strip()
        return content.strip()

def save_markdown_content(data, filepath):
    """
    업데이트된 데이터를 마크다운 파일로 저장합니다.
    """
    frontmatter = "---\n"
    for key, value in data.items():
        if key != 'body' and key != 'filepath': # filepath는 메타데이터에 저장하지 않음
            if isinstance(value, pd.Timestamp):
                # Ensure timestamp is tz-naive before saving
                if value.tz is not None:
                    value = value.tz_localize(None)
                frontmatter += f"{key}: {value.isoformat()}\n"
            else:
                frontmatter += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
    frontmatter += "---\n\n"

    body = data.get('body', '')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter + body)

def update_metadata_index(markdown_dir, metadata_path):
    """
    마크다운 파일들로부터 메타데이터 인덱스를 재생성합니다.
    """
    metadata_list = []
    for filename in os.listdir(markdown_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(markdown_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if match:
                    try:
                        metadata = yaml.safe_load(match.group(1))
                        if 'published_at' in metadata and metadata['published_at']:
                            try:
                                dt_obj = pd.to_datetime(metadata['published_at'], errors='coerce', format='ISO8601')
                                if pd.api.types.is_datetime64_any_dtype(dt_obj):
                                    if dt_obj.tz is not None:
                                        dt_obj = dt_obj.tz_localize(None)
                                metadata['published_at'] = dt_obj
                            except Exception as e:
                                st.warning(f"Could not parse published_at for {filename}: {e}")
                                metadata['published_at'] = None # Set to None if parsing fails
                        metadata['filepath'] = filepath
                        metadata_list.append(metadata)
                    except yaml.YAMLError as e:
                        st.error(f"Error parsing YAML in {filename}: {e}")

    metadata_list.sort(key=lambda x: x.get('published_at', '1970-01-01T00:00:00'), reverse=True)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=4)
    st.cache_data.clear() # 캐시 지우기
    st.rerun() # UI 새로고침

@st.cache_data
def get_all_relative_subdirs(base_path):
    """
    주어진 기본 경로 내의 모든 하위 디렉토리의 상대 경로를 반환합니다.
    """
    subdirs = []
    if os.path.exists(base_path):
        for root, dirs, files in os.walk(base_path):
            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                relative_path = os.path.relpath(full_path, base_path)
                subdirs.append(relative_path)
    return sorted(subdirs)



# Function to save current config as a preset
def save_config_as_preset(config_data: DictConfig, preset_name: str):
    preset_dir = os.path.join(os.getcwd(), "configs", "presets")
    os.makedirs(preset_dir, exist_ok=True)
    preset_filepath = os.path.join(preset_dir, f"{preset_name}.yaml")
    OmegaConf.save(config_data, preset_filepath)
    st.success(f"설정 프리셋 '{preset_name}'이 저장되었습니다.")

# Function to load a preset config
@st.cache_data
def load_preset_config(preset_name: str):
    preset_dir = os.path.join(os.getcwd(), "configs", "presets")
    preset_filepath = os.path.join(preset_dir, f"{preset_name}.yaml")
    if os.path.exists(preset_filepath):
        return OmegaConf.load(preset_filepath)
    return None

# 대시보드 UI
# 대시보드 UI
st.set_page_config(layout="wide", page_title="Omni-Collector Dashboard")
st.title("Omni-Collector Dashboard")

# Session State 초기화 (모든 위젯보다 먼저 실행되어야 함)
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
if 'confirm_delete' not in st.session_state:
    st.session_state['confirm_delete'] = False
if 'editing_data' not in st.session_state:
    st.session_state['editing_data'] = None
if 'load_preset_trigger' not in st.session_state:
    st.session_state['load_preset_trigger'] = False
if 'loaded_preset_config' not in st.session_state:
    st.session_state['loaded_preset_config'] = None

# Initialize session state for collection and processing based on base_cfg
if 'collect_sources_multiselect' not in st.session_state:
    st.session_state.collect_sources_multiselect = list(base_cfg.sources.keys())

for source_name in base_cfg.sources.keys():
    source_cfg = base_cfg.sources[source_name]
    if f"posts_to_scrape_{source_name}" not in st.session_state:
        st.session_state[f"posts_to_scrape_{source_name}"] = source_cfg.posts_to_scrape
    if f"filter_keywords_{source_name}" not in st.session_state:
        st.session_state[f"filter_keywords_{source_name}"] = ", ".join(source_cfg.filter_keywords)
    if source_name == "obsidian" and f"obsidian_folder_paths_{source_name}" not in st.session_state:
        st.session_state[f"obsidian_folder_paths_{source_name}"] = list(source_cfg.folder_paths)
    if source_name == "youtube":
        if f"youtube_channel_ids_{source_name}" not in st.session_state:
            st.session_state[f"youtube_channel_ids_{source_name}"] = "\n".join(source_cfg.channel_ids)
        if f"youtube_playlist_ids_{source_name}" not in st.session_state:
            st.session_state[f"youtube_playlist_ids_{source_name}"] = "\n".join(source_cfg.playlist_ids)
    if source_name == "raindrop" and f"raindrop_collection_ids_{source_name}" not in st.session_state:
        # Need to map IDs back to names for multiselect default
        raindrop_source_instance = RaindropSource(name="raindrop", posts_to_scrape=1)
        collections_map = {id: name for id, name in raindrop_source_instance.get_collections().items()}
        st.session_state[f"raindrop_collection_ids_{source_name}"] = [collections_map[cid] for cid in source_cfg.collection_ids if cid in collections_map]

if 'do_summarize_checkbox' not in st.session_state:
    st.session_state.do_summarize_checkbox = base_cfg.processing.summarize.enabled
if 'summarizer_prompt_select' not in st.session_state:
    st.session_state.summarizer_prompt_select = base_cfg.processing.summarize.selected_prompt_name
if 'do_index_checkbox' not in st.session_state:
    st.session_state.do_index_checkbox = base_cfg.indexing.enabled
if 'new_web_url_input' not in st.session_state:
    st.session_state.new_web_url_input = ""

# Process preset loading trigger at the very beginning
if st.session_state.get('load_preset_trigger', False):
    loaded_cfg = st.session_state.get('loaded_preset_config')
    if loaded_cfg:
        # Update Streamlit session state to reflect loaded config
        st.session_state.collect_sources_multiselect = list(loaded_cfg.sources.keys()) if "sources" in loaded_cfg else []
        
        for source_name, source_cfg_loaded in loaded_cfg.sources.items():
            # Ensure keys exist before setting to avoid errors for missing configs
            if source_name in base_cfg.sources: # Use base_cfg to check for existing sources
                st.session_state[f"posts_to_scrape_{source_name}"] = source_cfg_loaded.posts_to_scrape
                st.session_state[f"filter_keywords_{source_name}"] = ", ".join(source_cfg_loaded.filter_keywords)
                if source_name == "obsidian":
                    st.session_state[f"obsidian_folder_paths_{source_name}"] = list(source_cfg_loaded.folder_paths)
                elif source_name == "youtube":
                    st.session_state[f"youtube_channel_ids_{source_name}"] = "\n".join(source_cfg_loaded.channel_ids)
                    st.session_state[f"youtube_playlist_ids_{source_name}"] = "\n".join(source_cfg_loaded.playlist_ids)
                elif source_name == "raindrop":
                    # Need to map IDs back to names for multiselect default
                    raindrop_source_instance = RaindropSource(name="raindrop", posts_to_scrape=1)
                    collections_map = {id: name for id, name in raindrop_source_instance.get_collections().items()}
                    st.session_state[f"raindrop_collection_ids_{source_name}"] = [collections_map[cid] for cid in source_cfg_loaded.collection_ids if cid in collections_map]

        st.session_state.do_summarize_checkbox = loaded_cfg.processing.summarize.enabled
        st.session_state.summarizer_prompt_select = loaded_cfg.processing.summarize.selected_prompt_name
        st.session_state.do_index_checkbox = loaded_cfg.indexing.enabled
        st.session_state.new_web_url_input = loaded_cfg.get("new_web_url", "")

    # Reset the trigger and loaded config
    st.session_state['load_preset_trigger'] = False
    st.session_state['loaded_preset_config'] = None

metadata_file = os.path.join(os.getcwd(), 'results', 'metadata.json')
df = load_data(metadata_file)

# New section for Data Collection & Processing
st.sidebar.header("데이터 수집 및 처리")
with st.sidebar.expander("새로운 작업 실행", expanded=True): # Expander for better UI organization
    st.write("수집, 요약, 인덱싱 작업을 여기서 실행합니다.")

    

    # Source selection
    selected_sources_to_collect = st.multiselect(
        "수집할 소스 선택",
        options=all_available_sources,
        default=st.session_state.collect_sources_multiselect, # Use default for initial selection
        key="collect_sources_multiselect"
    )

    # Dynamic Source-specific configurations
    st.subheader("소스별 상세 설정")
    custom_source_configs = {}

    for source_name in selected_sources_to_collect:
        with st.expander(f"{source_name} 설정", expanded=False):
            source_cfg = base_cfg.sources[source_name]
            
            # Common settings for all sources
            posts_to_scrape = st.number_input(f"{source_name} - 가져올 게시글 수 (-1은 모두)", value=st.session_state[f"posts_to_scrape_{source_name}"], min_value=-1, key=f"posts_to_scrape_{source_name}")
            filter_keywords = st.text_input(f"{source_name} - 필터링 키워드 (쉼표 구분)", value=st.session_state[f"filter_keywords_{source_name}"], key=f"filter_keywords_{source_name}")
            
            custom_source_configs[source_name] = {
                "posts_to_scrape": posts_to_scrape,
                "filter_keywords": [kw.strip() for kw in filter_keywords.split(',')] if filter_keywords else []
            }

            # Specific settings for each source type
            if source_name == "obsidian":
                st.write("Obsidian 볼트 경로: ", source_cfg.vault_path)
                # Get only direct subdirectories in vault_path
                obsidian_direct_subdirs = []
                if os.path.exists(source_cfg.vault_path):
                    for item in os.listdir(source_cfg.vault_path):
                        if os.path.isdir(os.path.join(source_cfg.vault_path, item)):
                            obsidian_direct_subdirs.append(item)

                selected_folder_paths = st.multiselect(
                    "수집할 폴더 (볼트 내 1단계 하위 폴더만 선택)",
                    options=[""] + obsidian_direct_subdirs, # 빈 문자열 추가하여 전체 볼트 선택 옵션 제공
                    default=list(st.session_state[f"obsidian_folder_paths_{source_name}"]), # 기본값 설정
                    key=f"obsidian_folder_paths_{source_name}"
                )
                
                # 직접 상대 경로 입력 필드 추가
                manual_folder_paths_input = st.text_input(
                    "또는 수집할 폴더의 상대 경로를 직접 입력 (쉼표 구분, 예: folder1/subfolder, folder2)",
                    value=", ".join([fp for fp in st.session_state[f"obsidian_folder_paths_{source_name}"] if fp not in obsidian_direct_subdirs and fp != ""]), # Removed extra parenthesis
                    key=f"obsidian_manual_folder_paths_{source_name}"
                )

                # 최종 folder_paths 조합
                final_folder_paths = [fp for fp in selected_folder_paths if fp != ""]
                if manual_folder_paths_input:
                    final_folder_paths.extend([fp.strip() for fp in manual_folder_paths_input.split(',') if fp.strip()])
                
                custom_source_configs[source_name]["folder_paths"] = final_folder_paths

            elif source_name == "youtube":
                channel_ids_input = st.text_area("수집할 채널 ID (각 줄에 하나씩)", value=st.session_state[f"youtube_channel_ids_{source_name}"], key=f"youtube_channel_ids_{source_name}")
                playlist_ids_input = st.text_area("수집할 플레이리스트 ID (각 줄에 하나씩)", value=st.session_state[f"youtube_playlist_ids_{source_name}"], key=f"youtube_playlist_ids_{source_name}")
                custom_source_configs[source_name]["channel_ids"] = [cid.strip() for cid in channel_ids_input.split('\n')] if channel_ids_input else []
                custom_source_configs[source_name]["playlist_ids"] = [pid.strip() for pid in playlist_ids_input.split('\n')] if playlist_ids_input else []

            elif source_name == "raindrop":
                # Fetch Raindrop collections dynamically
                raindrop_source_instance = RaindropSource(name="raindrop", posts_to_scrape=1) # Dummy instance to get collections
                collections = raindrop_source_instance.get_collections()
                collection_options = {name: id for id, name in collections.items()} # {name: id}
                
                selected_collection_names = st.multiselect(
                    "수집할 컬렉션 선택",
                    options=list(collection_options.keys()),
                    default=[collections[cid] for cid in st.session_state[f"raindrop_collection_ids_{source_name}"] if cid in collections] if st.session_state[f"raindrop_collection_ids_{source_name}"] else [],
                    key=f"raindrop_collection_ids_{source_name}"
                )
                custom_source_configs[source_name]["collection_ids"] = [collection_options[name] for name in selected_collection_names]

    # Summarization option
    st.subheader("요약 설정")
    do_summarize = st.checkbox("수집 후 요약 실행", value=st.session_state.do_summarize_checkbox, key="do_summarize_checkbox")
    
    summarizer_prompts = base_cfg.processing.summarize.prompts
    selected_prompt_name = st.selectbox(
        "사용할 요약 프롬프트 선택",
        options=list(summarizer_prompts.keys()),
        index=list(summarizer_prompts.keys()).index(st.session_state.summarizer_prompt_select) if st.session_state.summarizer_prompt_select in summarizer_prompts else 0,
        key="summarizer_prompt_select"
    )
    with st.expander("프롬프트 미리보기"): # Prompt preview
        st.code(summarizer_prompts[selected_prompt_name], language='markdown')

    # Indexing option
    st.subheader("인덱싱 설정")
    do_index = st.checkbox("작업 완료 후 인덱스 재생성", value=st.session_state.do_index_checkbox, key="do_index_checkbox")

    # New Web URL Collection
    st.subheader("새로운 웹 주소 수집 (실험적)")
    new_web_url = st.text_input("수집할 웹 주소 입력 (예: https://example.com)", value=st.session_state.new_web_url_input, key="new_web_url_input")
    if new_web_url:
        st.warning("새로운 웹 주소 수집은 실험적 기능입니다. 웹사이트 구조에 따라 실패할 수 있습니다.")

    if st.button("작업 실행", key="run_process_button"):
        with st.spinner("작업을 실행 중입니다..."):
            try:
                # Create a mutable copy of the config for overrides
                current_cfg = OmegaConf.to_container(base_cfg, resolve=True, throw_on_missing=True)
                current_cfg = OmegaConf.create(current_cfg) # Convert back to DictConfig

                # Apply custom source configurations
                for source_name, custom_cfg in custom_source_configs.items():
                    if source_name in current_cfg.sources:
                        current_cfg.sources[source_name].posts_to_scrape = custom_cfg["posts_to_scrape"]
                        current_cfg.sources[source_name].filter_keywords = custom_cfg["filter_keywords"]
                        if source_name == "obsidian":
                            current_cfg.sources[source_name].folder_paths = custom_cfg["folder_paths"]
                        elif source_name == "youtube":
                            current_cfg.sources[source_name].channel_ids = custom_cfg["channel_ids"]
                            current_cfg.sources[source_name].playlist_ids = custom_cfg["playlist_ids"]
                        elif source_name == "raindrop":
                            current_cfg.sources[source_name].collection_ids = custom_cfg["collection_ids"]

                # Handle new web URL collection
                if new_web_url:
                    st.info(f"새로운 웹 주소 '{new_web_url}' 수집 중...")
                    # Dynamically create a WebSource config
                    web_source_cfg = OmegaConf.create({
                        "_target_": "src.sources.web.WebSource",
                        "name": "web_custom",
                        "url": new_web_url,
                        "filter_keywords": [] # No filtering for custom web source
                    })
                    # Temporarily add to sources for collection
                    current_cfg.sources.web_custom = web_source_cfg
                    selected_sources_to_collect.append("web_custom")

                # Ensure output directories exist
                output_dir = os.path.join(os.getcwd(), 'results')
                markdown_dir = os.path.join(output_dir, 'markdown')
                os.makedirs(markdown_dir, exist_ok=True)
                metadata_path = os.path.join(output_dir, 'metadata.json')

                # Initialize progress bar
                progress_bar = st.progress(0, text="작업 시작...")
                progress_text = st.empty()
                total_steps = 3 # Collect, Summarize, Index
                current_step = 0
                scraped_data = [] # Initialize scraped_data here

                # 1. Collect data
                if selected_sources_to_collect:
                    current_step += 1
                    progress_bar.progress(current_step / total_steps, text=f"({current_step}/{total_steps}) 데이터 수집 중...")
                    # Filter current_cfg.sources to only include selected_sources_to_collect
                    temp_sources_cfg = OmegaConf.create({s_name: current_cfg.sources[s_name] for s_name in selected_sources_to_collect})
                    current_cfg.sources = temp_sources_cfg

                    scraped_data = run_collection(current_cfg)
                    
                    # Save collected data with item-specific progress
                    item_progress_bar = st.progress(0, text="수집된 항목 저장 중...")
                    for i, data in enumerate(scraped_data):
                        save_to_markdown(data, markdown_dir)
                        item_progress_bar.progress((i + 1) / len(scraped_data), text=f"수집된 항목 저장 중... ({i+1}/{len(scraped_data)})")
                    item_progress_bar.empty() # Clear item progress bar

                    st.success(f"{len(scraped_data)}개 항목 수집 완료.")
                else:
                    st.warning("수집할 소스가 선택되지 않았습니다. 수집 작업을 건너뜁니다.")

                # 2. Summarize data
                processed_data = scraped_data # Start with newly collected data
                if do_summarize:
                    current_step += 1
                    progress_bar.progress(current_step / total_steps, text=f"({current_step}/{total_steps}) 데이터 요약 중...")
                    
                    # If no new data was collected, load from markdown files for summarization
                    if not processed_data: 
                        st.warning("수집된 새 데이터가 없습니다. 기존 마크다운 파일에서 요약 작업을 수행합니다.")
                        data_to_summarize_from_files = []
                        for filename in os.listdir(markdown_dir):
                            if filename.endswith('.md'):
                                filepath = os.path.join(markdown_dir, filename)
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    match = re.search(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                                    if match:
                                        metadata = yaml.safe_load(match.group(1))
                                        body = content[match.end():].strip()
                                        metadata['body'] = body
                                        data_to_summarize_from_files.append(metadata)
                        processed_data = data_to_summarize_from_files

                    # Instantiate summarizer with current config
                    summarizer = instantiate(current_cfg.processing.summarize)

                    # Define progress callback for UI update
                    def update_summarization_progress(current, total):
                        item_progress_bar.progress(current / total, text=f"항목 요약 중... ({current}/{total})")

                    item_progress_bar = st.progress(0, text="항목 요약 중...")
                    summarized_items = summarizer.summarize_data(
                        processed_data,
                        selected_prompt_name,
                        progress_callback=update_summarization_progress
                    )
                    item_progress_bar.empty() # Clear item progress bar

                    # Save summarized data back to markdown files
                    item_progress_bar = st.progress(0, text="요약된 항목 저장 중...")
                    for i, data in enumerate(summarized_items):
                        save_to_markdown(data, markdown_dir)
                        item_progress_bar.progress((i + 1) / len(summarized_items), text=f"요약된 항목 저장 중... ({i+1}/{len(summarized_items)})")
                    item_progress_bar.empty() # Clear item progress bar

                    st.success("데이터 요약 완료.")
                else:
                    st.info("요약 작업이 비활성화되었습니다.")

                # 3. Create/Update metadata index
                if do_index:
                    current_step += 1
                    progress_bar.progress(current_step / total_steps, text=f"({current_step}/{total_steps}) 메타데이터 인덱스 재생성 중...")
                    create_metadata_index(markdown_dir, metadata_path)
                    st.success("메타데이터 인덱스 재생성 완료.")
                else:
                    st.info("인덱스 재생성 작업이 비활성화되었습니다.")

                progress_bar.progress(1.0, text="모든 작업 완료!")
                st.success("모든 작업이 완료되었습니다!")
            except Exception as e:
                st.error(f"작업 중 오류가 발생했습니다: {e}")
            finally:
                st.cache_data.clear() # Clear cache to reload data
                st.rerun() # Rerun app to refresh UI

# Configuration Preset Management
st.sidebar.header("설정 프리셋 관리")
with st.sidebar.expander("프리셋 저장/로드", expanded=False):
    preset_name_to_save = st.text_input("저장할 프리셋 이름", key="preset_name_save_input")
    if st.button("현재 설정 저장", key="save_preset_button"):
        if preset_name_to_save:
            # Construct config from current UI selections
            current_ui_config = OmegaConf.create({
                "sources": {},
                "processing": {
                    "summarize": {
                        "enabled": st.session_state.do_summarize_checkbox,
                        "prompts": base_cfg.processing.summarize.prompts, # Use existing prompts
                        "selected_prompt_name": st.session_state.summarizer_prompt_select
                    }
                },
                "indexing": {
                    "enabled": st.session_state.do_index_checkbox
                },
                "new_web_url": st.session_state.new_web_url_input
            })

            # Add custom source configs
            for source_name, custom_cfg in custom_source_configs.items():
                current_ui_config.sources[source_name] = OmegaConf.create(custom_cfg)

            save_config_as_preset(current_ui_config, preset_name_to_save)
        else:
            st.warning("저장할 프리셋 이름을 입력해주세요.")

    st.markdown("--- ")
    preset_dir = os.path.join(os.getcwd(), "configs", "presets")
    os.makedirs(preset_dir, exist_ok=True) # Ensure presets directory exists
    preset_files = [f.replace(".yaml", "") for f in os.listdir(preset_dir) if f.endswith(".yaml")]
    selected_preset_to_load = st.selectbox("로드할 프리셋 선택", ["선택하세요"] + preset_files, key="preset_name_load_select")
    if st.button("프리셋 로드", key="load_preset_button"):
        if selected_preset_to_load != "선택하세요":
            loaded_cfg = load_preset_config(selected_preset_to_load)
            if loaded_cfg:
                st.session_state['loaded_preset_config'] = loaded_cfg
                st.session_state['load_preset_trigger'] = True
                st.success(f"프리셋 '{selected_preset_to_load}'이 로드되었습니다. 설정을 확인하고 작업을 실행해주세요.")
            else:
                st.error("프리셋 로드에 실패했습니다.")
        else:
            st.warning("로드할 프리셋을 선택해주세요.")
    # Add rerun here, outside the if block for the button
    if st.session_state.get('load_preset_trigger', False):
        st.rerun()

if df.empty:
    st.info("수집된 데이터가 없습니다. `main.py`를 실행하거나, 좌측 사이드바에서 작업을 실행해주세요.")
else:
    # 사이드바 필터 및 검색
    st.sidebar.header("필터 및 검색")
    search_query = st.sidebar.text_input("제목 또는 요약 검색", "")
    selected_source = st.sidebar.selectbox("소스 선택", ["모두"] + df['source'].unique().tolist())
    min_rating = st.sidebar.slider("최소 중요도 (별점)", 0, 5, 0)

    st.sidebar.header("정렬")
    sort_by = st.sidebar.selectbox("정렬 기준", ["발행일", "중요도", "제목", "조회수", "좋아요"], index=0)
    sort_order = st.sidebar.radio("정렬 순서", ["내림차순", "오름차순"], index=0)

    # 데이터 필터링
    filtered_df = df
    if search_query:
        filtered_df = filtered_df[filtered_df.apply(lambda row: search_query.lower() in str(row.get('title', '')).lower() or search_query.lower() in str(row.get('summary', '')).lower(), axis=1)]
    if selected_source != "모두":
        filtered_df = filtered_df[filtered_df['source'] == selected_source]
    
    # 중요도 필터링
    filtered_df = filtered_df[filtered_df['rating'].fillna(0) >= min_rating]

    # 데이터 정렬
    if sort_by == "발행일":
        filtered_df = filtered_df.sort_values(by='published_at', ascending=(sort_order == "오름차순"))
    elif sort_by == "중요도":
        filtered_df = filtered_df.sort_values(by='rating', ascending=(sort_order == "오름차순"), na_position='first')
    elif sort_by == "제목":
        filtered_df = filtered_df.sort_values(by='title', ascending=(sort_order == "오름차순"))
    elif sort_by == "조회수":
        filtered_df = filtered_df.sort_values(by='view_count', ascending=(sort_order == "오름차순"), na_position='first')
    elif sort_by == "좋아요":
        filtered_df = filtered_df.sort_values(by='like_count', ascending=(sort_order == "오름차순"), na_position='first')

    st.write(f"총 {len(filtered_df)}개의 항목이 있습니다.")

    # 탭 생성
    all_sources = ["모두"] + df['source'].unique().tolist()
    tabs = st.tabs(all_sources)

    for i, source_tab in enumerate(tabs):
        with source_tab:
            current_source = all_sources[i]
            tab_filtered_df = filtered_df
            if current_source != "모두":
                tab_filtered_df = filtered_df[filtered_df['source'] == current_source]
            
            if tab_filtered_df.empty:
                st.info(f"{current_source} 소스에는 필터링된 데이터가 없습니다.")
                continue

            # 데이터 표시 (테이블)
            st.dataframe(
                tab_filtered_df[['title', 'source', 'published_at', 'summary']],
                use_container_width=True,
                hide_index=True,
                on_select='rerun',
                selection_mode='single-row',
                key=f"data_table_{current_source}", # 탭별로 고유한 키 사용
                column_config={
                    "title": st.column_config.TextColumn("제목"),
                    "source": st.column_config.TextColumn("소스"),
                    "published_at": st.column_config.DatetimeColumn("발행일", format="YYYY-MM-DD HH:mm"),
                    "summary": st.column_config.TextColumn("요약"),
                }
            )

            # 선택된 항목 상세 보기
            # 탭별로 선택된 행을 확인
            selected_key = f'data_table_{current_source}'
            if st.session_state.get(selected_key) and st.session_state[selected_key].get('selection') and st.session_state[selected_key]['selection'].get('rows'):
                selected_index = st.session_state[selected_key]['selection']['rows'][0]
                selected_data = tab_filtered_df.iloc[selected_index]

                st.subheader("상세 정보")
                st.markdown(f"**제목:** {selected_data['title']}")
                st.markdown(f"**소스:** {selected_data['source']}")
                st.markdown(f"**URL:** [{selected_data['url']}]({selected_data['url']})")
                
                # 발행일 처리
                if 'published_at' in selected_data and pd.notna(selected_data['published_at']):
                    st.markdown(f"**발행일:** {selected_data['published_at'].strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.markdown("**발행일:** 정보 없음")

                # 추가 메타데이터 표시
                if 'channel_title' in selected_data and selected_data['channel_title']:
                    st.markdown(f"**채널:** {selected_data['channel_title']}")
                
                # view_count 처리
                view_count_val = 0
                if 'view_count' in selected_data:
                    try:
                        view_count_val = int(selected_data['view_count'])
                    except (ValueError, TypeError):
                        view_count_val = 0 # 숫자로 변환할 수 없으면 0으로 처리
                if view_count_val > 0:
                    st.markdown(f"**조회수:** {view_count_val:,}")
                
                # like_count 처리
                like_count_val = 0
                if 'like_count' in selected_data:
                    try:
                        like_count_val = int(selected_data['like_count'])
                    except (ValueError, TypeError):
                        like_count_val = 0
                if like_count_val > 0:
                    st.markdown(f"**좋아요:** {like_count_val:,}")
                
                # comment_count 처리
                comment_count_val = 0
                if 'comment_count' in selected_data:
                    try:
                        comment_count_val = int(selected_data['comment_count'])
                    except (ValueError, TypeError):
                        comment_count_val = 0
                if comment_count_val > 0:
                    st.markdown(f"**댓글 수:** {comment_count_val:,}")
                
                # tags 처리
                tags_list = selected_data.get('tags', [])
                if tags_list:
                    # Ensure tags_list is a list of strings
                    if isinstance(tags_list, str):
                        tags_list = [tag.strip() for tag in tags_list.split(',')]
                    elif not isinstance(tags_list, list):
                        tags_list = [str(tags_list)] # Convert to list containing string representation
                    
                    st.markdown(f"**태그:** {', '.join(tags_list)}")

                # 중요도 별점 표시 및 수정
                current_rating = selected_data.get('rating', 0)
                new_rating = st.slider("중요도 (별점)", 0, 5, current_rating, key=f"rating_slider_{selected_data['filepath']}")
                if new_rating != current_rating:
                    selected_data['rating'] = new_rating
                    save_markdown_content(selected_data.to_dict(), selected_data['filepath'])
                    update_metadata_index(os.path.join(os.getcwd(), 'results', 'markdown'), metadata_file)
                    st.success(f"''{selected_data['title']}''의 중요도가 {new_rating}점으로 업데이트되었습니다.")
                    st.rerun()

                st.subheader("요약 내용")
                st.write(selected_data['summary'])

                st.subheader("원본 내용")
                markdown_content = load_markdown_content(selected_data['filepath'])
                st.markdown(markdown_content)

                st.markdown("--- ")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("수정", key=f"edit_button_{selected_data['filepath']}"): # 수정 버튼
                        st.session_state['edit_mode'] = True
                        st.session_state['editing_data'] = selected_data.to_dict()
                        st.rerun()
                with col2:
                    if st.button("삭제", key=f"delete_button_{selected_data['filepath']}"): # 삭제 버튼
                        if st.session_state.get('confirm_delete', False):
                            os.remove(selected_data['filepath'])
                            update_metadata_index(os.path.join(os.getcwd(), 'results', 'markdown'), metadata_file)
                            st.success("항목이 삭제되었습니다.")
                            st.session_state['confirm_delete'] = False
                            st.rerun()
                        else:
                            st.session_state['confirm_delete'] = True
                            st.warning("정말로 삭제하시겠습니까? 다시 한번 삭제 버튼을 누르면 영구 삭제됩니다.")

    if st.session_state.get('edit_mode', False):
        editing_data = st.session_state['editing_data']
        st.subheader("항목 수정")
        with st.form("edit_form"):
            edited_title = st.text_input("제목", editing_data.get('title', ''))
            edited_url = st.text_input("URL", editing_data.get('url', ''))
            edited_summary = st.text_area("요약", editing_data.get('summary', ''), height=200)
            edited_body = st.text_area("원본 내용", load_markdown_content(editing_data['filepath']), height=400)
            edited_tags = st.text_input("태그 (쉼표로 구분)", ', '.join(editing_data.get('tags', [])))
            edited_rating = st.slider("중요도 (별점)", 0, 5, editing_data.get('rating', 0))

            submitted = st.form_submit_button("수정 완료")
            if submitted:
                editing_data['title'] = edited_title
                editing_data['url'] = edited_url
                editing_data['summary'] = edited_summary
                editing_data['body'] = edited_body
                editing_data['tags'] = [tag.strip() for tag in edited_tags.split(',')] if edited_tags else []
                editing_data['rating'] = edited_rating

                save_markdown_content(editing_data, editing_data['filepath'])
                update_metadata_index(os.path.join(os.getcwd(), 'results', 'markdown'), metadata_file)
                st.success("항목이 성공적으로 수정되었습니다.")
                st.session_state['edit_mode'] = False
                st.session_state['editing_data'] = None
                st.rerun()

            if st.form_submit_button("취소"):
                st.session_state['edit_mode'] = False
                st.session_state['editing_data'] = None
                st.rerun()