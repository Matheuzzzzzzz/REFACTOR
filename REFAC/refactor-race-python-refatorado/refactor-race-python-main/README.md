# REFactor Race Python

## EQUIPE
- [PREENCHER] Integrante 1
- [PREENCHER] Integrante 2
- [PREENCHER] Integrante 3

## DESCRIÇÃO
Sistema de processamento de pedidos (`src/legacy_checkout.py`) recebido em estado legado.
A função `process_order` calcula subtotal, descontos (tipo de cliente e cupons), frete,
impostos, pontos de fidelidade e produtos duplicados. O objetivo foi melhorar a qualidade
interna **sem alterar o comportamento**, comprovando o resultado com testes e métricas.

Como executar (raiz do repositório):
```
pip install -r requirements-dev.txt
pytest -v
pytest --cov=legacy_checkout --cov-report=term-missing
radon cc src/legacy_checkout.py -s -a
radon mi src/legacy_checkout.py -s
ruff check src/legacy_checkout.py --statistics
```
O `pytest.ini` já configura `pythonpath = src`.

## DIAGNÓSTICO INICIAL
1. `process_order` concentra ~10 responsabilidades (subtotal, descontos, cupons, teto de
   desconto, peso, frete, imposto, pontos, duplicados, impressão e persistência): baixa coesão e
   função muito longa, difícil de testar por partes.
2. Código duplicado: o subtotal é calculado duas vezes (`total1` e `subtotal`) e `total1`
   nunca é usado.
3. Condicionais aninhadas em cascata (`else: if ... else: if ...`) para o desconto por tipo de
   cliente; cadeia `if/elif` repetitiva para impostos.
4. Condicional verbosa `state == "MG" or state == "SP" or ...` no frete.
5. Números mágicos (0.15, 0.10, 0.20, 1000, 800, 500, 1.8, 0.4, 0.6, 20, 35, 0.12, 5, 10...) e
   strings mágicas (`"vip"`, `"PROMO10"`...) espalhados pelo código.
6. Nomes pouco claros e mistura de idiomas (`total1`, `taxa`, `peso`, `frete`, `valor_com_desconto`).
7. Comparações com booleanos (`express == False`, `express == True`).
8. Busca de duplicados com dois laços aninhados: O(n²) comparações e `not in` em lista.
9. Efeitos colaterais misturados ao cálculo: `print` e alteração do estado global
   `ORDERS_PROCESSED` dentro da mesma função.
