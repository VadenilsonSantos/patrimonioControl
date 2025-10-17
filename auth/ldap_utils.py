import logging
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
from config import LDAP_SERVER, LDAP_DOMAIN, GROUP_DN, BASE_DN
import os
from datetime import datetime

# ---------- Diretórios de logs ----------
LOGIN_LOG_DIR = "logs/login"
os.makedirs(LOGIN_LOG_DIR, exist_ok=True)

# ---------- Logger de login diário ----------
hoje = datetime.now().strftime("%Y%m%d")
login_logger = logging.getLogger("login")
login_logger.setLevel(logging.INFO)

login_handler = logging.FileHandler(
    filename=os.path.join(LOGIN_LOG_DIR, f"login_{hoje}.log"),
    encoding="utf-8"
)
login_handler.setFormatter(
    logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
)
login_logger.addHandler(login_handler)
login_logger.addHandler(logging.StreamHandler())  # também imprime no console

# ---------- LDAP Utilities ----------

def autenticar_ldap(usuario: str, senha: str) -> bool:
    """Faz bind no Active Directory usando NTLM."""
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(
            server,
            user=f"{LDAP_DOMAIN}\\{usuario}",
            password=senha,
            authentication=NTLM,
            receive_timeout=10
        )

        if conn.bind():
            login_logger.info(f"✅ Bind realizado com sucesso para '{usuario}'")
            return True
        else:
            login_logger.warning(f"❌ Falha no bind para '{usuario}': {conn.result}")
            return False

    except Exception as e:
        login_logger.exception(f"❌ Erro ao autenticar '{usuario}': {e}")
        return False


def usuario_tem_acesso(usuario: str, senha: str) -> bool:
    """Verifica se o usuário pertence ao grupo específico definido em GROUP_DN."""
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(
            server,
            user=f"{LDAP_DOMAIN}\\{usuario}",
            password=senha,
            authentication=NTLM,
            receive_timeout=10
        )

        if not conn.bind():
            login_logger.warning(f"❌ Bind falhou para '{usuario}': {conn.result}")
            return False

        login_logger.info(f"🔍 Verificando grupo do usuário '{usuario}'...")

        # Busca do usuário no Base DN e verificação de grupo
        search_filter = f"(&(sAMAccountName={usuario})(memberOf={GROUP_DN}))"
        conn.search(
            search_base=BASE_DN,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["distinguishedName", "memberOf"]
        )

        if conn.entries:
            login_logger.info(f"✅ Usuário '{usuario}' pertence ao grupo '{GROUP_DN}'")
            return True
        else:
            login_logger.warning(f"⚠ Usuário '{usuario}' NÃO pertence ao grupo '{GROUP_DN}'")
            return False

    except Exception as e:
        login_logger.exception(f"❌ Erro ao verificar grupo para '{usuario}': {e}")
        return False
