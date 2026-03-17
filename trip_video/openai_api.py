from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class OpenAIClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _request_json(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI API network error: {exc}") from exc

    def _request_binary(self, method: str, path: str, payload: dict[str, Any]) -> bytes:
        if not self.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI API network error: {exc}") from exc

    def responses_create(self, model: str, input_items: list[dict[str, Any]], instructions: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "input": input_items,
        }
        if instructions:
            payload["instructions"] = instructions
        return self._request_json("POST", "/responses", payload)

    def speech(self, text: str, voice: str, model: str, instructions: str = "", response_format: str = "mp3") -> bytes:
        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "instructions": instructions,
            "response_format": response_format,
        }
        return self._request_binary("POST", "/audio/speech", payload)


def file_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def responses_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                elif isinstance(text, dict) and isinstance(text.get("value"), str):
                    chunks.append(text["value"])
    return "\n".join(chunks).strip()
