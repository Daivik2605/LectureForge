"""
LLM provider factory and implementations.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_narration(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_narration_sync(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        raise NotImplementedError


def _get_memory_kb() -> int | None:
    try:
        import psutil  # type: ignore

        process = psutil.Process()
        return int(process.memory_info().rss // 1024)
    except Exception:
        pass
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        return int(parts[1])
    except Exception:
        pass
    return None


def _memory_delta_kb(before: int | None, after: int | None) -> int:
    if before is None or after is None:
        return 0
    return max(after - before, 0)


def _fallback_token_count(text: str) -> int:
    return len([t for t in text.split() if t.strip()])


def _coerce_total_tokens(payload: dict[str, Any]) -> int | None:
    usage = payload.get("usage")
    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
        completion = usage.get("completion_tokens")
        prompt = usage.get("prompt_tokens")
        if isinstance(completion, int) and isinstance(prompt, int):
            return completion + prompt
        if isinstance(completion, int):
            return completion
    return None


def _normalize_stream_line(line: str | bytes) -> str:
    if isinstance(line, bytes):
        return line.decode(errors="ignore")
    return line


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def _get_endpoint(self) -> tuple[str, bool]:
        base = self._base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base, True
        if base.endswith("/api/chat"):
            return base, False
        if base.endswith("/v1"):
            return f"{base}/chat/completions", True
        if base.endswith("/api"):
            return f"{base}/chat", False
        if "/v1" in base:
            return f"{base}/chat/completions", True
        return f"{base}/api/chat", False

    def _build_headers(self, is_openai: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if is_openai:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        is_openai: bool,
        stream: bool = True,
    ) -> dict[str, Any]:
        model = settings.ollama_model or "llama3.1:8b-instruct-q4"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if is_openai:
            payload["temperature"] = temperature
            payload["max_tokens"] = max_tokens
            if stream:
                payload["stream_options"] = {"include_usage": True}
        else:
            payload["options"] = {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        return payload

    async def generate_narration(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        endpoint, is_openai = self._get_endpoint()
        headers = self._build_headers(is_openai)
        payload = self._build_payload(messages, temperature, max_tokens, is_openai, stream=True)

        delay = 0.5
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        memory_before = _get_memory_kb()
        ttft: float | None = None
        chunks: list[str] = []
        total_tokens: int | None = None
        prompt_tokens: int | None = None
        completion_tokens: int | None = None

        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                        if response.status_code >= 400:
                            body = await response.aread()
                            logger.error(
                                "LLM response error",
                                extra={
                                    "status": response.status_code,
                                    "body": body.decode(errors="ignore"),
                                },
                            )
                            raise ConnectionError(f"LLM response status {response.status_code}")
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            line = _normalize_stream_line(line)
                            if is_openai:
                                if not line.startswith("data:"):
                                    continue
                                data = line[len("data:") :].strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    event = json.loads(data)
                                except json.JSONDecodeError:
                                    continue
                                if total_tokens is None:
                                    total_tokens = _coerce_total_tokens(event)
                                usage = event.get("usage")
                                if isinstance(usage, dict):
                                    pt = usage.get("prompt_tokens")
                                    ct = usage.get("completion_tokens")
                                    if isinstance(pt, int):
                                        prompt_tokens = pt
                                    if isinstance(ct, int):
                                        completion_tokens = ct
                                choices = event.get("choices", [])
                                if choices and isinstance(choices, list):
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if isinstance(content, str) and content:
                                        if ttft is None:
                                            ttft = perf_counter() - start
                                        chunks.append(content)
                            else:
                                try:
                                    event = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                message = event.get("message", {})
                                content = message.get("content")
                                if isinstance(content, str) and content:
                                    if ttft is None:
                                        ttft = perf_counter() - start
                                    chunks.append(content)
                                if event.get("done") is True:
                                    eval_count = event.get("eval_count")
                                    prompt_eval_count = event.get("prompt_eval_count")
                                    if isinstance(prompt_eval_count, int):
                                        prompt_tokens = prompt_eval_count
                                    if isinstance(eval_count, int):
                                        completion_tokens = eval_count
                                    if total_tokens is None:
                                        if isinstance(eval_count, int) and isinstance(prompt_eval_count, int):
                                            total_tokens = eval_count + prompt_eval_count
                                        elif isinstance(eval_count, int):
                                            total_tokens = eval_count
                break
            except (httpx.RequestError, ConnectionError) as exc:
                if attempt == 3:
                    raise
                logger.warning(
                    "LLM request failed, retrying",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                await asyncio.sleep(delay)
                delay *= 2

        text = "".join(chunks)
        duration = perf_counter() - start
        if ttft is None:
            ttft = duration
        if total_tokens is None:
            total_tokens = _fallback_token_count(text)
        if prompt_tokens is None and completion_tokens is None and total_tokens is not None:
            completion_tokens = total_tokens
        memory_after = _get_memory_kb()
        memory_kb = _memory_delta_kb(memory_before, memory_after)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        metrics = {
            "text": text,
            "ttft": ttft,
            "tps": tps,
            "duration": duration,
            "memory_kb": memory_kb,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }
        logger.info(
            "LLM stream metrics",
            extra={"ttft": ttft, "tps": tps, "duration": duration, "memory_kb": memory_kb},
        )
        return metrics

    def generate_narration_sync(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        endpoint, is_openai = self._get_endpoint()
        headers = self._build_headers(is_openai)
        payload = self._build_payload(messages, temperature, max_tokens, is_openai, stream=True)

        delay = 0.5
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        memory_before = _get_memory_kb()
        ttft: float | None = None
        chunks: list[str] = []
        total_tokens: int | None = None
        prompt_tokens: int | None = None
        completion_tokens: int | None = None

        for attempt in range(1, 4):
            try:
                with httpx.Client(timeout=timeout) as client:
                    with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                        if response.status_code >= 400:
                            body = response.read()
                            logger.error(
                                "LLM response error",
                                extra={
                                    "status": response.status_code,
                                    "body": body.decode(errors="ignore"),
                                },
                            )
                            raise ConnectionError(f"LLM response status {response.status_code}")
                        for line in response.iter_lines():
                            if not line:
                                continue
                            line = _normalize_stream_line(line)
                            if is_openai:
                                if not line.startswith("data:"):
                                    continue
                                data = line[len("data:") :].strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    event = json.loads(data)
                                except json.JSONDecodeError:
                                    continue
                                if total_tokens is None:
                                    total_tokens = _coerce_total_tokens(event)
                                usage = event.get("usage")
                                if isinstance(usage, dict):
                                    pt = usage.get("prompt_tokens")
                                    ct = usage.get("completion_tokens")
                                    if isinstance(pt, int):
                                        prompt_tokens = pt
                                    if isinstance(ct, int):
                                        completion_tokens = ct
                                choices = event.get("choices", [])
                                if choices and isinstance(choices, list):
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if isinstance(content, str) and content:
                                        if ttft is None:
                                            ttft = perf_counter() - start
                                        chunks.append(content)
                            else:
                                try:
                                    event = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                message = event.get("message", {})
                                content = message.get("content")
                                if isinstance(content, str) and content:
                                    if ttft is None:
                                        ttft = perf_counter() - start
                                    chunks.append(content)
                                if event.get("done") is True:
                                    eval_count = event.get("eval_count")
                                    prompt_eval_count = event.get("prompt_eval_count")
                                    if isinstance(prompt_eval_count, int):
                                        prompt_tokens = prompt_eval_count
                                    if isinstance(eval_count, int):
                                        completion_tokens = eval_count
                                    if total_tokens is None:
                                        if isinstance(eval_count, int) and isinstance(prompt_eval_count, int):
                                            total_tokens = eval_count + prompt_eval_count
                                        elif isinstance(eval_count, int):
                                            total_tokens = eval_count
                break
            except (httpx.RequestError, ConnectionError) as exc:
                if attempt == 3:
                    raise
                logger.warning(
                    "LLM request failed, retrying",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(delay)
                delay *= 2

        text = "".join(chunks)
        duration = perf_counter() - start
        if ttft is None:
            ttft = duration
        if total_tokens is None:
            total_tokens = _fallback_token_count(text)
        if prompt_tokens is None and completion_tokens is None and total_tokens is not None:
            completion_tokens = total_tokens
        memory_after = _get_memory_kb()
        memory_kb = _memory_delta_kb(memory_before, memory_after)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        metrics = {
            "text": text,
            "ttft": ttft,
            "tps": tps,
            "duration": duration,
            "memory_kb": memory_kb,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }
        logger.info(
            "LLM stream metrics",
            extra={"ttft": ttft, "tps": tps, "duration": duration, "memory_kb": memory_kb},
        )
        return metrics


class OpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def generate_narration(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ConnectionError("Missing OPENAI_API_KEY")
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ConnectionError(f"OpenAI response status {response.status_code}")
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        duration = perf_counter() - start
        usage = data.get("usage", {})
        prompt_tokens = None
        completion_tokens = None
        if isinstance(usage, dict):
            pt = usage.get("prompt_tokens")
            ct = usage.get("completion_tokens")
            if isinstance(pt, int):
                prompt_tokens = pt
            if isinstance(ct, int):
                completion_tokens = ct
        total_tokens = _coerce_total_tokens(data) or _fallback_token_count(text)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        return {
            "text": text,
            "ttft": duration,
            "tps": tps,
            "duration": duration,
            "memory_kb": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }

    def generate_narration_sync(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ConnectionError("Missing OPENAI_API_KEY")
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ConnectionError(f"OpenAI response status {response.status_code}")
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        duration = perf_counter() - start
        usage = data.get("usage", {})
        prompt_tokens = None
        completion_tokens = None
        if isinstance(usage, dict):
            pt = usage.get("prompt_tokens")
            ct = usage.get("completion_tokens")
            if isinstance(pt, int):
                prompt_tokens = pt
            if isinstance(ct, int):
                completion_tokens = ct
        total_tokens = _coerce_total_tokens(data) or _fallback_token_count(text)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        return {
            "text": text,
            "ttft": duration,
            "tps": tps,
            "duration": duration,
            "memory_kb": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }


class AnthropicProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    def _split_system(self, messages: list[dict[str, str]]) -> tuple[str | None, list[dict[str, str]]]:
        system_prompt = None
        remaining: list[dict[str, str]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system" and system_prompt is None:
                system_prompt = content
            else:
                remaining.append({"role": role, "content": content})
        return system_prompt, remaining

    async def generate_narration(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ConnectionError("Missing ANTHROPIC_API_KEY")
        url = f"{self._base_url.rstrip('/')}/messages"
        system_prompt, remaining = self._split_system(messages)
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.ollama_model,
            "messages": remaining,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ConnectionError(f"Anthropic response status {response.status_code}")
        data = response.json()
        content_items = data.get("content", [])
        text = ""
        if isinstance(content_items, list) and content_items:
            text = "".join([item.get("text", "") for item in content_items if isinstance(item, dict)])
        duration = perf_counter() - start
        usage = data.get("usage", {})
        total_tokens = None
        prompt_tokens = None
        completion_tokens = None
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                total_tokens = input_tokens + output_tokens
                prompt_tokens = input_tokens
                completion_tokens = output_tokens
            elif isinstance(output_tokens, int):
                total_tokens = output_tokens
                completion_tokens = output_tokens
        if total_tokens is None:
            total_tokens = _fallback_token_count(text)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        return {
            "text": text,
            "ttft": duration,
            "tps": tps,
            "duration": duration,
            "memory_kb": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }

    def generate_narration_sync(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ConnectionError("Missing ANTHROPIC_API_KEY")
        url = f"{self._base_url.rstrip('/')}/messages"
        system_prompt, remaining = self._split_system(messages)
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.ollama_model,
            "messages": remaining,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        timeout = httpx.Timeout(settings.llm_timeout)
        start = perf_counter()
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ConnectionError(f"Anthropic response status {response.status_code}")
        data = response.json()
        content_items = data.get("content", [])
        text = ""
        if isinstance(content_items, list) and content_items:
            text = "".join([item.get("text", "") for item in content_items if isinstance(item, dict)])
        duration = perf_counter() - start
        usage = data.get("usage", {})
        total_tokens = None
        prompt_tokens = None
        completion_tokens = None
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                total_tokens = input_tokens + output_tokens
                prompt_tokens = input_tokens
                completion_tokens = output_tokens
            elif isinstance(output_tokens, int):
                total_tokens = output_tokens
                completion_tokens = output_tokens
        if total_tokens is None:
            total_tokens = _fallback_token_count(text)
        tps = (total_tokens / duration) if duration > 0 else 0.0
        return {
            "text": text,
            "ttft": duration,
            "tps": tps,
            "duration": duration,
            "memory_kb": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "token_count": total_tokens,
        }


class LLMProviderFactory:
    @staticmethod
    def get_provider(model_name: str | None) -> BaseLLMProvider:
        name = (model_name or "").lower()
        if "gpt" in name or "openai" in name:
            return OpenAIProvider()
        if "claude" in name or "anthropic" in name:
            return AnthropicProvider()
        return OllamaProvider(settings.ollama_base_url)
