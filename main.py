import os
import shutil
import logging
import tempfile
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm

from config import ACCESS_TOKEN_EXPIRE_HOURS
from controllers.patrimonio_controller import processar_arquivo
from controllers.produto_controller import router as produto_router
from services.validations import validar_planilha

from auth.ldap_utils import autenticar_ldap, usuario_tem_acesso
from auth.token_utils import criar_token
from auth.deps import get_usuario_logado_cookie

# ----------------- CONFIG -----------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SISTEMA_LOG_DIR = "logs/sistema"
os.makedirs(SISTEMA_LOG_DIR, exist_ok=True)

# ----------------- LOGGER DO SISTEMA -----------------
hoje = datetime.now().strftime("%Y%m%d")
sistema_logger = logging.getLogger("sistema")
sistema_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(
    filename=os.path.join(SISTEMA_LOG_DIR, f"sistema_{hoje}.log"),
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
))

sistema_logger.addHandler(file_handler)
sistema_logger.addHandler(console_handler)

# ----------------- APP -----------------
app = FastAPI(title="Patrimônio API")

# ----------------- MIDDLEWARE PARA TRATAR TOKEN EXPIRADO -----------------
@app.middleware("http")
async def redirect_on_auth_error(request: Request, call_next):
    response = await call_next(request)

    if response.status_code in (401, 403):
        # Limpa cookie e redireciona para "/"
        redirect = RedirectResponse(url="/", status_code=302)
        redirect.delete_cookie("access_token")
        return redirect

    return response

# ----------------- AUTENTICAÇÃO -----------------
@app.get("/", response_class=HTMLResponse)
async def login_page():
    with open("templates/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = form_data.username
    senha = form_data.password

    if not autenticar_ldap(usuario, senha):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    if not usuario_tem_acesso(usuario, senha):
        raise HTTPException(status_code=403, detail="Usuário não tem acesso à esse serviço")

    token = criar_token(usuario)
    sistema_logger.info(f"✅ Login realizado: {usuario}")

    # Redireciona para /choose após login
    response = RedirectResponse(url="/choose", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(ACCESS_TOKEN_EXPIRE_HOURS) * 3600
    )
    return response

@app.post("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response

# ----------------- TELA DE ESCOLHA -----------------
@app.get("/choose", response_class=HTMLResponse)
async def choose_page(usuario_logado: dict = Depends(get_usuario_logado_cookie)):
    """
    Página para escolha de rota após login.
    Exige usuário logado.
    """
    try:
        with open("templates/choose.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        sistema_logger.exception(f"Erro ao abrir choose.html: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar a página de escolha")

# ----------------- ROTAS PROTEGIDAS -----------------
@app.get("/home", response_class=HTMLResponse)
async def home_page(usuario_logado: dict = Depends(get_usuario_logado_cookie)):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post('/patrimonio/upload')
async def upload_saldo(
    id_produto: str = Form(...),
    file: UploadFile = File(...),
    usuario_logado: dict = Depends(get_usuario_logado_cookie)
):
    if not id_produto:
        raise HTTPException(status_code=400, detail="id_produto é obrigatório")

    if not file.filename.lower().endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xls ou .xlsx")

    try:
        file_bytes = await file.read()

        # Salvar no UPLOAD_DIR
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        nome_novo = f"{usuario_logado['usuario']}_{timestamp}_{file.filename}"
        caminho_upload = os.path.join(UPLOAD_DIR, nome_novo)
        with open(caminho_upload, 'wb') as f:
            f.write(file_bytes)

        sistema_logger.info(f"📂 Arquivo salvo: {nome_novo} pelo usuário {usuario_logado['usuario']}")

        # Criar arquivo temporário para processar
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, file.filename)
        with open(tmp_path, 'wb') as f:
            f.write(file_bytes)

        # ------------------- VALIDAÇÃO -------------------
        validacao = validar_planilha(tmp_path, sistema_logger)
        if validacao["status"] != "sucesso":
            resultado = validacao
        else:
            df_valido = validacao["dados"]
            resultado = processar_arquivo(df_valido, id_produto, logger=sistema_logger)

    except Exception as e:
        sistema_logger.exception("❌ Falha ao salvar/processar arquivo")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass

    status_code = 200 if resultado.get("status") == "sucesso" else 400
    return JSONResponse(status_code=status_code, content=resultado)

# ----------------- STATIC FILES -----------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----------------- ROTAS DE PRODUTO -----------------
app.include_router(produto_router, prefix="/api", dependencies=[Depends(get_usuario_logado_cookie)])
