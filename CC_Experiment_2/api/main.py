from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/compute")
def compute():
    total = 0
    for i in range(1_000_000):
        total += i * i
    return {"result": total}


@app.get("/memory")
def memory():
    data = [i for i in range(1_000_000)]
    return {
        "elements": len(data)
    }
