# Responsavel: Robson
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

SEMENTE = 2026
QUANTIDADE_ALEATORIA = 30
CAMINHO_SAIDA = Path(__file__).resolve().parent / "propostas.json"
HISTORICOS = ("bom", "regular", "ruim")
PRAZOS = (6, 12)


def registro(**alteracoes: Any) -> dict[str, Any]:
    base = {
        "idade": 30,
        "renda_mensal": 4000.0,
        "historico_credito": "bom",
        "valor_solicitado": 4800.0,
        "prazo": 12,
    }
    base.update(alteracoes)
    return base


def sem_chave(chave: str, **alteracoes: Any) -> dict[str, Any]:
    return {k: v for k, v in registro(**alteracoes).items() if k != chave}


def casos_validos_tipicos() -> list[dict[str, Any]]:
    return [
        registro(idade=30, renda_mensal=3500.0, valor_solicitado=4200.0),
        registro(idade=45, renda_mensal=9000.0, valor_solicitado=12000.0, prazo=6),
        registro(idade=52, renda_mensal=2500.0, historico_credito="regular", valor_solicitado=3000.0),
        registro(idade=38, renda_mensal=6000, valor_solicitado=9000.0),
    ]


def casos_limite_renda() -> list[dict[str, Any]]:
    return [
        registro(renda_mensal=1500.0, valor_solicitado=3000.0),
        registro(renda_mensal=1500.0, valor_solicitado=5400.0),
        registro(renda_mensal=1499.99, valor_solicitado=1800.0),
        registro(renda_mensal=1500.01, valor_solicitado=1800.0),
    ]


def casos_limite_comprometimento() -> list[dict[str, Any]]:
    return [
        registro(renda_mensal=4000.0, valor_solicitado=14400.0),
        registro(renda_mensal=4000.0, valor_solicitado=14412.0),
        registro(renda_mensal=4000.0, valor_solicitado=9600.0),
        registro(renda_mensal=4000.0, valor_solicitado=9612.0),
        registro(renda_mensal=4000.0, historico_credito="regular", valor_solicitado=9600.0),
        registro(renda_mensal=4000.0, historico_credito="regular", valor_solicitado=9612.0),
    ]


def casos_idade() -> list[dict[str, Any]]:
    return [
        registro(idade=18),
        registro(idade=17),
        registro(idade=0),
        registro(idade=99),
    ]


def casos_prazo() -> list[dict[str, Any]]:
    return [
        registro(prazo=6, valor_solicitado=2400.0),
        registro(prazo=12),
        registro(prazo=24, valor_solicitado=7200.0),
        registro(prazo=1, valor_solicitado=100.0),
        registro(prazo=0),
        registro(prazo=-6),
    ]


def casos_historico() -> list[dict[str, Any]]:
    return [
        registro(historico_credito="excelente"),
        registro(historico_credito="BOM"),
        registro(historico_credito=""),
        registro(historico_credito="ruim", valor_solicitado=7200.0),
        registro(historico_credito="ruim", valor_solicitado=7220.0),
        registro(historico_credito="ruim", valor_solicitado=2400.0),
    ]


def casos_teto_de_credito() -> list[dict[str, Any]]:
    return [
        registro(renda_mensal=8000.0, valor_solicitado=21000.0),
        registro(renda_mensal=8000.0, valor_solicitado=20000.0),
        registro(renda_mensal=20000.0, valor_solicitado=60000.0, prazo=12),
    ]


def casos_chaves_ausentes() -> list[dict[str, Any]]:
    return [
        sem_chave("idade"),
        sem_chave("renda_mensal"),
        sem_chave("historico_credito"),
        sem_chave("valor_solicitado"),
        sem_chave("prazo"),
    ]


def casos_tipos_errados() -> list[dict[str, Any]]:
    return [
        registro(idade="30"),
        registro(idade=30.5),
        registro(idade=True),
        registro(renda_mensal="4000.0"),
        registro(renda_mensal=None),
        registro(historico_credito=5),
        registro(valor_solicitado="4800"),
        registro(valor_solicitado=None),
        registro(prazo="12"),
        registro(prazo=12.5),
        registro(prazo=12.0),
    ]


def casos_valores_invalidos() -> list[dict[str, Any]]:
    return [
        registro(renda_mensal=0.0),
        registro(renda_mensal=-1500.0),
        registro(valor_solicitado=0.0),
        registro(valor_solicitado=-100.0),
        registro(idade=-1),
    ]


def casos_aleatorios() -> list[dict[str, Any]]:
    gerador = random.Random(SEMENTE)
    return [
        registro(
            idade=gerador.randint(18, 70),
            renda_mensal=round(gerador.uniform(1500.0, 15000.0), 2),
            historico_credito=gerador.choice(HISTORICOS),
            valor_solicitado=round(gerador.uniform(500.0, 25000.0), 2),
            prazo=gerador.choice(PRAZOS),
        )
        for _ in range(QUANTIDADE_ALEATORIA)
    ]


def casos_sem_identificador_valido() -> list[dict[str, Any]]:
    return [
        sem_chave("id"),
        registro(id=123),
        registro(id=""),
    ]


def montar_dataset() -> list[dict[str, Any]]:
    grupos = (
        casos_validos_tipicos(),
        casos_limite_renda(),
        casos_limite_comprometimento(),
        casos_idade(),
        casos_prazo(),
        casos_historico(),
        casos_teto_de_credito(),
        casos_chaves_ausentes(),
        casos_tipos_errados(),
        casos_valores_invalidos(),
        casos_aleatorios(),
    )
    casos = [caso for grupo in grupos for caso in grupo]
    propostas = [{"id": f"PROP-{numero:03d}", **caso} for numero, caso in enumerate(casos, start=1)]
    return propostas + casos_sem_identificador_valido()


def main() -> None:
    propostas = montar_dataset()
    CAMINHO_SAIDA.write_text(json.dumps(propostas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(propostas)} propostas gravadas em {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()
