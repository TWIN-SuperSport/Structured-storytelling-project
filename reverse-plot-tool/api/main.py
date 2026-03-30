from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
import json
import os

app = FastAPI()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://swallow-relay.wos.ktsys.jp")
LLM_MODEL = os.getenv("LLM_MODEL", "swallow")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "240"))

SYSTEM_PROMPT = """あなたは、物語の終着条件から成立条件を遡上して構造化するアシスタントです。
ユーザーが与えた結末や終着条件から、物語の前提・欠落・欲望・誤信念・関係変化・転換点・起承転結・エピローグを逆算してください。
あわせて「突拍子レベル」に従い、展開の意外性を調整してください。
突拍子レベルは 0 なら自然で堅実、10 なら起承転結の「転」で大きく前提がひっくり返る級の変化です。
ただし、どのレベルでも因果関係・感情の流れ・終着条件との整合性は壊さないでください。

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
    wild_twist_level: int = Field(default=0, ge=0, le=10)
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


def build_wild_twist_guidance(level: int) -> str:
    if level == 0:
        return "突拍子レベル 0: 展開は堅実にし、唐突な急展開や奇矯さは入れない。"
    if level <= 3:
        return "突拍子レベル 1-3: 小さな意外性や新鮮さは入れてよいが、全体は自然な成長譚として保つ。"
    if level <= 6:
        return "突拍子レベル 4-6: 中盤から後半にかけて、予想外だが納得できる方向転換を明確に入れる。"
    if level <= 9:
        return "突拍子レベル 7-9: 『転』で前提や関係が大きく揺らぐ展開を入れる。ただし感情線と終着条件は守る。"
    return "突拍子レベル 10: 『転』で物語の見え方がひっくり返る級の大胆な変化を入れる。ただし破綻や投げっぱなしにはしない。"


def build_user_content(req: ReversePlotRequest) -> str:
    chunks = [f"終着条件:\n{req.ending_text.strip()}"]
    if req.protagonist_hint:
        chunks.append(f"主人公ヒント:\n{req.protagonist_hint.strip()}")
    if req.genre_hint:
        chunks.append(f"ジャンルヒント:\n{req.genre_hint.strip()}")
    chunks.append(f"突拍子レベル:\n{req.wild_twist_level}")
    chunks.append(build_wild_twist_guidance(req.wild_twist_level))
    chunks.append("突拍子レベルは、required_turning_points と plot.ten に最も強く反映してください。")
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
