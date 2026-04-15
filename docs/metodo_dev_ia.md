# Metodos Dsenvolvimento com IA - Workflow

## Problemas comuns do desenvolvimento com IA

1 - Overengineering
2 - Reiventar a Roda
3 - Não Saber fazer e não falar que não sabe
4 - Repete Trechos de Código
5 - Junta tudo no mesmo lugar

## Qualidade do Input

1 - Informações Incorretas
2 - Informações Incompletas
3 - Informações Inúteis
1 - Informações Demais

## Fluxo do Workflow

1 - Pesquisa
2 - Specs
3 - Code

## 1 - Pesquisa

### Imput

- Eu preciso Implementar XXXX
- Descreva o que deseja fazer de maneira sucinta e clara

### Pesquise

Indique os lugares que ele deve procurar

- Na Code Base
  - Para entender quais arquivos vão ser afetados com a nova implementação.
  - Padrões de implementação de coisas similares para reaproveitar

- Na Documentação
  - Buscar Doumentação das Tecnologias que serão usadas

- Busque padrões de implementação
  - No gitHub
  - Na Documentação Oficial
  - No Stack Overflow
  - Documentação própria (pasta)

### Output

- Arquivo Pesquisa e Desenvolvimento (PRD.md)
  - Resumo de tudo que ele achou na pesquisa.
  - Arquivos da Base de código que são relevantes
  - Remover arquivos inuteis
  - Links e Trechos dos documentos
  - Codes Snippets

## 2 - SPECS

- Suba o PRD.MD como Input inicial de um novo Prompt (limpo)
- Peça para o Modelo ler o PRD.MD e gerar uma Especificação
- Espec tatica

### Especificação deve ter

- Arquivos da base de Código que devem ser criados
- Arquivos da base de Código que devem ser alterados
- O que deve ser Criado ou Modificado
- Code snippets
- PATH do Arquivo -> e o que deve fazer

### Output 2

- SPEC.md

## 3 - CODE

- Implemente essa SPEC
- Suba o SPEC.MD como Input inicial de um novo Prompt (limpo)

### Output 3

- Codigo Inicial
