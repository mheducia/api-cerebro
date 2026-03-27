import os
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
from urllib3 import request
from chat import router as chat_router
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000) #compacta acima de 1kb

# Registra as rotas de chat
app.include_router(chat_router)

@app.get("/")
def home():
    return {"status": "API Online"}

@app.middleware("http")
async def validar_acesso(request: Request, call_next):
    api_key = request.headers.get("X-API-Key");
    API_KEY = os.getenv("API_KEY", "")

    if api_key != API_KEY:
        print("Chaves: {api_key} - {API_KEY}")
        return JSONResponse(status_code=403, content={"detail": "Não autorizado"})

    return await call_next(request)