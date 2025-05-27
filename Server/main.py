from fastapi import FastAPI

app = FastAPI()
print("FastAPI application is starting...")


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}