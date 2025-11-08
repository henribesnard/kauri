#!/usr/bin/env python3
"""
Construit un rapport de validation synthétique à partir des résultats JSON.

Le rapport inclut pour chaque question la latence observée et une appréciation
de la cohérence de la réponse en fonction du type de question.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "Tests" / "results"
OUTPUT_PATH = ROOT_DIR / "Tests" / "rapport_final.md"
QUESTIONS_PATH = ROOT_DIR / "backend" / "kauri_chatbot_service" / "QUESTIONS_TESTS_VALIDATION.md"


def load_questions() -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    content = QUESTIONS_PATH.read_text(encoding="utf-8")
    current_id = 0
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line[0].isdigit():
            parts = line.split(".", 1)
            try:
                current_id = int(parts[0])
            except ValueError:
                continue
            if len(parts) > 1:
                mapping[current_id] = parts[1].strip()
    return mapping


def question_category(qid: int) -> str:
    if 1 <= qid <= 10:
        return "general"
    if 11 <= qid <= 25:
        return "actes"
    if 26 <= qid <= 35:
        return "articles"
    if 36 <= qid <= 45:
        return "plan_comptable"
    if 46 <= qid <= 55:
        return "jurisprudence"
    return "cas_pratiques"


def evaluate_coherence(qid: int, data: Dict) -> Tuple[str, str]:
    category = question_category(qid)
    answer = (data.get("answer") or "").strip()
    sources = data.get("sources") or []
    error = data.get("error")

    if error:
        return "Non conforme", f"Erreur durant le stream: {error}"
    if not answer:
        return "Non conforme", "Réponse vide"

    if category in {"articles", "jurisprudence"}:
        if not sources:
            return "Non conforme", f"Question de type {category} sans sources"
        return "Conforme", "Sources présentes pour question de sourcing"

    if category == "cas_pratiques":
        if len(answer) < 200:
            return "À surveiller", "Réponse courte pour un cas pratique"
        return "Conforme", "Réponse détaillée pour cas pratique"

    return "Conforme", "Réponse textuelle fournie"


def load_result(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_latency(data: Dict) -> str:
    latency = data.get("latency_ms") or data.get("elapsed_ms")
    if latency is None:
        return "n/a"
    return f"{latency:.0f} ms"


def build_report():
    questions = load_questions()
    rows: List[str] = []
    for result_path in sorted(RESULTS_DIR.glob("question_*.json")):
        data = load_result(result_path)
        qid = int(data.get("question_id"))
        question_text = questions.get(qid, data.get("question", ""))
        latency = format_latency(data)
        status, comment = evaluate_coherence(qid, data)
        category = question_category(qid)
        row = (
            f"## Question {qid}: {question_text}\n"
            f"- Catégorie: {category}\n"
            f"- Latence: {latency}\n"
            f"- Cohérence: {status}\n"
            f"- Commentaire: {comment}\n"
        )
        rows.append(row)

    OUTPUT_PATH.write_text(
        "# Rapport final de validation KAURI Chatbot\n\n" + "\n".join(rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_report()
