"""CLI smoke test for the Gemini image generation pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Sequence

from app import logging_conf
from app.services import assistant_service, gemini_service, telegram_service


LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the image generation smoke test")
    parser.add_argument("--once", action="store_true", help="Run the pipeline a single time (default)")
    parser.add_argument("--n", type=int, default=2, help="Number of images to request")
    parser.add_argument(
        "--aspect",
        choices=("vertical", "square"),
        default="vertical",
        help="Image aspect ratio preset",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="Skip Telegram upload and print diagnostics instead",
    )
    return parser


def _format_caption(prompt: str, count: int, aspect: str) -> str:
    trimmed_prompt = prompt if len(prompt) <= 3000 else f"{prompt[:2997]}..."
    lines = [
        "Nano Banana — smoke",
        f"Model: {gemini_service.MODEL_NAME}",
        f"Count: {count}, Aspect: {aspect}",
        "",
        trimmed_prompt,
    ]
    return "\n".join(lines)


def _print_diagnostics(images: Sequence[bytes]) -> None:
    for idx, image in enumerate(images, start=1):
        print(f"image {idx}: {len(image)} bytes")


def main() -> None:
    logging_conf.configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    try:
        prompt = assistant_service.generate_prompt_text()
        aspect_key = args.aspect.upper()
        images = gemini_service.generate_images(prompt, n=args.n, aspect=aspect_key, fmt="png")

        if args.no_send:
            _print_diagnostics(images)
            LOGGER.info("smoke success", extra={"count": len(images), "sent": False})
            return

        caption = _format_caption(prompt, len(images), aspect_key)
        asyncio.run(telegram_service.send_images_with_caption(list(images), caption))
        LOGGER.info("smoke success", extra={"count": len(images), "sent": True})
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(
            "smoke test failed",
            extra={"err": exc.__class__.__name__, "detail": str(exc)},
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
