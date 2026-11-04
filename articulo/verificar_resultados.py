#!/usr/bin/env python3
"""Verifica la coherencia numérica del manuscrito SOC-Lite.

No genera resultados nuevos: recalcula las métricas que se derivan de las
matrices y de los agregados reportados, y comprueba que las cifras usadas en
el texto y en las tablas sean consistentes entre sí.

Uso:
    python articulo/verificar_resultados.py
"""
from __future__ import annotations

from math import isclose


def prf(cm: list[list[int]]) -> tuple[list[float], list[float], list[float], float]:
    """Precisión, exhaustividad y F1 por clase a partir de una matriz 3x3."""
    n = len(cm)
    precision, recall, f1 = [], [], []
    for k in range(n):
        tp = cm[k][k]
        pred = sum(cm[i][k] for i in range(n))
        real = sum(cm[k])
        p = tp / pred if pred else 0.0
        r = tp / real if real else 0.0
        precision.append(p)
        recall.append(r)
        f1.append(2 * p * r / (p + r) if (p + r) else 0.0)
    acc = sum(cm[k][k] for k in range(n)) / sum(sum(row) for row in cm)
    return precision, recall, f1, acc


def check(name: str, value: float, expected: float, tol: float = 5e-4) -> None:
    ok = isclose(value, expected, abs_tol=tol)
    print(f"{'OK ' if ok else 'FALLA'} {name}: {value:.6f} (esperado {expected:.6f})")
    if not ok:
        raise SystemExit(1)


def main() -> None:
    # Composición del banco de pruebas
    sources = {
        "CICIDS2017": (2304, 2880, 576),
        "UNSW-NB15": (1152, 1440, 288),
        "Wazuh/OPNsense": (720, 1440, 240),
        "Negativos duros": (0, 624, 816),
    }
    totals = [sum(v[i] for v in sources.values()) for i in range(3)]
    check("total VP", totals[0], 4176, 0)
    check("total FP", totals[1], 6384, 0)
    check("total SUS", totals[2], 1920, 0)
    check("total alertas", sum(totals), 12480, 0)
    check("proporción VP", totals[0] / 12480, 0.3346, 1e-4)
    check("proporción FP", totals[1] / 12480, 0.5115, 1e-4)
    check("proporción SUS", totals[2] / 12480, 0.1538, 1e-4)

    # Partición
    check("entrenamiento", round(12480 * 0.70), 8736, 0)
    check("validación", round(12480 * 0.10), 1248, 0)
    check("prueba", round(12480 * 0.20), 2496, 0)

    # Matriz de confusión del agente (filas = real, columnas = predicho)
    cm = [
        [760, 50, 25],
        [50, 1190, 37],
        [25, 37, 322],
    ]
    check("soporte VP", sum(cm[0]), 835, 0)
    check("soporte FP", sum(cm[1]), 1277, 0)
    check("soporte SUS", sum(cm[2]), 384, 0)
    check("total prueba", sum(sum(row) for row in cm), 2496, 0)

    precision, recall, f1, acc = prf(cm)
    check("exactitud del agente", acc, 0.9103, 5e-4)
    check("F1 VP", f1[0], 0.9102, 5e-4)
    check("F1 FP", f1[1], 0.9319, 5e-4)
    check("F1 SUS", f1[2], 0.8385, 5e-4)
    check("macro-F1 del agente", sum(f1) / 3, 0.8935, 5e-4)
    check("macro-precisión del agente", sum(precision) / 3, 0.8935, 5e-4)
    check("macro-exhaustividad del agente", sum(recall) / 3, 0.8935, 5e-4)

    # Severidad: soportes y F1 por clase
    sev_support = {"alta": 612, "media": 1104, "baja": 780}
    sev_f1 = {"alta": 0.868, "media": 0.864, "baja": 0.826}
    check("soporte severidad", sum(sev_support.values()), 2496, 0)
    weighted = sum(sev_support[k] * sev_f1[k] for k in sev_f1) / 2496
    check("F1 ponderada de severidad", weighted, 0.8531, 1e-4)

    # Impacto operacional
    hours_manual, hours_soc = 103.3, 7.2
    check("reducción de horas", (hours_manual - hours_soc) / hours_manual, 0.9303, 5e-4)
    check("costo analista SOC-Lite", hours_soc * 20, 144.0, 1e-6)
    check("costo total con infraestructura", hours_soc * 20 + 3.10, 147.10, 1e-6)

    # Consistencia de la política de decisión
    coverage, auto_error = 0.527, 0.082
    auto_closed = round(2496 * coverage)
    correct_auto = round(auto_closed * (1 - auto_error))
    remaining_fp = 1277 - correct_auto
    escalated = 2496 - auto_closed
    fp_rate = remaining_fp / escalated
    check("precisión de escalamiento", 1 - fp_rate, 0.9407, 5e-4)
    check("FP en cola escalada", fp_rate, 0.0593, 5e-4)
    check("cobertura de autocierre", auto_closed / 2496, 0.527, 1e-3)
    check("error de autocierre", 1 - correct_auto / auto_closed, 0.082, 1e-3)

    # Tamaños de efecto reportados
    check("Δ vs XGBoost", 0.891 - 0.829, 0.062, 1e-9)
    check("Δ vs BETO", 0.891 - 0.847, 0.044, 1e-9)
    check("Δ vs heurístico", 0.891 - 0.641, 0.250, 1e-9)
    check("Δ PR-AUC vs BETO", 0.931 - 0.897, 0.034, 1e-9)

    print("\nTodas las comprobaciones numéricas pasaron.")


if __name__ == "__main__":
    main()
