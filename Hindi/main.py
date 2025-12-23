import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from agent import VoiceAgent

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hindi Voice Agent is running"}

@app.websocket("/ws/conversation")
async def websocket_endpoint(websocket: WebSocket):
    agent = VoiceAgent()
    await websocket.accept()
    try:
        await agent.run_conversation(websocket)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        pass # Handle connection cleanup

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
