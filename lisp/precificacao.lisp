;;;; Responsavel: Isabelle

(require :asdf)

;; silencia stdout e stderr: na primeira execucao o ASDF imprime mensagens de compilacao,
;; que corromperiam o JSON de resposta em stdout
(defun carregar-yason-em-silencio ()
  (let ((*standard-output* (make-broadcast-stream))
        (*error-output* (make-broadcast-stream))
        (*load-verbose* nil)
        (*compile-verbose* nil)
        (*compile-print* nil)
        (configuracao-quicklisp
          (merge-pathnames "quicklisp/setup.lisp" (user-homedir-pathname))))
    ;; usa o Quicklisp se estiver instalado (Windows nativo); senao o ASDF acha o yason do apt
    (when (probe-file configuracao-quicklisp)
      (load configuracao-quicklisp))
    (if (find-package "QL")
        (funcall (find-symbol "QUICKLOAD" "QL") "yason" :silent t)
        (asdf:load-system "yason"))))

(carregar-yason-em-silencio)

;; nucleo funcional: funcoes puras sobre listas, sem alterar argumentos nem estado global
;; (as defparameter abaixo sao constantes de negocio do contrato v1.1)
(defparameter *teto-credito* 20000d0)

(defparameter *fracao-da-renda* 3/10)

;; taxas como racionais exatos (7/200 = 3,5%); so viram double no calculo da parcela.
;; a ordem importa: classificar-risco devolve a primeira faixa que casa, entao "alto" vem
;; antes de "baixo" e "medio" e a ultima regra, sempre verdadeira, cobre os demais casos
(defparameter *faixas-risco*
  (list (list "alto"
              (lambda (historico comprometimento)
                (or (string= historico "ruim")
                    (and (string= historico "regular") (> comprometimento 20))))
              7/200
              "APROVADO_COM_CONDICOES")
        (list "baixo"
              (lambda (historico comprometimento)
                (and (string= historico "bom") (<= comprometimento 20)))
              3/200
              "APROVADO")
        (list "medio"
              (lambda (historico comprometimento)
                (declare (ignore historico comprometimento))
                t)
              1/40
              "APROVADO")))

(defun faixa-nome (faixa) (first faixa))

(defun faixa-regra (faixa) (second faixa))

(defun faixa-taxa (faixa) (third faixa))

(defun faixa-status (faixa) (fourth faixa))

;; recursao no lugar de um laco: gera a lista (inicio ... fim) para o mapcar e o reduce
(defun sequencia (inicio fim)
  (if (> inicio fim)
      '()
      (cons inicio (sequencia (1+ inicio) fim))))

;; valores monetarios sao arredondados a centavos e devolvidos como double
(defun arredondar-centavos (valor)
  (/ (round (* valor 100)) 100d0))

;; remove-if-not mantem so as faixas que casam e first escolhe a de maior prioridade
(defun classificar-risco (historico comprometimento)
  (first (remove-if-not
          (lambda (faixa)
            (funcall (faixa-regra faixa) historico comprometimento))
          *faixas-risco*)))

;; menor valor entre 30% da renda ao longo do prazo e o teto de credito
(defun limite-credito (renda prazo)
  (arredondar-centavos (min (* renda *fracao-da-renda* prazo) *teto-credito*)))

(defun valor-aprovado (valor-solicitado limite)
  (min (arredondar-centavos valor-solicitado) limite))

;; Tabela Price: valor / soma dos fatores de desconto (1+i)^-mes de cada mes do prazo;
;; mapcar calcula cada fator e reduce soma
(defun fator-anuidade (taxa prazo)
  (reduce #'+
          (mapcar (lambda (mes) (expt (1+ taxa) (- mes)))
                  (sequencia 1 prazo))
          :initial-value 0d0))

(defun parcela-price (valor taxa prazo)
  (/ valor (fator-anuidade taxa prazo)))

;; recursao no lugar de um laco: cada chamada calcula um mes e repassa o novo saldo,
;; sem alterar nenhuma variavel
(defun tabela-amortizacao (saldo taxa parcela mes prazo)
  (if (> mes prazo)
      '()
      (let* ((juros (* saldo taxa))
             (amortizacao (- parcela juros))
             (novo-saldo (- saldo amortizacao)))
        (cons (list mes juros amortizacao novo-saldo)
              (tabela-amortizacao novo-saldo taxa parcela (1+ mes) prazo)))))

(defun saldo-final (tabela)
  (fourth (car (last tabela))))

;; verificacao de consistencia: com a parcela de Price correta o saldo final e ~0;
;; a tolerancia de 1 centavo absorve o erro de ponto flutuante
(defun tabela-quita-o-saldo-p (tabela)
  (< (abs (saldo-final tabela)) 0.01d0))

