# fastapi-fileparser

LLM を内部利用したファイルテキストパーサー API。
テキスト・画像・PDF・Word など複数形式のファイルを受け取り、テキスト抽出または内容説明を SSE ストリームで返却する。

## 技術スタック

| カテゴリ | ライブラリ | 用途 |
|---------|-----------|------|
| Web Framework | FastAPI + Uvicorn | API サーバー |
| パッケージ管理 | uv | 依存管理・仮想環境 |
| SSE | sse-starlette | Server-Sent Events による進捗通知 |
| PDF | pypdfium2 | テキスト抽出 + ページ画像化 |
| Word | python-docx | .docx テキスト抽出 |
| 文字コード検出 | charset-normalizer | エンコーディング自動判定 |
| MIME 判定 | filetype | バイナリシグネチャベースの MIME 検出 |
| 画像処理 | Pillow | PDF ページの画像レンダリング |
| LLM (Anthropic) | anthropic SDK | Claude によるマルチモーダル解析 |
| LLM (OpenAI) | openai SDK | GPT-4o によるマルチモーダル解析 |
| LLM (Ollama) | openai SDK (互換API) | ローカル LLM (LLaVA 等) |
| LLM (vLLM) | openai SDK (互換API) | セルフホスト LLM サーバー |
| 設定管理 | pydantic-settings | 環境変数ベースの設定 |

## セットアップ

```bash
# 依存インストール
uv sync

# 環境変数の設定
cp .env.example .env
# .env を編集して API キーを設定

# 起動
uv run uvicorn app.main:app --reload
```

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `APP_LLM_PROVIDER` | LLM プロバイダー (`anthropic`, `openai`, `ollama`, `vllm`) | `anthropic` |
| `APP_ANTHROPIC_API_KEY` | Anthropic API キー | - |
| `APP_ANTHROPIC_MODEL` | Claude モデル名 | `claude-sonnet-4-20250514` |
| `APP_OPENAI_API_KEY` | OpenAI API キー | - |
| `APP_OPENAI_MODEL` | OpenAI モデル名 | `gpt-4o` |
| `APP_OLLAMA_BASE_URL` | Ollama サーバー URL | `http://localhost:11434/v1` |
| `APP_OLLAMA_MODEL` | Ollama モデル名 | `llava` |
| `APP_VLLM_BASE_URL` | vLLM サーバー URL | `http://localhost:8000/v1` |
| `APP_VLLM_MODEL` | vLLM モデル名 | - |
| `APP_MAX_UPLOAD_SIZE_MB` | アップロード上限 (MB) | `20` |
| `APP_LOG_LEVEL` | ログレベル | `INFO` |

## API

### `POST /parse`

ファイルをアップロードしてテキスト抽出を行う。レスポンスは SSE ストリーム。

```bash
curl -N -F "file=@sample.pdf" http://localhost:8000/parse
```

#### SSE イベント

**`progress`** — 処理進捗

```
event: progress
data: {"step": "file_received", "message": "ファイルを受信しました: sample.pdf"}

event: progress
data: {"step": "mime_detected", "message": "MIME判定完了: application/pdf"}

event: progress
data: {"step": "parsing_page", "message": "テキスト抽出中: ページ 1/3"}
```

**`complete`** — 処理完了（最終結果）

```
event: complete
data: {"filename": "sample.pdf", "content_type": "application/pdf", "parser_used": "pdf", "text": "...", "metadata": {"page_count": "3", "extraction_method": "text"}}
```

**`error`** — エラー発生

```
event: error
data: {"detail": "Unsupported file type: application/zip"}
```

#### 進捗ステップ一覧

| step | タイミング |
|------|-----------|
| `file_received` | ファイル受信直後 |
| `mime_detected` | MIME タイプ判定完了 |
| `parsing` | パース処理開始・状態変化 |
| `parsing_page` | ページ単位の処理進捗 (PDF) |
| `llm_processing` | LLM 解析開始 |
| `llm_complete` | LLM 解析完了 |

## 対応ファイル形式

### テキスト (`text` パーサー)

文字コードを自動検出し UTF-8 に正規化して返却。

- `text/plain`, `text/csv`, `text/html`, `text/markdown`, `text/xml`, `text/css`, `text/javascript`
- `application/json`, `application/xml`

