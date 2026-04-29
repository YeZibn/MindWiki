#!/usr/bin/env python3
"""Run a minimal end-to-end local LLM verification."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mindwiki.infrastructure import settings as settings_module
from mindwiki.llm.service import GenerateTextInput, build_llm_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local LLM generate_text flow against the configured gateway.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional LLM base URL override. Defaults to LLM_BASE_URL or .env.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional LLM API key override. Defaults to LLM_API_KEY or .env.",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Optional model override. Defaults to LLM_MODEL_ID or .env.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30000,
        help="Request timeout in milliseconds.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.base_url:
        os.environ["LLM_BASE_URL"] = args.base_url
    if args.api_key:
        os.environ["LLM_API_KEY"] = args.api_key
    if args.model:
        os.environ["LLM_MODEL_ID"] = args.model
    os.environ["LLM_TIMEOUT_MS"] = str(args.timeout_ms)
    settings_module.clear_settings_cache()

    settings = settings_module.get_settings()
    missing = [
        name
        for name, value in (
            ("LLM_BASE_URL", settings.llm_base_url),
            ("LLM_API_KEY", settings.llm_api_key),
            ("LLM_MODEL_ID", settings.llm_model_id),
        )
        if not value
    ]
    if missing:
        print(f"Verification failed: missing LLM config: {', '.join(missing)}")
        return 1

    service = build_llm_service()
    response = service.generate_text(
        GenerateTextInput(
            system_prompt="You are a concise assistant. Reply with plain text only.",
            user_prompt="Reply with exactly: MINDWIKI_LLM_OK",
            task_type="smoke_test",
            max_tokens=32,
            metadata={"request_id": "verify-local-llm"},
        )
    )

    summary = {
        "status": response.status,
        "model": response.model,
        "output_text": response.output_text,
        "finish_reason": response.finish_reason,
        "usage": response.usage,
        "validation": {
            "protocol_validation": response.validation.protocol_validation.passed,
            "schema_validation": response.validation.schema_validation.passed,
            "citation_validation": response.validation.citation_validation.passed,
            "final_status": response.validation.final_status,
        },
        "error": None
        if response.error is None
        else {
            "error_type": response.error.error_type,
            "retryable": response.error.retryable,
            "fallback_allowed": response.error.fallback_allowed,
            "message": response.error.message,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if response.status != "success":
        return 1
    if response.output_text.strip() != "MINDWIKI_LLM_OK":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
