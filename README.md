# nginx-ai-proxy

腾讯云 Nginx 裸跑 + Go 单二进制 `aiproxy` 管理的 GLM 反向代理（8088 端口，自定义 Key 鉴权，SSE 零缓冲）。

## 部署（本机一键）
```powershell
uv run scripts/deploy.py --host tencent --dst ~/nginx-ai-proxy
```
脚本自动完成：交叉编译 → scp 上传 → 服务器安装并执行 `init/reload/status`，可重复执行；nginx 未运行时 `reload` 会自动启动。首次部署前，先在服务器完成下节的 `.env` 初始化。

> **注意**：`nginx -s reload` 只能作用于**已运行**的 nginx；未运行时（如服务器重启后 `/run/nginx.pid` 为空）会报 `invalid PID number "" in "/run/nginx.pid"`。`aiproxy reload` 已内置状态感知：未运行自动启动、运行中热加载，无需手动 `systemctl start`。

## 服务器 .env 初始化（仅首次）
`ssh tencent` 登录后：
```bash
cd ~/nginx-ai-proxy
cp .env.example .env
aiproxy keygen        # 生成 PROXY_KEY（服务器还没装 aiproxy 时，可本地执行 go run ./cmd/aiproxy keygen）
nano .env             # 填入 PROXY_KEY 与 GLM_KEY，其余保持默认
```
注意：`aiproxy` 查找 `.env` 的顺序为 exe 同目录 → 当前目录，请在 `~/nginx-ai-proxy` 目录下执行 aiproxy 命令。

## 应急手动部署（已登录服务器时，一般不用）
```bash
cd ~/nginx-ai-proxy
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
