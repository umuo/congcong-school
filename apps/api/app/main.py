from contextlib import asynccontextmanager
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.avatars.router import router as avatar_router
from app.config import API_ROOT, Settings, get_settings
from app.content.router import router as content_router
from app.curriculum.router import router as curriculum_router
from app.database import Database
from app.diagnostics.router import router as diagnostics_router
from app.learning.router import router as learning_router
from app.portability.router import router as portability_router
from app.students.router import router as student_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    database = Database(settings)
    expected_heads = set(ScriptDirectory.from_config(Config(API_ROOT / "alembic.ini")).get_heads())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await database.engine.dispose()

    app = FastAPI(title="聪聪学堂家庭 API", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.include_router(auth_router)
    app.include_router(avatar_router)
    app.include_router(admin_router)
    app.include_router(student_router)
    app.include_router(curriculum_router)
    app.include_router(content_router)
    app.include_router(learning_router)
    app.include_router(diagnostics_router)
    app.include_router(portability_router)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "HTTP_ERROR", "message": str(exc.detail)}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={**detail, "request_id": request.state.request_id},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # 不返回 Pydantic 的 input/ctx，避免密码及个人资料出现在错误响应里。
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "请求参数无效",
                "request_id": request.state.request_id,
                "fields": [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
            },
        )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health/live")
    async def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(request: Request):
        try:
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                revisions = set(
                    (await connection.execute(text("SELECT version_num FROM alembic_version")))
                    .scalars()
                    .all()
                )
                if revisions != expected_heads:
                    raise ValueError("Migration mismatch")
        except (SQLAlchemyError, ValueError, OSError):
            return JSONResponse(
                status_code=503,
                content={
                    "code": "DATABASE_NOT_READY",
                    "message": "数据库尚未就绪",
                    "request_id": request.state.request_id,
                },
            )
        return {"status": "ok", "database": "ready"}

    return app
