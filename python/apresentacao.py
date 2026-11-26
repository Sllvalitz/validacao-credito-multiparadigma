# Responsavel: Anderson da Silva Pinto
from __future__ import annotations

import html
from typing import Any

# status -> (icone, cor no terminal, cor do texto no HTML, cor de fundo no HTML, rotulo)
ESTILOS = {
    "APROVADO": ("✔", "verde", "#1b7f3b", "#e6f4ea", "Aprovado"),
    "APROVADO_COM_CONDICOES": ("▲", "amarelo", "#8a6100", "#fff4d6", "Aprovado com condições"),
    "REPROVADO": ("✘", "vermelho", "#b3261e", "#fde7e6", "Reprovado"),
    "ERRO_VALIDACAO": ("!", "magenta", "#7b2d8e", "#f3e5f7", "Erro de validação"),
    "ERRO_INTEGRACAO": ("‼", "magenta", "#7b2d8e", "#f3e5f7", "Erro de integração"),
}
ESTILO_PADRAO = ("?", "cinza", "#555555", "#eeeeee", "Desconhecido")
CODIGOS_ANSI = {"verde": "32", "amarelo": "33", "vermelho": "31", "magenta": "35",
                "ciano": "36", "cinza": "90"}
LARGURA_BARRA = 24
LARGURA_CAIXA = 64


def estilo(status: str) -> tuple[str, str, str, str, str]:
    return ESTILOS.get(status, ESTILO_PADRAO)


# todas as funcoes devolvem texto em vez de imprimir: assim podem ser testadas sem terminal
def colorir(texto: str, cor: str, ativo: bool) -> str:
    return f"\033[{CODIGOS_ANSI[cor]}m{texto}\033[0m" if ativo else texto


def negrito(texto: str, ativo: bool) -> str:
    return f"\033[1m{texto}\033[0m" if ativo else texto


