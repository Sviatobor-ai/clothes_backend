"""Utilities for interacting with Telegram via Telethon."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from getpass import getpass
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from telethon import TelegramClient, errors

from app.config import settings
from app import logging_conf


logger = logging.getLogger(__name__)

_SESSION_NAME = "nano_banana_session"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SESSION_PATH = _PROJECT_ROOT / _SESSION_NAME

_client: TelegramClient | None = None
_client_lock = asyncio.Lock()
_LOGIN_MODE = False

_T = TypeVar("_T")


def sanitize_caption(caption: str, limit: int = 1024) -> str:
    """Return a caption trimmed to the Telegram-safe limit without control characters."""

    cleaned = caption.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    cleaned = "".join(ch for ch in cleaned if ch >= " " or ch in {"\n", "\r", "\t"})
    if len(cleaned) > limit:
        cleaned = cleaned[:limit]
    return cleaned


def ensure_png_bytes(data: bytes) -> bytes:
    """Return image data and warn if the payload does not appear to be a PNG."""

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        context = logging_conf.get_log_context()
        payload = {
            "event": "telegram_non_png_payload",
            "warning": "payload_does_not_look_like_png",
            "request_id": context.get("request_id"),
            "job_id": context.get("job_id"),
        }
        logger.warning(json.dumps(payload, ensure_ascii=False))
    return data


async def _ensure_client() -> TelegramClient:
    """Return a connected and authorized Telegram client instance."""

    global _client

    if _client and _client.is_connected():
        return _client

    async with _client_lock:
        if _client and _client.is_connected():
            return _client

        client = TelegramClient(str(_SESSION_PATH), settings.tg_api_id, settings.tg_api_hash)

        await client.connect()

        if not await client.is_user_authorized():
            if not _LOGIN_MODE:
                await client.disconnect()
                raise RuntimeError(
                    "Telegram session not authorized. Run `python -m app.services.telegram_service --login` first."
                )

            await client.send_code_request(settings.tg_phone)
            code = input("Enter the Telegram code sent to your app: ").strip()
            try:
                await client.sign_in(settings.tg_phone, code)
            except errors.SessionPasswordNeededError:
                password = getpass("Enter your Telegram 2FA password: ")
                await client.sign_in(password=password)

        _client = client
        return client


async def close_client() -> None:
    """Disconnect the client and reset shared state."""

    global _client

    async with _client_lock:
        if _client:
            await _client.disconnect()
        _client = None


def chunk_text(text: str, limit: int = 4096) -> list[str]:
    """Split text into Telegram-safe chunks without breaking words when possible."""

    if limit <= 0:
        raise ValueError("limit must be positive")

    if not text:
        return []

    if len(text) <= limit:
        return [text]

    def _split_recursive(segment: str, separators: list[str]) -> list[str]:
        if not separators:
            return [segment]

        separator = separators[0]
        pieces = segment.split(separator)
        units: list[str] = []
        for index, piece in enumerate(pieces):
            units.extend(_split_recursive(piece, separators[1:]))
            if index < len(pieces) - 1:
                units.append(separator)
        return units

    units = _split_recursive(text, ["\n\n", "\n", " "])
    chunks: list[str] = []
    current = ""

    for unit in units:
        if unit == "":
            continue

        remaining = unit
        while remaining:
            available = limit - len(current)
            if available <= 0:
                if current:
                    chunks.append(current)
                    current = ""
                    available = limit
                else:
                    available = limit

            take = min(len(remaining), available)
            if take <= 0:
                break
            current += remaining[:take]
            remaining = remaining[take:]

            if len(current) >= limit:
                chunks.append(current)
                current = ""

        if not remaining and len(current) == limit:
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)

    # Fallback if the splitting produced nothing due to unexpected input.
    if not chunks:
        for start in range(0, len(text), limit):
            chunks.append(text[start : start + limit])

    return chunks


async def _resolve_target_entity(client: TelegramClient):
    """Return the Telegram entity for the configured target chat."""

    return await client.get_input_entity(settings.tg_target_chat_id)


def _log_success(event: str, **details: object) -> None:
    context = logging_conf.get_log_context()
    payload = {
        "event": event,
        "status": "success",
        "request_id": context.get("request_id"),
        "job_id": context.get("job_id"),
        **{k: v for k, v in details.items() if v is not None},
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


def _log_error(event: str, exc: Exception) -> None:
    context = logging_conf.get_log_context()
    payload = {
        "event": event,
        "status": "error",
        "error": exc.__class__.__name__,
        "error_message": str(exc),
        "request_id": context.get("request_id"),
        "job_id": context.get("job_id"),
    }
    logger.error(json.dumps(payload, ensure_ascii=False))


def _log_warning(event: str, **details: object) -> None:
    context = logging_conf.get_log_context()
    payload = {
        "event": event,
        "level": "warning",
        "request_id": context.get("request_id"),
        "job_id": context.get("job_id"),
        **{k: v for k, v in details.items() if v is not None},
    }
    logger.warning(json.dumps(payload, ensure_ascii=False))


async def _execute_with_retry(
    action: str, func: Callable[[TelegramClient], Awaitable[object]]
) -> object:
    attempts = 0
    while True:
        attempts += 1
        client = await _ensure_client()
        try:
            return await func(client)
        except errors.FloodWaitError as exc:
            if attempts >= 2:
                _log_error(action, exc)
                raise
            wait_seconds = min(getattr(exc, "seconds", 0) or 0, 30) or 1
            _log_warning(
                action,
                warning="flood_wait",
                wait_seconds=wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except errors.ChatWriteForbiddenError as exc:
            _log_error(action, exc)
            raise
        except Exception as exc:  # pragma: no cover - defensive catch for unexpected errors
            _log_error(action, exc)
            raise


async def send_text(message: str) -> None:
    """Send a text message to the configured Telegram chat."""

    async def _send(client: TelegramClient) -> None:
        await client.send_message(settings.tg_target_chat_id, message)

    await _execute_with_retry("telegram_send_text", _send)
    _log_success("telegram_send_text")


async def send_error_message(message: str) -> None:
    """Send a formatted error message including the request identifier when available."""

    context = logging_conf.get_log_context()
    request_id = context.get("request_id")
    prefix = "❌ Error:"
    if request_id:
        prefix = f"{prefix} [request_id={request_id}]"
    formatted = f"{prefix} {message}"

    await send_text(formatted)


async def send_images_with_caption(images: list[bytes], caption: str) -> None:
    """Upload PNG images and send them as an album with a caption."""

    if not images:
        combined_caption = sanitize_caption(caption)
        await send_text(f"{combined_caption}\n(no images)")
        return

    if len(images) > 10:
        raise ValueError("Telegram supports at most 10 media files per album")

    safe_caption = sanitize_caption(caption)

    await send_images_and_prompt(images, prompt_text=safe_caption)
    _log_success("telegram_send_images", image_count=len(images))


async def _run_with_floodwait_retry(
    operation: Callable[[], Awaitable[_T]],
) -> _T:
    attempts = 0
    while True:
        attempts += 1
        try:
            return await operation()
        except errors.FloodWaitError as exc:
            if attempts >= 2:
                raise
            wait_seconds = min(getattr(exc, "seconds", 0) or 0, 30) or 1
            logger.warning("telegram flood wait: sleeping %s seconds", wait_seconds)
            await asyncio.sleep(wait_seconds)


async def send_images_and_prompt(
    images: list[bytes], prompt_text: str, header: str | None = None
) -> None:
    """Send an image album without caption followed by the full prompt in 4096-char chunks."""

    try:
        client = await _ensure_client()
        target = await _resolve_target_entity(client)

        uploaded_files = []
        if images:
            if len(images) > 10:
                raise ValueError("Telegram supports at most 10 media files per album")

            for image in images:
                data = ensure_png_bytes(image)
                uploaded = await _run_with_floodwait_retry(
                    lambda data=data: client.upload_file(data)
                )
                uploaded_files.append(uploaded)

            if uploaded_files:
                await _run_with_floodwait_retry(
                    lambda: client.send_file(entity=target, file=uploaded_files)
                )

        text_parts: list[str] = []
        if header:
            header_line = header.strip()
            if header_line:
                text_parts.append(header_line)
                text_parts.append("")

        text_parts.append("Prompt:")
        text_parts.append(prompt_text)
        full_text = "\n".join(text_parts)
        chunks = chunk_text(full_text, limit=4096)

        for chunk in chunks:
            await _run_with_floodwait_retry(
                lambda chunk=chunk: client.send_message(
                    target, chunk, link_preview=False
                )
            )

        logger.info(
            "telegram: sent album=%d and prompt parts=%d (prompt length=%d)",
            len(images),
            len(chunks),
            len(full_text),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("telegram send failed: %s: %s", exc.__class__.__name__, str(exc))
        raise


async def _cli_login() -> None:
    global _LOGIN_MODE
    _LOGIN_MODE = True
    await _ensure_client()
    print("Telegram session authorized.")


async def _cli_send_text(message: str) -> None:
    await send_text(message)
    print("Message sent.")


async def _cli_logout(remove_file: bool) -> None:
    await close_client()
    if remove_file and _SESSION_PATH.with_suffix(".session").exists():
        _SESSION_PATH.with_suffix(".session").unlink()
        print("Session file removed.")
    else:
        print("Session closed.")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram service CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--login", action="store_true", help="Perform interactive login")
    group.add_argument("--send-text", help="Send a text message to the target chat")
    group.add_argument("--logout", action="store_true", help="Logout and optionally remove session")
    parser.add_argument(
        "--remove-session",
        action="store_true",
        help="Remove the session file during logout",
    )
    return parser


def _main() -> None:
    logging_conf.configure_logging()
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.login:
        asyncio.run(_cli_login())
    elif args.send_text:
        asyncio.run(_cli_send_text(args.send_text))
    elif args.logout:
        confirm = input("Are you sure you want to logout? [y/N]: ").strip().lower()
        if confirm == "y":
            asyncio.run(_cli_logout(args.remove_session))
        else:
            print("Logout aborted.")


if __name__ == "__main__":
    _main()

