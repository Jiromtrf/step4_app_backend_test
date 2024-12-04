# backend/main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi

from routers.auth_router import router as auth_router
from routers.user_router import router as user_router
from routers.team_router import router as team_router
from db.config import ALLOWED_ORIGINS
import logging

app = FastAPI()

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セキュリティスキームの定義
bearer_scheme = HTTPBearer()

# ルーターの登録
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(team_router)

# OpenAPI スキーマのカスタマイズ
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="API documentation",
        routes=app.routes,
    )
    print("OpenAPI schema before adding security schemes:", openapi_schema)  # デバッグ用

    # セキュリティスキームの追加
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",  # 文字列 "http" を使用
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    print("SecuritySchemes added:", openapi_schema["components"]["securitySchemes"])  # デバッグ用

    # 全エンドポイントにセキュリティスキームを適用
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    print("Security applied to all paths")  # デバッグ用

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )