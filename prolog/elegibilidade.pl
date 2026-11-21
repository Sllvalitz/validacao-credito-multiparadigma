% Responsavel: Chico
:- use_module(library(http/json)).

renda_minima_exigida(1500.0).
idade_minima_exigida(18).
comprometimento_maximo_permitido(30.0).
comprometimento_maximo_historico_ruim(15.0).

prazo_permitido(6).
prazo_permitido(12).

historico_sem_restricao(bom).
historico_sem_restricao(regular).

criterio(renda_minima, renda_abaixo_do_minimo).
criterio(idade_minima, idade_abaixo_do_minimo).
criterio(prazo_valido, prazo_invalido).
criterio(historico_aceito, historico_nao_aceito).
criterio(comprometimento_renda, comprometimento_acima_30_porcento).

campo_obrigatorio(id, texto).
campo_obrigatorio(idade, inteiro).
campo_obrigatorio(renda_mensal, numero).
campo_obrigatorio(historico_credito, texto).
campo_obrigatorio(prazo, inteiro).
campo_obrigatorio(parcela_base, numero).
campo_obrigatorio(comprometimento_percentual, numero).

valor_valido(texto, Valor) :-
    string(Valor).
valor_valido(inteiro, Valor) :-
    integer(Valor).
valor_valido(numero, Valor) :-
    number(Valor).

validar_campos([], _).
validar_campos([campo(Chave, Tipo) | Resto], Entrada) :-
    (   get_dict(Chave, Entrada, Valor)
    ->  true
    ;   throw(error(chave_ausente(Chave), _))
    ),
    (   valor_valido(Tipo, Valor)
    ->  true
    ;   throw(error(tipo_invalido(Chave), _))
    ),
    validar_campos(Resto, Entrada).

validar_entrada(Entrada) :-
    (   is_dict(Entrada)
    ->  true
    ;   throw(error(entrada_invalida(objeto_json_esperado), _))
    ),
    findall(campo(Chave, Tipo), campo_obrigatorio(Chave, Tipo), Campos),
    validar_campos(Campos, Entrada).

historico_valido(Historico, _) :-
    historico_sem_restricao(Historico).
historico_valido(ruim, Comprometimento) :-
    comprometimento_maximo_historico_ruim(Limite),
    Comprometimento =< Limite.

criterio_satisfeito(renda_minima, Proposta) :-
    renda_minima_exigida(Minimo),
    Proposta.renda_mensal >= Minimo.
criterio_satisfeito(idade_minima, Proposta) :-
    idade_minima_exigida(Minima),
    Proposta.idade >= Minima.
criterio_satisfeito(prazo_valido, Proposta) :-
    prazo_permitido(Proposta.prazo).
criterio_satisfeito(historico_aceito, Proposta) :-
    atom_string(Historico, Proposta.historico_credito),
    historico_valido(Historico, Proposta.comprometimento_percentual).
criterio_satisfeito(comprometimento_renda, Proposta) :-
    comprometimento_maximo_permitido(Maximo),
    Proposta.comprometimento_percentual =< Maximo.

avaliar_criterios([], _, [], []).
avaliar_criterios([criterio(Regra, _) | Resto], Proposta, [Regra | Satisfeitas], Impedimentos) :-
    criterio_satisfeito(Regra, Proposta),
    !,
    avaliar_criterios(Resto, Proposta, Satisfeitas, Impedimentos).
avaliar_criterios([criterio(_, Impedimento) | Resto], Proposta, Satisfeitas, [Impedimento | Impedimentos]) :-
    avaliar_criterios(Resto, Proposta, Satisfeitas, Impedimentos).

determinar_elegibilidade([], true).
determinar_elegibilidade([_ | _], false).

avaliar_proposta(Proposta, Parecer) :-
    findall(criterio(Regra, Impedimento), criterio(Regra, Impedimento), Criterios),
    avaliar_criterios(Criterios, Proposta, RegrasSatisfeitas, Impedimentos),
    determinar_elegibilidade(Impedimentos, Elegivel),
    Parecer = _{
        id: Proposta.id,
        elegivel: Elegivel,
        regras_satisfeitas: RegrasSatisfeitas,
        impedimentos: Impedimentos
    }.

executar :-
    json_read_dict(current_input, Entrada),
    validar_entrada(Entrada),
    avaliar_proposta(Entrada, Parecer),
    json_write_dict(current_output, Parecer, [width(0)]),
    nl(current_output),
    flush_output(current_output).

main :-
    catch(
        (   executar
        ->  true
        ;   format(user_error, 'Erro ao avaliar proposta~n', []),
            halt(1)
        ),
        Erro,
        (   format(user_error, 'Erro: ~w~n', [Erro]),
            halt(1)
        )
    ).
