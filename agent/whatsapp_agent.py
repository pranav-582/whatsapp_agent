from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/agent")
async def agent_endpoint(request: QueryRequest):
    # TODO: Replace with actual LangChain logic
    response = f"Received: {request.query}"
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("whatsapp_agent:app", host="0.0.0.0", port=5000, reload=True)