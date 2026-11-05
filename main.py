from fastapi import FastAPI
import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("ZHIPU_API_KEY")
app = FastAPI()

@app.get("/Hello")
def say_hello():
    return {"message": "Hello, World!"}

@app.post("/chat")
def chat(payload: dict):
    你说 = payload["question"]

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": "Bearer " + key}
    menu = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": 你说}],
        "max_tokens": 512,
    }
    response = requests.post(url, headers=headers, json=menu, timeout=60)
    data = response.json()
    return {"answer": data["choices"][0]["message"]["content"]}