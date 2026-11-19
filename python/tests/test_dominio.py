# Responsavel: Lucy
import unittest

from python.dominio import (
    AnaliseRisco,
    Cliente,
    ErroCredito,
    ErroIntegracao,
    ErroValidacao,
    Proposta,
    merge_sort,
    ordenar_aprovadas_por_valor,
)


def registro_valido(**alteracoes):
    registro = {
        "id": "PROP-001",
        "idade": 30,
        "renda_mensal": 3500.0,
        "historico_credito": "bom",
        "valor_solicitado": 4200.0,
        "prazo": 12,
    }
    registro.update(alteracoes)
    return registro


def precificacao(id_proposta, valor_aprovado, status="APROVADO"):
    return {
        "id": id_proposta,
        "status": status,
        "classificacao_risco": "baixo",
        "taxa_juros_mensal": 0.015,
        "limite_calculado": 12600.0,
        "valor_aprovado": valor_aprovado,
        "valor_parcela_final": 385.06,
    }


def analise_aprovada(id_proposta, valor_aprovado):
    analise = AnaliseRisco(id_proposta)
    analise.aprovar(precificacao(id_proposta, valor_aprovado))
    return analise


class TestCliente(unittest.TestCase):
    def test_cliente_valido_expoe_atributos(self):
        cliente = Cliente(30, 3500.0, "bom")
        self.assertEqual(cliente.idade, 30)
        self.assertEqual(cliente.renda_mensal, 3500.0)
        self.assertEqual(cliente.historico_credito, "bom")

    def test_renda_inteira_vira_float(self):
        self.assertIsInstance(Cliente(30, 3500, "bom").renda_mensal, float)

    def test_idade_17_e_aceita_pelo_dominio(self):
        self.assertEqual(Cliente(17, 3500.0, "bom").idade, 17)

    def test_historico_fora_do_dominio_e_aceito_para_o_prolog_decidir(self):
        self.assertEqual(Cliente(30, 3500.0, "pessimo").historico_credito, "pessimo")

    def test_idade_negativa(self):
        with self.assertRaises(ErroValidacao):
            Cliente(-1, 3500.0, "bom")

    def test_renda_zero_ou_negativa(self):
        for renda in (0, 0.0, -100.0):
            with self.subTest(renda=renda), self.assertRaises(ErroValidacao):
                Cliente(30, renda, "bom")

    def test_tipos_errados(self):
        casos = [
            ("idade", ("30", 3500.0, "bom")),
            ("idade", (30.5, 3500.0, "bom")),
            ("idade", (True, 3500.0, "bom")),
            ("renda", (30, "3500", "bom")),
            ("renda", (30, True, "bom")),
            ("renda", (30, float("nan"), "bom")),
            ("renda", (30, float("inf"), "bom")),
            ("historico", (30, 3500.0, 1)),
            ("historico", (30, 3500.0, "")),
        ]
        for nome, argumentos in casos:
            with self.subTest(nome=nome, argumentos=argumentos), self.assertRaises(ErroValidacao):
                Cliente(*argumentos)


class TestProposta(unittest.TestCase):
    def test_de_registro_valido(self):
        proposta = Proposta.de_registro(registro_valido())
        self.assertEqual(proposta.id_proposta, "PROP-001")
        self.assertEqual(proposta.cliente.idade, 30)
        self.assertEqual(proposta.valor_solicitado, 4200.0)
        self.assertEqual(proposta.prazo, 12)

    def test_calculos_derivados(self):
        proposta = Proposta.de_registro(registro_valido())
        self.assertEqual(proposta.parcela_base, 350.0)
        self.assertEqual(proposta.comprometimento_percentual, 10.0)

    def test_comprometimento_exatamente_30_porcento(self):
        proposta = Proposta.de_registro(registro_valido(renda_mensal=1500.0, valor_solicitado=5400.0))
        self.assertEqual(proposta.comprometimento_percentual, 30.0)

    def test_comprometimento_arredondado_a_4_casas(self):
        proposta = Proposta.de_registro(registro_valido(renda_mensal=3000.0, valor_solicitado=1000.0, prazo=6))
        self.assertEqual(proposta.comprometimento_percentual, 5.5556)

    def test_para_prolog_segue_o_contrato(self):
        esperado = {
            "id": "PROP-001",
            "idade": 30,
            "renda_mensal": 3500.0,
            "historico_credito": "bom",
            "prazo": 12,
            "parcela_base": 350.0,
            "comprometimento_percentual": 10.0,
        }
        self.assertEqual(Proposta.de_registro(registro_valido()).para_prolog(), esperado)

    def test_para_lisp_segue_o_contrato(self):
        esperado = {
            "id": "PROP-001",
            "renda_mensal": 3500.0,
            "historico_credito": "bom",
            "valor_solicitado": 4200.0,
            "prazo": 12,
            "comprometimento_percentual": 10.0,
        }
        self.assertEqual(Proposta.de_registro(registro_valido()).para_lisp(), esperado)

    def test_prazo_positivo_fora_de_6_e_12_e_aceito_para_o_prolog_reprovar(self):
        self.assertEqual(Proposta.de_registro(registro_valido(prazo=7)).prazo, 7)

    def test_chave_ausente(self):
        for chave in registro_valido():
            registro = registro_valido()
            del registro[chave]
            with self.subTest(chave=chave), self.assertRaises(ErroValidacao) as contexto:
                Proposta.de_registro(registro)
            self.assertIn(chave, str(contexto.exception))

    def test_registro_que_nao_e_objeto(self):
        for registro in (None, [], "PROP-001", 42):
            with self.subTest(registro=registro), self.assertRaises(ErroValidacao):
                Proposta.de_registro(registro)

    def test_valores_invalidos(self):
        casos = [
            {"id": 1},
            {"id": ""},
            {"idade": -5},
            {"idade": "30"},
            {"renda_mensal": 0},
            {"renda_mensal": -1.0},
            {"renda_mensal": "3500"},
            {"valor_solicitado": 0},
            {"valor_solicitado": -4200.0},
            {"valor_solicitado": "4200"},
            {"prazo": 0},
            {"prazo": -12},
            {"prazo": 12.0},
            {"prazo": "12"},
            {"prazo": True},
        ]
        for alteracao in casos:
            with self.subTest(alteracao=alteracao), self.assertRaises(ErroValidacao):
                Proposta.de_registro(registro_valido(**alteracao))


