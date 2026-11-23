import json
import shutil
import unittest
from pathlib import Path

from python.dominio import ErroIntegracao
from python.integracao import (ModuloExterno, ModuloLisp, ModuloProlog,
                               criar_modulo_lisp, criar_modulo_prolog)
from python.orquestrador import Orquestrador

CAMINHO_DATASET = Path(__file__).resolve().parents[2] / "data" / "propostas.json"
STATUS_FINAIS = {"APROVADO", "APROVADO_COM_CONDICOES", "REPROVADO", "ERRO_VALIDACAO"}
# sem swipl e sbcl os testes de ponta a ponta sao ignorados em vez de falhar
FERRAMENTAS_INSTALADAS = bool(shutil.which("swipl") and shutil.which("sbcl"))

REGISTRO = {"id": "PROP-001", "idade": 30, "renda_mensal": 3500.00,
            "historico_credito": "bom", "valor_solicitado": 4200.00, "prazo": 12}


# dubles de teste: permitem verificar o fluxo do orquestrador sem executar subprocessos
class ModuloFalso(ModuloExterno):
    def __init__(self, resposta=None, erro=None):
        super().__init__([])
        self.resposta = resposta
        self.erro = erro
        self.chamadas = 0

    @property
    def chaves_saida(self):
        return ()

    def executar(self, mensagem):
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return self.resposta


class TestFluxo(unittest.TestCase):
    # regra do contrato: o Lisp so e chamado para propostas elegiveis
    def test_reprovado_nao_aciona_lisp(self):
        prolog = ModuloFalso({"id": "PROP-001", "elegivel": False, "regras_satisfeitas": [],
                              "impedimentos": ["renda_abaixo_do_minimo"]})
        lisp = ModuloFalso({})
        resultado = Orquestrador(prolog, lisp).processar(REGISTRO)
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertEqual(resultado["impedimentos"], ["renda_abaixo_do_minimo"])
        self.assertEqual(lisp.chamadas, 0)

    def test_erro_de_integracao_vira_status(self):
        orquestrador = Orquestrador(ModuloFalso(erro=ErroIntegracao("saida malformada")), ModuloFalso({}))
        self.assertEqual(orquestrador.processar(REGISTRO)["status"], "ERRO_INTEGRACAO")

    def test_erro_de_validacao_vira_status(self):
        orquestrador = Orquestrador(ModuloFalso({}), ModuloFalso({}))
        self.assertEqual(orquestrador.processar({"id": "X"})["status"], "ERRO_VALIDACAO")
        self.assertEqual(orquestrador.processar("lixo")["status"], "ERRO_VALIDACAO")

    # a validacao acontece antes de qualquer subprocesso, que e a etapa cara
    def test_registro_invalido_nao_chama_os_modulos(self):
        prolog = ModuloFalso({})
        Orquestrador(prolog, ModuloFalso({})).processar({"id": "X"})
        self.assertEqual(prolog.chamadas, 0)


class TestDataset(unittest.TestCase):
    def test_minimo_de_50_registros_com_ids_unicos(self):
        registros = json.loads(CAMINHO_DATASET.read_text(encoding="utf-8"))
        ids = [registro["id"] for registro in registros]
        self.assertGreaterEqual(len(registros), 50)
        self.assertEqual(len(ids), len(set(ids)))


@unittest.skipUnless(FERRAMENTAS_INSTALADAS, "requer swipl e sbcl")
class TestPontaAPonta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orquestrador = Orquestrador(criar_modulo_prolog(), criar_modulo_lisp())

    def test_exemplo_do_contrato(self):
        resultado = self.orquestrador.processar(REGISTRO)
        self.assertEqual(resultado["status"], "APROVADO")
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "baixo")
        self.assertEqual(resultado["precificacao"]["valor_parcela_final"], 385.06)

    def test_reprovado_por_renda(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, renda_mensal=1400.0, valor_solicitado=1000.0))
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertIn("renda_abaixo_do_minimo", resultado["impedimentos"])

    # casos de borda: os limites exatos (R$ 1.500, 18 anos, 30%) devem ser aceitos
    def test_renda_exatamente_no_minimo_e_aceita(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, renda_mensal=1500.0, valor_solicitado=4000.0))
        self.assertNotEqual(resultado["status"], "REPROVADO")

    def test_idade_18_aceita_e_17_reprovada(self):
        self.assertNotEqual(self.orquestrador.processar(dict(REGISTRO, idade=18))["status"], "REPROVADO")
        reprovado = self.orquestrador.processar(dict(REGISTRO, idade=17))
        self.assertEqual(reprovado["status"], "REPROVADO")
        self.assertIn("idade_abaixo_do_minimo", reprovado["impedimentos"])

    def test_comprometimento_exatamente_30_e_aceito(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, renda_mensal=3000.0, valor_solicitado=10800.0))
        self.assertNotEqual(resultado["status"], "REPROVADO")

    def test_comprometimento_acima_de_30_e_reprovado(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, renda_mensal=3000.0, valor_solicitado=11000.0))
        self.assertIn("comprometimento_acima_30_porcento", resultado["impedimentos"])

    # o dominio so barra prazo <= 0; 24 meses e reprovado como regra de negocio, pelo Prolog
    def test_prazo_fora_de_6_ou_12_e_reprovado_pelo_prolog(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, prazo=24))
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertIn("prazo_invalido", resultado["impedimentos"])

    def test_historico_ruim_so_com_comprometimento_ate_15(self):
        aceito = self.orquestrador.processar(dict(REGISTRO, historico_credito="ruim",
                                                  renda_mensal=4000.0, valor_solicitado=7200.0))
        self.assertEqual(aceito["status"], "APROVADO_COM_CONDICOES")
        reprovado = self.orquestrador.processar(dict(REGISTRO, historico_credito="ruim",
                                                     renda_mensal=4000.0, valor_solicitado=9600.0))
        self.assertEqual(reprovado["status"], "REPROVADO")

    def test_historico_fora_do_dominio_e_reprovado(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, historico_credito="excelente"))
        self.assertIn("historico_nao_aceito", resultado["impedimentos"])

    # renda x 30% x prazo daria R$ 36.000, mas o teto de R$ 20.000 corta o valor
    def test_teto_de_credito(self):
        resultado = self.orquestrador.processar(dict(REGISTRO, renda_mensal=10000.0, valor_solicitado=36000.0))
        self.assertEqual(resultado["precificacao"]["valor_aprovado"], 20000.0)

    # um erro de integracao em qualquer registro indicaria bug nos modulos, nao no dado
    def test_dataset_inteiro_termina_sem_erro_de_integracao(self):
        registros = json.loads(CAMINHO_DATASET.read_text(encoding="utf-8"))
        resultados = [self.orquestrador.processar(registro) for registro in registros]
        self.assertEqual(len(resultados), len(registros))
        self.assertTrue({r["status"] for r in resultados} <= STATUS_FINAIS)

    # sleep 5 com timeout de 0,2 s simula um processo travado
    def test_timeout_vira_erro_de_integracao(self):
        with self.assertRaises(ErroIntegracao):
            ModuloProlog(["sleep", "5"], timeout=0.2).executar({"id": "X"})

    def test_executavel_inexistente(self):
        with self.assertRaises(ErroIntegracao):
            ModuloLisp(["nao-existe-xyz"]).executar({"id": "X"})


if __name__ == "__main__":
    unittest.main()
