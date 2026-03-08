
from fastapi import FastAPI
from core.engine import process_ingredient

app = FastAPI(title="Grocy AI Assistant")

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/ingredient")
def ingredient(data: dict):
    return process_ingredient(data["name"])
