package nginx

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"text/template"

	"nginx-ai-proxy/internal/config"
)

// nginxPID 为 nginx master 的 pid 文件路径（Ubuntu 默认）
const nginxPID = "/run/nginx.pid"

// Render 按模板渲染配置（先渲染到内存，成功后再写盘，避免出错时截断线上配置）
func Render(tmplPath string, c config.Config, outPath string) error {
	t, err := template.ParseFiles(tmplPath)
	if err != nil {
		return err
	}
	var buf bytes.Buffer
	if err := t.Execute(&buf, c); err != nil {
		return err
	}
	return os.WriteFile(outPath, buf.Bytes(), 0o644)
}

// Test 执行 nginx -t
func Test() error {
	cmd := exec.Command("nginx", "-t")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// Control 封装 start/stop/reload（start 幂等；reload 在未运行时自动启动）
func Control(action string) error {
	switch action {
	case "start":
		if runtime.GOOS != "linux" {
			return fmt.Errorf("未知动作: %s", action)
		}
		return ensureRunning()
	case "stop":
		c := exec.Command("nginx", "-s", "stop")
		c.Stdout, c.Stderr = os.Stdout, os.Stderr
		return c.Run()
	case "reload":
		if runtime.GOOS == "linux" && !running() {
			return ensureRunning()
		}
		c := exec.Command("nginx", "-s", "reload")
		c.Stdout, c.Stderr = os.Stdout, os.Stderr
		return c.Run()
	default:
		return fmt.Errorf("未知动作: %s", action)
	}
}

// ensureRunning 幂等启动 nginx：已在运行则直接返回，否则先试 systemd 再裸启动
func ensureRunning() error {
	if running() {
		return nil
	}
	for _, args := range [][]string{{"systemctl", "start", "nginx"}, {"nginx"}} {
		cmd := exec.Command(args[0], args[1:]...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err == nil {
			return nil
		}
	}
	return fmt.Errorf("nginx 启动失败")
}

// running 判断 nginx master 是否存活（pid 文件 + /proc 进程存在性）
func running() bool {
	if runtime.GOOS != "linux" {
		return false
	}
	b, err := os.ReadFile(nginxPID)
	if err != nil {
		return false
	}
	pid := strings.TrimSpace(string(b))
	if pid == "" {
		return false
	}
	_, err = os.Stat("/proc/" + pid)
	return err == nil
}

// StatusRSS 读取 nginx 进程 RSS（Linux 走 /proc，Windows 提示手动查看）
func StatusRSS() (string, error) {
	if runtime.GOOS != "linux" {
		return "当前为 Windows，仅做配置渲染验证；RSS 请在 Linux 服务器上执行 aiproxy status 查看", nil
	}
	out, err := exec.Command("sh", "-c", "ps -o pid,rss,comm -C nginx | awk 'NR>1{sum+=$2; n++} END{print n\":\"sum}'").Output()
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("nginx 进程与总 RSS(KB): %s", string(out)), nil
}
