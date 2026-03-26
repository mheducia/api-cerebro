
from asyncio.log import logger
from http.client import HTTPException
import traceback
from urllib import response
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os
import httpx

load_dotenv()

router = APIRouter(prefix="/prompt", tags=["prompt"])

class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    gemini_url    = os.getenv("URL_GEMINI")
    gemini_key    = os.getenv("GEMINI_API_KEY")
    system_prompt = os.getenv("SYSTEM_PROMPT")

    if not gemini_url:
        print("Variável URL_GEMINI não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not gemini_key:
        print("Variável GEMINI_API_KEY não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt não pode ser vazio")
        
    try:        
        usar_mock = os.getenv("USAR_MOCK", "false").lower() == "true"

        if (usar_mock):
            return {"response": "Mensagem Mockada para testes. Gemini não foi chamado."};
        
        system_prompt=os.getenv("SYSTEM_PROMPT").replace("\\n", "\n")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{os.getenv('URL_GEMINI')}?key={os.getenv('GEMINI_API_KEY')}",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]}, 
                        "contents": [{"parts": [{"text": request.prompt}]}]
                    },
                timeout=60.0
            )
                            
        if response.status_code == 400:
            print(f"Requisição inválida para o Gemini: {response.text[:200]}")
            raise HTTPException(status_code=422, detail="Prompt inválido ou mal formatado")

        if response.status_code == 401 or response.status_code == 403:
            print(f"API Key do Gemini inválida ou sem permissão: {response.status_code}")
            raise HTTPException(status_code=502, detail="Erro de autenticação com o Gemini")

        if response.status_code == 429:
            print("Limite de requisições do Gemini atingido")
            raise HTTPException(status_code=429, detail="Limite de requisições atingido. Tente novamente em instantes.")

        if response.status_code >= 500:
            print(f"Gemini retornou erro interno: {response.status_code}")
            raise HTTPException(status_code=502, detail="Serviço do Gemini indisponível")

        try:
            data = response.json()
        except Exception:
            print(f"Gemini retornou resposta inválida: {response.text[:200]}")
            raise HTTPException(status_code=502, detail="Resposta inválida do Gemini")

        try:
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            # verifica se foi bloqueado por safety
            if "promptFeedback" in data:
                motivo = data["promptFeedback"].get("blockReason", "desconhecido")
                print(f"Prompt bloqueado pelo Gemini: {motivo}")
                raise HTTPException(status_code=422, detail=f"Prompt bloqueado pelo Gemini: {motivo}")

            print(f"Estrutura inesperada na resposta do Gemini: {data}")
            raise HTTPException(status_code=502, detail="Resposta do Gemini em formato inesperado")

        return {"response": texto}

    except httpx.TimeoutException:
        print("Timeout ao chamar o Gemini após 60s")
        raise HTTPException(status_code=504, detail="Gemini não respondeu a tempo. Tente novamente.")

    except httpx.ConnectError:
        print(f"Não foi possível conectar ao Gemini em {gemini_url}")
        raise HTTPException(status_code=502, detail="Não foi possível conectar ao Gemini")

    except httpx.RequestError as e:
        print(f"Erro de rede ao chamar o Gemini: {e}")
        raise HTTPException(status_code=502, detail="Erro de comunicação com o Gemini")

    except HTTPException:
        raise

    except Exception as e:
        print(f"Erro inesperado: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno. Tente novamente.")

#@router.post("/chat/stream")
#async def chat_stream(req: ChatRequest):
#    async def generate():
#        try:
#            model = genai.GenerativeModel("models/gemini-2.5-flash")
#            response = model.generate_content(req.message, stream=True)
#            for chunk in response:
#                yield chunk.text
#        except ResourceExhausted:
#            yield "⚠️ Limite de requisições atingido. Tente novamente em alguns minutos."
#        except Exception as e:
#            yield f"⚠️ Erro: {str(e)}"
#
#    return StreamingResponse(generate(), media_type="text/plain")    