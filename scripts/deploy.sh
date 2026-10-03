#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
go build -o bin/aiproxy ./cmd/aiproxy
sudo install -m 0755 bin/aiproxy /usr/local/bin/aiproxy
aiproxy init && aiproxy reload && aiproxy status