class TestAnaliseRisco(unittest.TestCase):
    def test_estado_inicial(self):
        analise = AnaliseRisco("PROP-001")
        self.assertEqual(analise.status, "PENDENTE")
        self.assertFalse(analise.aprovada)
        self.assertEqual(analise.valor_aprovado, 0.0)

    def test_reprovar(self):
        analise = AnaliseRisco("PROP-001")
        analise.reprovar(["renda_abaixo_do_minimo", "prazo_invalido"])
        self.assertEqual(analise.status, "REPROVADO")
        self.assertEqual(analise.para_dict(), {
            "id": "PROP-001",
            "status": "REPROVADO",
            "impedimentos": ["renda_abaixo_do_minimo", "prazo_invalido"],
            "precificacao": None,
            "erro": None,
        })

    def test_aprovar_usa_o_status_do_lisp(self):
        for status in ("APROVADO", "APROVADO_COM_CONDICOES"):
            analise = AnaliseRisco("PROP-001")
            analise.aprovar(precificacao("PROP-001", 4200.0, status))
            with self.subTest(status=status):
                self.assertEqual(analise.status, status)
                self.assertTrue(analise.aprovada)
                self.assertEqual(analise.valor_aprovado, 4200.0)
                self.assertEqual(analise.para_dict()["precificacao"]["valor_parcela_final"], 385.06)

    def test_registrar_erro(self):
        analise = AnaliseRisco("PROP-001")
        analise.registrar_erro("ERRO_VALIDACAO", "chave ausente: prazo")
        self.assertEqual(analise.para_dict(), {
            "id": "PROP-001",
            "status": "ERRO_VALIDACAO",
            "impedimentos": [],
            "precificacao": None,
            "erro": "chave ausente: prazo",
        })

    def test_para_dict_devolve_copias(self):
        analise = AnaliseRisco("PROP-001")
        analise.reprovar(["prazo_invalido"])
        analise.para_dict()["impedimentos"].append("outro")
        self.assertEqual(analise.para_dict()["impedimentos"], ["prazo_invalido"])

    def test_reprovar_nao_guarda_referencia_da_lista_original(self):
        impedimentos = ["prazo_invalido"]
        analise = AnaliseRisco("PROP-001")
        analise.reprovar(impedimentos)
        impedimentos.append("outro")
        self.assertEqual(analise.para_dict()["impedimentos"], ["prazo_invalido"])


class TestExcecoes(unittest.TestCase):
    def test_hierarquia(self):
        self.assertTrue(issubclass(ErroValidacao, ErroCredito))
        self.assertTrue(issubclass(ErroIntegracao, ErroCredito))
        self.assertFalse(issubclass(ErroValidacao, ErroIntegracao))


class TestMergeSort(unittest.TestCase):
    def test_lista_vazia_e_com_um_elemento(self):
        self.assertEqual(merge_sort([], lambda x: x), [])
        self.assertEqual(merge_sort([7], lambda x: x), [7])

    def test_ordena_numeros_desordenados(self):
        self.assertEqual(merge_sort([5, 2, 9, 1, 5, 6], lambda x: x), [1, 2, 5, 5, 6, 9])

    def test_ja_ordenada_e_inversa(self):
        self.assertEqual(merge_sort([1, 2, 3, 4], lambda x: x), [1, 2, 3, 4])
        self.assertEqual(merge_sort([4, 3, 2, 1], lambda x: x), [1, 2, 3, 4])

    def test_e_estavel_com_chaves_iguais(self):
        itens = [("a", 2), ("b", 1), ("c", 2), ("d", 1)]
        self.assertEqual(merge_sort(itens, lambda item: item[1]),
                         [("b", 1), ("d", 1), ("a", 2), ("c", 2)])

    def test_nao_altera_a_lista_original(self):
        original = [3, 1, 2]
        merge_sort(original, lambda x: x)
        self.assertEqual(original, [3, 1, 2])


class TestOrdenarAprovadasPorValor(unittest.TestCase):
    def test_ordena_so_as_aprovadas_em_ordem_crescente(self):
        reprovada = AnaliseRisco("PROP-004")
        reprovada.reprovar(["idade_abaixo_do_minimo"])
        com_erro = AnaliseRisco("PROP-005")
        com_erro.registrar_erro("ERRO_INTEGRACAO", "tempo limite")
        analises = [
            analise_aprovada("PROP-001", 8000.0),
            reprovada,
            analise_aprovada("PROP-002", 1500.0),
            com_erro,
            analise_aprovada("PROP-003", 20000.0),
        ]
        ordenadas = ordenar_aprovadas_por_valor(analises)
        self.assertEqual([a.id_proposta for a in ordenadas], ["PROP-002", "PROP-001", "PROP-003"])

    def test_sem_aprovadas_devolve_lista_vazia(self):
        self.assertEqual(ordenar_aprovadas_por_valor([]), [])
        reprovada = AnaliseRisco("PROP-001")
        reprovada.reprovar(["prazo_invalido"])
        self.assertEqual(ordenar_aprovadas_por_valor([reprovada]), [])


if __name__ == "__main__":
    unittest.main()
