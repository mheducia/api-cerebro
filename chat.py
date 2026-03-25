
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
    try:
        usar_mock = os.getenv("USAR_MOCK", "false").lower() == "true"

        if (usar_mock):
            return {"response": "Mensagem Mockada para testes. Gemini não foi chamado."};
        else:
            system_prompt=os.getenv("SYSTEM_PROMPT").replace("\\n", "\n")
            prompt = f"{system_prompt}{request.prompt}""";
            print(prompt)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{os.getenv('URL_GEMINI')}?key={os.getenv('GEMINI_API_KEY')}",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                            "systemInstruction": {"parts": [{"text": os.getenv("SYSTEM_PROMPT")}]}, 
                            "contents": [{"parts": [{"text": prompt}]}]
                        },
                    timeout=60.0
                )
                               
                print(f"Resposta bruta do Gemini: {response}")  # Log completo da resposta para depuração

                data = response.json()
                return {"response": data['candidates'][0]['content']['parts'][0]['text']}
        
    except httpx.ReadTimeout:
        return {"error": "O Gemini demorou muito para responder. Tente novamente."}
    except httpx.HTTPStatusError as e:
        return {"error": f"Erro na API do Google: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": f"Erro inesperado: {str(e)}"}

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