# Responsavel: Robson
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from python.dominio import ErroIntegracao, ErroValidacao
from python.integracao import ModuloLisp, ModuloProlog, criar_modulo_lisp, criar_modulo_prolog
from python.orquestrador import Orquestrador

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_DATASET = RAIZ / "data" / "propostas.json"
CAMINHO_GERADOR = RAIZ / "data" / "gerar_dataset.py"
FERRAMENTAS_DISPONIVEIS = shutil.which("swipl") is not None and shutil.which("sbcl") is not None
STATUS_FINAIS = {
    "APROVADO",
    "APROVADO_COM_CONDICOES",
    "REPROVADO",
    "ERRO_VALIDACAO",
    "ERRO_INTEGRACAO",
}


def registro_valido(**alteracoes):
    registro = {
        "id": "PROP-001",
        "idade": 30,
        "renda_mensal": 4000.0,
        "historico_credito": "bom",
        "valor_solicitado": 4800.0,
        "prazo": 12,
    }
    registro.update(alteracoes)
    return registro


def parecer_elegivel(id_proposta="PROP-001"):
    return {"id": id_proposta, "elegivel": True, "regras_satisfeitas": [], "impedimentos": []}


def parecer_inelegivel(impedimentos, id_proposta="PROP-001"):
    return {"id": id_proposta, "elegivel": False, "regras_satisfeitas": [], "impedimentos": impedimentos}


def precificacao_aprovada(id_proposta="PROP-001", status="APROVADO"):
    return {
        "id": id_proposta,
        "status": status,
        "classificacao_risco": "baixo",
        "taxa_juros_mensal": 0.015,
        "limite_calculado": 12600.0,
        "valor_aprovado": 4200.0,
        "valor_parcela_final": 385.06,
    }


class ModuloProibido:
    def executar(self, mensagem):
        raise AssertionError("o modulo nao deveria ter sido acionado")


class ModuloFixo:
    def __init__(self, resposta):
        self.resposta = resposta
        self.mensagens_recebidas = []

    def executar(self, mensagem):
        self.mensagens_recebidas.append(mensagem)
        return self.resposta


class ModuloQueFalha:
    def executar(self, mensagem):
        raise ErroIntegracao("falha simulada")


def modulo_que_imprime(texto, timeout=10.0):
    return ModuloProlog([sys.executable, "-c", f"print({texto!r})"], timeout)


def carregar_gerador_de_dataset():
    especificacao = importlib.util.spec_from_file_location("gerar_dataset", CAMINHO_GERADOR)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


class TestValidacaoDeEntrada(unittest.TestCase):
    def setUp(self):
        self.orquestrador = Orquestrador(ModuloProibido(), ModuloProibido())

    def assertErroDeValidacao(self, registro):
        resultado = self.orquestrador.processar(registro)
        self.assertEqual(resultado["status"], "ERRO_VALIDACAO")
        self.assertIsNone(resultado["precificacao"])
        self.assertTrue(resultado["erro"])

    def test_chave_ausente_nao_aciona_nenhum_modulo(self):
        for chave in ("id", "idade", "renda_mensal", "historico_credito", "valor_solicitado", "prazo"):
            with self.subTest(chave=chave):
                registro = registro_valido()
                del registro[chave]
                self.assertErroDeValidacao(registro)

    def test_tipo_errado_nao_aciona_nenhum_modulo(self):
        alteracoes = (
            {"idade": "30"},
            {"idade": 30.5},
            {"idade": True},
            {"renda_mensal": "4000.0"},
            {"renda_mensal": None},
            {"historico_credito": 5},
            {"valor_solicitado": "4800"},
            {"valor_solicitado": None},
            {"prazo": "12"},
            {"prazo": 12.5},
            {"prazo": 12.0},
            {"id": 123},
        )
        for alteracao in alteracoes:
            with self.subTest(alteracao=alteracao):
                self.assertErroDeValidacao(registro_valido(**alteracao))

    def test_valores_zero_ou_negativos_sao_erro_de_validacao(self):
        alteracoes = (
            {"renda_mensal": 0.0},
            {"renda_mensal": -1500.0},
            {"valor_solicitado": 0.0},
            {"valor_solicitado": -100.0},
            {"prazo": 0},
            {"prazo": -6},
            {"idade": -1},
        )
        for alteracao in alteracoes:
            with self.subTest(alteracao=alteracao):
                self.assertErroDeValidacao(registro_valido(**alteracao))

    def test_historico_vazio_e_erro_de_validacao(self):
        self.assertErroDeValidacao(registro_valido(historico_credito=""))

    def test_registro_que_nao_e_objeto_usa_id_sem_id(self):
        for registro in (None, "texto", 42, [1, 2]):
            with self.subTest(registro=registro):
                resultado = self.orquestrador.processar(registro)
                self.assertEqual(resultado["status"], "ERRO_VALIDACAO")
                self.assertEqual(resultado["id"], "SEM_ID")


