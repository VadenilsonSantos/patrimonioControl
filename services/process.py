import datetime
import json
import requests
from config import API_BASE_URL, basic_auth_header, IXC_SESSION
from typing import Dict
import pandas as pd

def processar_arquivo(df: pd.DataFrame, patrimonios: list, logger) -> Dict:
    """
    Atualiza os patrimônios via API. Recebe DataFrame validado e lista de patrimônios disponíveis.
    """
    resultados_detalhados = []

    headers_put = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {basic_auth_header()}',
    }
    if IXC_SESSION:
        headers_put['Cookie'] = IXC_SESSION

    for i, row in df.iterrows():
        if i >= len(patrimonios):
            resultados_detalhados.append({"linha": i + 1, "id": None, "status": "erro", "mensagem": "Sem patrimônio disponível"})
            continue

        try:
            patrimonio = patrimonios[i].copy()
            patrimonio_id = patrimonio.get("id")

            patrimonio["id_mac"] = row.get("mac", "").strip()
            patrimonio["serial_fornecedor"] = row.get("serie", "").strip()
            patrimonio["data_aquisicao"] = datetime.datetime.now().strftime("%d/%m/%Y")

            url_put = f"{API_BASE_URL}/{patrimonio_id}"
            response_put = requests.put(url_put, headers=headers_put, data=json.dumps(patrimonio), timeout=30)

            if response_put.status_code == 200 and '"type":"success"' in response_put.text:
                resultados_detalhados.append({"linha": i + 1, "id": patrimonio_id, "status": "sucesso", "mensagem": "Atualizado com sucesso"})
                logger.info(f"✅ Patrimônio {patrimonio_id} atualizado com sucesso (linha {i+1})")
            else:
                try:
                    msg_erro = response_put.json().get("message", response_put.text)
                except Exception:
                    msg_erro = response_put.text
                resultados_detalhados.append({"linha": i + 1, "id": patrimonio_id, "status": "erro", "mensagem": msg_erro})
                logger.warning(f"❌ Erro ao atualizar patrimônio {patrimonio_id} (linha {i+1}): {msg_erro}")

        except Exception as e:
            resultados_detalhados.append({"linha": i + 1, "id": None, "status": "erro", "mensagem": str(e)})
            logger.exception(f"❌ Exceção ao atualizar patrimônio na linha {i+1}: {e}")

    status_geral = "sucesso" if all(r["status"] == "sucesso" for r in resultados_detalhados) else "erro"
    return {"status": status_geral, "detalhes": resultados_detalhados}
