# Responsavel: Anderson
"""Orquestrador: controla o fluxo Python -> Prolog -> (Lisp) de cada proposta."""
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
        """Processa UMA proposta. Nunca levanta excecao: erro vira status no
        resultado, para uma proposta ruim nao derrubar o lote inteiro."""
        id_proposta = registro.get("id") if isinstance(registro, dict) else None
        analise = AnaliseRisco(id_proposta if isinstance(id_proposta, str) else "SEM_ID")
        try:
            proposta = Proposta.de_registro(registro)
            parecer = self._prolog.executar(proposta.para_prolog())
            if not parecer["elegivel"]:
                # Regra de fluxo do contrato: reprovado NAO aciona o Lisp.
                analise.reprovar(parecer["impedimentos"])
            else:
                analise.aprovar(self._lisp.executar(proposta.para_lisp()))
        except ErroValidacao as e:
            analise.registrar_erro("ERRO_VALIDACAO", str(e))
        except ErroIntegracao as e:
            analise.registrar_erro("ERRO_INTEGRACAO", str(e))
        return analise.para_dict()

    def processar_arquivo(self, caminho: Path) -> list[dict[str, Any]]:
        try:
            registros = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ErroValidacao(f"nao foi possivel ler {caminho}: {e}") from None
        if not isinstance(registros, list):
            raise ErroValidacao(f"{caminho}: esperada uma lista JSON de propostas")
        return [self.processar(r) for r in registros]