class TestFluxoDoOrquestrador(unittest.TestCase):
    def test_reprovado_pelo_prolog_nao_aciona_o_lisp(self):
        prolog = ModuloFixo(parecer_inelegivel(["idade_abaixo_do_minimo"]))
        resultado = Orquestrador(prolog, ModuloProibido()).processar(registro_valido(idade=17))
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertEqual(resultado["impedimentos"], ["idade_abaixo_do_minimo"])
        self.assertIsNone(resultado["precificacao"])

    def test_elegivel_aciona_o_lisp_e_usa_o_status_dele(self):
        for status in ("APROVADO", "APROVADO_COM_CONDICOES"):
            with self.subTest(status=status):
                lisp = ModuloFixo(precificacao_aprovada(status=status))
                resultado = Orquestrador(ModuloFixo(parecer_elegivel()), lisp).processar(registro_valido())
                self.assertEqual(resultado["status"], status)
                self.assertEqual(resultado["precificacao"]["valor_parcela_final"], 385.06)
                self.assertEqual(len(lisp.mensagens_recebidas), 1)

    def test_prolog_recebe_parcela_base_e_comprometimento_calculados_pelo_python(self):
        prolog = ModuloFixo(parecer_inelegivel(["prazo_invalido"]))
        Orquestrador(prolog, ModuloProibido()).processar(registro_valido(renda_mensal=4000.0, valor_solicitado=14400.0))
        mensagem = prolog.mensagens_recebidas[0]
        self.assertEqual(mensagem["parcela_base"], 1200.0)
        self.assertEqual(mensagem["comprometimento_percentual"], 30.0)

    def test_falha_do_prolog_vira_erro_de_integracao(self):
        resultado = Orquestrador(ModuloQueFalha(), ModuloProibido()).processar(registro_valido())
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("falha simulada", resultado["erro"])

    def test_falha_do_lisp_vira_erro_de_integracao(self):
        resultado = Orquestrador(ModuloFixo(parecer_elegivel()), ModuloQueFalha()).processar(registro_valido())
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")

    def test_lote_continua_depois_de_registro_com_erro(self):
        registros = [registro_valido(id="PROP-001"), registro_valido(id="PROP-002", prazo=0), registro_valido(id="PROP-003")]
        orquestrador = Orquestrador(ModuloFixo(parecer_elegivel()), ModuloFixo(precificacao_aprovada()))
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "lote.json"
            caminho.write_text(json.dumps(registros), encoding="utf-8")
            resultados = orquestrador.processar_arquivo(caminho)
        self.assertEqual([r["status"] for r in resultados], ["APROVADO", "ERRO_VALIDACAO", "APROVADO"])

    def test_arquivo_inexistente_levanta_erro_de_validacao(self):
        orquestrador = Orquestrador(ModuloProibido(), ModuloProibido())
        with self.assertRaises(ErroValidacao):
            orquestrador.processar_arquivo(Path("nao_existe.json"))

    def test_arquivo_que_nao_e_lista_levanta_erro_de_validacao(self):
        orquestrador = Orquestrador(ModuloProibido(), ModuloProibido())
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "objeto.json"
            caminho.write_text('{"id": "PROP-001"}', encoding="utf-8")
            with self.assertRaises(ErroValidacao):
                orquestrador.processar_arquivo(caminho)

    def test_arquivo_com_json_invalido_levanta_erro_de_validacao(self):
        orquestrador = Orquestrador(ModuloProibido(), ModuloProibido())
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "quebrado.json"
            caminho.write_text("{ nao e json", encoding="utf-8")
            with self.assertRaises(ErroValidacao):
                orquestrador.processar_arquivo(caminho)


