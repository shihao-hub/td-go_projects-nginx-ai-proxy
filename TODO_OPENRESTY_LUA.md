# TODO: 升级至 OpenResty + Lua 演进方案

## 1. 升级背景与动机
当需要以下能力时考虑升级：多 Key 配额校验、Token 用量统计、Prompt 内容审查、多上游容灾轮询、动态限流。

## 2. 安装 OpenResty（Ubuntu/Debian）
```bash
apt install -y openresty
openresty -v
```

## 3. Lua 模块规划
- `access_by_lua_block`：连接本地 Redis，做 `PROXY_KEY` 配额与黑白名单校验，不合法直接 `ngx.exit(401)`。
- `body_filter_by_lua_block`：解析 SSE chunk，捕获 `usage.total_tokens` 并异步上报 Redis/日志。
- `header_filter_by_lua_block`：统一注入 `Authorization: Bearer <GLM_KEY>`，并剥离客户端原始鉴权头。
- 日志：`log_by_lua_block` 记录状态码、耗时、token 数。

## 4. 平滑迁移步骤
1. 保留现有 `configs/nginx.conf.tmpl` 变量（Port/ProxyKey/GlmKey/Upstream）。
2. Go CLI 模板增加 Lua 代码块渲染开关（`--openresty`）。
3. `aiproxy init` 输出 openresty 配置并 `openresty -t` 校验。
4. `openresty -s reload` 热重载，观察 401 与 200 探针。
5. 确认 SSE 仍为 `proxy_buffering off` 逐字直出。
