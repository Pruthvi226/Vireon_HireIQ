import json
import os
import random
import re
import time
from hashlib import sha256
from typing import Any, Dict

import google.generativeai as genai

_DEFAULT_MODEL = "gemini-1.5-flash"
_CACHE_TTL_SECONDS = 300
_CACHE_MAX_SIZE = 512

_cache: dict[str, tuple[float, str]] = {}


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", _DEFAULT_MODEL)


def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return key


def _get_model() -> genai.GenerativeModel:
    genai.configure(api_key=_api_key())
    return genai.GenerativeModel(model_name=model_name())


def _cache_key(system_prompt: str, user_prompt: str, temperature: float, max_output_tokens: int) -> str:
    payload = f"{model_name()}|{temperature}|{max_output_tokens}|{system_prompt}|{user_prompt}"
    return sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> str | None:
    hit = _cache.get(key)
    if not hit:
        return None
    expires_at, value = hit
    if time.time() > expires_at:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: str) -> None:
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_cache.keys()))
        _cache.pop(oldest_key, None)
    _cache[key] = (time.time() + _CACHE_TTL_SECONDS, value)


def generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    max_output_tokens: int = 400,
    retries: int = 4,
) -> str:
    model = _get_model()
    key = _cache_key(system_prompt, user_prompt, temperature, max_output_tokens)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    prompt = f"{system_prompt}\n\n{user_prompt}"
    delay = 0.8
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "response_mime_type": "application/json" if "json" in system_prompt.lower() else "text/plain",
                },
            )
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned empty response")
            _cache_set(key, text)
            return text
        except Exception as exc:  # rate limits/network/transient
            last_error = exc
            if attempt == retries - 1:
                break
            jitter = random.uniform(0.0, 0.25)
            time.sleep(delay + jitter)
            delay *= 2

    raise RuntimeError(f"Gemini request failed after retries: {last_error}")


def parse_json_strict(raw_text: str) -> Dict[str, Any]:
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw_text, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Failed to parse JSON response")
