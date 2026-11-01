from typing import Annotated

from fastapi import Depends, Request

from app.auth.dependencies import Identity, identity
from app.auth.service import client_context
from app.errors import APIError


async def learning_identity(request: Request, who: Annotated[Identity, Depends(identity)]):
    expected = request.headers.get("x-csf-learning-context")
    if expected is not None and expected != str(client_context(who.user, who.auth_session)):
        raise APIError(409, "LEARNING_CONTEXT_CHANGED", "登录身份已变化，请刷新后继续")
    return who
