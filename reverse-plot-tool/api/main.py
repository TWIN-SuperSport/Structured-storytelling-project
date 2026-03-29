from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
import os

app = FastAPI()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://llm-relay.wos.ktsys.jp")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))

SYSTEM_PROMPT = """あなたは、物語の終着条件から成立条件を遡上して構造化するアシスタントです。
ユーザーが与えた結末や終着条件から、物語の前提・欠落・欲望・誤信念・関係変化・転換点・起承転結・エピローグを逆算してください。

必ず以下の JSON 形式のみで返してください（前置き禁止、説明禁止）:
{
  "title": "仮タイトル",
  "ending_summary": "物語の結末要約",
  "core_theme": "中心テーマ",
  "protagonist_final_state": "結末時の主人公の状態",
  "structural_conditions": {
    "initial_lack": "初期欠落",
    "desire": "主人公の欲望",
    "fear": "主人公の恐れ",
    "false_belief": "誤信念",
    "starting_situation": "物語開始時の初期配置"
  },
  "relationship_changes": [
    "必要な関係変化1",
    "必要な関係変化2"
  ],
  "required_turning_points": [
    "必要な転換点1",
    "必要な転換点2",
    "必要な転換点3"
  ],
  "failure_conditions": [
    "破綻してはいけない条件1",
    "破綻してはいけない条件2"
  ],
  "plot": {
    "prologue": "2〜3文のあらすじ",
    "ki": "2〜3文のあらすじ",
    "sho": "2〜3文のあらすじ",
    "ten": "2〜3文のあらすじ",
    "ketsu": "2〜3文のあらすじ",
    "epilogue": "2〜3文のあらすじ"
  }
}"""


class ReversePlotRequest(BaseModel):
    ending_text: str
    protagonist_hint: str | None = None
    genre_hint: str | None = None
    output_format_version: str | None = None


async def call_llm(messages: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT, verify=False) as client:
        res = await client.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": 1400,
                "temperature": 0.7,
            },
        )
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("LLM が JSON を返しませんでした")
        return json.loads(content[start:end])


def validate_reverse_plot(data: dict) -> dict:
    required_top = [
        "title",
        "ending_summary",
        "core_theme",
        "protagonist_final_state",
        "structural_conditions",
        "relationship_changes",
        "required_turning_points",
        "failure_conditions",
        "plot",
    ]
    for key in required_top:
        if key not in data:
            raise ValueError(f"必須フィールドが欠落: {key}")

    structural = data["structural_conditions"]
    for key in ["initial_lack", "desire", "fear", "false_belief", "starting_situation"]:
        if key not in structural or not structural[key]:
            raise ValueError(f"structural_conditions.{key} が不足")

    plot = data["plot"]
    for key in ["prologue", "ki", "sho", "ten", "ketsu", "epilogue"]:
        if key not in plot or not plot[key]:
            raise ValueError(f"plot.{key} が不足")

    return data


def build_user_content(req: ReversePlotRequest) -> str:
    chunks = [f"終着条件:\n{req.ending_text.strip()}"]
    if req.protagonist_hint:
        chunks.append(f"主人公ヒント:\n{req.protagonist_hint.strip()}")
    if req.genre_hint:
        chunks.append(f"ジャンルヒント:\n{req.genre_hint.strip()}")
    chunks.append("結末から最初の前提までを遡上し、JSON だけで返してください。")
    return "\n\n".join(chunks)


@app.post("/api/story/reverse-plot")
async def reverse_plot(req: ReversePlotRequest):
    if not req.ending_text.strip():
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is required"})
    if len(req.ending_text) > 1200:
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is too long"})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_content(req)},
    ]

    try:
        payload = validate_reverse_plot(await call_llm(messages))
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"status": "invalid_llm_output", "message": str(e)})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"status": "llm_timeout", "message": "LLM の応答がタイムアウトしました"})
    except Exception as e:
        raise HTTPException(status_code=502, detail={"status": "llm_upstream_error", "message": str(e)})

    return {"status": "success", "story": payload}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
