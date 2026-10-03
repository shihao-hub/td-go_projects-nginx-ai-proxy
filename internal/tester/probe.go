package tester

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Probe 发送 401 探针与鉴权探针
func Probe(baseURL, proxyKey string) error {
	client := &http.Client{Timeout: 30 * time.Second}
	body := []byte(`{"model":"glm-5.3-flash","max_tokens":8,"messages":[{"role":"user","content":"hi"}]}`)

	check := func(key string, want int) error {
		req, _ := http.NewRequest("POST", baseURL, bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
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
