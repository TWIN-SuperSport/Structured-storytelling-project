from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
import json
import os
import asyncio

app = FastAPI()
PLOT_STEP_ORDER = ["epilogue", "ketsu", "ten", "sho", "ki", "prologue"]
APP_VERSION = os.getenv("APP_VERSION", "dev")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://swallow-relay.wos.ktsys.jp")
LLM_MODEL = os.getenv("LLM_MODEL", "swallow")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "240"))
LLM_POLL_INTERVAL = float(os.getenv("LLM_POLL_INTERVAL", "2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1800"))
LLM_RETRY_MAX_TOKENS = int(os.getenv("LLM_RETRY_MAX_TOKENS", "2400"))

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

EPILOGUE_CHOICES_SYSTEM_PROMPT = """あなたは、物語の終着条件からエピローグ候補を複数案出すアシスタントです。
ユーザーが与えた終着条件、主人公ヒント、ジャンルヒント、突拍子レベルをもとに、
最終局面の余韻として成立する epilogue 候補だけを複数案作ってください。

重要:
- 出すのは epilogue 候補だけ
- 各候補は 2〜3 文
- 候補同士は意味や後味を少し変える
- JSON 以外は返さない

必ず以下の JSON 形式のみで返してください:
{
  "choices": [
    "候補1",
    "候補2",
    "候補3"
  ]
}"""

STAGED_CHOICES_SYSTEM_PROMPT = """あなたは、物語の終着条件から各 plot 段の候補を複数案出すアシスタントです。
ユーザーは物語を逆順に確定していくため、指定された step だけの候補を返してください。

重要:
- 指定 step 以外の段は本文として返さない
- すでに確定済みの後段がある場合は、それと整合する候補を出す
- 各候補は 2〜3 文
- 候補同士は意味や後味を少し変える
- JSON 以外は返さない

必ず以下の JSON 形式のみで返してください:
{
  "step": "epilogue",
  "choices": [
    "候補1",
    "候補2",
    "候補3"
  ]
}"""

