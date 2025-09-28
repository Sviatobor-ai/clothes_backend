"""CLI smoke test for the Gemini image generation pipeline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import time
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


def _format_header(count: int, aspect: str) -> str:
    return (
        "Nano Banana — smoke | "
        f"{gemini_service.MODEL_NAME} | "
        f"count={count} | aspect={aspect} | format=png"
    )


def _print_diagnostics(images: Sequence[bytes]) -> None:
    for idx, image in enumerate(images, start=1):
        print(f"image {idx}: {len(image)} bytes")


def main() -> None:
    logging_conf.configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    try:
        prompt = assistant_service.generate_prompt_text()
        LOGGER.info(
            "generated prompt metadata: length=%d hash=%s",
            len(prompt),
            hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8],
        )
        LOGGER.info("sleeping 30s before image generation")
        time.sleep(30)
        aspect_key = args.aspect.upper()
        images = gemini_service.generate_images(prompt, n=args.n, aspect=aspect_key, fmt="png")

        if args.no_send:
            _print_diagnostics(images)
            LOGGER.info("smoke success: count=%d sent=%s", len(images), False)
            return

        header = _format_header(len(images), aspect_key)
        asyncio.run(
            telegram_service.send_images_and_prompt(
                list(images), prompt_text=prompt, header=header
            )
        )
        LOGGER.info("smoke success: count=%d sent=%s", len(images), True)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("smoke test failed: %s: %s", exc.__class__.__name__, str(exc))
        raise


if __name__ == "__main__":
    main()
