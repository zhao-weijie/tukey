"""TF-IDF similarity tool.

Best suited for structured extraction tasks where vocabulary overlap is
meaningful. Less useful for creative/open-ended responses — see the project
brainstorm notes for why.

Example plugin: demonstrates the SynthesisTool protocol.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from tukey.synthesis.bundle import ExperimentBundle
from tukey.synthesis.tool import Section, SynthesisResult

_WORD_RE = re.compile(r"[a-z]+(?:['\u2019][a-z]+)?")


def _tokenize(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if len(w) >= 2]


def _ngrams(words: list[str]) -> list[str]:
    bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)]
    return words + bigrams


def _build_tfidf(documents: list[str]) -> list[dict[str, float]]:
    n = len(documents)
    tf_list: list[Counter[str]] = []
    df: Counter[str] = Counter()
    for doc in documents:
        terms = _ngrams(_tokenize(doc))
        tf = Counter(terms)
        tf_list.append(tf)
        df.update(set(tf.keys()))

    vectors: list[dict[str, float]] = []
    for tf in tf_list:
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log(n / df[term]) if df[term] < n else 0.0
            if (weight := count * idf) > 0:
                vec[term] = weight
        vectors.append(vec)
    return vectors


def _cosine_sim(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b[k] for k, v in a.items() if k in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class TfIdfTool:
    """TF-IDF cosine similarity matrix and distinctive terms per model."""

    @property
    def name(self) -> str:
        return "tfidf"

    @property
    def description(self) -> str:
        return "TF-IDF cosine similarity matrix and per-model distinctive terms"

    def analyze(self, bundle: ExperimentBundle) -> SynthesisResult:
        names = bundle.model_names

        # Collect all (model_id, response_text) pairs
        entries: list[tuple[str, int, str]] = []  # (model_id, idx, text)
        for model_id in bundle.model_ids:
            for i, text in enumerate(bundle.responses_for_model(model_id)):
                entries.append((model_id, i, text))

        if not entries:
            return SynthesisResult(
                tool_name=self.name,
                sections=[Section(title="No Data", content_type="text", body="No responses to analyze.")],
            )

        documents = [text for _, _, text in entries]
        vectors = _build_tfidf(documents)
        n = len(entries)

        # Similarity matrix
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 1.0
            for j in range(i + 1, n):
                sim = round(_cosine_sim(vectors[i], vectors[j]), 4)
                matrix[i][j] = sim
                matrix[j][i] = sim

        labels = [
            f"{names.get(mid, mid)}[{idx}]"
            for mid, idx, _ in entries
        ]

        # Intra vs cross model similarity
        intra, cross = [], []
        for i in range(n):
            for j in range(i + 1, n):
                (intra if entries[i][0] == entries[j][0] else cross).append(matrix[i][j])

        # Distinctive terms per model
        distinctive: dict[str, list[str]] = {}
        for model_id in bundle.model_ids:
            indices = [i for i, (mid, _, _) in enumerate(entries) if mid == model_id]
            term_weights: dict[str, float] = {}
            for idx in indices:
                for term, w in vectors[idx].items():
                    term_weights[term] = term_weights.get(term, 0.0) + w
            count = len(indices)
            for t in term_weights:
                term_weights[t] /= count
            top = sorted(term_weights, key=lambda t: term_weights[t], reverse=True)[:10]
            distinctive[names.get(model_id, model_id)] = [t.replace("_", " ") for t in top]

        sections = [
            Section(
                title="TF-IDF Similarity Matrix",
                content_type="matrix",
                body={"labels": labels, "matrix": matrix},
            ),
            Section(
                title="Similarity Summary",
                content_type="json",
                body={
                    "intra_model_avg": round(sum(intra) / len(intra), 4) if intra else 0,
                    "cross_model_avg": round(sum(cross) / len(cross), 4) if cross else 0,
                    "intra_pairs": len(intra),
                    "cross_pairs": len(cross),
                },
            ),
            Section(
                title="Distinctive Terms",
                content_type="json",
                body=distinctive,
            ),
        ]

        return SynthesisResult(tool_name=self.name, sections=sections)
