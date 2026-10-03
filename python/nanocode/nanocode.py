#!/usr/bin/env python3
"""nanocode - minimal claude code alternative
nanocode - 极简的 Claude Code 替代方案"""

import glob as globlib, json, os, re, subprocess, urllib.request


def load_env(env_path=None):
    """Load environment variables from a .env file (zero-dependency with dotenv fallback).
    从 .env 文件加载环境变量（优先使用 python-dotenv，无第三方库时使用内置轻量解析器）。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path)
        return
    except ImportError:
        pass

    candidates = [env_path] if env_path else [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key, val = key.strip(), val.strip()
                            if (val.startswith('"') and val.endswith('"')) or (
                                val.startswith("'") and val.endswith("'")
                            ):
                                val = val[1:-1]
                            elif " #" in val:
                                val = val.split(" #", 1)[0].strip()
                            os.environ.setdefault(key, val)
                break
            except Exception:
                pass


load_env()

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = os.environ.get("API_URL") or (
    "https://openrouter.ai/api/v1/messages"
    if OPENROUTER_KEY
    else "https://api.anthropic.com/v1/messages"
)
if API_URL and not API_URL.endswith(("/v1/messages", "/messages")):
    API_URL = API_URL.rstrip("/") + "/v1/messages"

MODEL = os.environ.get("MODEL", "anthropic/claude-opus-4.5" if OPENROUTER_KEY else "claude-opus-4-5")

# ANSI colors | ANSI 颜色代码
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)


# --- Tool implementations | 工具实现 ---


def read(args):
    """Read file with line numbers, supporting offset and limit.
    读取文件内容并附带行号，支持起始偏移量（offset）和行数限制（limit）。"""
    lines = open(args["path"]).readlines()
    offset = args.get("offset", 0)
    limit = args.get("limit", len(lines))
    selected = lines[offset : offset + limit]
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


def write(args):
    """Write content to the specified file path.
    将内容写入指定的文件路径。"""
    with open(args["path"], "w") as f:
        f.write(args["content"])
    return "ok"


def edit(args):
    """Replace old string with new string in file (must be unique unless all=true).
    替换文件中的字符串（除非指定 all=true，否则被替换内容必须唯一）。"""
    text = open(args["path"]).read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = (
        text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    )
    with open(args["path"], "w") as f:
        f.write(replacement)
    return "ok"


def glob(args):
    """Find files matching glob pattern, sorted by modification time (newest first).
    按通配符模式查找文件，并按修改时间倒序排列（最新修改的在前）。"""
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def grep(args):
    """Search files for regex pattern and return up to 50 matching lines.
    使用正则表达式搜索文件内容，最多返回前 50 条匹配行。"""
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath), 1):
                if pattern.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def bash(args):
    """Execute shell command, stream output in real time, with a 30s timeout.
    执行 Shell 命令并实时流式打印输出，超时时间为 30 秒。"""
    proc = subprocess.Popen(
        args["cmd"], shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")
    return "".join(output_lines).strip() or "(empty)"


# --- Tool definitions: (description, schema, function) | 工具定义：(描述, 参数结构, 实现函数) ---

TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
}


def run_tool(name, args):
    """Dispatch and execute the specified tool by name, catching any exceptions.
    根据名称分发并执行对应的工具函数，捕获并返回异常信息。"""
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_schema():
    """Convert TOOLS definitions into Anthropic API JSON Schema format.
    将 TOOLS 工具定义转换为符合 Anthropic API 规范的 JSON Schema 格式。"""
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
        result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return result


def call_api(messages, system_prompt):
    """Send conversation messages and tool schemas to the LLM API and return the JSON response.
    向大模型 API 发送对话历史与工具定义，并返回解析后的 JSON 响应。"""
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": messages,
                "tools": make_schema(),
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            **({"Authorization": f"Bearer {OPENROUTER_KEY}"} if OPENROUTER_KEY else {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", "")}),
        },
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read())


def separator():
    """Generate a horizontal divider line adapted to the terminal width (max 80 chars).
    生成自适应终端宽度的水平分隔线（最大宽度 80 字符）。"""
    try:
        cols = os.get_terminal_size().columns
        # sh-ai-todo: 除了 print 整体使用 structlog 但是只写入文件，便于日志打点 debug
    except OSError:
        cols = 80
    return f"{DIM}{'─' * min(cols, 80)}{RESET}"


def render_markdown(text):
    """Render basic Markdown bold syntax (**text**) into ANSI bold sequences.
    将基础的 Markdown 粗体语法（**文本**）渲染为终端 ANSI 加粗序列。"""
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def main():
    """Run the interactive CLI REPL and the agentic tool-calling loop.
    运行交互式命令行循环（REPL）及智能体工具调用循环。"""
    print(f"{BOLD}nanocode{RESET} | {DIM}{MODEL} ({'OpenRouter' if OPENROUTER_KEY else 'Anthropic'}){RESET} | {DIM}{os.getcwd()}{RESET}\n")
    messages = []
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}❯{RESET} ").strip() # user_input strip()
            print(separator())
            if not user_input:
                continue
            if user_input in ("/q", "exit"):
                break
            if user_input == "/c":
                messages = []
                print(f"{GREEN}⏺ Cleared conversation{RESET}")
                continue

            # sh-ai-todo: 随着会话越来越长，messages 常驻内存应该是不允许的。
            # 是否可以不改变结构的情况下，将 messages 变成鸭子类？实现隐式磁盘与内存的交换？
            # 或者说其实没必要？只需要处理 base64 元数据即可？
            messages.append({"role": "user", "content": user_input})

            # agentic loop: keep calling API until no more tool calls | 智能体循环：持续调用 API 直到不再有工具调用
            while True:
                response = call_api(messages, system_prompt)
                if "error" in response or response.get("success") is False:
                    err_detail = response.get("error") or response.get("msg") or response
                    print(f"\n{RED}⏺ API Error: {err_detail}{RESET}")
                    break
                    
                content_blocks = response.get("content", [])
                tool_results = []

                for block in content_blocks:
                    # sh-ai-answer-me: 这个 block type 有哪些类型？下面的 tool_use 是 ai 返回的是吗？
                    if block["type"] == "text":
                        print(f"\n{CYAN}⏺{RESET} {render_markdown(block['text'])}")

                    if block["type"] == "tool_use":
                        tool_name = block["name"]
                        tool_args = block["input"]
                        arg_preview = str(list(tool_args.values())[0])[:50]
                        print(
                            f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})"
                        )

                        result = run_tool(tool_name, tool_args)
                        result_lines = result.split("\n")
                        preview = result_lines[0][:60]
                        if len(result_lines) > 1:
                            preview += f" ... +{len(result_lines) - 1} lines"
                        elif len(result_lines[0]) > 60:
                            preview += "..."
                        print(f"  {DIM}│  {preview}{RESET}")

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block["id"],
                                "content": result,
                            }
                        )

                messages.append({"role": "assistant", "content": content_blocks})

                if not tool_results:
                    break
                messages.append({"role": "user", "content": tool_results})

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()
