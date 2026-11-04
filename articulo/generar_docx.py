#!/usr/bin/env python3
"""Genera una versión DOCX del manuscrito SOC-Lite a partir del Markdown.

El conversor está adaptado a la estructura del artículo: portada, secciones,
tablas de tuberías, figuras, listas, bloques de código y referencias con sangría
francesa. No pretende ser un conversor Markdown general.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
MD_PATH = BASE / "Clasificador_automatico_SOC-Lite.md"
OUT_PATH = BASE / "Clasificador_automatico_SOC-Lite.docx"

AZUL = RGBColor(0x1F, 0x3A, 0x5F)
GRIS = RGBColor(0x55, 0x55, 0x55)
FUENTE = "Times New Roman"
MONO = "Consolas"


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
def latex_a_texto(texto: str) -> str:
    """Convierte el LaTeX inline del manuscrito en texto legible."""
    texto = texto.replace("$", "")
    texto = texto.replace("{,}", ",")
    reemplazos = {
        r"\times": "×",
        r"\chi": "χ",
        r"\gamma": "γ",
        r"\eta": "η",
        r"\alpha": "α",
        r"\le": "≤",
        r"\ge": "≥",
        r"\approx": "≈",
        r"\pm": "±",
    }
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    texto = re.sub(r"\\text\{([^}]*)\}", r"\1", texto)
    superindices = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
    texto = re.sub(r"\^\{([^}]*)\}", lambda m: m.group(1).translate(superindices), texto)
    texto = re.sub(r"\^(\d)", lambda m: m.group(1).translate(superindices), texto)
    texto = texto.replace("\\", "")
    return texto


def agregar_runs(parrafo, texto: str, tamano: float | None = None,
                 color: RGBColor | None = None, negrita: bool = False,
                 cursiva: bool = False) -> None:
    """Agrega texto con formato inline (**negrita**, *cursiva*, `código`)."""
    texto = latex_a_texto(texto)
    patron = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)")
    for fragmento in patron.split(texto):
        if not fragmento:
            continue
        bold = negrita
        italic = cursiva
        code = False
        if fragmento.startswith("**") and fragmento.endswith("**") and len(fragmento) > 4:
            fragmento = fragmento[2:-2]
            bold = True
        elif fragmento.startswith("*") and fragmento.endswith("*") and len(fragmento) > 2:
            fragmento = fragmento[1:-1]
            italic = True
        elif fragmento.startswith("`") and fragmento.endswith("`") and len(fragmento) > 2:
            fragmento = fragmento[1:-1]
            code = True
        for indice, parte in enumerate(fragmento.split("\n")):
            if indice:
                parrafo.add_run().add_break()
            run = parrafo.add_run(parte)
            run.bold = bold
            run.italic = italic
            if code:
                run.font.name = MONO
                run.font.size = Pt((tamano or 11) - 1)
            else:
                run.font.name = FUENTE
                if tamano:
                    run.font.size = Pt(tamano)
            if color is not None:
                run.font.color.rgb = color


def configurar_parrafo(parrafo, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
                       espacio_antes: float = 0, espacio_despues: float = 6,
                       interlineado: float = 1.15, sangria: float | None = None,
                       sangria_francesa: float | None = None) -> None:
    pf = parrafo.paragraph_format
    pf.alignment = alineacion
    pf.space_before = Pt(espacio_antes)
    pf.space_after = Pt(espacio_despues)
    pf.line_spacing = interlineado
    if sangria is not None:
        pf.first_line_indent = Cm(sangria)
    if sangria_francesa is not None:
        pf.left_indent = Cm(sangria_francesa)
        pf.first_line_indent = Cm(-sangria_francesa)
    pf.widow_control = True


def sombrear_celda(celda, relleno: str) -> None:
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), relleno)
    tc_pr.append(shd)


def repetir_encabezado(fila) -> None:
    tr_pr = fila._tr.get_or_add_trPr()
    cabecera = OxmlElement("w:tblHeader")
    cabecera.set(qn("w:val"), "true")
    tr_pr.append(cabecera)


def agregar_campo(parrafo, instruccion: str) -> None:
    run = parrafo.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    texto = OxmlElement("w:instrText")
    texto.set(qn("xml:space"), "preserve")
    texto.text = instruccion
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run._r.append(inicio)
    run._r.append(texto)
    run._r.append(fin)


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------
def configurar_documento(doc: Document) -> None:
    seccion = doc.sections[0]
    seccion.page_width = Cm(21.0)
    seccion.page_height = Cm(29.7)
    seccion.top_margin = Cm(2.2)
    seccion.bottom_margin = Cm(2.2)
    seccion.left_margin = Cm(2.0)
    seccion.right_margin = Cm(2.0)
    seccion.header_distance = Cm(1.0)
    seccion.footer_distance = Cm(1.0)

    estilos = doc.styles
    normal = estilos["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for nombre, tamano, color in (("Heading 1", 14, AZUL), ("Heading 2", 12, AZUL),
                                  ("Heading 3", 11.5, AZUL)):
        estilo = estilos[nombre]
        estilo.font.name = FUENTE
        estilo.font.size = Pt(tamano)
        estilo.font.bold = True
        estilo.font.color.rgb = color
        estilo.paragraph_format.keep_with_next = True
        estilo.paragraph_format.space_before = Pt(12 if nombre != "Heading 3" else 8)
        estilo.paragraph_format.space_after = Pt(5)

    # Encabezado y pie
    encabezado = seccion.header.paragraphs[0]
    encabezado.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = encabezado.add_run("Clasificador automático de alertas SOC para PYMES")
    run.font.name = FUENTE
    run.font.size = Pt(8.5)
    run.font.color.rgb = GRIS
    run.italic = True

    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = pie.add_run("Página ")
    run.font.name = FUENTE
    run.font.size = Pt(9)
    agregar_campo(pie, "PAGE")
    run = pie.add_run(" de ")
    run.font.name = FUENTE
    run.font.size = Pt(9)
    agregar_campo(pie, "NUMPAGES")


def portada(doc: Document, lineas: list[str]) -> None:
    """Compone la portada a partir del bloque inicial del Markdown."""
    for _ in range(3):
        doc.add_paragraph()

    titulo = next((l[2:].strip() for l in lineas if l.startswith("# ")), "")
    subtitulo = next((l.strip().strip("*") for l in lineas
                      if l.strip().startswith("**") and l.strip().endswith("**")
                      and "Automatic SOC" in l), "")
    autores = next((l.strip() for l in lineas
                    if l.strip().startswith("[Author 1]")), "")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    agregar_runs(p, titulo, tamano=20, color=AZUL, negrita=True)
    p.paragraph_format.space_after = Pt(10)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    agregar_runs(p, subtitulo, tamano=12.5, color=GRIS, cursiva=True)
    p.paragraph_format.space_after = Pt(18)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    agregar_runs(p, autores, tamano=11.5, negrita=True)
    p.paragraph_format.space_after = Pt(10)

    for linea in lineas:
        texto = linea.strip()
        if texto.startswith("^"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            agregar_runs(p, texto.lstrip("^"), tamano=9.5, color=GRIS)
            p.paragraph_format.space_after = Pt(2)
        elif texto.startswith("**Autor de correspondencia:**") or \
                texto.startswith("**Recibido:**") or texto.startswith("**Cómo citar:**"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            agregar_runs(p, texto, tamano=9)
            p.paragraph_format.space_after = Pt(4)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Manuscrito de investigación · Resultados de un escenario de evaluación simulado")
    run.font.name = FUENTE
    run.font.size = Pt(9)
    run.italic = True
    run.font.color.rgb = GRIS
    p.paragraph_format.space_before = Pt(28)

    doc.add_page_break()


def longitud_visible(texto: str) -> int:
    texto = re.sub(r"\*\*|\*|`", "", texto)
    return max(3, min(42, len(texto)))


def agregar_tabla(doc: Document, filas: list[list[str]]) -> None:
    if not filas:
        return
    ncols = max(len(f) for f in filas)
    filas = [f + [""] * (ncols - len(f)) for f in filas]
    tabla = doc.add_table(rows=len(filas), cols=ncols)
    tabla.style = "Table Grid"
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False
    tamano = 6.8 if ncols >= 9 else (7.4 if ncols >= 7 else 8.3)

    # Anchos proporcionales al contenido, con un mínimo legible.
    pesos = []
    for j in range(ncols):
        largo = max(longitud_visible(f[j]) for f in filas)
        pesos.append(max(4.0, largo) ** 0.55)
    disponible = 17.0  # cm útiles con márgenes de 2,0 cm
    anchos = [disponible * p / sum(pesos) for p in pesos]
    anchos = [max(1.0, a) for a in anchos]
    factor = disponible / sum(anchos)
    anchos = [a * factor for a in anchos]
    for j, ancho in enumerate(anchos):
        tabla.columns[j].width = Cm(ancho)

    for i, fila in enumerate(filas):
        for j, celda_texto in enumerate(fila):
            celda = tabla.cell(i, j)
            celda.width = Cm(anchos[j])
            celda.text = ""
            p = celda.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            # Los intervalos de confianza largos se parten de forma deliberada.
            celda_texto = re.sub(r"^([\d,]+) \[(.+)\]$", r"\1\n[\2]", celda_texto)
            agregar_runs(p, celda_texto, tamano=tamano,
                         negrita=(i == 0))
            if i == 0:
                sombrear_celda(celda, "E8EEF5")
        tr_pr = tabla.rows[i]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
    repetir_encabezado(tabla.rows[0])

    # Pequeña separación posterior
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0


def agregar_lista(doc: Document, items: list[str], numerada: bool) -> None:
    for indice, item in enumerate(items, start=1):
        p = doc.add_paragraph()
        configurar_parrafo(p, espacio_despues=3, interlineado=1.1,
                           sangria_francesa=0.7)
        prefijo = f"{indice}. " if numerada else "• "
        run = p.add_run(prefijo)
        run.font.name = FUENTE
        run.font.size = Pt(11)
        agregar_runs(p, item, tamano=11)


def agregar_codigo(doc: Document, lineas: list[str]) -> None:
    for linea in lineas:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(linea if linea else " ")
        run.font.name = MONO
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)


def es_inicio_especial(linea: str) -> bool:
    return (not linea.strip() or linea.startswith(("#", "|", "![", "```", "---"))
            or re.match(r"^[-*] ", linea) is not None
            or re.match(r"^\d+\.\s", linea) is not None)


def convertir() -> None:
    texto = MD_PATH.read_text(encoding="utf-8")
    lineas = texto.splitlines()

    doc = Document()
    configurar_documento(doc)
    doc.core_properties.title = ("Clasificador automático de alertas SOC para PYMES "
                                 "basado en un agente LLM local y enriquecimiento contextual")
    doc.core_properties.subject = "Triaje automático de alertas SOC; LLM local; PYMES"
    doc.core_properties.author = "[Autor 1]; [Autor 2]"
    doc.core_properties.keywords = ("triaje de alertas; SOC; LLM; agentes locales; "
                                    "calibración; PYMES")

    # Portada: desde el inicio hasta el primer separador horizontal.
    fin_portada = next((i for i, l in enumerate(lineas) if l.strip() == "---"), 0)
    portada(doc, lineas[:fin_portada])
    i = fin_portada + 1

    en_referencias = False
    while i < len(lineas):
        linea = lineas[i].rstrip()

        if not linea.strip() or linea.strip() == "---":
            i += 1
            continue

        # Bloques de código
        if linea.startswith("```"):
            i += 1
            bloque = []
            while i < len(lineas) and not lineas[i].startswith("```"):
                bloque.append(lineas[i].rstrip())
                i += 1
            i += 1
            agregar_codigo(doc, bloque)
            continue

        # Imágenes
        if linea.startswith("!["):
            match = re.match(r"!\[[^\]]*\]\(([^)]+)\)", linea)
            if match:
                ruta = (BASE / match.group(1)).resolve()
                if ruta.exists():
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.keep_with_next = True
                    p.add_run().add_picture(str(ruta), width=Cm(15.2))
            i += 1
            continue

        # Tablas
        if linea.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                cruda = lineas[i].strip().strip("|")
                celdas = [c.strip() for c in cruda.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in celdas if c):
                    filas.append(celdas)
                i += 1
            agregar_tabla(doc, filas)
            continue

        # Títulos
        if linea.startswith("### "):
            doc.add_heading(linea[4:].strip(), level=2)
            i += 1
            continue
        if linea.startswith("## "):
            titulo = linea[3:].strip()
            doc.add_heading(titulo, level=1)
            en_referencias = titulo.lower().startswith("referencias")
            i += 1
            continue

        # Listas
        if re.match(r"^[-*] ", linea):
            items = []
            while i < len(lineas) and re.match(r"^[-*] ", lineas[i]):
                items.append(lineas[i][2:].strip())
                i += 1
            agregar_lista(doc, items, numerada=False)
            continue
        if re.match(r"^\d+\.\s", linea):
            items = []
            while i < len(lineas) and re.match(r"^\d+\.\s", lineas[i]):
                items.append(re.sub(r"^\d+\.\s", "", lineas[i]).strip())
                i += 1
            agregar_lista(doc, items, numerada=True)
            continue

        # Párrafo (puede ocupar varias líneas)
        parrafo_lineas = [linea.strip()]
        i += 1
        while i < len(lineas) and not es_inicio_especial(lineas[i]):
            parrafo_lineas.append(lineas[i].strip())
            i += 1
        parrafo_texto = " ".join(parrafo_lineas)

        p = doc.add_paragraph()
        if re.match(r"^\*\*(Tabla|Figura)\s+\d+\.\*\*", parrafo_texto):
            configurar_parrafo(p, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
                               espacio_antes=2, espacio_despues=5,
                               interlineado=1.0)
            agregar_runs(p, parrafo_texto, tamano=9, cursiva=False)
            p.paragraph_format.keep_with_next = parrafo_texto.startswith("**Tabla")
        elif en_referencias:
            configurar_parrafo(p, alineacion=WD_ALIGN_PARAGRAPH.LEFT,
                               espacio_despues=4, interlineado=1.0,
                               sangria_francesa=0.8)
            agregar_runs(p, parrafo_texto, tamano=9.5)
        elif parrafo_texto.startswith("**Palabras clave:**") or \
                parrafo_texto.startswith("**Keywords:**"):
            configurar_parrafo(p, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
                               espacio_despues=5, interlineado=1.1)
            agregar_runs(p, parrafo_texto, tamano=10)
        elif parrafo_texto.startswith("**Contexto.**") or \
                parrafo_texto.startswith("**Objetivo.**") or \
                parrafo_texto.startswith("**Método.**") or \
                parrafo_texto.startswith("**Resultados.**") or \
                parrafo_texto.startswith("**Conclusiones.**"):
            configurar_parrafo(p, espacio_despues=5, interlineado=1.12)
            agregar_runs(p, parrafo_texto, tamano=10.5)
        else:
            configurar_parrafo(p)
            agregar_runs(p, parrafo_texto, tamano=11)

    doc.save(OUT_PATH)
    print(f"DOCX generado: {OUT_PATH}")


if __name__ == "__main__":
    convertir()
