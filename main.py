# Responsavel: Anderson da Silva Pinto
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from python import apresentacao
from python.dominio import ErroValidacao, ordenar_aprovadas_por_valor
from python.integracao import criar_modulo_lisp, criar_modulo_prolog
from python.orquestrador import Orquestrador

QUANTIDADE_NO_RANKING = 5


def preparar_terminal() -> None:
    # o console do Windows precisa de UTF-8 para os simbolos e de uma chamada ao sistema para ativar as cores ANSI
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        os.system("")


def usar_cores(sem_cor: bool) -> bool:
    # cores so em terminal interativo; NO_COLOR e a convencao para desligar
    return not sem_cor and sys.stdout.isatty() and "NO_COLOR" not in os.environ


def mostrar_detalhe(orquestrador: Orquestrador, caminho: Path, id_proposta: str, colorido: bool) -> int:
    registros = orquestrador.carregar_registros(caminho)
    alvo = next((r for r in registros if isinstance(r, dict) and r.get("id") == id_proposta), None)
    if alvo is None:
        print(f"Erro: proposta {id_proposta} nao encontrada em {caminho}", file=sys.stderr)
        return 1
    rastro: dict = {}
    resultado = orquestrador.analisar(alvo, rastro).para_dict()
    print(apresentacao.fluxo(resultado, rastro, colorido))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validacao de credito (Python + Prolog + Lisp)")
    parser.add_argument("--entrada", type=Path, default=Path("data/propostas.json"))
    parser.add_argument("--saida", type=Path, default=Path("saida/resultados.json"))
    parser.add_argument("--html", type=Path, default=Path("saida/relatorio.html"))
    parser.add_argument("--detalhe", metavar="ID", help="mostra o caminho de uma proposta pelos tres modulos")
    parser.add_argument("--sem-cor", action="store_true", help="desliga as cores do terminal")
    args = parser.parse_args()

    preparar_terminal()
    colorido = usar_cores(args.sem_cor)
    orquestrador = Orquestrador(criar_modulo_prolog(), criar_modulo_lisp())
    # so falhas no arquivo inteiro (inexistente, JSON invalido) chegam aqui;
    # erros de uma proposta isolada viram status no resultado
    try:
        if args.detalhe:
            return mostrar_detalhe(orquestrador, args.entrada, args.detalhe, colorido)
        analises = orquestrador.analisar_arquivo(args.entrada)
    except ErroValidacao as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    resultados = [analise.para_dict() for analise in analises]
    # o merge sort devolve do menor para o maior; o ranking mostra do maior para o menor
    maiores = [a.para_dict() for a in reversed(ordenar_aprovadas_por_valor(analises))][:QUANTIDADE_NO_RANKING]

    print(apresentacao.cabecalho(colorido), "", sep="\n")
    print(apresentacao.tabela(resultados, colorido), "", sep="\n")
    print(apresentacao.resumo(resultados, colorido), "", sep="\n")
    print(apresentacao.ranking(maiores, colorido), "", sep="\n")

    # saida/ nao e versionada, entao a pasta e criada na primeira execucao
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(apresentacao.pagina_html(resultados, maiores), encoding="utf-8")
    print(f"Arquivos gerados:\n  {args.saida}  (dados)\n  {args.html}  (relatorio visual, abra no navegador)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
