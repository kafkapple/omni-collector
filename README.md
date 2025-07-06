# omni-collector

`omni-collector`는 다양한 온라인 소스(웹사이트, API 기반 서비스) 및 로컬 파일 시스템에서 콘텐츠를 수집하고, Google Gemini API를 활용하여 핵심 내용을 요약하며, 체계적으로 분석된 결과를 관리하는 다목적 정보 수집 및 관리 도구입니다.

## 🚀 주요 기능

*   **모듈화된 실행 흐름:** 데이터 수집, 요약, 메타데이터 인덱스 생성을 독립적으로 실행하거나 통합하여 수행할 수 있습니다.
*   **하이브리드 데이터 저장:** 수집된 각 콘텐츠를 개별 마크다운 파일(`.md`)로 저장하고, 빠른 검색을 위한 메타데이터 인덱스(`metadata.json`)를 별도로 관리합니다. 이는 Obsidian과 같은 지식 관리 도구와의 호환성을 높여줍니다.
*   **유연한 설정 관리:** [Hydra](https://hydra.cc/)를 사용하여 `configs/config.yaml` 파일 하나로 모든 수집 및 요약 설정을 중앙에서 관리합니다.
*   **다양한 소스 지원:**
    *   **웹 스크래핑:** PyTorch Korea 커뮤니티, GPTERS 뉴스 등 특정 웹사이트의 게시글을 스크랩하며, 조회수, 좋아요 수 등 추가 메타데이터를 수집합니다.
    *   **API 연동:** Raindrop.io와 같은 개인 웹 스크랩 앱에서 데이터를 가져옵니다.
    *   **로컬 파일 시스템:** Obsidian 볼트 내의 마크다운 파일 내용을 읽어 처리합니다.
    *   **YouTube:** 채널 또는 플레이리스트의 비디오 메타데이터를 가져오고, 자막(있는 경우)을 추출합니다. IP 차단에 대비한 견고한 재시도 및 딜레이 로직이 포함되어 있습니다.
*   **지능형 요약:** Google Gemini API를 사용하여 수집된 콘텐츠의 핵심 내용을 자동으로 요약합니다.
*   **필터링:** 키워드 기반 필터링 기능을 제공하며, 필터링 키워드가 없을 경우 모든 자료를 수집합니다.
*   **웹 기반 관리 대시보드 (Streamlit):** 수집 및 처리된 데이터를 시각적으로 확인하고, 검색, 필터링, 정렬은 물론, 항목 수정 및 삭제(CRUD)가 가능한 사용자 친화적인 UI를 제공합니다.
*   **Conda 기반 환경 관리:** `environment.yml` 파일을 통해 안정적이고 재현 가능한 개발 환경을 구축할 수 있습니다.

## 🛠️ 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/omni-collector.git # 실제 저장소 URL로 대체
cd omni-collector
```

### 2. 개발 환경 설정 (Conda)

이 프로젝트는 **Conda**를 사용하여 파이썬 환경을 관리하는 것을 권장합니다. Conda를 사용하면 프로젝트에 필요한 모든 라이브러리(의존성)를 격리된 환경에 설치하여 버전 충돌을 방지하고 재현성을 보장할 수 있습니다.

#### Conda 설치
Conda가 설치되어 있지 않다면, [Miniconda 설치 가이드](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html)를 참조하여 설치를 진행해 주세요.

#### Conda 환경 생성 및 활성화
프로젝트 루트 디렉토리에 포함된 `environment.yml` 파일을 사용하여 `omni-collector` 실행에 필요한 모든 패키지가 포함된 Conda 환경을 생성합니다.

```bash
# 1. environment.yml 파일로 Conda 환경 생성
conda env create -f environment.yml

# 2. 생성된 환경 활성화
conda activate omni-collector
```

이제 터미널 프롬프트 앞에 `(omni-collector)`가 표시되며, 프로젝트 실행에 필요한 모든 라이브러리가 준비된 상태입니다.

### 3. API 키 설정 (`.env` 파일)

`omni-collector` 디렉토리 내에 `.env` 파일을 생성하고, 필요한 API 키를 다음과 같이 추가합니다.

```
# Google Gemini API 키
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Raindrop.io Permanent Access Token
# Raindrop.io 설정 > 통합 > API 에서 발급 가능
RAINDROP_ACCESS_TOKEN="YOUR_RAINDROP_ACCESS_TOKEN"

# Google YouTube Data API v3 키
# Google Cloud Console에서 YouTube Data API v3 활성화 후 발급
YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
```

### 4. 설정 파일 (`configs/config.yaml`)

`configs/config.yaml` 파일은 `omni-collector`의 모든 동작을 제어합니다. 각 소스, 처리 방식, 저장 옵션을 여기서 설정할 수 있습니다. 자세한 설정 방법은 파일 내 주석을 참고하세요.

## 🚀 사용법

`omni-collector`는 다양한 모드로 실행될 수 있습니다. `main.py`를 실행할 때 `cli.mode` 파라미터를 사용하여 원하는 작업을 지정할 수 있습니다.

*   **모든 작업 실행 (기본값):** 데이터 수집, 요약, 메타데이터 인덱스 생성을 순차적으로 실행합니다.
    ```bash
    python main.py
    # 또는
    python main.py cli.mode=all
    ```

*   **데이터 수집만 실행:** 설정된 소스에서 데이터를 수집하여 마크다운 파일로 저장합니다.
    ```bash
    python main.py cli.mode=collect
    ```

*   **요약만 실행:** 기존에 수집된 마크다운 파일들을 읽어 요약하고, 요약된 내용을 다시 마크다운 파일에 업데이트합니다. `--input` 파라미터로 요약할 파일 또는 디렉토리를 지정해야 합니다.
    ```bash
    # results/markdown 디렉토리의 모든 마크다운 파일 요약
    python main.py cli.mode=summarize cli.input=results/markdown

    # 특정 마크다운 파일만 요약
    python main.py cli.mode=summarize cli.input=results/markdown/Your_Article_Title.md
    ```

*   **메타데이터 인덱스만 생성:** `results/markdown` 디렉토리의 마크다운 파일들을 기반으로 `results/metadata.json` 파일을 재생성합니다. 데이터 수집이나 요약 없이 인덱스만 업데이트할 때 유용합니다.
    ```bash
    python main.py cli.mode=index
    ```

## 📊 웹 대시보드 사용법

수집 및 처리된 데이터를 시각적으로 확인하고 관리하려면 웹 대시보드를 사용할 수 있습니다. 프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다.

```bash
streamlit run app.py
```

웹 브라우저에 대시보드가 열리면, 수집된 콘텐츠 목록을 확인하고 검색 및 필터링할 수 있습니다. 각 항목을 클릭하면 상세 내용을 볼 수 있으며, 수정 및 삭제 기능도 제공됩니다.

## 📂 출력 결과

스크립트 실행이 완료되면, 프로젝트 루트 디렉토리의 `results/` 폴더에 다음 파일들이 생성됩니다.

*   `results/markdown/`: 수집 및 처리된 각 콘텐츠가 개별 마크다운 파일(`.md`)로 저장됩니다. 각 파일은 YAML Frontmatter에 메타데이터를 포함합니다.
*   `results/metadata.json`: 모든 마크다운 파일의 핵심 메타데이터를 포함하는 JSON 인덱스 파일입니다. 웹 대시보드에서 빠른 검색 및 로딩을 위해 사용됩니다.

마크다운 파일 예시 (`results/markdown/Your_Article_Title.md`):

```markdown
---
title: "수집된 게시글 제목"
url: "게시글 URL"
source: "소스 이름 (예: pytorch_kr, raindrop)"
published_at: "2024-07-04T10:30:00+09:00" # ISO 8601 형식
view_count: 12345
like_count: 678
tags: ["AI", "LLM"]
summary: "Gemini가 요약한 내용"
filepath: "/path/to/your/project/results/markdown/Your_Article_Title.md"
---

원본 본문 내용 또는 요약된 본문 내용이 여기에 표시됩니다.
```

`results/metadata.json` 파일 예시:

```json
[
  {
    "title": "수집된 게시글 제목",
    "url": "게시글 URL",
    "source": "소스 이름 (예: pytorch_kr, raindrop)",
    "published_at": "2024-07-04T10:30:00+09:00",
    "view_count": 12345,
    "like_count": 678,
    "tags": ["AI", "LLM"],
    "summary": "Gemini가 요약한 내용",
    "filepath": "/path/to/your/project/results/markdown/Your_Article_Title.md"
  }
]
```

## ⚙️ 환경 업데이트

프로젝트의 의존성이 변경된 경우(예: 새로운 라이브러리 추가), 다음 명령어를 사용하여 Conda 환경을 업데이트할 수 있습니다.

```bash
conda env update --file environment.yml --prune
```

## ⚠️ 문제 해결

### YouTube 자막 스크래핑 문제 (IP 차단)

`youtube-transcript-api`를 사용하여 YouTube 자막을 가져오는 과정에서 `YouTube is blocking requests from your IP`와 같은 오류가 발생할 수 있습니다. 이는 YouTube의 자동화된 요청 방지 정책으로 인한 IP 차단 때문입니다.

**해결 방법:**

1.  **딜레이 설정:** `configs/config.yaml` 파일의 `youtube` 소스 설정에서 `delay_between_requests` 값을 늘려보세요. (예: `10`)
2.  **IP 주소 변경:**
    *   **VPN 사용:** VPN을 사용하여 IP 주소를 변경하면 YouTube의 IP 차단을 우회할 수 있습니다.
    *   **네트워크 변경:** 다른 Wi-Fi 네트워크를 사용하거나, 모바일 핫스팟을 사용하여 IP 주소를 변경해 볼 수 있습니다.
3.  **시간 대기:** YouTube의 IP 차단은 일시적일 수 있습니다. 몇 시간 또는 하루 정도 기다린 후 다시 시도하면 차단이 해제될 수 있습니다.

### API 키 관련 오류

*   `.env` 파일에 API 키가 올바르게 설정되었는지 확인합니다. (오타, 공백 주의)
*   Google Cloud Console에서 해당 API(Gemini API, YouTube Data API 등)가 프로젝트에서 활성화되어 있고, API 키에 해당 API에 대한 접근 권한이 부여되어 있는지 확인합니다.

### 웹 스크래핑 오류

*   웹사이트의 HTML 구조가 변경되었을 수 있습니다. `configs/config.yaml` 내의 해당 소스 `selectors`를 웹사이트의 최신 HTML 구조에 맞춰 업데이트해야 합니다.

## ✨ 향후 개선 사항 (Roadmap)

*   **날짜 기반 필터링:** `config.yaml`에서 날짜 범위를 지정하여 콘텐츠를 수집하는 기능.
*   **작성자/채널 정보 추가:** 수집된 결과에 작성자 또는 채널 정보를 포함하는 기능.
*   **원본 콘텐츠 저장 옵션:** 수집된 원본 콘텐츠(HTML, 텍스트)를 별도로 저장할지 여부를 설정하는 기능.
*   **다양한 요약 프롬프트:** `config.yaml`에서 여러 요약 프롬프트 템플릿을 정의하고 선택하여 사용하는 기능.
*   **추가 소스 연동:** Reddit, Threads, Towards Data Science, Technology Review, DeepMind 블로그 등 다양한 웹사이트 및 API 연동.
*   **개인 웹 스크랩 앱 연동 확장:** Pocket 등 다른 개인 웹 스크랩 앱 연동.
*   **YouTube 고급 기능:** 자막 없는 영상의 음성-텍스트 변환(STT) 기능 (OpenAI Whisper 등 활용).
*   **Obsidian 플러그인 연동:** `obsidian-llm-workspace`와 같은 플러그인을 참고하여 Obsidian 내에서 직접 콘텐츠를 분석하고 관리하는 기능.
*   **데이터베이스 저장:** JSON 파일 외에 SQLite, Notion 데이터베이스 등 다양한 저장 옵션 제공.
