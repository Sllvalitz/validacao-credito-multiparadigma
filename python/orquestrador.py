# Responsavel: Anderson da Silva Pinto
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from python.dominio import AnaliseRisco, ErroIntegracao, ErroValidacao, Proposta
from python.integracao import ModuloExterno


class Orquestrador:
    def __init__(self, prolog: ModuloExterno, lisp: ModuloExterno) -> None:
        self._prolog = prolog
        self._lisp = lisp

    def processar(self, registro: Any) -> dict[str, Any]:
        # o id vem do registro bruto porque a validacao pode falhar antes de existir uma Proposta
        id_proposta = registro.get("id") if isinstance(registro, dict) else None
        analise = AnaliseRisco(id_proposta if isinstance(id_proposta, str) else "SEM_ID")
        try:
            proposta = Proposta.de_registro(registro)
            parecer = self._prolog.executar(proposta.para_prolog())
            # regra do contrato: reprovado pelo Prolog nao aciona o Lisp
            if not parecer["elegivel"]:
                analise.reprovar(parecer["impedimentos"])
            else:
                analise.aprovar(self._lisp.executar(proposta.para_lisp()))
        # erro numa proposta vira status do resultado: uma proposta ruim nao pode derrubar o lote
        except ErroValidacao as erro:
            analise.registrar_erro("ERRO_VALIDACAO", str(erro))
        except ErroIntegracao as erro:
            analise.registrar_erro("ERRO_INTEGRACAO", str(erro))
        return analise.para_dict()

    def processar_arquivo(self, caminho: Path) -> list[dict[str, Any]]:
        # arquivo ilegivel ou fora do formato invalida o lote inteiro, por isso sobe como ErroValidacao
        try:
            registros = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erro:
            raise ErroValidacao(f"nao foi possivel ler {caminho}: {erro}") from None
        if not isinstance(registros, list):
            raise ErroValidacao(f"{caminho}: esperada uma lista JSON de propostas")
        return [self.processar(registro) for registro in registros]
