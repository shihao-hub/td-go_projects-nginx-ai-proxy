# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""一键发布脚本：交叉编译 Linux 二进制并推送至腾讯云服务器。

用法（Windows 本地）：
    uv run scripts/deploy.py --host tencent --dst ~/nginx-ai-proxy
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser(description="交叉编译 aiproxy 并发布到服务器")
    ap.add_argument("--host", default="tencent", help="ssh 目标（如 tencent）")
    ap.add_argument("--dst", default="~/nginx-ai-proxy", help="服务器端目录")
    args = ap.parse_args()

    env = dict(os.environ, GOOS="linux", GOARCH="amd64")
    run(["go", "build", "-o", "bin/aiproxy-linux-amd64", "./cmd/aiproxy"],
        cwd=ROOT, env=env)
    run(["scp", "-r", "bin/aiproxy-linux-amd64", "configs", ".env.example",
         f"{args.host}:{args.dst}/"], cwd=ROOT)
    run(["ssh", args.host,
         f"cd {args.dst} && sudo install -m 0755 aiproxy-linux-amd64"
         " /usr/local/bin/aiproxy && aiproxy init && aiproxy reload"
         " && aiproxy status"])
    print("发布完成")


if __name__ == "__main__":
    sys.exit(main())