# formato brasileiro (R$ 4.200,00): o formato do Python usa virgula para milhar e ponto para decimal
def moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def percentual(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


def barra(parte: float, total: float, largura: int = LARGURA_BARRA) -> str:
    preenchido = round(parte / total * largura) if total > 0 else 0
    return "█" * preenchido + "░" * (largura - preenchido)


def contar_por_status(resultados: list[dict[str, Any]]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for resultado in resultados:
        contagem[resultado["status"]] = contagem.get(resultado["status"], 0) + 1
    return contagem


def cabecalho(colorido: bool) -> str:
    linhas = ["VALIDAÇÃO DE CRÉDITO  ·  Python + Prolog + Lisp",
              "Python orquestra  ·  Prolog decide  ·  Lisp precifica"]
    corpo = [f"║ {linha:<{LARGURA_CAIXA - 4}} ║" for linha in linhas]
    caixa = ["╔" + "═" * (LARGURA_CAIXA - 2) + "╗", corpo[0],
             "╠" + "═" * (LARGURA_CAIXA - 2) + "╣", corpo[1],
             "╚" + "═" * (LARGURA_CAIXA - 2) + "╝"]
    return colorir("\n".join(caixa), "ciano", colorido)


def detalhe_da_linha(resultado: dict[str, Any]) -> str:
    preco = resultado["precificacao"]
    if preco:
        return f"risco {preco['classificacao_risco']} · taxa {percentual(preco['taxa_juros_mensal'] * 100)} a.m."
    return ", ".join(resultado["impedimentos"]) or (resultado["erro"] or "")


def tabela(resultados: list[dict[str, Any]], colorido: bool) -> str:
    titulo = f"{'ID':<9} {'STATUS':<24}   {'APROVADO':>14} {'PARCELA':>13}   DETALHE"
    linhas = [negrito(titulo, colorido), "─" * 96]
    for resultado in resultados:
        icone, cor, _, _, rotulo = estilo(resultado["status"])
        preco = resultado["precificacao"]
        aprovado = moeda(preco["valor_aprovado"]) if preco else "-"
        parcela = moeda(preco["valor_parcela_final"]) if preco else "-"
        status = colorir(f"{icone} {rotulo:<22}", cor, colorido)
        linhas.append(f"{resultado['id']:<9} {status}   {aprovado:>14} {parcela:>13}   {detalhe_da_linha(resultado)}")
    return "\n".join(linhas)


def resumo(resultados: list[dict[str, Any]], colorido: bool) -> str:
    total = len(resultados)
    linhas = [negrito(f"RESUMO  ({total} propostas)", colorido)]
    if total == 0:
        return linhas[0] + "\n  nenhuma proposta processada"
    contagem = contar_por_status(resultados)
    ordem = list(ESTILOS) + [s for s in contagem if s not in ESTILOS]
    for status in ordem:
        quantidade = contagem.get(status, 0)
        icone, cor, _, _, rotulo = estilo(status)
        grafico = colorir(barra(quantidade, total), cor, colorido)
        linhas.append(f"  {colorir(icone, cor, colorido)} {rotulo:<24} {quantidade:>3}  {grafico}  {quantidade / total:>4.0%}")
    return "\n".join(linhas)


def ranking(maiores: list[dict[str, Any]], colorido: bool) -> str:
    linhas = [negrito("MAIORES VALORES APROVADOS  (ordenados pelo merge sort da equipe)", colorido)]
    if not maiores:
        return linhas[0] + "\n  nenhuma proposta aprovada"
    teto = max(item["precificacao"]["valor_aprovado"] for item in maiores)
    for posicao, item in enumerate(maiores, start=1):
        valor = item["precificacao"]["valor_aprovado"]
        grafico = colorir(barra(valor, teto), "verde", colorido)
        linhas.append(f"  {posicao}. {item['id']:<9} {moeda(valor):>14}  {grafico}")
    return "\n".join(linhas)


def _etapa(numero: int, nome: str, paradigma: str, tarefa: str, colorido: bool) -> str:
    titulo = f"{numero}  {nome:<7} ({paradigma})"
    return f"{negrito(titulo, colorido)}  {tarefa}"


def fluxo(resultado: dict[str, Any], rastro: dict[str, Any], colorido: bool) -> str:
    icone, cor, _, _, rotulo = estilo(resultado["status"])
    linhas = [f"{negrito(resultado['id'], colorido)}  {colorir(f'{icone} {rotulo}', cor, colorido)}", ""]

    linhas.append(_etapa(1, "PYTHON", "orientado a objetos", "valida os dados e calcula os indicadores", colorido))
    indicadores = rastro.get("indicadores")
    if indicadores:
        linhas.append(f"     parcela base {moeda(indicadores['parcela_base'])} · "
                      f"comprometimento {percentual(indicadores['comprometimento_percentual'], 2)} da renda")
    else:
        linhas.append(f"     {colorir(resultado['erro'] or 'sem detalhes', 'magenta', colorido)}")

    linhas += ["", _etapa(2, "PROLOG", "lógico", "verifica as regras de elegibilidade", colorido)]
    parecer = rastro.get("parecer")
    if parecer:
        for regra in parecer["regras_satisfeitas"]:
            linhas.append(f"     {colorir('✔', 'verde', colorido)} {regra}")
        for impedimento in parecer["impedimentos"]:
            linhas.append(f"     {colorir('✘', 'vermelho', colorido)} {impedimento}")
        veredito = "ELEGÍVEL" if parecer["elegivel"] else "NÃO ELEGÍVEL"
        linhas.append(f"     parecer: {negrito(veredito, colorido)}")
    else:
        linhas.append("     não executado (os dados não passaram na validação)")

    linhas += ["", _etapa(3, "LISP", "funcional", "classifica o risco e calcula os valores", colorido)]
    preco = rastro.get("preco")
    if preco:
        linhas.append(f"     risco {preco['classificacao_risco']} · taxa {percentual(preco['taxa_juros_mensal'] * 100)} a.m.")
        linhas.append(f"     limite {moeda(preco['limite_calculado'])} · aprovado {moeda(preco['valor_aprovado'])} · "
                      f"parcela {moeda(preco['valor_parcela_final'])}")
    elif parecer:
        linhas.append("     não executado (reprovado pelo Prolog)")
    else:
        linhas.append("     não executado")
    return "\n".join(linhas)


_CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f4f6f9;color:#1d2433}
main{max-width:1080px;margin:0 auto;padding:32px 20px}
h1{margin:0 0 4px;font-size:28px}h2{margin:36px 0 12px;font-size:18px}
.sub{margin:0;color:#5b667a}
.cards{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.card{flex:1 1 170px;border-radius:10px;padding:14px 16px;border:1px solid #d9deea}
.card b{display:block;font-size:30px}.card span{font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:14px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #edf0f6}
th{background:#1f3a5f;color:#fff;font-weight:600}td.num{text-align:right;white-space:nowrap}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.rank{display:flex;align-items:center;gap:12px;margin:6px 0}
.rank .barra{height:14px;border-radius:7px;background:#1b7f3b}
footer{margin-top:32px;font-size:12px;color:#6b7589}
"""


def _selo(status: str) -> str:
    icone, _, cor_texto, cor_fundo, rotulo = estilo(status)
    return (f'<span class="badge" style="color:{cor_texto};background:{cor_fundo}">'
            f'{html.escape(icone)} {html.escape(rotulo)}</span>')


def pagina_html(resultados: list[dict[str, Any]], maiores: list[dict[str, Any]]) -> str:
    total = len(resultados)
    contagem = contar_por_status(resultados)
    cartoes = []
    for status in list(ESTILOS):
        _, _, cor_texto, cor_fundo, rotulo = estilo(status)
        quantidade = contagem.get(status, 0)
        porcentagem = percentual(quantidade / total * 100, 0) if total else "0%"
        cartoes.append(f'<div class="card" style="background:{cor_fundo};color:{cor_texto}">'
                       f'<b>{quantidade}</b><span>{html.escape(rotulo)} · {porcentagem}</span></div>')

    linhas = []
    for resultado in resultados:
        preco = resultado["precificacao"]
        aprovado = moeda(preco["valor_aprovado"]) if preco else "-"
        parcela = moeda(preco["valor_parcela_final"]) if preco else "-"
        linhas.append(f"<tr><td>{html.escape(resultado['id'])}</td><td>{_selo(resultado['status'])}</td>"
                      f'<td class="num">{aprovado}</td><td class="num">{parcela}</td>'
                      f"<td>{html.escape(detalhe_da_linha(resultado))}</td></tr>")

    teto = max((item["precificacao"]["valor_aprovado"] for item in maiores), default=0)
    posicoes = []
    for posicao, item in enumerate(maiores, start=1):
        valor = item["precificacao"]["valor_aprovado"]
        largura = round(valor / teto * 100) if teto else 0
        posicoes.append(f'<div class="rank"><span>{posicao}. {html.escape(item["id"])}</span>'
                        f'<div class="barra" style="width:{largura}%;min-width:4px"></div>'
                        f"<span>{moeda(valor)}</span></div>")

    return ("<!DOCTYPE html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>Validação de Crédito</title><style>{_CSS}</style></head><body><main>"
            "<h1>Validação de Crédito</h1>"
            '<p class="sub">Python (orientado a objetos) · SWI-Prolog (lógico) · Common Lisp (funcional)</p>'
            f'<div class="cards">{"".join(cartoes)}</div>'
            f"<h2>Propostas ({total})</h2>"
            "<table><tr><th>ID</th><th>Status</th><th>Aprovado</th><th>Parcela</th><th>Detalhe</th></tr>"
            f'{"".join(linhas)}</table>'
            "<h2>Maiores valores aprovados</h2>"
            f'{"".join(posicoes) or "<p>Nenhuma proposta aprovada.</p>"}'
            "<footer>Gerado por main.py · dados fictícios, fins exclusivamente acadêmicos</footer>"
            "</main></body></html>")