10. Comentários usados para explicar código confuso ("procura produtos repetidos de forma
    bem pouco elegante").
11. Baixa testabilidade: só era possível testar via `process_order` completo.

## CODE SMELLS ENCONTRADOS
| Code smell | Onde | Por que é problema |
|---|---|---|
| Long Method / God Function | `process_order` | Muitas razões para mudar; difícil de ler e testar |
| Duplicated Code | `total1` / `subtotal` | Duas fontes de verdade para o mesmo valor |
| Deeply nested conditionals | desconto por tipo | Caminhos difíceis de seguir; alta complexidade ciclomática |
| Magic Numbers / Strings | descontos, frete, impostos, cupons | Regras de negócio escondidas e difíceis de alterar |
| Primitive comparison chains | estados no frete e imposto | Repetição; deveria ser dado (conjunto/mapeamento) |
| Dead code | `total1` | Variável calculada e nunca usada |
| Inefficient algorithm | duplicados O(n²) | Custo cresce quadraticamente com o número de itens |
| Mixed responsibilities | `print` + estado global | Cálculo acoplado a I/O e a efeitos colaterais |
| Poor naming | `x`, `taxa`, `frete`... | Nomes não revelam intenção |

## REFATORAÇÕES REALIZADAS
**1. Extract Function (uma função por regra de negócio)**
- Problema: `process_order` fazia tudo.
- Alteração: `calculate_subtotal`, `calculate_total_weight`, `calculate_customer_discount`,
  `calculate_coupon_discount`, `calculate_discount`, `calculate_shipping`, `calculate_tax`,
  `calculate_loyalty_points`, `find_duplicate_products`, `print_order_summary`.
- Justificativa: cada regra pode ser lida e testada isoladamente; `process_order` virou uma
  orquestração curta.

**2. Remove Duplicate Code / Dead Code**
- Problema: subtotal calculado duas vezes; `total1` sem uso.
- Alteração: um único `calculate_subtotal`.
- Justificativa: uma só fonte de verdade e menos código para manter.

**3. Simplify Conditional + Guard Clauses (desconto por tipo de cliente)**
- Problema: `else: if ... else: if ...` aninhados.
- Alteração: `if/if/if` com retornos antecipados.
- Justificativa: leitura linear, sem aninhamento.

**4. Replace Conditional with Mapping (impostos)**
- Problema: cadeia `if/elif` por estado.
- Alteração: `TAX_RATES` (dict) + `DEFAULT_TAX_RATE` e `TAX_RATES.get(state, DEFAULT_TAX_RATE)`.
- Justificativa: incluir/alterar um estado passa a ser alteração de dado, não de lógica.

**5. Simplify Conditional (frete)**
- Problema: `state == "MG" or state == "SP" or ...` e `express == True/False`.
- Alteração: `state in REGIONAL_SHIPPING_STATES` (frozenset) e `not express` / `if express`.
- Justificativa: mais legível e sem comparações com booleanos.

**6. Replace Magic Number/String with Constant**
- Problema: números e textos fixos espalhados.
- Alteração: constantes nomeadas agrupadas por assunto (`EXPRESS_SHIPPING_MULTIPLIER`,
  `MAX_DISCOUNT_RATE`, `COUPON_PROMO10`, `CUSTOMER_VIP`...).
- Justificativa: regras de negócio visíveis e alteráveis em um único lugar.

**7. Otimização de algoritmo (duplicados)**
- Problema: dois laços aninhados (O(n²)).
- Alteração: `collections.Counter` (uma passada, O(n)); resultado na mesma ordem
  (primeira ocorrência de cada nome).
- Justificativa: mesmo resultado com muito menos comparações. É refatoração **e** otimização.

**8. Separate Responsibilities**
- Problema: `print` misturado ao cálculo.
- Alteração: `print_order_summary` isolada; a saída impressa foi mantida idêntica.
- Justificativa: o cálculo não depende mais de I/O.

**Ponto de atenção (comportamento preservado).** Ao trocar o laço `+=` por `sum()`, os
testes diferenciais mostraram diferenças de ponto flutuante nas últimas casas
(o `sum()` do Python 3.12 usa soma compensada). Por isso `calculate_subtotal` e
`calculate_total_weight` mantêm acumulação explícita. Isso é uma decisão para preservar o
comportamento, não um esquecimento.

## TESTES ADICIONADOS
Os 4 testes originais foram mantidos. Foram adicionados (nomes descrevem o comportamento):
- 26 cenários parametrizados de pedido completo: VIP abaixo/no limite de 1000; funcionário;
  regular abaixo/no limite de 800; tipo desconhecido; PROMO10, PROMO20 (499 e 500), VIP50
  (VIP e não VIP); cupom desconhecido e em minúsculas (comportamento atual: diferencia
  maiúsculas); teto de 25%; frete grátis a partir de 500; frete regional e nacional; frete
  expresso (nunca grátis); impostos de SP, RJ, ES e demais estados; pontos VIP x regular;
  pedido vazio.
- Itens com quantidade <= 0, item sem peso, produtos duplicados (várias repetições e sem
  repetição), registro em `ORDERS_PROCESSED` e texto impresso.
- Testes unitários das funções extraídas.

Os valores esperados foram obtidos executando a **versão legada original** (testes de
caracterização), sem inventar regras. Foi feito também um teste diferencial com 20.000
pedidos aleatórios comparando original x refatorado (retorno, saída impressa e
`ORDERS_PROCESSED`), todos idênticos.

## MÉTRICAS ANTES E DEPOIS
Ver `METRICS.md`.

## DECISÕES TÉCNICAS
- Manter o nome do módulo `legacy_checkout.py` e a assinatura de `process_order`, além do
  formato do dicionário retornado, da saída impressa e de `ORDERS_PROCESSED`, para não
  quebrar quem já usa o módulo (inclusive testes adicionais do professor).
- Nenhuma regra de negócio foi alterada. Cupons continuam diferenciando maiúsculas e
  minúsculas e a quantidade <= 0 continua sendo ignorada no subtotal (isso só muda com os
  tickets liberados pelo professor).
- Constantes no próprio módulo (sem novas dependências nem novos arquivos).
- `pytest.ini` com `pythonpath = src` para os testes importarem `legacy_checkout`.
- Nota: `express` agora é tratado por verdade (`not express`). Para `True`/`False`, que são
  os valores esperados, o resultado é idêntico ao original.

## USO DE INTELIGÊNCIA ARTIFICIAL
- Ferramenta utilizada: Claude (Anthropic)
- Finalidade: apoio à análise do código legado, proposta da refatoração, geração dos testes
  de caracterização e do teste diferencial, e rascunho deste README.
- Exemplo de sugestão recebida: extrair as regras de negócio em funções `calculate_*` e
  trocar a busca de duplicados por `Counter`.
- A sugestão foi aceita, modificada ou rejeitada? [PREENCHER — ex.: aceita com modificação:
  a troca de laços por `sum()` foi rejeitada por alterar o ponto flutuante]
- Como a equipe validou a solução? [PREENCHER — ex.: `pytest`, cobertura, Radon, Ruff no
  Colab e revisão do código pela equipe]

## MELHORIAS FUTURAS
- Separar em módulos (`discounts.py`, `shipping.py`, `taxes.py`) e tornar `print` e o
  histórico injetáveis (remover o estado global `ORDERS_PROCESSED`).
- Usar `Decimal` para valores monetários no lugar de `float`.
- Substituir dicionários por `dataclass`/tipos para cliente e item, com validação de entrada.
- Tickets previstos: quantidade inválida (`ValueError`), cupons sem diferenciar maiúsculas
  e minúsculas, e regra de pontos de fidelidade.
