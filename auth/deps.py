from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from config import SECRET_KEY, ALGORITHM

def get_usuario_logado_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token ausente. Faça login novamente")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario: str = payload.get("sub")
        if not usuario:
            raise HTTPException(status_code=401, detail="Token inválido")
        return {"usuario": usuario}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")
