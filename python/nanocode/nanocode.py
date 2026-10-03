# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""nanocode 单脚本客户端：经 nginx-ai-proxy 转发调用 GLM（Anthropic 兼容接口），零依赖，uv run 直接运行。"""
import json
import os
import sys
import urllib.request


def load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\" "))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(here, ".env"))
    api_url = os.environ.get("API_URL", "")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("MODEL", "glm-5.3-flash")
    if not api_url or not api_key:
        print("请先配置 python/nanocode/.env（参考 .env.example）", file=sys.stderr)
        sys.exit(1)
    prompt = " ".join(sys.argv[1:]) or "用一句话介绍你自己。"
    payload = json.dumps({"model": model, "max_tokens": 512, "stream": True,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(api_url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                for chunk in obj.get("content", []):
                    t = chunk.get("text", "")
                    if t:
                        print(t, end="", flush=True)
                delta = obj.get("delta", {})
                if isinstance(delta, dict) and delta.get("text"):
                    print(delta["text"], end="", flush=True)
    except Exception as e:
        print(f"\n请求失败: {e}", file=sys.stderr)
        sys.exit(1)
    print()


if __name__ == "__main__":
    main()
