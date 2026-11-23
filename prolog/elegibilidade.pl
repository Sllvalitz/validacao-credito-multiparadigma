% Fronteira 1 do contrato: recebe UMA proposta em stdin e devolve o parecer em stdout.
% Sem estado global: nada de assert/retract, todo o estado trafega nos argumentos.

:- use_module(library(http/json)).

% constantes de negocio do contrato v1.1: alterar somente aqui
renda_minima(1500.0).
idade_minima(18).
comprometimento_maximo(30.0).
% historico "ruim" so e aceito com comprometimento baixo (decisao da equipe)
comprometimento_maximo_historico_ruim(15.0).
prazo_permitido(6).
prazo_permitido(12).

% criterio(Nome, Impedimento): a ordem destes fatos define a ordem das listas na resposta
criterio(renda_minima, renda_abaixo_do_minimo).
criterio(idade_minima, idade_abaixo_do_minimo).
criterio(prazo_valido, prazo_invalido).
criterio(historico_aceito, historico_nao_aceito).
criterio(comprometimento_renda, comprometimento_acima_30_porcento).

% satisfeito(+Criterio, +Proposta), com Proposta = proposta(Idade, Renda, Historico, Prazo, Comprometimento)
satisfeito(renda_minima, proposta(_, Renda, _, _, _)) :-
    renda_minima(Minima),
    Renda >= Minima.
satisfeito(idade_minima, proposta(Idade, _, _, _, _)) :-
    idade_minima(Minima),
    Idade >= Minima.
% prazo_permitido/1 tem um fato por prazo valido, e a unificacao faz a checagem
satisfeito(prazo_valido, proposta(_, _, _, Prazo, _)) :-
    prazo_permitido(Prazo).
% tres clausulas para o mesmo criterio expressam a alternativa (bom OU regular OU ruim restrito)
satisfeito(historico_aceito, proposta(_, _, bom, _, _)).
satisfeito(historico_aceito, proposta(_, _, regular, _, _)).
satisfeito(historico_aceito, proposta(_, _, ruim, _, Comprometimento)) :-
    comprometimento_maximo_historico_ruim(Limite),
    Comprometimento =< Limite.
satisfeito(comprometimento_renda, proposta(_, _, _, _, Comprometimento)) :-
    comprometimento_maximo(Maximo),
    Comprometimento =< Maximo.

% recursao sobre a lista de criterios: cada passo separa o criterio entre satisfeito e impedimento;
% o if-then-else descarta os pontos de escolha de satisfeito/2 (so a primeira prova importa)
avaliar_criterios([], _, [], []).
avaliar_criterios([Nome-Impedimento|Resto], Proposta, Satisfeitas, Impedimentos) :-
    avaliar_criterios(Resto, Proposta, SatisfeitasResto, ImpedimentosResto),
    (   satisfeito(Nome, Proposta)
    ->  Satisfeitas = [Nome|SatisfeitasResto],
        Impedimentos = ImpedimentosResto
    ;   Satisfeitas = SatisfeitasResto,
        Impedimentos = [Impedimento|ImpedimentosResto]
    ).

% findall/3 e nao setof/bagof: preserva a ordem dos fatos de criterio/2 e nunca falha
avaliar(Proposta, Satisfeitas, Impedimentos) :-
    findall(Nome-Impedimento, criterio(Nome, Impedimento), Criterios),
    avaliar_criterios(Criterios, Proposta, Satisfeitas, Impedimentos).

% o historico chega como string no JSON; atom_string o converte em atomo para unificar com bom/regular/ruim
proposta_de(Dict, proposta(Idade, Renda, Historico, Prazo, Comprometimento)) :-
    Idade = Dict.idade,
    Renda = Dict.renda_mensal,
    atom_string(Historico, Dict.historico_credito),
    Prazo = Dict.prazo,
    Comprometimento = Dict.comprometimento_percentual.

executar :-
    json_read_dict(user_input, Entrada),
    proposta_de(Entrada, Proposta),
    avaliar(Proposta, Satisfeitas, Impedimentos),
    % contrato: elegivel e verdadeiro exatamente quando nao ha impedimentos
    (   Impedimentos == []
    ->  Elegivel = true
    ;   Elegivel = false
    ),
    Saida = _{id: Entrada.id,
              elegivel: Elegivel,
              regras_satisfeitas: Satisfeitas,
              impedimentos: Impedimentos},
    json_write_dict(current_output, Saida, [width(0)]),
    nl.

% qualquer excecao (JSON invalido, chave ausente) vai para o stderr com codigo 2,
% que o Python converte em ERRO_INTEGRACAO
main :-
    set_stream(user_input, encoding(utf8)),
    catch(executar, Erro, (print_message(error, Erro), halt(2))).
