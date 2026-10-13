from fastapi import FastAPI

app = FastAPI(title="Climate Hazard Trend Analyzer")


@app.get("/api/health")
def health():
    return {"status":"ok"}