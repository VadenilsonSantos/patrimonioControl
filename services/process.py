import datetime
import json
import requests
from config import API_BASE_URL, basic_auth_header, IXC_SESSION
from typing import Dict
import pandas as pd


def _normalizar_patrimonios(patrimonios, logger):
    """
    Garante que patrimonios seja uma lista de dicionários.
    Aceita: dict, list[dict], list[str JSON], list[str id], list[int].
    """
    import json
    normalizados = []

    if patrimonios is None:
        return normalizados

    # Se veio um único dict
    if isinstance(patrimonios, dict):
        return [patrimonios]

    # Se veio string JSON representando lista/objeto
    if isinstance(patrimonios, str):
        try:
            obj = json.loads(patrimonios)
            return _normalizar_patrimonios(obj, logger)
        except Exception:
            # string simples (id)
            return [{"id": str(patrimonios)}]

    # Se veio lista
    if isinstance(patrimonios, list):
        for item in patrimonios:
            if isinstance(item, dict):
                normalizados.append(item)
            elif isinstance(item, (int, float)):
                normalizados.append({"id": str(int(item))})
            elif isinstance(item, str):
                # Pode ser um JSON de um objeto ou lista… ou um id simples
                try:
                    obj = json.loads(item)
                    if isinstance(obj, dict):
                        normalizados.append(obj)
                    elif isinstance(obj, list):
                        for sub in obj:
                            if isinstance(sub, dict):
                                normalizados.append(sub)
                            elif isinstance(sub, (int, float, str)):
                                normalizados.append({"id": str(sub)})
                            else:
                                logger.warning(
                                    f"Formato inesperado em registros (subitem): {type(sub)}")
                    else:
                        # string que não é JSON de dict/list -> tratar como id
                        normalizados.append({"id": str(item)})
                except Exception:
                    # string simples (provável id)
                    normalizados.append({"id": str(item)})
            else:
                logger.warning(
                    f"Formato inesperado em registros: {type(item)}")
        return normalizados

    # Qualquer outro tipo inesperado
    logger.warning(f"Formato inesperado de 'patrimonios': {type(patrimonios)}")
    return normalizados


def _normalizar_patrimonios(patrimonios, logger):
    """
    Garante que patrimonios seja uma lista de dicionários.
    Aceita: dict, list[dict], list[str JSON], list[str id], list[int].
    """
    import json
    normalizados = []

    if patrimonios is None:
        return normalizados

    # Se veio um único dicionário
    if isinstance(patrimonios, dict):
        return [patrimonios]

    # Se veio string JSON representando lista/objeto
    if isinstance(patrimonios, str):
        try:
            obj = json.loads(patrimonios)
            return _normalizar_patrimonios(obj, logger)
        except Exception:
            return [{"id": str(patrimonios)}]

    # Se veio lista
    if isinstance(patrimonios, list):
        for item in patrimonios:
            if isinstance(item, dict):
                normalizados.append(item)
            elif isinstance(item, (int, float)):
                normalizados.append({"id": str(int(item))})
            elif isinstance(item, str):
                try:
                    obj = json.loads(item)
                    if isinstance(obj, dict):
                        normalizados.append(obj)
                    elif isinstance(obj, list):
                        normalizados.extend(
                            _normalizar_patrimonios(obj, logger))
                    else:
                        normalizados.append({"id": str(item)})
                except Exception:
                    normalizados.append({"id": str(item)})
            else:
                logger.warning(
                    f"Formato inesperado em registros: {type(item)}")
        return normalizados

    logger.warning(f"Formato inesperado de 'patrimonios': {type(patrimonios)}")
    return normalizados


def processar_arquivo(df: pd.DataFrame, patrimonios: list, logger) -> Dict:
    """
    Atualiza os patrimônios via API. Recebe DataFrame validado e lista de patrimônios disponíveis.
    """
    import datetime
    import json
    import requests

    resultados_detalhados = []

    headers_put = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {basic_auth_header()}',
    }
    if IXC_SESSION:
        headers_put['Cookie'] = IXC_SESSION

    # 🔒 Normaliza os registros para garantir que sejam sempre dicionários
    patrimonios = _normalizar_patrimonios(patrimonios, logger)

    for i, row in df.iterrows():
        if i >= len(patrimonios):
            resultados_detalhados.append({
                "linha": i + 1,
                "id": None,
                "status": "erro",
                "mensagem": "Sem patrimônio disponível"
            })
            continue

        try:
            item = patrimonios[i]
            if isinstance(item, dict):
                patrimonio = item.copy()
                patrimonio_id = str(patrimonio.get(
                    "id") or patrimonio.get("ID") or "")
            else:
                patrimonio_id = str(item)
                patrimonio = {"id": patrimonio_id}

            if not patrimonio_id:
                raise ValueError(
                    f"Registro de patrimônio sem 'id' na posição {i}")

            patrimonio["id_mac"] = row.get("mac", "").strip()
            patrimonio["serial_fornecedor"] = row.get("serie", "").strip()
            patrimonio["data_aquisicao"] = datetime.datetime.now().strftime(
                "%d/%m/%Y")

            url_put = f"{API_BASE_URL}/{patrimonio_id}"
            response_put = requests.put(
                url_put,
                headers=headers_put,
                data=json.dumps(patrimonio),
                timeout=30
            )

            if response_put.status_code == 200 and '"type":"success"' in response_put.text:
                resultados_detalhados.append({
                    "linha": i + 1,
                    "id": patrimonio_id,
                    "status": "sucesso",
                    "mensagem": "Atualizado com sucesso"
                })
                logger.info(
                    f"✅ Patrimônio {patrimonio_id} atualizado com sucesso (linha {i+1})")
            else:
                try:
                    msg_erro = response_put.json().get("message", response_put.text)
                except Exception:
                    msg_erro = response_put.text
                resultados_detalhados.append({
                    "linha": i + 1,
                    "id": patrimonio_id,
                    "status": "erro",
                    "mensagem": msg_erro
                })
                logger.warning(
                    f"❌ Erro ao atualizar patrimônio {patrimonio_id} (linha {i+1}): {msg_erro}")

        except Exception as e:
            resultados_detalhados.append({
                "linha": i + 1,
                "id": None,
                "status": "erro",
                "mensagem": str(e)
            })
            logger.exception(
                f"❌ Exceção ao atualizar patrimônio na linha {i+1}: {e}")

    status_geral = "sucesso" if all(
        r["status"] == "sucesso" for r in resultados_detalhados) else "erro"
    logger.info(
        f"📦 Resultado final do processamento: {json.dumps(resultados_detalhados, ensure_ascii=False, indent=2)}")
    return {"status": status_geral, "detalhes": resultados_detalhados}
