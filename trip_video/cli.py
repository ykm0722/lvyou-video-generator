from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import create_draft, load_review_document
from .render import render_video
from .review_server import serve_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="generate", description="Travel promo video generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    draft_parser = subparsers.add_parser("draft", help="Generate a draft document")
    draft_parser.add_argument("trip_dir", help="Trip directory under resource/")
    draft_parser.add_argument("--model", default="gpt-4o-mini")
    draft_parser.add_argument("--skip-ai", action="store_true")
    draft_parser.add_argument("--voice", default="")

    review_parser = subparsers.add_parser("review", help="Launch local review server")
    review_parser.add_argument("trip_dir", help="Trip directory under resource/")
    review_parser.add_argument("--port", type=int, default=8765)

    render_parser = subparsers.add_parser("render", help="Render the reviewed document")
    render_parser.add_argument("trip_dir", help="Trip directory under resource/")

    all_parser = subparsers.add_parser("all", help="Generate draft, then launch review")
    all_parser.add_argument("trip_dir", help="Trip directory under resource/")
    all_parser.add_argument("--model", default="gpt-4o-mini")
    all_parser.add_argument("--skip-ai", action="store_true")
    all_parser.add_argument("--voice", default="")
    all_parser.add_argument("--port", type=int, default=8765)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "draft":
        draft = create_draft(args.trip_dir, model=args.model, skip_ai=args.skip_ai, voice=args.voice)
        print(json.dumps(draft.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "review":
        serve_review(args.trip_dir, port=args.port)
        return 0

    if args.command == "render":
        document = load_review_document(args.trip_dir)
        outputs = render_video(document)
        print(json.dumps(outputs, ensure_ascii=False, indent=2))
        return 0

    if args.command == "all":
        create_draft(args.trip_dir, model=args.model, skip_ai=args.skip_ai, voice=args.voice)
        serve_review(args.trip_dir, port=args.port)
        return 0

    parser.error("Unknown command")
    return 2
