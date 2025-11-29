import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from inbound_call import router as inbound_router

load_dotenv()

app = FastAPI()

app.include_router(inbound_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
