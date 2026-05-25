from __future__ import annotations

import contextlib
import io

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    identificador: str
    senha: str


class AuthStatus(BaseModel):
    authenticated: bool
    identificador: str | None = None


@router.post("/auth/login")
def login(request: Request, body: LoginRequest) -> AuthStatus:
    """Valida credenciais ANA e abre uma sessão autenticada."""
    from ANA.ANA_Swagger_Autenticacao import gerar_token_ana  # noqa
    try:
        # gerar_token_ana imprime na stdout — suprimimos para não poluir os logs do servidor
        with contextlib.redirect_stdout(io.StringIO()):
            gerar_token_ana(body.identificador, body.senha)
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciais ANA inválidas.")

    request.session["identificador"] = body.identificador
    request.session["senha"] = body.senha
    return AuthStatus(authenticated=True, identificador=body.identificador)


@router.post("/auth/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"status": "ok"}


@router.get("/auth/me")
def me(request: Request) -> AuthStatus:
    identificador = request.session.get("identificador")
    if not identificador:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return AuthStatus(authenticated=True, identificador=identificador)
