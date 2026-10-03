#Requires -Version 5.1
param([string]$Host = "tencent", [string]$Dst = "~/nginx-ai-proxy")
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location "$root/go_projects/nginx-ai-proxy"
$env:GOOS = "linux"; $env:GOARCH = "amd64"
go build -o bin/aiproxy-linux-amd64 ./cmd/aiproxy
scp -r bin/aiproxy-linux-amd64 configs .env.example "${Host}:${Dst}/"
ssh $Host "cd $Dst && sudo install -m 0755 aiproxy-linux-amd64 /usr/local/bin/aiproxy && aiproxy init && aiproxy reload && aiproxy status"
