from fastapi import APIRouter
import mysql.connector
from config import DB_CONFIG
import logging

router = APIRouter()

# Pega o logger já existente (sem criar handlers)
logger = logging.getLogger("produto_controller")

query = """
    SELECT 
        p.id,
        p.descricao
    FROM produtos p 
    WHERE p.tipo = 'P'
    ORDER BY p.id ASC
"""

#      AND p.ativo = 'S'

@router.get("/produtos")
def listar_produtos():
    try:
        logger.info("Iniciando consulta de produtos no banco")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"{len(resultados)} produtos encontrados")

        return [{"id": r["id"], "text": f'{r["id"]} - {r["descricao"]}'} for r in resultados]

    except mysql.connector.Error as err:
        logger.error(f"Erro ao consultar o banco: {err}")
        return {"status": "erro", "mensagem": f"Erro ao consultar o banco: {err}"}
