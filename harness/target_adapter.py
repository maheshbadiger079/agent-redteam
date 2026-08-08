"""
Target Adapter
--------------
Generalizes the harness so it can attack ANY agent, not just your own demo.

Supports two target types out of the box, both free to use:
  1. "openai_compatible" — works for OpenAI, Groq, Together, and local Ollama
     (Ollama exposes an OpenAI-compatible /v1/chat/completions endpoint).
  2. "http_custom" — a plain HTTP POST endpoint (for people wrapping their own
     agent without an OpenAI-style API). You send {"input": "..."} and expect
     {"output": "..."} back, or configure the field names via CLI flags.

Nothing here is tied to one provider — the endpoint, model, and API key are
all supplied at run time via CLI flags or environment variables.
"""

import os
import requests


class TargetAgent:
    def __init__(self, base_url: str, api_key_env: str = None, model: str = None,
                 target_type: str = "openai_compatible",
                 request_field: str = "input", response_field: str = "output",
                 api_key_header: str = "Authorization",
                 timeout: int = 30, **kwargs):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env) if api_key_env else None
        self.model = model
        self.target_type = target_type
        self.request_field = request_field
        self.response_field = response_field
        self.api_key_header = api_key_header or "Authorization"
        self.timeout = timeout


    def _get_auth_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if not self.api_key:
            return headers

        header_name_lower = self.api_key_header.lower()
        if header_name_lower in ("authorization", "bearer"):
            if self.api_key.startswith("Bearer "):
                headers["Authorization"] = self.api_key
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        elif header_name_lower in ("x-api-key", "api-key", "apikey"):
            headers["X-API-Key"] = self.api_key
        else:
            headers[self.api_key_header] = self.api_key
        return headers

    def send(self, prompt: str) -> str:
        if self.target_type == "openai_compatible":
            return self._send_openai_compatible(prompt)
        elif self.target_type == "http_custom":
            return self._send_http_custom(prompt)
        else:
            raise ValueError(f"Unknown target_type: {self.target_type}")

    def _send_openai_compatible(self, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions" if not self.base_url.endswith("/chat/completions") else self.base_url
        headers = self._get_auth_headers()

        payload = {
            "model": self.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ADAPTER ERROR] {e}"

    def _send_http_custom(self, prompt: str) -> str:
        headers = self._get_auth_headers()
        try:
            resp = requests.post(
                self.base_url,
                json={self.request_field: prompt},
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                val = data.get(self.response_field)
                if val is not None:
                    return str(val)
            return str(data)
        except Exception as e:
            return f"[ADAPTER ERROR] {e}"

