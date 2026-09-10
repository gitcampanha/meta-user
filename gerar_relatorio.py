import json
import os
import glob
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PASTA_DADOS = os.environ.get("PASTA_DADOS", "dados")
ARQUIVO_SAIDA = "relatorio.pdf"


def arquivo_mais_recente():
    arquivos = glob.glob(os.path.join(PASTA_DADOS, "*.json"))
    if not arquivos:
        raise SystemExit(f"Nenhum .json encontrado em '{PASTA_DADOS}/'")
    return max(arquivos, key=os.path.getmtime)


def carregar_dados(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        bruto = json.load(f)
    if isinstance(bruto, dict) and "data" in bruto:
        return bruto["data"]
    if isinstance(bruto, list):
        return bruto
    return [bruto]


def fmt_moeda(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "-"


def fmt_int(v):
    try:
        return f"{int(float(v)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def montar_pdf(linhas, origem):
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("Titulo", parent=styles["Title"], fontSize=16)
    sub = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9,
                         textColor=colors.grey)

    doc = SimpleDocTemplate(ARQUIVO_SAIDA, pagesize=A4,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    hoje = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph("Relatório de Tráfego Pago — Campanha 7075", titulo))
    story.append(Paragraph(f"Gerado em {hoje} • Fonte: {os.path.basename(origem)}", sub))
    story.append(Spacer(1, 14))

    total_gasto = sum(float(l.get("spend", 0) or 0) for l in linhas)
    total_impr = sum(float(l.get("impressions", 0) or 0) for l in linhas)
    total_cliques = sum(float(l.get("clicks", 0) or 0) for l in linhas)
    ctr = (total_cliques / total_impr * 100) if total_impr else 0
    cpc = (total_gasto / total_cliques) if total_cliques else 0

    resumo = [
        ["Investimento", "Impressões", "Cliques", "CTR", "CPC médio"],
        [fmt_moeda(total_gasto), fmt_int(total_impr), fmt_int(total_cliques),
         f"{ctr:.2f}%", fmt_moeda(cpc)],
    ]
    t = Table(resumo, colWidths=[3.4 * cm] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c6e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Detalhamento", styles["Heading2"]))
    cab = ["Campanha", "Gasto", "Impressões", "Cliques", "CTR"]
    corpo = [cab]
    for l in linhas:
        nome = (l.get("campaign_name") or l.get("adset_name")
                or l.get("ad_name") or l.get("account_name") or "—")
        imp = float(l.get("impressions", 0) or 0)
        clq = float(l.get("clicks", 0) or 0)
        corpo.append([
            Paragraph(str(nome), styles["Normal"]),
            fmt_moeda(l.get("spend")),
            fmt_int(imp),
            fmt_int(clq),
            f"{(clq / imp * 100):.2f}%" if imp else "-",
        ])
    td = Table(corpo, colWidths=[7 * cm, 2.8 * cm, 2.8 * cm, 2.2 * cm, 2 * cm],
               repeatRows=1)
    td.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf5")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
    ]))
    story.append(td)

    doc.build(story)
    print(f"OK: {ARQUIVO_SAIDA} gerado a partir de {origem} ({len(linhas)} linhas)")


if __name__ == "__main__":
    origem = arquivo_mais_recente()
    montar_pdf(carregar_dados(origem), origem)
