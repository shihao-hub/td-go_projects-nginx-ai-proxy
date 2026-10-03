package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"nginx-ai-proxy/internal/config"
	"nginx-ai-proxy/internal/nginx"
	"nginx-ai-proxy/internal/tester"
)

func envPath() string {
	if v := os.Getenv("AIPROXY_ENV"); v != "" {
		return v
	}
	exe, err := os.Executable()
	if err == nil {
		p := filepath.Join(filepath.Dir(exe), ".env")
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ".env"
}

func tmplPath() string {
	if v := os.Getenv("AIPROXY_TMPL"); v != "" {
		return v
	}
	return "configs/nginx.conf.tmpl"
}

func usage() {
	fmt.Println("用法: aiproxy <keygen|init|start|stop|reload|status|test>")
}

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}
	switch os.Args[1] {
	case "keygen":
		fs := flag.NewFlagSet("keygen", flag.ExitOnError)
		write := fs.Bool("write", false, "写回 .env 的 PROXY_KEY")
		_ = fs.Parse(os.Args[2:])
		k, err := config.GenerateKey()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println(k)
		if *write {
			fmt.Println("已生成 Key，请手动写入 .env 的 PROXY_KEY")
		}
	case "init":
		c, err := config.Load(envPath())
		if err != nil {
			fmt.Fprintln(os.Stderr, "读取 .env 失败: ", err)
			os.Exit(1)
		}
		if err := c.Validate(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		out := c.ConfDst
		if os.Getenv("AIPROXY_OUT") != "" {
			out = os.Getenv("AIPROXY_OUT")
		}
		if err := nginx.Render(tmplPath(), c, out); err != nil {
			fmt.Fprintln(os.Stderr, "渲染失败: ", err)
			os.Exit(1)
		}
		fmt.Println("已渲染: ", out)
		if err := nginx.Test(); err != nil {
			fmt.Fprintln(os.Stderr, "nginx -t 失败（Windows 无 nginx 属正常）: ", err)
		}
	case "start", "stop", "reload":
		if err := nginx.Control(os.Args[1]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println(os.Args[1], "ok")
	case "status":
		s, err := nginx.StatusRSS()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println(s)
	case "test":
		c, err := config.Load(envPath())
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		base := "http://127.0.0.1:" + c.Port + "/api/anthropic/v1/messages"
		if v := os.Getenv("AIPROXY_URL"); v != "" {
			base = v
		}
		if err := tester.Probe(base, c.ProxyKey); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	default:
		usage()
		os.Exit(1)
	}
}