(defun precificar (renda historico valor-solicitado prazo comprometimento)
  (let* ((faixa (classificar-risco historico comprometimento))
         (taxa (coerce (faixa-taxa faixa) 'double-float))
         (limite (limite-credito renda prazo))
         (aprovado (valor-aprovado valor-solicitado limite))
         (parcela (parcela-price aprovado taxa prazo))
         (tabela (tabela-amortizacao aprovado taxa parcela 1 prazo)))
    (unless (tabela-quita-o-saldo-p tabela)
      (error "tabela de amortizacao nao quita o saldo"))
    (list :status (faixa-status faixa)
          :classificacao-risco (faixa-nome faixa)
          :taxa-juros-mensal (faixa-taxa faixa)
          :limite-calculado limite
          :valor-aprovado aprovado
          :valor-parcela-final (arredondar-centavos parcela))))

;; os campos sao validados na fronteira: se o JSON vier com tipo errado o programa sai com erro
;; em vez de calcular e produzir uma resposta incorreta
(defun campo (proposta chave)
  (let ((par (assoc chave proposta :test #'string=)))
    (if par
        (cdr par)
        (error "campo ausente: ~A" chave))))

(defun campo-numerico-positivo (proposta chave)
  (let ((valor (campo proposta chave)))
    (if (and (realp valor) (> valor 0))
        (coerce valor 'double-float)
        (error "campo ~A deve ser numero positivo" chave))))

(defun campo-comprometimento (proposta)
  (let ((valor (campo proposta "comprometimento_percentual")))
    (if (and (realp valor) (>= valor 0))
        (coerce valor 'double-float)
        (error "campo comprometimento_percentual deve ser numero nao negativo"))))

(defun campo-prazo (proposta)
  (let ((valor (campo proposta "prazo")))
    (if (and (integerp valor) (> valor 0))
        valor
        (error "campo prazo deve ser inteiro positivo"))))

(defun campo-texto (proposta chave)
  (let ((valor (campo proposta chave)))
    (if (stringp valor)
        valor
        (error "campo ~A deve ser texto" chave))))

(defun precificar-proposta (proposta)
  (precificar (campo-numerico-positivo proposta "renda_mensal")
              (campo-texto proposta "historico_credito")
              (campo-numerico-positivo proposta "valor_solicitado")
              (campo-prazo proposta)
              (campo-comprometimento proposta)))

;; formata com casas fixas e sem o sufixo d0: o ~A de um double imprimiria 4200.0d0,
;; que nao e JSON valido
(defun formatar-decimal (valor casas)
  (multiple-value-bind (inteiro fracao)
      (floor (round (* valor (expt 10 casas))) (expt 10 casas))
    (format nil "~D.~V,'0D" inteiro casas fracao)))

(defun texto-json (texto)
  (with-output-to-string (saida)
    (yason:encode texto saida)))

(defun par-json (par)
  (format nil "\"~A\":~A" (car par) (cdr par)))

;; o JSON de resposta e montado a mao para controlar as casas decimais;
;; o yason so e usado para ler a entrada e para escapar os textos
(defun objeto-json (pares)
  (format nil "{~{~A~^,~}}" (mapcar #'par-json pares)))

(defun resposta-json (proposta resultado)
  (objeto-json
   (list (cons "id" (texto-json (campo proposta "id")))
         (cons "status" (texto-json (getf resultado :status)))
         (cons "classificacao_risco" (texto-json (getf resultado :classificacao-risco)))
         (cons "taxa_juros_mensal" (formatar-decimal (getf resultado :taxa-juros-mensal) 3))
         (cons "limite_calculado" (formatar-decimal (getf resultado :limite-calculado) 2))
         (cons "valor_aprovado" (formatar-decimal (getf resultado :valor-aprovado) 2))
         (cons "valor_parcela_final" (formatar-decimal (getf resultado :valor-parcela-final) 2)))))

;; sem double-float como formato padrao o yason leria decimais como single-float
;; e perderia precisao
(defun ler-proposta ()
  (let ((*read-default-float-format* 'double-float))
    (yason:parse *standard-input* :object-as :alist)))

;; unica funcao com efeitos colaterais (ler stdin, escrever stdout/stderr); em erro sai com
;; codigo 1, que o Python converte em ERRO_INTEGRACAO
(defun main ()
  (handler-case
      (let ((proposta (ler-proposta)))
        (write-line (resposta-json proposta (precificar-proposta proposta)))
        (finish-output))
    (error (erro)
      (format *error-output* "erro na precificacao: ~A~%" erro)
      (finish-output *error-output*)
      (sb-ext:exit :code 1))))

(main)
