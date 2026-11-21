;;;; Responsavel: Isabelle

(require :asdf)

(defun carregar-yason-em-silencio ()
  (let ((*standard-output* (make-broadcast-stream))
        (*error-output* (make-broadcast-stream))
        (*load-verbose* nil)
        (*compile-verbose* nil)
        (*compile-print* nil)
        (configuracao-quicklisp
          (merge-pathnames "quicklisp/setup.lisp" (user-homedir-pathname))))
    (when (probe-file configuracao-quicklisp)
      (load configuracao-quicklisp))
    (if (find-package "QL")
        (funcall (find-symbol "QUICKLOAD" "QL") "yason" :silent t)
        (asdf:load-system "yason"))))

(carregar-yason-em-silencio)

(defparameter *teto-credito* 20000d0)

(defparameter *fracao-da-renda* 3/10)

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

(defun sequencia (inicio fim)
  (if (> inicio fim)
      '()
      (cons inicio (sequencia (1+ inicio) fim))))

(defun arredondar-centavos (valor)
  (/ (round (* valor 100)) 100d0))

(defun classificar-risco (historico comprometimento)
  (first (remove-if-not
          (lambda (faixa)
            (funcall (faixa-regra faixa) historico comprometimento))
          *faixas-risco*)))

(defun limite-credito (renda prazo)
  (arredondar-centavos (min (* renda *fracao-da-renda* prazo) *teto-credito*)))

(defun valor-aprovado (valor-solicitado limite)
  (min (arredondar-centavos valor-solicitado) limite))

(defun fator-anuidade (taxa prazo)
  (reduce #'+
          (mapcar (lambda (mes) (expt (1+ taxa) (- mes)))
                  (sequencia 1 prazo))
          :initial-value 0d0))

(defun parcela-price (valor taxa prazo)
  (/ valor (fator-anuidade taxa prazo)))

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

(defun formatar-decimal (valor casas)
  (multiple-value-bind (inteiro fracao)
      (floor (round (* valor (expt 10 casas))) (expt 10 casas))
    (format nil "~D.~V,'0D" inteiro casas fracao)))

(defun texto-json (texto)
  (with-output-to-string (saida)
    (yason:encode texto saida)))

(defun par-json (par)
  (format nil "\"~A\":~A" (car par) (cdr par)))

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

(defun ler-proposta ()
  (let ((*read-default-float-format* 'double-float))
    (yason:parse *standard-input* :object-as :alist)))

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
