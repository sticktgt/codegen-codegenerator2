from fastapi import FastAPI

app = FastAPI(title="Generated Prototype")

@app.get("/health")
def health():
    return {"status": "ok"}
