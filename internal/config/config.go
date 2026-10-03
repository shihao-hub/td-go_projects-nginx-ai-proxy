package config

import (
	"bufio"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"strings"
)

type Config struct {
	Port     string
	ProxyKey string
	GlmKey   string
	Upstream string
	ConfDst  string
}

func defaults() Config {
	return Config{Port: "8088", Upstream: "https://open.bigmodel.cn/api/anthropic/", ConfDst: "/etc/nginx/conf.d/aiproxy.conf"}
}

// Load 读取 .env 文件（KEY=VALUE，每行一个，支持 # 注释）
func Load(path string) (Config, error) {
	c := defaults()
	f, err := os.Open(path)
	if err != nil {
		return c, err
	}
	defer f.Close()
	m := map[string]string{}
	s := bufio.NewScanner(f)
	for s.Scan() {
		line := strings.TrimSpace(s.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		k, v, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		m[strings.TrimSpace(k)] = strings.TrimSpace(strings.Trim(v, `"' `))
	}
	if v, ok := m["PROXY_PORT"]; ok && v != "" {
		c.Port = v
	}
	if v, ok := m["PROXY_KEY"]; ok {
		c.ProxyKey = v
	}
	if v, ok := m["GLM_KEY"]; ok {
		c.GlmKey = v
	}
	if v, ok := m["GLM_UPSTREAM"]; ok && v != "" {
		c.Upstream = v
	}
	if v, ok := m["NGINX_CONF_DST"]; ok && v != "" {
		c.ConfDst = v
	}
	if err := s.Err(); err != nil {
		return c, err
	}
	return c, nil
}

func (c Config) Validate() error {
	if c.ProxyKey == "" || c.ProxyKey == "sk-proxy-CHANGE_ME" {
		return fmt.Errorf("PROXY_KEY 未配置，请先执行 aiproxy keygen --write")
	}
	if c.GlmKey == "" || c.GlmKey == "CHANGE_ME_GLM_KEY" {
		return fmt.Errorf("GLM_KEY 未配置")
	}
	return nil
}

// GenerateKey 生成 sk-proxy-<32hex>
func GenerateKey() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return "sk-proxy-" + hex.EncodeToString(b), nil
}