FINALIZE_SYSTEM_PROMPT = """あなたは、ユーザーが段階的に確定した plot をもとに、
物語構造 JSON を完成させるアシスタントです。

重要:
- plot の各段は、入力で与えられた確定済み本文をそのまま採用する
- あなたは title, ending_summary, core_theme, protagonist_final_state,
  structural_conditions, relationship_changes, required_turning_points, failure_conditions
  を補完する
- plot は与えられた本文と矛盾させない
- JSON 以外は返さない

必ず以下の JSON 形式のみで返してください:
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


class EpilogueChoicesRequest(BaseModel):
    ending_text: str
    protagonist_hint: str | None = None
    genre_hint: str | None = None
    wild_twist_level: int = Field(default=0, ge=0, le=10)
    choice_count: int = Field(default=3, ge=2, le=5)


class StagedChoicesRequest(BaseModel):
    ending_text: str
    protagonist_hint: str | None = None
    genre_hint: str | None = None
    wild_twist_level: int = Field(default=0, ge=0, le=10)
    choice_count: int = Field(default=3, ge=2, le=5)
    step: str
    selected_plot: dict[str, str] = Field(default_factory=dict)


class FinalizeRequest(BaseModel):
    ending_text: str
    protagonist_hint: str | None = None
    genre_hint: str | None = None
    wild_twist_level: int = Field(default=0, ge=0, le=10)
    selected_plot: dict[str, str]


async def submit_llm_job(client: httpx.AsyncClient, messages: list[dict], max_tokens: int) -> str:
    res = await client.post(
        f"{LLM_BASE_URL}/v1/jobs/chat/completions",
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
    )
    res.raise_for_status()
    body = res.json()
    job_id = body.get("job_id")
    if not job_id:
        raise ValueError("relay が job_id を返しませんでした")
    return job_id


async def poll_llm_job(client: httpx.AsyncClient, job_id: str) -> dict:
    deadline = asyncio.get_running_loop().time() + LLM_TIMEOUT

    while True:
        if asyncio.get_running_loop().time() >= deadline:
            raise httpx.TimeoutException("LLM job polling timed out")

        status_res = await client.get(f"{LLM_BASE_URL}/v1/jobs/{job_id}")
        status_res.raise_for_status()
        status_body = status_res.json()
        status = status_body.get("status")

        if status == "success":
            result_res = await client.get(f"{LLM_BASE_URL}/v1/jobs/{job_id}/result")
            result_res.raise_for_status()
            result_body = result_res.json()
            return result_body["result_json"]

        if status in {"error", "expired"}:
            error_code = status_body.get("error_code") or status
            error_message = status_body.get("error_message") or f"LLM job failed: {status}"
            raise RuntimeError(f"{error_code}: {error_message}")

        await asyncio.sleep(LLM_POLL_INTERVAL)


def extract_json_text(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    start = stripped.find("{")
    end = stripped.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("LLM が JSON を返しませんでした")
    return stripped[start:end]


def parse_llm_json(result_json: dict) -> dict:
    choice = result_json["choices"][0]
    content = choice["message"]["content"]
    json_text = extract_json_text(content)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        if choice.get("finish_reason") == "length":
            raise ValueError("LLM の出力が長さ上限で途中切れになりました")
        raise ValueError(str(exc))


async def call_llm(messages: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT, verify=False) as client:
        for index, max_tokens in enumerate([LLM_MAX_TOKENS, LLM_RETRY_MAX_TOKENS]):
            job_id = await submit_llm_job(client, messages, max_tokens=max_tokens)
            result_json = await poll_llm_job(client, job_id)
            try:
                return parse_llm_json(result_json)
            except ValueError:
                if index == 0:
                    continue
                raise

    raise ValueError("LLM の JSON 解析に失敗しました")


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


def validate_epilogue_choices(data: dict, expected_count: int) -> list[str]:
    choices = data.get("choices")
    if not isinstance(choices, list):
        raise ValueError("choices が配列ではありません")

    normalized = []
    for item in choices:
        if isinstance(item, str) and item.strip():
            normalized.append(item.strip())

    if len(normalized) < expected_count:
        raise ValueError(f"epilogue 候補が不足: {len(normalized)} / {expected_count}")

    return normalized[:expected_count]


def validate_step_name(step: str) -> str:
    if step not in PLOT_STEP_ORDER:
        raise ValueError(f"不正な step: {step}")
    return step


def normalize_selected_plot(selected_plot: dict[str, str]) -> dict[str, str]:
    normalized = {}
    for key, value in selected_plot.items():
        if key in PLOT_STEP_ORDER and isinstance(value, str) and value.strip():
            normalized[key] = value.strip()
    return normalized


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


def build_epilogue_choices_user_content(req: EpilogueChoicesRequest) -> str:
    chunks = [f"終着条件:\n{req.ending_text.strip()}"]
    if req.protagonist_hint:
        chunks.append(f"主人公ヒント:\n{req.protagonist_hint.strip()}")
    if req.genre_hint:
        chunks.append(f"ジャンルヒント:\n{req.genre_hint.strip()}")
    chunks.append(f"突拍子レベル:\n{req.wild_twist_level}")
    chunks.append(build_wild_twist_guidance(req.wild_twist_level))
    chunks.append(f"必要候補数:\n{req.choice_count}")
    chunks.append("epilogue 候補だけを複数案出してください。")
    return "\n\n".join(chunks)


def build_staged_choices_user_content(req: StagedChoicesRequest) -> str:
    step = validate_step_name(req.step)
    selected_plot = normalize_selected_plot(req.selected_plot)

    chunks = [f"終着条件:\n{req.ending_text.strip()}"]
    if req.protagonist_hint:
        chunks.append(f"主人公ヒント:\n{req.protagonist_hint.strip()}")
    if req.genre_hint:
        chunks.append(f"ジャンルヒント:\n{req.genre_hint.strip()}")
    chunks.append(f"対象 step:\n{step}")
    chunks.append(f"突拍子レベル:\n{req.wild_twist_level}")
    chunks.append(build_wild_twist_guidance(req.wild_twist_level))
    chunks.append(f"必要候補数:\n{req.choice_count}")
    if selected_plot:
        chunks.append("すでに確定済みの plot:\n" + json.dumps(selected_plot, ensure_ascii=False, indent=2))
    chunks.append(f"{step} 候補だけを複数案出してください。")
    return "\n\n".join(chunks)


def build_finalize_user_content(req: FinalizeRequest) -> str:
    selected_plot = normalize_selected_plot(req.selected_plot)
    chunks = [f"終着条件:\n{req.ending_text.strip()}"]
    if req.protagonist_hint:
        chunks.append(f"主人公ヒント:\n{req.protagonist_hint.strip()}")
    if req.genre_hint:
        chunks.append(f"ジャンルヒント:\n{req.genre_hint.strip()}")
    chunks.append(f"突拍子レベル:\n{req.wild_twist_level}")
    chunks.append(build_wild_twist_guidance(req.wild_twist_level))
    chunks.append("確定済み plot:\n" + json.dumps(selected_plot, ensure_ascii=False, indent=2))
    chunks.append("与えられた plot をそのまま使い、残りの構造情報を補完して完成 JSON を返してください。")
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


@app.post("/api/story/reverse-plot/staged/epilogue")
async def reverse_plot_epilogue_choices(req: EpilogueChoicesRequest):
    if not req.ending_text.strip():
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is required"})
    if len(req.ending_text) > 1200:
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is too long"})

    messages = [
        {"role": "system", "content": EPILOGUE_CHOICES_SYSTEM_PROMPT},
        {"role": "user", "content": build_epilogue_choices_user_content(req)},
    ]

    try:
        choices = validate_epilogue_choices(await call_llm(messages), req.choice_count)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"status": "invalid_llm_output", "message": str(e)})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"status": "llm_timeout", "message": "LLM の応答がタイムアウトしました"})
    except Exception as e:
        raise HTTPException(status_code=502, detail={"status": "llm_upstream_error", "message": str(e)})

    return {
        "status": "success",
        "step": "epilogue",
        "choices": [
            {"id": f"epilogue_{index + 1}", "text": text}
            for index, text in enumerate(choices)
        ],
    }


@app.post("/api/story/reverse-plot/staged/choices")
async def reverse_plot_staged_choices(req: StagedChoicesRequest):
    if not req.ending_text.strip():
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is required"})
    if len(req.ending_text) > 1200:
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is too long"})

    try:
        step = validate_step_name(req.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": str(e)})

    messages = [
        {"role": "system", "content": STAGED_CHOICES_SYSTEM_PROMPT},
        {"role": "user", "content": build_staged_choices_user_content(req)},
    ]

    try:
        choices = validate_epilogue_choices(await call_llm(messages), req.choice_count)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"status": "invalid_llm_output", "message": str(e)})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"status": "llm_timeout", "message": "LLM の応答がタイムアウトしました"})
    except Exception as e:
        raise HTTPException(status_code=502, detail={"status": "llm_upstream_error", "message": str(e)})

    return {
        "status": "success",
        "step": step,
        "choices": [
            {"id": f"{step}_{index + 1}", "text": text}
            for index, text in enumerate(choices)
        ],
    }


@app.post("/api/story/reverse-plot/staged/finalize")
async def reverse_plot_staged_finalize(req: FinalizeRequest):
    if not req.ending_text.strip():
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is required"})
    if len(req.ending_text) > 1200:
        raise HTTPException(status_code=400, detail={"status": "invalid_request", "message": "ending_text is too long"})

    selected_plot = normalize_selected_plot(req.selected_plot)
    missing = [step for step in PLOT_STEP_ORDER if step not in selected_plot]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"status": "invalid_request", "message": f"未確定の step があります: {', '.join(missing)}"},
        )

    messages = [
        {"role": "system", "content": FINALIZE_SYSTEM_PROMPT},
        {"role": "user", "content": build_finalize_user_content(req)},
    ]

    try:
        payload = validate_reverse_plot(await call_llm(messages))
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"status": "invalid_llm_output", "message": str(e)})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"status": "llm_timeout", "message": "LLM の応答がタイムアウトしました"})
    except Exception as e:
        raise HTTPException(status_code=502, detail={"status": "llm_upstream_error", "message": str(e)})

    payload["plot"].update(selected_plot)

    return {
        "status": "success",
        "story": payload,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}
