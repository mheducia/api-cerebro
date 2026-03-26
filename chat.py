
from asyncio.log import logger
from http.client import HTTPException
import json
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
    usar_mock = os.getenv("USAR_MOCK", "false").lower() == "true"

    if not gemini_url:
        print("Variável URL_GEMINI não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not gemini_key:
        print("Variável GEMINI_API_KEY não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt não pode ser vazio")
        
    try:
        if (usar_mock):
            return {"response": "Mensagem Mockada para testes. Gemini não foi chamado."};
        
        system_prompt=os.getenv("SYSTEM_PROMPT").replace("\\n", "\n")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gemini_url}?key={gemini_key}",
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

@router.post("/chat/stream")
async def chat(request: ChatRequest):
    gemini_url    = os.getenv("URL_GEMINI_STREAM")
    gemini_key    = os.getenv("GEMINI_API_KEY")
    system_prompt = os.getenv("SYSTEM_PROMPT")
    usar_mock = os.getenv("USAR_MOCK", "false").lower() == "true"

    if not gemini_url:
        print("Variável URL_GEMINI_STREAM não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not gemini_key:
        print("Variável GEMINI_API_KEY não configurada")
        raise HTTPException(status_code=500, detail="Serviço não configurado corretamente")

    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt não pode ser vazio")

    async def gerar():
        if usar_mock:
            import asyncio
            texto = "Essa é uma resposta mockada para testes. O Gemini não foi chamado. Com base na análise dos dados fornecidos, identifiquei um padrão significativo nas interações recentes. O processamento de linguagem natural indica que a intenção do usuário está voltada para a otimização de fluxos de trabalho internos. Para implementar uma solução robusta, recomendo a seguinte abordagem: primeiro, a estruturação de um banco de dados vetorial para recuperação de informações (RAG); segundo, o ajuste fino dos prompts para garantir que o tom de voz da marca seja preservado. Além disso, é fundamental monitorar a latência das chamadas de API, garantindo que o tempo de resposta não prejudique a experiência do usuário final. Se precisar de uma análise mais detalhada sobre os custos de tokens ou sobre a integração de novos modelos de linguagem de grande escala (LLMs), estou à disposição para aprofundar cada um desses pontos técnicos."
            for palavra in texto.split():
                yield f"data: {palavra} \n\n"
                await asyncio.sleep(0.15)  # ← simula o delay do stream
            yield "event: done\ndata: [DONE]\n\n"
            return
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{gemini_url}&key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": request.prompt}]}]
                    },
                    timeout=60.0
                ) as response:

                    if response.status_code == 400:
                        yield "event: error\ndata: Prompt inválido ou mal formatado\n\n"
                        return

                    if response.status_code in (401, 403):
                        print(f"{gemini_url}&key={gemini_key}")
                        yield "event: error\ndata: Erro de autenticação com o Gemini\n\n"
                        return

                    if response.status_code == 429:
                        yield "event: error\ndata: Limite de requisições atingido. Tente novamente.\n\n"
                        return

                    if response.status_code >= 500:
                        yield "event: error\ndata: Serviço do Gemini indisponível\n\n"
                        return
                    
                    async for linha in response.aiter_lines():
                        if not linha:
                            continue

                        if not linha.startswith("data: "):
                            continue
                        
                        chunk = linha.replace("data: ", "")
                        if chunk == "[DONE]":
                            yield "event: done\ndata: [DONE]\n\n"
                            break

                        try:
                            data = json.loads(chunk)
                        except json.JSONDecodeError:
                            logger.warning(f"Chunk inválido ignorado: {chunk[:100]}")
                            continue

                        if "promptFeedback" in data:
                            motivo = data["promptFeedback"].get("blockReason", "desconhecido")
                            print(f"Prompt bloqueado pelo Gemini: {motivo}")
                            yield f"event: error\ndata: Conteúdo bloqueado pelo Gemini: {motivo}\n\n"
                            return

                        try:
                            token = data["candidates"][0]["content"]["parts"][0]["text"]
                            if token:
                                yield f"data: {token}\n\n"
                        except (KeyError, IndexError):
                            print(f"Estrutura inesperada no chunk: {data}")
                            continue

        except httpx.TimeoutException:
            print("Timeout no stream do Gemini")
            yield "event: error\ndata: Gemini não respondeu a tempo\n\n"

        except httpx.RemoteProtocolError:
            print("Conexão com o Gemini encerrada inesperadamente")
            yield "event: error\ndata: Conexão encerrada inesperadamente\n\n"

        except httpx.ConnectError:
            print(f"Não foi possível conectar ao Gemini")
            yield "event: error\ndata: Não foi possível conectar ao Gemini\n\n"

        except httpx.RequestError as e:
            print(f"Erro de rede no stream: {e}")
            yield "event: error\ndata: Erro de comunicação com o Gemini\n\n"

        except Exception:
            print(f"Erro inesperado no stream: {traceback.format_exc()}")
            yield "event: error\ndata: Ocorreu um erro interno. Tente novamente.\n\n"
            
    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )