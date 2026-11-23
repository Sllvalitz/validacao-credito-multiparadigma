# Responsavel: Anderson
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from python.dominio import ErroValidacao
from python.integracao import criar_modulo_lisp, criar_modulo_prolog
from python.orquestrador import Orquestrador


def detalhe(resultado: dict) -> str:
    if resultado["precificacao"]:
        p = resultado["precificacao"]
        return (f"risco {p['classificacao_risco']}, aprovado R$ {p['valor_aprovado']:.2f}, "
                f"parcela R$ {p['valor_parcela_final']:.2f}")
    return ", ".join(resultado["impedimentos"]) or (resultado["erro"] or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validacao de credito (Python + Prolog + Lisp)")
    parser.add_argument("--entrada", type=Path, default=Path("data/propostas.json"))
    parser.add_argument("--saida", type=Path, default=Path("saida/resultados.json"))
    args = parser.parse_args()

    orquestrador = Orquestrador(criar_modulo_prolog(), criar_modulo_lisp())
    # so falhas no arquivo inteiro (inexistente, JSON invalido) chegam aqui;
    # erros de uma proposta isolada viram status no resultado
    try:
        resultados = orquestrador.processar_arquivo(args.entrada)
    except ErroValidacao as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    for resultado in resultados:
        print(f"{resultado['id']:<10} {resultado['status']:<24} {detalhe(resultado)}")
    print("\nResumo:", dict(Counter(r["status"] for r in resultados)))

    # saida/ nao e versionada, entao a pasta e criada na primeira execucao
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultados gravados em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
