package tester

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Probe 发送 401 探针与鉴权探针
func Probe(baseURL, proxyKey, model string) error {
	client := &http.Client{Timeout: 60 * time.Second}
	body := []byte(fmt.Sprintf(`{"model":%q,"max_tokens":8,"messages":[{"role":"user","content":"hi"}]}`, model))
	session := newSessionID()

	check := func(key string, want int) error {
		req, _ := http.NewRequest("POST", baseURL, bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("anthropic-version", "2023-06-01")
		req.Header.Set("User-Agent", "nginx-ai-proxy/1.0")
		req.Header.Set("x-opencode-session", session)
		if key != "" {
			req.Header.Set("Authorization", "Bearer "+key)
		}
		resp, err := client.Do(req)
		if err != nil {
			return err
		}
		defer resp.Body.Close()
		io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<20))
		if resp.StatusCode != want {
			return fmt.Errorf("期望 %d，实际 %d", want, resp.StatusCode)
		}
		return nil
	}
	if err := check("bad-key", 401); err != nil {
		return fmt.Errorf("401 拦截探针失败: %w", err)
	}
	fmt.Println("401 拦截正常")
	if err := check(proxyKey, 200); err != nil {
		return fmt.Errorf("转发探针失败: %w", err)
	}
	fmt.Println("鉴权转发正常")
	return nil
}

func newSessionID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("aiproxy-%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}
