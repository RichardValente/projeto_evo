import os  # Lê variáveis de ambiente para não deixar URLs e credenciais fixas no código.
import time  # Pausa entre páginas para reduzir a frequência das chamadas à API.
from datetime import datetime  # Cria um horário para identificar o arquivo CSV gerado.

import pandas as pd  # Organiza os registros em uma tabela e exporta para CSV.
import requests  # Envia as requisições HTTP para a API EVO.
from dotenv import load_dotenv  # Carrega as configurações armazenadas no arquivo .env.


load_dotenv()  # Disponibiliza neste programa as variáveis definidas no arquivo .env.

URL = os.getenv("URL_S")  # Usa o mesmo endereço da API para consultar todas as filiais.
TAMANHO_PAGINA = 50  # Limita cada chamada a 50 registros, conforme o limite da API.
CREDENCIAIS_FILIAIS = [  # Agrupa nome, DNS e token para consultar cada filial separadamente.
    ("Filial A", os.getenv("APP_DNS_S"), os.getenv("APP_TOKEN_S")),  # Credenciais da primeira filial.
    ("Filial B", os.getenv("APP_DNS_C"), os.getenv("APP_TOKEN_C")),  # Credenciais da segunda filial.
]

#função com o objetivo de extrair registros de vendas de uma resposta da API, normalizando os formatos conhecidos para uma lista de dicionários. A função verifica se a resposta é uma lista direta, um dicionário com a chave "registros" ou um dicionário contendo uma única venda. Se o formato não for reconhecido, a função levanta um ValueError. Além disso, a função garante que todos os registros extraídos sejam dicionários válidos antes de retorná-los.
def extrair_registros(dados: object) -> list[dict]:  # Normaliza formatos de resposta conhecidos para uma lista de vendas.
    if isinstance(dados, list):  # A API pode retornar diretamente uma lista
        registros = dados  # Usa a lista recebida sem precisar procurar uma chave.
    elif isinstance(dados, dict) and isinstance(dados.get("registros"), list):  # Aceita também uma resposta agrupada em "registros".
        registros = dados["registros"]  # Extrai a lista de vendas do objeto da resposta.
    elif isinstance(dados, dict) and "idSale" in dados:  # Aceita a resposta contendo uma única venda.
        registros = [dados]  # Envolve a venda em uma lista para usar o mesmo processamento.
    else:  # Interrompe se a resposta não estiver em um formato esperado.
        raise ValueError("Formato inesperado na resposta da API.")  # Evita tratar um formato desconhecido como sucesso.

    if not all(isinstance(registro, dict) for registro in registros):  # Confere se cada venda tem formato de objeto.
        raise ValueError("A resposta da API contém registros em formato inválido.")  # Informa claramente quando há dados inválidos.

    return registros  # Devolve as vendas já normalizadas para o restante do programa.