metadata: `detected_encoding`, `confidence`

### 画像 (`image` パーサー)

マルチモーダル LLM で解析。テキストが含まれていれば OCR、写真なら情景説明。

- `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/tiff`

### PDF (`pdf` パーサー)

pypdfium2 でテキスト抽出を試行。テキストが少ない場合（スキャン PDF 等）はページを画像化して LLM で OCR。

- `application/pdf`

metadata: `page_count`, `extraction_method` (`"text"` or `"image_fallback"`)

判定基準: 全ページのテキストが空白除去後 50 文字未満の場合、スキャン PDF と判断。

### Word (`docx` パーサー)

段落テキストおよびテーブルセルのテキストを抽出。

- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

metadata: `paragraph_count`, `table_count`

## アーキテクチャ

```
POST /parse
  ↓
ファイル受信 → MIME 判定 (filetype + 拡張子フォールバック)
  ↓
ParserRegistry → MIMEタイプに対応する BaseParser を取得
  ↓
Parser.parse() 実行 (進捗コールバック付き)
  ↓
SSE ストリームで progress → complete を返却
```

### ディレクトリ構成

```
src/app/
├── main.py                  # アプリ生成・パーサー登録
├── config.py                # 環境変数設定
├── schemas.py               # レスポンスモデル
├── api/
│   └── routes.py            # POST /parse エンドポイント (SSE)
├── parsers/
│   ├── base.py              # BaseParser ABC + ParseResult
│   ├── text.py              # テキスト (文字コード正規化)
│   ├── image.py             # 画像 (LLM OCR/情景説明)
│   ├── pdf.py               # PDF (pypdfium2 + LLM フォールバック)
│   └── docx.py              # Word 文書
└── services/
    ├── llm.py               # BaseLLMService ABC
    ├── llm_anthropic.py     # Claude 実装
    ├── llm_openai.py        # OpenAI 実装
    └── parser_registry.py   # パーサー登録・ディスパッチ
```

### LLM プロバイダー切替

`APP_LLM_PROVIDER` 環境変数で切り替え可能。

| プロバイダー | 説明 | API キー要否 |
|---|---|---|
| `anthropic` | Anthropic Claude API | 要 |
| `openai` | OpenAI API | 要 |
| `ollama` | ローカル Ollama サーバー (OpenAI 互換 API) | 不要 |
| `vllm` | vLLM サーバー (OpenAI 互換 API) | 不要 |

Ollama / vLLM は OpenAI 互換エンドポイントを利用するため、追加の SDK 依存はなし。
`BaseLLMService` ABC を実装する形で、新しいプロバイダーも追加できる。

#### Ollama での利用例

```bash
# Ollama でマルチモーダルモデルを起動
ollama pull llava
ollama serve

# .env 設定
APP_LLM_PROVIDER=ollama
APP_OLLAMA_MODEL=llava
```

#### vLLM での利用例

```bash
# vLLM でマルチモーダルモデルを起動
vllm serve llava-hf/llava-1.5-7b-hf

# .env 設定
APP_LLM_PROVIDER=vllm
APP_VLLM_MODEL=llava-hf/llava-1.5-7b-hf
```

## 新しいファイル形式の追加方法

1. `src/app/parsers/` に新しいパーサーモジュールを作成:

```python
from app.parsers.base import BaseParser, ParseResult, ProgressCallback

class ExcelParser(BaseParser):
    def supported_mimetypes(self) -> set[str]:
        return {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    async def parse(
        self,
        content: bytes,
        mime_type: str,
        filename: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ParseResult:
        await self._notify(progress_callback, "parsing", "Excel解析中...")
        # ... パース処理 ...
        return ParseResult(
            text=extracted_text,
            content_type=mime_type,
            parser_used="excel",
            metadata={"sheet_count": "3"},
        )
```

2. `src/app/main.py` の `lifespan()` でレジストリに登録:

```python
from app.parsers.excel import ExcelParser

registry.register(ExcelParser())  # LLM不要の場合
# registry.register(ExcelParser(llm_service))  # LLM必要の場合
```

他のファイルの変更は不要。

## テスト

```bash
# 全テスト実行
uv run pytest -v

# lint
uv run ruff check src/ tests/
```

LLM 依存のテストはモックを使用しており、API キーなしで実行可能。
