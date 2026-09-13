import random
import time

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

SYSTEM = (
    "You turn a union leader's hurried note into a clear announcement for members. "
    "Keep every concrete detail: dates, times, places, and what members are being "
    "asked to do. Never invent facts that are not in the note. "
    "title is one short line. body is two or three plain sentences. "
    "push_preview is a single line of at most 120 characters."
)


class Draft(BaseModel):
    title: str
    body: str
    push_preview: str


def generate_draft(raw_text):
    if not settings.GEMINI_API_KEY:
        return _fallback(raw_text)

    for attempt in range(settings.AI_MAX_RETRIES + 1):
        try:
            return _from_model(raw_text)
        except Exception as exc:
            if attempt == settings.AI_MAX_RETRIES or not _retryable(exc):
                break
            time.sleep(0.25 + random.random() * 0.25)

    return _fallback(raw_text)


def _retryable(exc):
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, errors.ServerError):
        return True
    return isinstance(exc, errors.ClientError) and exc.code == 429


def _from_model(raw_text):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.AI_MODEL,
        contents=raw_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=Draft,
            max_output_tokens=1024,
            http_options=types.HttpOptions(timeout=settings.AI_TIMEOUT_SECONDS * 1000),
        ),
    )
    draft = response.parsed
    if not (draft and draft.title.strip() and draft.body.strip()):
        raise ValueError("model returned no usable draft")
    return _shape(draft.title, draft.body, draft.push_preview, "llm")


def _fallback(raw_text):
    text = " ".join(raw_text.split())
    first = text.split(".")[0].strip() or text
    title = first[:80].capitalize() or "Announcement"
    return _shape(title, text, text, "fallback")


def _shape(title, body, push_preview, source):
    return {
        "title": title.strip()[:255],
        "body": body.strip(),
        "push_preview": push_preview.strip()[: settings.PUSH_PREVIEW_MAX_CHARS],
        "source": source,
    }
