# nginx-ai-proxy

腾讯云 Nginx 裸跑 + Go 单二进制 `aiproxy` 管理的 GLM 反向代理（8088 端口，自定义 Key 鉴权，SSE 零缓冲）。

## 服务端（Linux）
```bash
cp .env.example .env   # 填入 PROXY_KEY（aiproxy keygen 生成）与 GLM_KEY
go build -o /usr/local/bin/aiproxy ./cmd/aiproxy
aiproxy init && aiproxy reload
aiproxy status   # 查看 nginx RSS（目标 <10MB）
```

## 客户端（Windows）
```powershell
Copy-Item python\nanocode\.env.example python\nanocode\.env  # 填入代理地址与 PROXY_KEY
uv run python/nanocode/nanocode.py "你好"
```

详见 `TODO_OPENRESTY_LUA.md` 获取 OpenResty 演进方案。
