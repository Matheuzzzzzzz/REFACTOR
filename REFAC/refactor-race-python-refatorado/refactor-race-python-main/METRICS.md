# METRICS

Preencha com os valores **reais** obtidos no Colab. A coluna "Antes" deve ser medida no
código original (primeiro commit / zip original), antes de aplicar a refatoração.

| Indicador | Antes | Depois |
|---|---|---|
| Testes passando | [preencher: `pytest -v`] | [preencher: `pytest -v`] |
| Quantidade de testes | 4 | 48 (confirmar em `pytest -v`) |
| Cobertura de testes | [preencher: `pytest --cov=legacy_checkout --cov-report=term-missing`] | [preencher] |
| Complexidade da função principal | [preencher: `radon cc ... -s -a`, `process_order`] | [preencher: `process_order`] |
| Complexidade média | [preencher: média do `radon cc ... -a`] | [preencher] |
| Índice de manutenibilidade | [preencher: `radon mi ... -s`] | [preencher] |
| Problemas identificados pelo Ruff | [preencher: `ruff check ... --statistics`] | [preencher] |

## Como reproduzir
```
pip install -r requirements-dev.txt
pytest -v
pytest --cov=legacy_checkout --cov-report=term-missing
radon cc src/legacy_checkout.py -s -a
radon mi src/legacy_checkout.py -s
ruff check src/legacy_checkout.py --statistics
```
