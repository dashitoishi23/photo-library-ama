from fastapi import FastAPI

app = FastAPI(title="Photo Library AMA")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/photos")
def list_photos():
    raise NotImplementedError


@app.post("/query")
def query():
    raise NotImplementedError


@app.post("/index")
def index():
    raise NotImplementedError
