#!/usr/bin/env python3
"""
Outil de validation du endpoint /api/v1/chat/stream

Permet de lancer une requête question par question, stocker les résultats
en JSON et compléter un rapport Markdown.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT_DIR / "Tests"
RESULTS_DIR = TESTS_DIR / "results"
QUESTIONS_PATH = ROOT_DIR / "backend" / "kauri_chatbot_service" / "QUESTIONS_TESTS_VALIDATION.md"
REPORT_PATH = TESTS_DIR / "rapport.md"

LOGIN_URL = os.environ.get("KAURI_LOGIN_URL", "http://localhost:3201/api/v1/auth/login")
STREAM_URL = os.environ.get("KAURI_STREAM_URL", "http://localhost:3202/api/v1/chat/stream")
EMAIL = os.environ.get("KAURI_TEST_EMAIL", "henri.hounwanou@gmail.com")
PASSWORD = os.environ.get("KAURI_TEST_PASSWORD", "Harena2032@")


def utc_now_iso() -> str:
    """Return current UTC datetime as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def ensure_directories() -> None:
    """Create Tests/ structure and rapport if needed."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not REPORT_PATH.exists():
        REPORT_PATH.write_text(
            "# Rapport de validation KAURI Chatbot\n\n"
            "Ce document est rempli question par question.\n",
            encoding="utf-8",
        )


def load_questions() -> Dict[int, str]:
    """Parse numbered questions from QUESTIONS_TESTS_VALIDATION.md."""
    if not QUESTIONS_PATH.exists():
        raise FileNotFoundError(f"Questions file not found: {QUESTIONS_PATH}")

    content = QUESTIONS_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"^\s*(\d+)\.\s+(.*\S)", re.MULTILINE)

    questions: Dict[int, str] = {}
    for match in pattern.finditer(content):
        qid = int(match.group(1))
        questions[qid] = match.group(2).strip()

    if not questions:
        raise ValueError("No questions parsed from QUESTIONS_TESTS_VALIDATION.md")

    return questions


def authenticate(session: requests.Session) -> str:
    """Return JWT token from user service."""
    response = session.post(
        LOGIN_URL,
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def stream_question(
    session: requests.Session,
    token: str,
    question: str,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Call the stream endpoint and capture the SSE flow."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    result: Dict[str, Any] = {
        "question": question,
        "answer": "",
        "sources": [],
        "metadata": {},
        "message_id": None,
        "http_status": None,
        "latency_ms": None,
        "elapsed_ms": None,
        "error": None,
        "status_chunks": [],
        "timestamp": utc_now_iso(),
    }

    start = time.perf_counter()
    try:
        response = session.post(
            STREAM_URL,
            headers=headers,
            json={"query": question},
            stream=True,
            timeout=(10, 300),
        )
    except requests.RequestException as exc:
        result["error"] = f"RequestException: {exc}"
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return result, None

    result["http_status"] = response.status_code

    if response.status_code != 200:
        body = response.text[:500]
        result["error"] = f"HTTP {response.status_code}: {body}"
        response.close()
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return result, None

    done_received = False
    try:
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or raw_line.startswith(":"):
                continue
            if not raw_line.startswith("data: "):
                continue

            payload = raw_line[6:]
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                result["status_chunks"].append({"type": "malformed", "raw": payload})
                continue

            chunk_type = chunk.get("type")
            if chunk_type == "token":
                result["answer"] += chunk.get("content", "")
            elif chunk_type == "sources":
                result["sources"] = chunk.get("sources", [])
            elif chunk_type == "status":
                result["status_chunks"].append({"type": "status", "content": chunk.get("content")})
            elif chunk_type == "message_id":
                result["message_id"] = chunk.get("message_id")
            elif chunk_type == "done":
                result["metadata"] = chunk.get("metadata", {})
                result["latency_ms"] = result["metadata"].get("latency_ms")
                done_received = True
                break
            elif chunk_type == "error":
                result["error"] = chunk.get("content", "Stream error")
                break
    finally:
        response.close()

    result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
    if not done_received and not result["error"]:
        result["error"] = "Stream ended without done event"

    return result, result["answer"]


def save_json(question_id: int, payload: Dict[str, Any]) -> Path:
    """Persist raw result to Tests/results/question_##.json."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"question_{question_id:02d}.json"
    data = {"generated_at": utc_now_iso(), **payload}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_report(question_id: int, question: str, result: Dict[str, Any]) -> None:
    """Append a human-readable section to Tests/rapport.md."""
    latency = result.get("latency_ms") or result.get("elapsed_ms")
    latency_str = "n/a" if latency is None else f"{latency:.2f} ms"
    sources_lines = [
        f"  - {src.get('title', 'Sans titre')} (score: {src.get('score')})"
        for src in result.get("sources", [])
    ]
    sources_str = "\n".join(sources_lines) if sources_lines else "  - Aucune source"

    answer_preview = (result.get("answer") or "").strip()
    if len(answer_preview) > 800:
        answer_preview = answer_preview[:800].rstrip() + "..."

    block = (
        f"## Question {question_id}: {question}\n\n"
        f"- Horodatage test: {result.get('timestamp')}\n"
        f"- Latence rapportee: {latency_str}\n"
        f"- Status HTTP: {result.get('http_status')}\n"
        f"- Message ID: {result.get('message_id') or 'n/a'}\n"
        f"- Sources:\n{sources_str}\n"
        f"- Extrait reponse:\n\n"
        f"```\n{answer_preview}\n```\n\n"
        f"- Analyse (a completer):\n\n"
    )
    with REPORT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(block)


def already_processed(question_id: int) -> bool:
    """Return True if a JSON result already exists."""
    path = RESULTS_DIR / f"question_{question_id:02d}.json"
    return path.exists()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test KAURI chatbot stream endpoint question par question.",
    )
    parser.add_argument("--question-id", type=int, help="Numero de question a traiter (1-60).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rejouer la question meme si un resultat existe deja.",
    )
    args = parser.parse_args()

    ensure_directories()
    questions = load_questions()

    if args.question_id:
        if args.question_id not in questions:
            print(
                f"Question {args.question_id} introuvable dans QUESTIONS_TESTS_VALIDATION.md",
                file=sys.stderr,
            )
            sys.exit(1)
        question_ids: List[int] = [args.question_id]
    else:
        question_ids = sorted(questions.keys())

    session = requests.Session()
    try:
        token = authenticate(session)
    except Exception as exc:
        print(f"Echec de l'authentification: {exc}", file=sys.stderr)
        sys.exit(1)

    for qid in question_ids:
        if already_processed(qid) and not args.force:
            print(f"[Question {qid}] deja traitee - utiliser --force pour rejouer.")
            continue

        question_text = questions[qid]
        print(f"\n[Question {qid}] {question_text}")

        result, _ = stream_question(session, token, question_text)
        if result.get("error"):
            print(f"  -> Echec: {result['error']}")
        else:
            nb_sources = len(result.get("sources", []))
            latency = result.get("latency_ms") or result.get("elapsed_ms")
            latency_disp = "n/a" if latency is None else f"{latency:.2f} ms"
            print(f"  -> OK | Latence: {latency_disp} | Sources: {nb_sources}")

        json_path = save_json(qid, {"question_id": qid, **result})
        append_report(qid, question_text, result)
        print(f"  -> Resultat sauvegarde: {json_path}")


if __name__ == "__main__":
    main()
