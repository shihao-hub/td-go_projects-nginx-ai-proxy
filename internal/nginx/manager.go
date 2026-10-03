package nginx

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"text/template"

	"nginx-ai-proxy/internal/config"
)

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

// Control 封装 start/stop/reload
func Control(action string) error {
	if runtime.GOOS == "linux" {
		if action == "start" {
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
	}
	switch action {
	case "stop":
		c := exec.Command("nginx", "-s", "stop")
		c.Stdout, c.Stderr = os.Stdout, os.Stderr
		return c.Run()
	case "reload":
		c := exec.Command("nginx", "-s", "reload")
		c.Stdout, c.Stderr = os.Stdout, os.Stderr
		return c.Run()
	default:
		return fmt.Errorf("未知动作: %s", action)
	}
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
