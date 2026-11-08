import os
import requests
from dotenv import load_dotenv


load_dotenv()
key = os.getenv("ZHIPU_API_KEY")

url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
headers = {"Authorization": "Bearer " + key}
payload = {
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "用三句话介绍 SSE"}],
    "max_tokens": 64,
    "stream": True,
}

r = requests.post(url, headers=headers, json=payload, stream=True, timeout=(10, 60))
print("HTTP", r.status_code)
for line in r.iter_lines():
    if line:
        print(line.decode("utf-8"))