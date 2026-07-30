from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .service import RAGService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-rag",
        description="Local PDF RAG with OpenAI embeddings and grounded answers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Index PDFs")
    ingest.add_argument("--pdf-dir", type=Path)
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="Clear the generated index before ingesting",
    )

    search = subparsers.add_parser("search", help="Retrieve relevant excerpts")
    search.add_argument("query")
    search.add_argument("--top-k", type=int)
    search.add_argument("--source")

    ask = subparsers.add_parser("ask", help="Answer from indexed papers")
    ask.add_argument("question")
    ask.add_argument("--top-k", type=int)
    ask.add_argument("--source")

    serve = subparsers.add_parser("serve", help="Start the local Agent API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("health", help="Show index and model status")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    service = RAGService.from_env()

    if args.command == "ingest":
        result = service.ingest_directory(args.pdf_dir, reset=args.reset)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "search":
        result = service.search(
            args.query, args.top_k, source=args.source
        )
        print(
            json.dumps(
                [item.to_dict() for item in result],
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "ask":
        result = service.ask(
            args.question, args.top_k, source=args.source
        )
        print(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        )
    elif args.command == "health":
        print(
            json.dumps(service.health(), ensure_ascii=False, indent=2)
        )
    elif args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError(
                "uvicorn is required. Install the project first."
            ) from exc
        uvicorn.run("local_rag.api:app", host=args.host, port=args.port)
