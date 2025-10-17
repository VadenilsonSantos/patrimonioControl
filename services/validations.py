import pandas as pd
import json
import requests
from config import API_BASE_URL, basic_auth_header, IXC_SESSION, DB_CONFIG
from typing import Dict
import mysql.connector
import logging

logger = logging.getLogger("validations")


def validar_duplicidade_ixc(df: pd.DataFrame) -> Dict:
    """
    Valida se algum MAC ou série do DataFrame já está cadastrado no IXC via banco de dados.
    Retorna erros detalhados com linha, valor duplicado, id do patrimônio e id_produto.
    """
    try:
        logger.info("Conectando ao banco para validar duplicidades IXC")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, id_produto, id_mac, serial_fornecedor
            FROM patrimonio
            WHERE id_mac IS NOT NULL AND id_mac != ''
              AND serial_fornecedor IS NOT NULL AND serial_fornecedor != ''
        """
        cursor.execute(query)
        registros = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(
            f"{len(registros)} registros de patrimônio carregados do banco")

        macs_existentes = {r["id_mac"]: (
            r["id"], r["id_produto"]) for r in registros if r["id_mac"]}
        series_existentes = {r["serial_fornecedor"]: (
            r["id"], r["id_produto"]) for r in registros if r["serial_fornecedor"]}

        erros = []

        for idx, row in df.iterrows():
            linha_num = idx + 2
            mac = row.get("mac")
            serie = row.get("serie")

            if mac in macs_existentes:
                patr_id, produto_id = macs_existentes[mac]
                erros.append({
                    "linha": linha_num,
                    "mensagem": f"MAC '{mac}' já cadastrado no patrimônio {patr_id}, produto {produto_id}"
                })

            if serie in series_existentes:
                patr_id, produto_id = series_existentes[serie]
                erros.append({
                    "linha": linha_num,
                    "mensagem": f"Série '{serie}' já cadastrado no patrimônio {patr_id}, produto {produto_id}"
                })

        if erros:
            logger.warning(
                f"{len(erros)} duplicidades encontradas na validação IXC")
            return {"status": "erro", "detalhes": erros}

        return {"status": "sucesso"}

    except mysql.connector.Error as err:
        logger.error(f"Erro ao consultar o banco: {err}")
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": str(err)}]}


def validar_planilha(path_arquivo: str, logger) -> Dict:
    """
    Valida o XLSX recebido: primeiro verifica duplicidade no IXC,
    depois colunas obrigatórias, campos preenchidos e duplicatas internas.
    """
    try:
        df = pd.read_excel(path_arquivo, dtype=str).fillna("")
        logger.info(f"Colunas lidas: {df.columns.tolist()}")
        logger.info(f"Quantidade de linhas: {len(df)}")
    except Exception as e:
        logger.exception(f"Erro ao ler o arquivo Excel: {e}")
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": f"Erro ao abrir arquivo: {e}"}]}

    # Primeira validação: duplicidade no IXC
    resultado_ixc = validar_duplicidade_ixc(df)
    if resultado_ixc["status"] != "sucesso":
        return resultado_ixc

    # Validação interna da planilha
    colunas_obrigatorias = ["mac", "serie"]
    colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]

    if colunas_faltando:
        msg = f"Colunas obrigatórias ausentes: {', '.join(colunas_faltando)}"
        logger.error(msg)
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": msg}]}

    detalhes_erros = []

    for idx, row in df.iterrows():
        erros_linha = [
            f"Campo obrigatório vazio: {col}" for col in colunas_obrigatorias if not row[col]]
        if erros_linha:
            detalhes_erros.append(
                {"linha": idx + 2, "mensagem": "; ".join(erros_linha)})

    for col in colunas_obrigatorias:
        duplicados = df[df.duplicated([col], keep=False)]
        for idx, row in duplicados.iterrows():
            detalhes_erros.append(
                {"linha": idx + 2, "mensagem": f"Duplicado na coluna {col}: {row[col]}"})

    if detalhes_erros:
        logger.warning(f"{len(detalhes_erros)} erros encontrados na planilha.")
        return {"status": "erro", "detalhes": detalhes_erros}

    return {"status": "sucesso", "dados": df}


def validar_estoque(df: pd.DataFrame, id_produto: str, logger) -> Dict:
    """
    Verifica se há patrimônio suficiente para atualizar.
    Retorna dict com status e lista de patrimônios disponíveis.
    """
    logger.info(
        f"🧩 Iniciando validação de estoque para id_produto={id_produto}")
    qtd_equipamentos = len(df)

    headers_get = {
        'Content-Type': 'application/json',
        'ixcsoft': 'listar',
        'Authorization': f'Basic {basic_auth_header()}',
    }
    if IXC_SESSION:
        headers_get['Cookie'] = IXC_SESSION

     # Payload GET Versão diferente GridPARAM
    payload_get = {
        "qtype": "patrimonio.id_produto",
        "query": id_produto,
        "oper": "=",
        "rp": "1000",
        "page": "1",
        "sortname": "patrimonio.id_produto",
        "sortorder": "desc",
        "grid_param": json.dumps([
            {"TB": "patrimonio.situacao", "OP": "=", "P": "1"},
            {"TB": "patrimonio.id_mac", "OP": "NU"},
            {"TB": "patrimonio.serial_fornecedor", "OP": "=", "P": ""}
        ])
    }

    # Versão nova que comunmente da erros
    # filtros = [
    #    {"TB": "patrimonio.id_produto", "OP": "=", "P": str(id_produto)},
    #    {"TB": "patrimonio.situacao", "OP": "=", "P": "1"},
    #    {"TB": "patrimonio.id_mac", "OP": "=", "P": ""},
    #    {"TB": "patrimonio.serial_fornecedor", "OP": "=", "P": ""}
    # ]
#
    # payload_get = {
    #    "grid_param": json.dumps(filtros),
    #    "page": "1",
    #    "rp": "1000",
    #    "sortname": "patrimonio.id",
    #    "sortorder": "desc"
    # }

    try:
        response = requests.get(
            API_BASE_URL, headers=headers_get, json=payload_get, timeout=30)
    except Exception as e:
        logger.exception(f"Falha na requisição GET: {e}")
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": str(e)}]}

    if response.status_code != 200:
        logger.error(f"GET retornou {response.status_code}: {response.text}")
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": response.text}]}

    # --- Tratamento robusto do retorno da API ---
    dados = response.json()
    patrimonios = dados.get("registros", [])
    total_disponivel = int(dados.get("total", 0))

    # Diagnóstico
    logger.info(f"Tipo inicial de 'patrimonios': {type(patrimonios)}")

    # Corrige se vier string JSON
    if isinstance(patrimonios, str):
        try:
            patrimonios = json.loads(patrimonios)
            logger.info(
                "✅ Convertido 'registros' de string JSON para lista de dicionários.")
        except Exception as e:
            logger.error(f"Erro ao converter string JSON: {e}")
            patrimonios = []

    # Corrige se vier lista de strings (cada uma um JSON individual)
    elif isinstance(patrimonios, list) and all(isinstance(x, str) for x in patrimonios):
        try:
            patrimonios = [json.loads(x) for x in patrimonios]
            logger.info(
                "✅ Convertido lista de strings JSON para lista de dicionários.")
        except Exception as e:
            logger.error(f"Erro ao converter lista de strings JSON: {e}")
            patrimonios = []

    # Garante tipo correto
    elif not isinstance(patrimonios, list):
        logger.error(
            f"❌ Tipo inesperado em 'registros': {type(patrimonios)} — esperado list.")
        patrimonios = []

    if total_disponivel < qtd_equipamentos:
        msg = f"Estoque insuficiente: necessário {qtd_equipamentos}, disponível {total_disponivel}"
        logger.warning(msg)
        return {"status": "erro", "detalhes": [{"linha": None, "mensagem": msg}]}

    logger.info(f"✅ Estoque validado. Total disponível: {total_disponivel}")
    logger.info(
        f"🔍 Exemplo de patrimônio: {patrimonios[0] if patrimonios else 'Nenhum'}")
    logger.info(
        f"📦 Estoque retornado (total={total_disponivel}): {json.dumps(patrimonios[:3], ensure_ascii=False)}")

    return {"status": "sucesso", "patrimonios": patrimonios}
