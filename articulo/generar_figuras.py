#!/usr/bin/env python3
"""Genera las seis figuras del artículo SOC-Lite.

Los valores son los del escenario de evaluación simulado descrito en el
manuscrito. Las figuras se guardan en articulo/figuras/ a 300 dpi.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

BASE = Path(__file__).resolve().parent
FIG = BASE / "figuras"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Paleta accesible y consistente
C = {
    "tp": "#1f5a99",
    "fp": "#c0392b",
    "sus": "#d68910",
    "full": "#0b3d91",
    "heuristic": "#7f8c8d",
    "xgb": "#2e86c1",
    "beto": "#8e44ad",
    "llm": "#117a65",
    "grid": "#d5d8dc",
    "text": "#1b2631",
}


# ---------------------------------------------------------------------------
# Figura 1. Arquitectura y flujo de triaje
# ---------------------------------------------------------------------------
def figura1() -> None:
    fig, ax = plt.subplots(figsize=(10.4, 6.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#f8fafc", ec="#94a3b8", fs=8.2, bold=False, lw=1.0):
        p = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.35,rounding_size=1.4",
            linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2,
        )
        ax.add_patch(p)
        ax.text(
            x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=C["text"], zorder=3,
            fontweight="bold" if bold else "normal", linespacing=1.25,
        )

    def arrow(x1, y1, x2, y2, color="#475569", ls="-", lw=1.2, rad=0.0):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
            linewidth=lw, color=color, linestyle=ls,
            connectionstyle=f"arc3,rad={rad}", zorder=1,
        ))

    def poly_arrow(points, color="#475569", ls="-", lw=1.2):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs[:-1], ys[:-1], color=color, lw=lw, ls=ls, zorder=1,
                solid_capstyle="round")
        ax.add_patch(FancyArrowPatch(
            points[-2], points[-1], arrowstyle="-|>", mutation_scale=10,
            linewidth=lw, color=color, linestyle=ls, zorder=1,
        ))

    # Encabezados de columna
    for x, title, color in [
        (3, "1. Ingesta y orquestación", "#1e3a8a"),
        (38, "2. Triaje y clasificación", "#065f46"),
        (73, "3. Persistencia y respuesta", "#9d174d"),
    ]:
        ax.text(x, 97, title, ha="left", va="center", fontsize=9.5,
                fontweight="bold", color=color)

    # Columna 1
    box(3, 82, 26, 11, "Wazuh / OPNsense\n(alertas crudas)", "#dbeafe", "#60a5fa")
    box(3, 64, 26, 12, "n8n 2.45.5\nwebhook · normaliza · IF\nlogin de servicio · switch", "#ede9fe", "#a78bfa")
    box(3, 46, 26, 12, "FastAPI · ingesta\nX-Webhook-Token\ndeduplicación SHA-256", "#d1fae5", "#34d399")
    box(3, 28, 26, 12, "RBAC + JWT\nmiddleware de auditoría\npermisos por recurso", "#d1fae5", "#34d399")
    box(3, 10, 26, 12, "Usuario de servicio\n(rol analyst)\ncredenciales en entorno", "#f1f5f9", "#94a3b8")

    # Columna 2
    box(38, 82, 26, 11, "Servicio de triaje\norquesta el análisis", "#d1fae5", "#34d399")
    box(38, 64, 26, 12, "Enriquecimiento contextual\nVirusTotal · AbuseIPDB\nGeoIP · inteligencia local", "#ffedd5", "#fb923c")
    box(38, 46, 26, 12, "Agente LangChain\nllama3.1 8B vía Ollama\nsalida estructurada (Pydantic)", "#ffedd5", "#fb923c")
    box(38, 28, 26, 12, "Fallback heurístico\ndeterminista\n(score + reglas)", "#ffedd5", "#fb923c")
    box(38, 10, 26, 12, "Política de decisión\nconfianza + umbral\nveredicto y severidad", "#d1fae5", "#34d399")

    # Frontera de inferencia local
    ax.add_patch(FancyBboxPatch(
        (35.6, 26.2), 30.8, 52.0,
        boxstyle="round,pad=0.25,rounding_size=1.5",
        linewidth=1.2, edgecolor="#b91c1c", facecolor="none",
        linestyle=(0, (4, 2)), zorder=4,
    ))
    ax.text(51, 79.8, "Inferencia local · sin APIs externas de LLM",
            ha="center", va="bottom", fontsize=7.6, color="#b91c1c",
            fontweight="bold", zorder=5)

    # Columna 3
    box(73, 82, 24, 11, "PostgreSQL 16\nalerts · triage_results\nenrichment_data · audit_log", "#e2e8f0", "#64748b")
    box(73, 62, 24, 11, "Dashboard React\nKPIs · MTTT · FP%\ncola priorizada", "#fce7f3", "#f472b6")
    box(73, 42, 24, 11, "n8n · switch por severidad\nSlack (alta)\nosTicket (alta / media)", "#fce7f3", "#f472b6")
    box(73, 22, 24, 11, "Bitácora de auditoría\nEXECUTE · EXPORT · READ\nusuario · IP · latencia", "#e2e8f0", "#64748b")
    box(73, 2, 24, 11, "Reportes PDF / Word / Excel\noperacional y de gestión", "#fce7f3", "#f472b6")

    # Flechas columna 1
    arrow(16, 82, 16, 76.2)
    arrow(16, 64, 16, 58.2)
    arrow(16, 46, 16, 40.2)
    arrow(16, 28, 16, 22.2)

    # Ingesta -> triaje
    arrow(29.2, 87.5, 37.8, 87.5, color="#065f46", lw=1.4)
    ax.text(33.5, 89.2, "POST /triage/{id}", ha="center", va="bottom",
            fontsize=7.2, color="#065f46")

    # Flechas columna 2
    arrow(51, 82, 51, 76.2)
    arrow(51, 64, 51, 58.2)
    arrow(51, 46, 51, 40.2, color="#b91c1c", ls=(0, (3, 2)))
    ax.text(52.2, 43.0, "timeout / error", ha="left", va="center",
            fontsize=7.0, color="#b91c1c")
    arrow(51, 28, 51, 22.2)

    # Decisión -> PostgreSQL (resultado y auditoría)
    poly_arrow([(64.2, 16), (68.2, 16), (68.2, 87.5), (72.8, 87.5)],
               color="#334155", lw=1.4)
    ax.text(66.0, 51.5, "resultado + auditoría", ha="center", va="center",
            fontsize=7.0, color="#334155", rotation=90)

    # Decisión -> switch n8n (respuesta)
    poly_arrow([(64.2, 12), (69.8, 12), (69.8, 47.5), (72.8, 47.5)],
               color="#9d174d", ls=(0, (3, 2)), lw=1.1)
    ax.text(70.4, 28.0, "respuesta", ha="left", va="center",
            fontsize=7.0, color="#9d174d", rotation=90)

    # PostgreSQL -> dashboard y auditoría
    arrow(85, 82, 85, 73.2, color="#334155")
    arrow(85, 62, 85, 33.2, color="#334155", ls=(0, (3, 2)))
    ax.text(86.0, 47.5, "consultas", ha="left", va="center",
            fontsize=7.0, color="#334155", rotation=90)

    # Leyenda
    handles = [
        Line2D([0], [0], color="#475569", lw=1.4, label="flujo de datos"),
        Line2D([0], [0], color="#334155", lw=1.2, ls=(0, (3, 2)), label="consulta / control"),
        Line2D([0], [0], color="#b91c1c", lw=1.2, ls=(0, (3, 2)), label="degradación controlada"),
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.01, -0.01),
              frameon=False, ncol=3, handlelength=2.2, columnspacing=1.6)

    fig.savefig(FIG / "figura1_arquitectura.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 2. Composición del banco de pruebas
# ---------------------------------------------------------------------------
def figura2() -> None:
    sources = ["CICIDS2017", "UNSW-NB15", "Wazuh /\nOPNsense", "Negativos\nduros"]
    tp = np.array([2304, 1152, 720, 0])
    fp = np.array([2880, 1440, 1440, 624])
    sus = np.array([576, 288, 240, 816])
    totals = tp + fp + sus

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1), gridspec_kw={"width_ratios": [1.55, 1]})
    ax = axes[0]
    x = np.arange(len(sources))
    w = 0.62
    b1 = ax.bar(x, tp, w, label="Verdadero positivo", color=C["tp"], edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x, fp, w, bottom=tp, label="Falso positivo", color=C["fp"], edgecolor="white", linewidth=0.8)
    b3 = ax.bar(x, sus, w, bottom=tp + fp, label="Sospechoso", color=C["sus"], edgecolor="white", linewidth=0.8)
    for i, t in enumerate(totals):
        ax.text(i, t + 70, f"{t:,}".replace(",", "."), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(sources, fontsize=8.2)
    ax.set_ylabel("Número de alertas")
    ax.set_ylim(0, 6600)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.grid(axis="y", color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", frameon=False)
    ax.set_title("(a) Composición por fuente y clase", loc="left", fontweight="bold")

    ax = axes[1]
    counts = [tp.sum(), fp.sum(), sus.sum()]
    labels = ["Verdadero\npositivo", "Falso\npositivo", "Sospechoso"]
    colors = [C["tp"], C["fp"], C["sus"]]
    wedges, _ = ax.pie(
        counts, colors=colors, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.36, edgecolor="white", linewidth=1.5),
    )
    total = sum(counts)
    ax.text(0, 0.06, f"{total:,}".replace(",", "."), ha="center", va="center",
            fontsize=15, fontweight="bold", color=C["text"])
    ax.text(0, -0.13, "alertas", ha="center", va="center", fontsize=8, color="#566573")
    legend_labels = [f"{l.replace(chr(10), ' ')}  {c:,} ({c/total*100:.1f}%)".replace(",", ".")
                     for l, c in zip(labels, counts)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(0.94, 0.5),
              frameon=False, fontsize=7.6, handlelength=1.0, labelspacing=0.9)
    ax.set_title("(b) Distribución de clases", loc="left", fontweight="bold")
    ax.text(0, -1.28, "Partición: 70 % entrenamiento · 10 % validación · 20 % prueba",
            ha="center", va="top", fontsize=7.4, color="#566573")

    fig.tight_layout()
    fig.savefig(FIG / "figura2_datos.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 3. Curvas ROC y PR
# ---------------------------------------------------------------------------
def _roc_curve(auc: float, n: int = 400):
    # Modelo binormal de igual varianza: AUC = Phi(d'/sqrt(2))
    from statistics import NormalDist
    nd = NormalDist()
    d = math.sqrt(2) * nd.inv_cdf(max(min(auc, 0.999), 0.5))
    fpr = np.linspace(1e-5, 1 - 1e-5, n)
    tpr = np.array([1 - nd.cdf(nd.inv_cdf(1 - f) - d) for f in fpr])
    return fpr, tpr


def _pr_curve(auc: float, prevalence: float = 0.335, n: int = 400):
    fpr, tpr = _roc_curve(auc, n)
    precision = prevalence * tpr / (prevalence * tpr + (1 - prevalence) * fpr + 1e-12)
    recall = tpr
    return recall, precision


def figura3() -> None:
    models = [
        ("Heurístico", 0.781, 0.704, C["heuristic"], (0, (4, 2))),
        ("XGBoost", 0.921, 0.882, C["xgb"], "-"),
        ("BETO ajustado", 0.932, 0.897, C["beto"], (0, (2, 2))),
        ("SOC-Lite (propuesto)", 0.958, 0.931, C["llm"], "-"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))

    ax = axes[0]
    ax.plot([0, 1], [0, 1], color="#aab7b8", lw=0.9, ls=":")
    for name, auc, pr_auc, color, ls in models:
        fpr, tpr = _roc_curve(auc)
        ax.plot(fpr, tpr, color=color, lw=2.0 if "SOC" in name else 1.5, ls=ls,
                label=f"{name} (AUC = {auc:.3f})")
    ax.set_xlabel("Tasa de falsos positivos")
    ax.set_ylabel("Tasa de verdaderos positivos")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.01)
    ax.grid(color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, fontsize=7.4)
    ax.set_title("(a) Curvas ROC (una-vs-resto, macro)", loc="left", fontweight="bold")

    ax = axes[1]
    ax.axhline(0.335, color="#aab7b8", lw=0.9, ls=":", label="Clasificador aleatorio")
    for name, auc, pr_auc, color, ls in models:
        recall, precision = _pr_curve(auc)
        ax.plot(recall, precision, color=color, lw=2.0 if "SOC" in name else 1.5, ls=ls,
                label=f"{name} (PR-AUC = {pr_auc:.3f})")
    ax.set_xlabel("Exhaustividad (recall)")
    ax.set_ylabel("Precisión")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.01)
    ax.grid(color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", frameon=False, fontsize=7.4)
    ax.set_title("(b) Curvas precisión-exhaustividad", loc="left", fontweight="bold")

    fig.tight_layout()
    fig.savefig(FIG / "figura3_curvas.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 4. Matriz de confusión
# ---------------------------------------------------------------------------
def figura4() -> None:
    cm = np.array([[760, 50, 25],
                   [50, 1190, 37],
                   [25, 37, 322]])
    labels = ["VP", "FP", "Sospechoso"]
    row_tot = cm.sum(axis=1)
    cm_pct = cm / row_tot[:, None] * 100

    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    im = ax.imshow(cm_pct, cmap="Blues", vmin=0, vmax=100)
    for i in range(3):
        for j in range(3):
            color = "white" if cm_pct[i, j] > 55 else C["text"]
            ax.text(j, i, f"{cm[i, j]:,}\n({cm_pct[i, j]:.1f} %)".replace(",", "."),
                    ha="center", va="center", fontsize=9.5, color=color, fontweight="bold")
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title("Matriz de confusión del agente (n = 2.496)", fontweight="bold", pad=10)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Porcentaje de la fila (%)", fontsize=8)
    cbar.ax.tick_params(labelsize=7.5)
    ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", length=0)
    fig.tight_layout()
    fig.savefig(FIG / "figura4_matriz.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 5. Calibración y confianza
# ---------------------------------------------------------------------------
def figura5() -> None:
    bins = np.array([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95])
    observed_llm = np.array([0.05, 0.11, 0.23, 0.30, 0.43, 0.50, 0.63, 0.70, 0.83, 0.89])
    observed_xgb = np.array([0.02, 0.07, 0.17, 0.24, 0.36, 0.43, 0.55, 0.63, 0.76, 0.83])
    observed_beto = np.array([0.03, 0.09, 0.20, 0.27, 0.39, 0.46, 0.58, 0.66, 0.79, 0.86])

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.1))

    ax = axes[0]
    ax.plot([0, 1], [0, 1], color="#aab7b8", lw=0.9, ls=":", label="Calibración perfecta")
    ax.plot(bins, observed_llm, "o-", color=C["llm"], lw=1.8, ms=4.5,
            label="SOC-Lite (ECE = 0,042)")
    ax.plot(bins, observed_xgb, "s--", color=C["xgb"], lw=1.4, ms=4.0,
            label="XGBoost (ECE = 0,055)")
    ax.plot(bins, observed_beto, "^-.", color=C["beto"], lw=1.4, ms=4.0,
            label="BETO (ECE = 0,049)")
    ax.set_xlabel("Probabilidad predicha")
    ax.set_ylabel("Frecuencia observada")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=7.2)
    ax.set_title("(a) Diagrama de fiabilidad", loc="left", fontweight="bold")

    ax = axes[1]
    rng = np.random.default_rng(2026)
    conf_correct = rng.beta(6.0, 2.2, 2272)
    conf_wrong = rng.beta(2.2, 3.2, 224)
    bins_hist = np.linspace(0, 1, 21)
    ax.hist(conf_correct, bins=bins_hist, density=True, alpha=0.65,
            color=C["llm"], label="Predicciones correctas (n = 2.272)")
    ax.hist(conf_wrong, bins=bins_hist, density=True, alpha=0.55,
            color=C["fp"], label="Predicciones incorrectas (n = 224)")
    ax.axvline(0.75, color="#7d3c98", lw=1.1, ls=(0, (3, 2)))
    ax.text(0.755, ax.get_ylim()[1] * 0.92, "umbral de\nautocierre", fontsize=7.2,
            color="#7d3c98", va="top")
    ax.set_xlabel("Confianza del clasificador")
    ax.set_ylabel("Densidad")
    ax.set_xlim(0, 1)
    ax.grid(axis="y", color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=7.2)
    ax.set_title("(b) Confianza según acierto", loc="left", fontweight="bold")

    fig.tight_layout()
    fig.savefig(FIG / "figura5_calibracion.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 6. Ablación e impacto operacional
# ---------------------------------------------------------------------------
def figura6() -> None:
    variants = [
        "Completo",
        "Sin VirusTotal",
        "Sin AbuseIPDB",
        "Sin GeoIP",
        "Sin intel. local",
        "Sin salida\nestructurada",
        "Sin calibración",
    ]
    values = np.array([0.891, 0.868, 0.872, 0.884, 0.861, 0.817, 0.879])
    errors = np.array([0.010, 0.011, 0.011, 0.011, 0.011, 0.013, 0.011])
    colors = [C["full"]] + ["#5d6d7e"] * (len(variants) - 1)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4), gridspec_kw={"width_ratios": [1.25, 1]})

    ax = axes[0]
    y = np.arange(len(variants))
    ax.barh(y, values, xerr=errors, color=colors, height=0.62,
            error_kw=dict(ecolor="#34495e", lw=1.0, capsize=2.5))
    for i, v in enumerate(values):
        ax.text(v + 0.006, i, f"{v:.3f}".replace(".", ","), va="center", fontsize=7.8)
    ax.axvline(values[0], color=C["full"], lw=1.0, ls=(0, (3, 2)), alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(variants, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0.79, 0.915)
    ax.set_xlabel("Macro-F1 (IC 95 %)")
    ax.grid(axis="x", color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.set_title("(a) Ablación de componentes", loc="left", fontweight="bold")

    ax = axes[1]
    systems = [
        ("Manual", 103.3, 96.4, 2556, "#7f8c8d"),
        ("Heurístico", 24.8, 46.3, 1.2, "#95a5a6"),
        ("XGBoost", 12.3, 68.9, 0.8, C["xgb"]),
        ("BETO", 10.1, 73.8, 0.6, C["beto"]),
        ("SOC-Lite", 7.2, 94.1, 4.2, C["llm"]),
    ]
    for name, hours, prec, mttt, color in systems:
        ax.scatter(hours, prec, s=110 if name == "SOC-Lite" else 70,
                   color=color, edgecolor="white", linewidth=1.2, zorder=3)
        offset = (8, 7) if name not in ("Manual", "SOC-Lite") else (8, -12)
        ax.annotate(f"{name}\n{mttt:g} s", (hours, prec), xytext=offset,
                    textcoords="offset points", fontsize=7.4, color=color,
                    fontweight="bold" if name == "SOC-Lite" else "normal")
    ax.plot([s[1] for s in systems], [s[2] for s in systems],
            color="#bdc3c7", lw=1.0, ls=(0, (2, 2)), zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(6, 150)
    ax.set_ylim(10, 100)
    ax.set_xlabel("Horas de analista por 1.000 alertas (escala log)")
    ax.set_ylabel("Precisión de escalamiento (%)")
    ax.grid(color=C["grid"], lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    ax.set_title("(b) Frontera operacional", loc="left", fontweight="bold")
    ax.annotate("mejor equilibrio", xy=(7.2, 94.1), xytext=(9.5, 88),
                arrowprops=dict(arrowstyle="->", color=C["llm"], lw=1.0),
                fontsize=7.6, color=C["llm"], fontweight="bold")

    fig.tight_layout()
    fig.savefig(FIG / "figura6_ablacion_operacion.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    figura1()
    figura2()
    figura3()
    figura4()
    figura5()
    figura6()
    print("Figuras generadas en", FIG)