# função principal que busca todas as vendas de todas as filiais, lidando com paginação e erros. A função retorna um DataFrame contendo todas as vendas coletadas e uma lista de mensagens de erro para qualquer falha ocorrida durante a execução. Ela utiliza uma sessão HTTP para otimizar as requisições e inclui pausas entre chamadas para reduzir a carga na API.
def buscar_todas_vendas() -> tuple[pd.DataFrame, list[str]]:  # Busca vendas e devolve também as falhas encontradas.
    if not URL:  # Verifica se o endereço da API foi configurado.
        raise ValueError("Configure URL_S no arquivo .env.")  # Interrompe com instrução em vez de fazer uma chamada inválida.

    vendas: list[dict] = []  # Acumula aqui as vendas recebidas de todas as filiais e páginas.
    erros: list[str] = []  # Guarda falhas para relatá-las sem descartar os dados já obtidos.

    with requests.Session() as sessao:  # Reutiliza a sessão HTTP e fecha seus recursos ao terminar.
        for nome_filial, dns, token in CREDENCIAIS_FILIAIS:  # Faz uma sequência de consultas para cada filial configurada, usando suas credenciais específicas.
            print(f"Token de {nome_filial}: {token[:4]}***")
            if not dns or not token:  # Confere se as credenciais desta filial foram configuradas.
                mensagem = f"{nome_filial}: DNS ou token não configurado no arquivo .env."  # Explica a configuração ausente.
                erros.append(mensagem)  # Registra a falha sem descartar os dados já obtidos.
                print(mensagem)  # Exibe o problema antes de continuar com outra filial.
                continue  # Tenta consultar a próxima filial em vez de interromper o programa.

            skip = 0  # Começa do primeiro registro ao iniciar cada filial.
            while True:  # Continua pedindo páginas até a API retornar menos de 50 registros ou ocorrer uma falha.
                try:  # Trata falhas desta filial sem apagar os dados já acumulados.
                    # Adaptação dos exemplos da documentação: usamos requests.Session().get
                    # em vez de http.client ou requests.request. A URL completa do endpoint
                    # fica em URL_S; o requests acrescenta os parâmetros de consulta abaixo
                    # à URL, sem precisarmos montar manualmente a sequência após o "?".
                    #
                    # O cabeçalho "Authorization: Basic ..." dos exemplos é gerado pelo
                    # requests a partir de auth=(dns, token), usando as credenciais desta
                    # filial. Como esta rotina pagina os resultados, enviamos take e skip;
                    # os demais filtros mostrados na documentação não são usados aqui.
                    # Também não enviamos payload/data: a chamada é GET e não precisa de corpo.
                    resposta = sessao.get(
                        URL,
                        auth=(dns, token),
                        params={"take": TAMANHO_PAGINA, "skip": skip},
                        timeout=60,  # Evita que a execução fique aguardando indefinidamente uma resposta.
                    )  # Finaliza a requisição e guarda a resposta HTTP.
                    if not resposta.ok:  # Detecta respostas HTTP que indicam falha.
                        raise requests.HTTPError(  # Converte o status HTTP em erro que será registrado abaixo.
                            f"{resposta.status_code} - {resposta.text}",  # Guarda o status e a mensagem devolvidos pela API.
                            response=resposta,  # Anexa a resposta ao erro para permitir inspeção adicional.
                        )  # Finaliza a criação do erro HTTP.

                    registros = extrair_registros(resposta.json())  # Converte o JSON da resposta para uma lista validada de vendas.
                except (requests.exceptions.RequestException, ValueError) as erro:  # Captura falhas HTTP, de conexão e de formato da resposta.
                    mensagem = f"Erro ao consultar {nome_filial}: {erro}"  # Identifica a filial e descreve a falha.
                    erros.append(mensagem)  # Mantém o erro para informar ao final da execução.
                    print(mensagem)  # Exibe o problema sem interromper o salvamento dos dados coletados.
                    break  # Abandona as páginas desta filial e continua com a próxima.

                for registro in registros:  # Percorre as vendas retornadas nesta página.
                    venda = registro.copy()  # Copia o registro para não modificar o objeto original da resposta.
                    venda["filial_consulta"] = nome_filial  # Marca a filial de origem para distinguir registros no CSV.
                    vendas.append(venda)  # Acrescenta esta venda ao resultado geral.

                print(f"{nome_filial}: {len(registros)} registros nesta página.")  # Mostra o progresso da consulta da filial.

                if len(registros) < TAMANHO_PAGINA:  # Uma página incompleta indica que não há outra página para buscar.
                    break  # Encerra a paginação desta filial e passa para a próxima.

                skip += len(registros)  # Avança a posição para pedir os próximos registros sem repetir esta página.
                time.sleep(1)  # Aguarda um segundo antes da próxima chamada para reduzir a carga na API.

    return pd.DataFrame(vendas), erros  # Devolve os registros e as falhas para que ambos sejam tratados no final.


if __name__ == "__main__":  # Executa o bloco abaixo somente quando este arquivo é iniciado diretamente.
    df_vendas, erros = buscar_todas_vendas()  # Busca vendas e recebe também os erros ocorridos por filial.

    if df_vendas.empty:  # Verifica se alguma filial retornou vendas.
        print("Nenhuma venda foi retornada.")  # Informa que não há dados para exportar.
    else:  # Só cria o arquivo quando existem vendas.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Gera um identificador de data e hora para evitar sobrescrita.
        nome_arquivo = f"vendas_{timestamp}.csv"  # Define o nome do arquivo de saída com o horário atual.
        df_vendas.to_csv(nome_arquivo, index=False, encoding="utf-8-sig")  # Salva os dados sem índice e compatíveis com Excel.
        print(f"{len(df_vendas)} vendas salvas em {nome_arquivo}.")  # Informa quantas vendas foram exportadas e onde.

    if erros:  # Verifica se alguma filial não pôde ser consultada por completo.
        print("Atenção: houve falhas; o CSV contém somente os registros coletados com sucesso.")  # Explica que o arquivo é parcial.
        
