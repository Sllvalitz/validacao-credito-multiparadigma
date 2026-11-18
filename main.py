# Responsavel: Anderson
"""Ponto de entrada unico: roda Python + Prolog + Lisp sobre o dataset e mostra o resultado.

Uso: python main.py [--entrada data/propostas.json] [--saida saida/resultados.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from python.dominio import ErroValidacao
from python.integracao import criar_modulo_lisp, criar_modulo_prolog
from python.orquestrador import Orquestrador


def detalhe(r: dict) -> str:
    if r["precificacao"]:
        p = r["precificacao"]
        return (f"risco {p['classificacao_risco']}, aprovado R$ {p['valor_aprovado']:.2f}, "
                f"parcela R$ {p['valor_parcela_final']:.2f}")
    return ", ".join(r["impedimentos"]) or (r["erro"] or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validacao de credito (Python + Prolog + Lisp)")
    ap.add_argument("--entrada", type=Path, default=Path("data/propostas.json"))
    ap.add_argument("--saida", type=Path, default=Path("saida/resultados.json"))
    args = ap.parse_args()

    orquestrador = Orquestrador(criar_modulo_prolog(), criar_modulo_lisp())
    try:
        resultados = orquestrador.processar_arquivo(args.entrada)
    except ErroValidacao as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    for r in resultados:
        print(f"{r['id']:<10} {r['status']:<24} {detalhe(r)}")
    print("\nResumo:", dict(Counter(r["status"] for r in resultados)))

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultados gravados em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
