from services.validations import validar_planilha, validar_estoque
from services.process import processar_arquivo

def handle_upload(path_arquivo, id_produto, logger):
    # 1️⃣ Valida planilha
    resultado = validar_planilha(path_arquivo, logger)
    if resultado["status"] != "sucesso":
        return resultado

    df = resultado["dados"]

    # 2️⃣ Valida estoque
    estoque = validar_estoque(df, id_produto, logger)
    if estoque["status"] != "sucesso":
        return estoque

    patrimonios = estoque["patrimonios"]

    # 3️⃣ Processa arquivo
    return processar_arquivo(df, patrimonios, logger)
