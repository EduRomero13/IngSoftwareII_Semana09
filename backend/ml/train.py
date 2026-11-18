"""Entrena el clasificador de triaje (TF-IDF + regresión logística) y guarda el modelo.

Uso:
    cd backend
    python -m ml.train

Genera:
    backend/ml/model.joblib   (pipeline sklearn)
    backend/ml/metrics.json   (accuracy, macro-F1, matriz de confusión, latencia media)

El dataset es sintético y determinista: parte de 12 plantillas de alerta con su
veredicto de referencia y añade ruido de etiqueta (6 %) para que las métricas sean
realistas (no 100 %).
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
METRICS_PATH = Path(__file__).resolve().parent / "metrics.json"

# (título, descripción, veredicto, severidad final)
TEMPLATES = [
    ("Multiple failed SSH logins", "25 intentos fallidos de autenticación SSH en 5 minutos", "verdadero_positivo", "alta"),
    ("Port scan detected from external host", "Escaneo TCP SYN desde una IP externa hacia el perímetro", "verdadero_positivo", "media"),
    ("Malware C2 beacon to known bad IP", "Conexión periódica cada 60 s hacia infraestructura C2", "verdadero_positivo", "alta"),
    ("SQL injection attempt blocked", "Petición con UNION SELECT sobre el portal público", "verdadero_positivo", "alta"),
    ("Brute force on RDP", "Intentos de login RDP con credenciales inválidas", "verdadero_positivo", "alta"),
    ("Suspicious PowerShell execution", "PowerShell en Base64 con descarga remota", "verdadero_positivo", "alta"),
    ("Web shell upload attempt", "Archivo PHP creado en el directorio de subidas", "verdadero_positivo", "alta"),
    ("DNS query to malicious domain", "Resolución hacia un dominio en listas de amenazas", "verdadero_positivo", "media"),
    ("Lateral movement via SMB", "Autenticaciones SMB internas fuera de horario", "sospechoso", "media"),
    ("TLS certificate with weak cipher", "Negociación TLS con cifrados obsoletos internos", "falso_positivo", "baja"),
    ("Outbound connection to Tor exit node", "Conexión saliente hacia un nodo de salida de Tor", "sospechoso", "media"),
    ("Repeated 404 errors on admin panel", "Ráfaga de 404 sobre /wp-admin desde una IP", "falso_positivo", "baja"),
]

VERDICTS = ["verdadero_positivo", "sospechoso", "falso_positivo"]
NOISE = 0.06


def build_dataset(rows: int = 12000, seed: int = 42) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    texts: list[str] = []
    labels: list[str] = []
    for i in range(rows):
        title, description, verdict, severity = TEMPLATES[i % len(TEMPLATES)]
        # Ruido léxico: número de eventos y sufijo de regla, como en Wazuh real.
        text = f"{title}. {description}. severidad {severity}. regla {rng.randint(1000, 99999)}"
        if rng.random() < NOISE:
            verdict = rng.choice([v for v in VERDICTS if v != verdict])
        texts.append(text)
        labels.append(verdict)
    return texts, labels


def main() -> None:
    texts, labels = build_dataset()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=5.0)),
        ]
    )
    start = time.perf_counter()
    pipeline.fit(x_train, y_train)
    train_seconds = round(time.perf_counter() - start, 2)

    predictions = pipeline.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))
    macro_f1 = float(f1_score(y_test, predictions, average="macro"))

    # Chequeo mínimo: si el modelo no supera esto, algo se rompió.
    assert accuracy > 0.85, f"accuracy inesperada: {accuracy:.3f}"

    joblib.dump(pipeline, MODEL_PATH)

    metrics = {
        "model": "tfidf+logistic_regression",
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "train_seconds": train_seconds,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "labels": VERDICTS,
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=VERDICTS).tolist(),
        "classification_report": classification_report(
            y_test, predictions, labels=VERDICTS, output_dict=True, zero_division=0
        ),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("accuracy", "macro_f1", "train_seconds")}, indent=2))
    print(f"modelo: {MODEL_PATH}")


if __name__ == "__main__":
    main()
