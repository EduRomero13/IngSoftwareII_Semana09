"""Clasificador ML de triaje (TF-IDF + regresión logística).

Carga perezosa: si `backend/ml/model.joblib` no existe, el endpoint responde 503
y el resto del sistema sigue funcionando con la heurística o el LLM.
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "model.joblib"
MODEL_NAME = "tfidf+logistic_regression"


class ModelUnavailable(RuntimeError):
    """El modelo no está entrenado (`python -m ml.train`)."""


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists():
        raise ModelUnavailable(f"Modelo no encontrado en {MODEL_PATH}. Ejecuta: python -m ml.train")
    return joblib.load(MODEL_PATH)


def predict(*, title: str, description: str | None = None, severity: str = "media",
            source: str = "wazuh") -> dict:
    """Devuelve veredicto, severidad estimada, confianza y latencia de inferencia."""
    pipeline = _load()
    text = f"{title}. {description or ''}. severidad {severity}. fuente {source}"
    start = time.perf_counter()
    proba = pipeline.predict_proba([text])[0]
    verdict = str(pipeline.classes_[proba.argmax()])
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "verdict": verdict,
        "severity": _severity_for(verdict, severity),
        "confidence": round(float(proba.max()), 3),
        "model_name": MODEL_NAME,
        "latency_ms": latency_ms,
    }


def _severity_for(verdict: str, original: str) -> str:
    if verdict == "verdadero_positivo":
        return "alta"
    if verdict == "falso_positivo":
        return "baja"
    return "media" if original != "baja" else "baja"
