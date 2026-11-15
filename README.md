# Consulta de vendas da EVO

Este projeto consulta vendas da API EVO para duas filiais e salva os registros recebidos em um arquivo CSV. O script principal é `fVendas.py`.

## Requisitos

- Python 3.9 ou superior.
- Acesso à internet e credenciais válidas da API EVO para cada filial.
- Os pacotes listados em `requirements.txt`:
  - `pandas`: organiza os registros e grava o CSV.
  - `requests`: faz as chamadas HTTP para a API.
  - `python-dotenv`: carrega as configurações do arquivo `.env`.

`os`, `time` e `datetime` são módulos da biblioteca padrão do Python e não precisam ser instalados.

## Instalação no Windows

Abra o PowerShell na pasta do projeto e crie um ambiente virtual:

```powershell
py -m venv .venv
```

Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se a política do PowerShell impedir a ativação, também é possível usar o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

Com o ambiente virtual ativo, instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

## Configuração das credenciais

Crie ou edite o arquivo `.env` na mesma pasta de `fVendas.py`. Preencha-o com o endereço do endpoint e as credenciais das duas filiais:

```dotenv
URL_S=https://evo-integracao-api.w12app.com.br/api/v2/sales
APP_DNS_S=seu_dns_da_filial_a
APP_TOKEN_S=seu_token_da_filial_a
APP_DNS_C=seu_dns_da_filial_b
APP_TOKEN_C=seu_token_da_filial_b
```

Substitua os valores de exemplo pelos dados fornecidos para a sua integração. Não compartilhe o `.env`, não coloque credenciais no código e não envie tokens em capturas de tela ou logs.

O nome `URL_S` é o nome da variável que o script procura; o valor deve ser o endereço completo do endpoint de vendas. As variáveis `APP_DNS_S` e `APP_TOKEN_S` formam o par de autenticação da Filial A. `APP_DNS_C` e `APP_TOKEN_C` formam o par da Filial B. Os nomes “Filial A” e “Filial B” são rótulos definidos no código e podem ser alterados em `CREDENCIAIS_FILIAIS`.

> **Atenção:** atualmente, o script imprime os quatro primeiros caracteres do token de cada filial no terminal. Evite compartilhar essa saída. Para não exibir nenhuma parte do token, remova ou comente a linha `print(f"Token de {nome_filial}: {token[:4]}***")` em `fVendas.py`.

## Como executar

Com o ambiente virtual ativo e o arquivo `.env` preenchido, execute na pasta do projeto:

```powershell
python fVendas.py
```

O arquivo `.env` precisa estar acessível na pasta de execução para que `load_dotenv()` carregue as variáveis.

## Como o código funciona

1. **Carrega configurações:** `load_dotenv()` lê o `.env`. O script obtém o endpoint e os pares DNS/token das duas filiais.
2. **Abre uma sessão HTTP:** `requests.Session()` reutiliza a sessão durante as chamadas e a fecha ao terminar.
3. **Consulta cada filial:** para cada par de credenciais, faz uma requisição GET ao endpoint configurado.
4. **Autentica a requisição:** `auth=(dns, token)` pede ao `requests` que gere o cabeçalho HTTP Basic a partir do DNS e do token. Isso corresponde ao cabeçalho `Authorization: Basic ...` dos exemplos da documentação.
5. **Busca em páginas:** envia `take=50` e `skip` como parâmetros da URL. A primeira chamada começa em `skip=0`; quando uma página vem completa, o script avança `skip` pela quantidade recebida e espera um segundo antes de pedir a próxima.
6. **Interpreta a resposta:** espera JSON e `extrair_registros()` normaliza os formatos aceitos: uma lista de vendas, um objeto com a lista na chave `registros` ou um objeto representando uma venda com `idSale`.
7. **Identifica a filial:** acrescenta `filial_consulta` a cada registro para indicar de qual filial veio.
8. **Trata falhas:** registra erros de requisição, status HTTP não bem-sucedidos ou formato de resposta inesperado. Uma falha interrompe a paginação daquela filial, mas as outras ainda podem ser consultadas.
9. **Gera o CSV:** se houver vendas, salva-as em `vendas_AAAAmmdd_HHMMSS.csv`, na pasta de execução, com codificação `utf-8-sig` para facilitar a abertura no Excel. Se nenhuma venda for recebida, informa isso e não cria o arquivo.

### Adaptação dos exemplos da documentação da EVO

A documentação mostra exemplos usando `http.client` e `requests.request`. Este projeto usa `requests.Session().get`, que também faz uma requisição GET, mas permite reutilizar a sessão nas consultas de várias páginas e filiais.

Em vez de montar manualmente a URL com os parâmetros depois de `?`, o script passa `params={"take": 50, "skip": skip}`. O `requests` codifica esses parâmetros e os acrescenta à URL. A documentação lista outros filtros, mas este código envia somente `take` e `skip`; portanto, não aplica filtros de filial, datas ou tipo de venda. Também não envia `payload` ou `data`, pois a chamada GET não precisa de corpo.

## Arquivos gerados e avisos

- O CSV é criado na pasta de onde o comando `python fVendas.py` foi executado.
- Uma execução pode gerar um CSV parcial se uma filial falhar depois que outras vendas já foram coletadas. Nesse caso, o terminal informa que houve falhas.
- O script não sobrescreve os CSVs anteriores, pois inclui data e hora no nome do arquivo.
