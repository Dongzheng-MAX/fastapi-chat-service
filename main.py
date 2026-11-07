import os
import json
import traceback

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

load_dotenv()
key = os.getenv("ZHIPU_API_KEY")
app = FastAPI()



URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


# ---------- 参数校验 ----------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


# ---------- 统一错误 ----------
def error(status_code: int, code: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "code": code, "message": message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error(422, "INVALID_REQUEST", "请求参数不合法：question 必须是 1~500 字的文本")


# ---------- 接口 ----------
@app.get("/Hello")
def say_hello():
    return {"message": "Hello, World!"}


@app.post("/chat")
def chat(payload: ChatRequest):
    question = payload.question

    if not key:
        return error(500, "CONFIG_MISSING", "未配置 ZHIPU_API_KEY")

    headers = {"Authorization": "Bearer " + key}
    menu = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 512,
    }

    try:
        response = requests.post(URL, headers=headers, json=menu, timeout=(10, 60))
    except requests.exceptions.Timeout:
        return error(504, "UPSTREAM_TIMEOUT", "模型服务超时，请稍后再试")
    except requests.exceptions.ConnectionError:
        return error(502, "UPSTREAM_UNREACHABLE", "连不上模型服务，请检查网络")
    except Exception:
        traceback.print_exc()
        return error(500, "INTERNAL_ERROR", "服务器内部错误")

    if response.status_code == 401:
        return error(502, "UPSTREAM_AUTH", "模型服务鉴权失败，请检查 Key")
    if response.status_code == 429:
        return error(503, "UPSTREAM_RATE_LIMIT", "模型服务限流，请稍后再试")
    if response.status_code != 200:
        return error(502, "UPSTREAM_ERROR", "模型服务返回错误")

    try:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
    except Exception:
        traceback.print_exc()
        return error(502, "UPSTREAM_ERROR", "模型返回格式异常")

    return {"ok": True, "answer": answer}


@app.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    question = payload.question

    if not key:
        return error(500, "CONFIG_MISSING", "未配置 ZHIPU_API_KEY")

    def event_generator():
        headers = {"Authorization": "Bearer " + key}
        menu = {
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 512,
            "stream": True,
        }

        try:
            with requests.post(
                URL,
                headers=headers,
                json=menu,
                stream=True,
                timeout=(10, 60),
            ) as response:
                if response.status_code == 401:
                    yield 'event: error\ndata: {"ok": false, "code": "UPSTREAM_AUTH", "message": "模型服务鉴权失败"}\n\n'
                    return
                if response.status_code == 429:
                    yield 'event: error\ndata: {"ok": false, "code": "UPSTREAM_RATE_LIMIT", "message": "模型服务限流"}\n\n'
                    return
                if response.status_code != 200:
                    yield 'event: error\ndata: {"ok": false, "code": "UPSTREAM_ERROR", "message": "上游返回错误"}\n\n'
                    return

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return

                    try:
                        obj = json.loads(raw)
                        delta = obj.get("choices", [{}])[0].get("delta", {}).get("content")
                    except Exception:
                        continue

                    if delta:
                        yield 'data: ' + json.dumps({"text": delta}, ensure_ascii=False) + "\n\n"

                yield "data: [DONE]\n\n"

        except requests.exceptions.Timeout:
            yield 'event: error\ndata: {"ok": false, "code": "UPSTREAM_TIMEOUT", "message": "模型服务超时"}\n\n'
        except requests.exceptions.ConnectionError:
            yield 'event: error\ndata: {"ok": false, "code": "UPSTREAM_UNREACHABLE", "message": "连不上模型服务"}\n\n'
        except Exception:
            traceback.print_exc()
            yield 'event: error\ndata: {"ok": false, "code": "INTERNAL_ERROR", "message": "服务器内部错误"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")