class TestErrosDeIntegracaoComProcessoReal(unittest.TestCase):
    def processar_com(self, prolog):
        return Orquestrador(prolog, ModuloProibido()).processar(registro_valido())

    def test_saida_malformada(self):
        resultado = self.processar_com(modulo_que_imprime("isto nao e json"))
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("malformada", resultado["erro"])

    def test_saida_sem_chaves_obrigatorias(self):
        resultado = self.processar_com(modulo_que_imprime(json.dumps({"id": "PROP-001"})))
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("elegivel", resultado["erro"])

    def test_saida_que_nao_e_objeto_json(self):
        resultado = self.processar_com(modulo_que_imprime("[1, 2, 3]"))
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")

    def test_id_divergente(self):
        resultado = self.processar_com(modulo_que_imprime(json.dumps(parecer_elegivel("PROP-999"))))
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("id divergente", resultado["erro"])

    def test_codigo_de_retorno_diferente_de_zero(self):
        prolog = ModuloProlog([sys.executable, "-c", "import sys; sys.exit(3)"])
        resultado = self.processar_com(prolog)
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("codigo de retorno 3", resultado["erro"])

    def test_tempo_limite_excedido(self):
        prolog = ModuloProlog([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5)
        resultado = self.processar_com(prolog)
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("tempo limite", resultado["erro"])

    def test_executavel_ausente(self):
        resultado = self.processar_com(ModuloProlog(["executavel-que-nao-existe-xyz"]))
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("executavel nao encontrado", resultado["erro"])

    def test_lisp_com_saida_incompleta_vira_erro_de_integracao(self):
        lisp = ModuloLisp([sys.executable, "-c", f"print({json.dumps({'id': 'PROP-001'})!r})"])
        resultado = Orquestrador(ModuloFixo(parecer_elegivel()), lisp).processar(registro_valido())
        self.assertEqual(resultado["status"], "ERRO_INTEGRACAO")
        self.assertIn("status", resultado["erro"])


class TestDataset(unittest.TestCase):
    def setUp(self):
        self.propostas = json.loads(CAMINHO_DATASET.read_text(encoding="utf-8"))

    def test_tem_pelo_menos_50_registros(self):
        self.assertGreaterEqual(len(self.propostas), 50)

    def test_ids_textuais_sao_unicos(self):
        ids = [p["id"] for p in self.propostas if isinstance(p.get("id"), str) and p["id"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_arquivo_corresponde_ao_que_o_gerador_produz(self):
        self.assertEqual(self.propostas, carregar_gerador_de_dataset().montar_dataset())

    def test_cobre_os_casos_de_borda_do_enunciado(self):
        dicionarios = [p for p in self.propostas if isinstance(p, dict)]
        self.assertTrue(any(p.get("renda_mensal") == 1500.0 for p in dicionarios))
        self.assertTrue(any(p.get("idade") == 18 for p in dicionarios))
        self.assertTrue(any(p.get("idade") == 17 for p in dicionarios))
        self.assertTrue(any(p.get("prazo") == 0 for p in dicionarios))
        self.assertTrue(any(p.get("prazo") not in (6, 12, None) and isinstance(p.get("prazo"), int) and p["prazo"] > 0 for p in dicionarios))
        self.assertTrue(any(p.get("historico_credito") not in ("bom", "regular", "ruim", None) for p in dicionarios))
        self.assertTrue(any(p.get("renda_mensal") == 0.0 for p in dicionarios))
        self.assertTrue(any(isinstance(p.get("renda_mensal"), (int, float)) and p["renda_mensal"] < 0 for p in dicionarios))
        self.assertTrue(any("idade" not in p for p in dicionarios))
        self.assertTrue(any(isinstance(p.get("idade"), str) for p in dicionarios))

    def test_registros_invalidos_viram_erro_de_validacao_sem_acionar_modulos(self):
        orquestrador = Orquestrador(ModuloFixo(parecer_elegivel()), ModuloFixo(precificacao_aprovada()))
        statuses = {orquestrador.processar(p)["status"] for p in self.propostas}
        self.assertIn("ERRO_VALIDACAO", statuses)
        self.assertNotIn("ERRO_INTEGRACAO", statuses)


@unittest.skipUnless(FERRAMENTAS_DISPONIVEIS, "swipl e sbcl nao estao instalados")
class TestPontaAPonta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orquestrador = Orquestrador(criar_modulo_prolog(), criar_modulo_lisp())

    def processar(self, **alteracoes):
        return self.orquestrador.processar(registro_valido(**alteracoes))

    def assertReprovadoPor(self, resultado, impedimentos):
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertEqual(resultado["impedimentos"], impedimentos)
        self.assertIsNone(resultado["precificacao"])

    def test_exemplo_do_contrato(self):
        resultado = self.processar(renda_mensal=3500.0, valor_solicitado=4200.0)
        precificacao = resultado["precificacao"]
        self.assertEqual(resultado["status"], "APROVADO")
        self.assertEqual(precificacao["classificacao_risco"], "baixo")
        self.assertEqual(precificacao["taxa_juros_mensal"], 0.015)
        self.assertEqual(precificacao["limite_calculado"], 12600.0)
        self.assertEqual(precificacao["valor_aprovado"], 4200.0)
        self.assertEqual(precificacao["valor_parcela_final"], 385.06)

    def test_renda_exatamente_1500_e_aceita(self):
        resultado = self.processar(renda_mensal=1500.0, valor_solicitado=3000.0)
        self.assertEqual(resultado["status"], "APROVADO")

    def test_renda_1499_99_e_reprovada(self):
        resultado = self.processar(renda_mensal=1499.99, valor_solicitado=1800.0)
        self.assertReprovadoPor(resultado, ["renda_abaixo_do_minimo"])

    def test_renda_1500_com_comprometimento_30_exato_e_aceita(self):
        resultado = self.processar(renda_mensal=1500.0, valor_solicitado=5400.0)
        self.assertEqual(resultado["status"], "APROVADO")
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "medio")
        self.assertEqual(resultado["precificacao"]["valor_aprovado"], 5400.0)

    def test_comprometimento_exatamente_30_e_aceito(self):
        resultado = self.processar(renda_mensal=4000.0, valor_solicitado=14400.0)
        self.assertEqual(resultado["status"], "APROVADO")

    def test_comprometimento_acima_de_30_e_reprovado(self):
        resultado = self.processar(renda_mensal=4000.0, valor_solicitado=14412.0)
        self.assertReprovadoPor(resultado, ["comprometimento_acima_30_porcento"])

    def test_idade_18_e_aceita(self):
        self.assertEqual(self.processar(idade=18)["status"], "APROVADO")

    def test_idade_17_e_reprovada(self):
        self.assertReprovadoPor(self.processar(idade=17), ["idade_abaixo_do_minimo"])

    def test_prazo_positivo_fora_de_6_e_12_e_reprovado(self):
        for prazo in (1, 9, 24):
            with self.subTest(prazo=prazo):
                resultado = self.processar(prazo=prazo, valor_solicitado=100.0)
                self.assertReprovadoPor(resultado, ["prazo_invalido"])

    def test_prazo_6_e_aceito(self):
        self.assertEqual(self.processar(prazo=6, valor_solicitado=2400.0)["status"], "APROVADO")

    def test_prazo_zero_ou_negativo_e_erro_de_validacao(self):
        for prazo in (0, -6):
            with self.subTest(prazo=prazo):
                self.assertEqual(self.processar(prazo=prazo)["status"], "ERRO_VALIDACAO")

    def test_historico_fora_do_dominio_e_reprovado(self):
        for historico in ("excelente", "BOM"):
            with self.subTest(historico=historico):
                resultado = self.processar(historico_credito=historico)
                self.assertReprovadoPor(resultado, ["historico_nao_aceito"])

    def test_historico_ruim_com_comprometimento_15_exato_e_aprovado_com_condicoes(self):
        resultado = self.processar(historico_credito="ruim", valor_solicitado=7200.0)
        self.assertEqual(resultado["status"], "APROVADO_COM_CONDICOES")
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "alto")
        self.assertEqual(resultado["precificacao"]["taxa_juros_mensal"], 0.035)

    def test_historico_ruim_com_comprometimento_acima_de_15_e_reprovado(self):
        resultado = self.processar(historico_credito="ruim", valor_solicitado=7220.0)
        self.assertReprovadoPor(resultado, ["historico_nao_aceito"])

    def test_risco_baixo_ate_20_por_cento(self):
        resultado = self.processar(renda_mensal=4000.0, valor_solicitado=9600.0)
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "baixo")

    def test_risco_medio_acima_de_20_por_cento_com_historico_bom(self):
        resultado = self.processar(renda_mensal=4000.0, valor_solicitado=9612.0)
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "medio")
        self.assertEqual(resultado["precificacao"]["taxa_juros_mensal"], 0.025)

    def test_risco_medio_com_historico_regular_ate_20_por_cento(self):
        resultado = self.processar(historico_credito="regular", valor_solicitado=9600.0)
        self.assertEqual(resultado["status"], "APROVADO")
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "medio")

    def test_risco_alto_com_historico_regular_acima_de_20_por_cento(self):
        resultado = self.processar(historico_credito="regular", valor_solicitado=9612.0)
        self.assertEqual(resultado["status"], "APROVADO_COM_CONDICOES")
        self.assertEqual(resultado["precificacao"]["classificacao_risco"], "alto")

    def test_teto_de_credito_limita_o_valor_aprovado(self):
        resultado = self.processar(renda_mensal=8000.0, valor_solicitado=21000.0)
        self.assertEqual(resultado["status"], "APROVADO")
        self.assertEqual(resultado["precificacao"]["limite_calculado"], 20000.0)
        self.assertEqual(resultado["precificacao"]["valor_aprovado"], 20000.0)

    def test_varios_impedimentos_aparecem_juntos(self):
        resultado = self.processar(idade=17, renda_mensal=1000.0, valor_solicitado=1200.0)
        self.assertEqual(resultado["status"], "REPROVADO")
        self.assertIn("idade_abaixo_do_minimo", resultado["impedimentos"])
        self.assertIn("renda_abaixo_do_minimo", resultado["impedimentos"])

    def test_dataset_completo_nao_gera_erro_de_integracao(self):
        propostas = json.loads(CAMINHO_DATASET.read_text(encoding="utf-8"))
        resultados = self.orquestrador.processar_arquivo(CAMINHO_DATASET)
        self.assertEqual(len(resultados), len(propostas))
        for resultado in resultados:
            with self.subTest(id=resultado["id"]):
                self.assertIn(resultado["status"], STATUS_FINAIS)
                self.assertNotEqual(resultado["status"], "ERRO_INTEGRACAO")


if __name__ == "__main__":
    unittest.main()
