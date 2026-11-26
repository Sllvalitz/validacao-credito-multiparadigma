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

    # rastro, quando informado, recebe o que cada etapa produziu (usado pelo --detalhe do main)
    def analisar(self, registro: Any, rastro: dict[str, Any] | None = None) -> AnaliseRisco:
        # o id vem do registro bruto porque a validacao pode falhar antes de existir uma Proposta
        id_proposta = registro.get("id") if isinstance(registro, dict) else None
        analise = AnaliseRisco(id_proposta if isinstance(id_proposta, str) else "SEM_ID")
        try:
            proposta = Proposta.de_registro(registro)
            indicadores = proposta.para_prolog()
            parecer = self._prolog.executar(indicadores)
            self._registrar(rastro, indicadores=indicadores, parecer=parecer)
            # regra do contrato: reprovado pelo Prolog nao aciona o Lisp
            if not parecer["elegivel"]:
                analise.reprovar(parecer["impedimentos"])
            else:
                preco = self._lisp.executar(proposta.para_lisp())
                self._registrar(rastro, preco=preco)
                analise.aprovar(preco)
        # erro numa proposta vira status do resultado: uma proposta ruim nao pode derrubar o lote
        except ErroValidacao as erro:
            analise.registrar_erro("ERRO_VALIDACAO", str(erro))
        except ErroIntegracao as erro:
            analise.registrar_erro("ERRO_INTEGRACAO", str(erro))
        return analise

    def processar(self, registro: Any) -> dict[str, Any]:
        return self.analisar(registro).para_dict()

    def carregar_registros(self, caminho: Path) -> list[Any]:
        # arquivo ilegivel ou fora do formato invalida o lote inteiro, por isso sobe como ErroValidacao
        try:
            registros = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erro:
            raise ErroValidacao(f"nao foi possivel ler {caminho}: {erro}") from None
        if not isinstance(registros, list):
            raise ErroValidacao(f"{caminho}: esperada uma lista JSON de propostas")
        return registros

    def analisar_arquivo(self, caminho: Path) -> list[AnaliseRisco]:
        return [self.analisar(registro) for registro in self.carregar_registros(caminho)]

    @staticmethod
    def _registrar(rastro: dict[str, Any] | None, **etapas: Any) -> None:
        if rastro is not None:
            rastro.update(etapas)
