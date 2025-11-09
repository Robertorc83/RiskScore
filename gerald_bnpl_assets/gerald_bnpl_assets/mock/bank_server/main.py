from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import os

app = FastAPI(title="Mock Bank Server", version="1.0.0")
# Support both local development and Docker
DATA_DIR = Path("/bank_stub") if os.path.exists("/bank_stub") else Path(__file__).resolve().parents[2] / "bank_stub"

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/bank/transactions")
def get_transactions(user_id: str):
    file = DATA_DIR / f"transactions_{user_id}.json"
    if not file.exists():
        raise HTTPException(status_code=404, detail="user not found")
    return JSONResponse(content=json.loads(file.read_text()))
