import json
import requests

url = "http://127.0.0.1:8000/chat/stream"
payload = {"question": "用三句话介绍 SSE，每句话短一点"}

r = requests.post(url, json=payload, stream=True, timeout=(10, 120))
print("HTTP", r.status_code)

for line in r.iter_lines(decode_unicode=True):
    if not line:
        continue
    print(line, flush=True)

    if line.startswith("data:"):
        raw = line[5:].strip()
        if raw and raw != "[DONE]":
            try:
                obj = json.loads(raw)
                if "text" in obj:
                    print(obj["text"], end="", flush=True)
            except Exception:
                pass
print()