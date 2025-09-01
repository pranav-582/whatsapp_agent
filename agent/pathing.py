from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import os
from dotenv import load_dotenv
from intent_router import IntentRouter

load_dotenv()

app = FastAPI()

intent_router = IntentRouter()


class QueryRequest(BaseModel):
    query: str
    phone_number: str
    whatsapp_name: str = "WhatsApp User"

class QueryResponse(BaseModel):
    response: str
    intent: str
    entities: Dict[str, Any]
    agent_used: str


@app.post("/agent", response_model=QueryResponse)
async def agent_endpoint(request: QueryRequest):
    """Main endpoint that orchestrates the multi-agent system"""
    try:
        user_message = request.query
        phone_number = request.phone_number
        whatsapp_name = request.whatsapp_name  
        
        result = intent_router.process_user_message(
            phone_no=phone_number,
            user_message=user_message,
            whatsapp_name=whatsapp_name
        )
        
        return QueryResponse(
            response=result["agent_response"],
            intent=result.get("message_category", "unknown"),
            entities={},
            agent_used="langgraph_agent"
        )
        
    except Exception as e:
        print(f"🔥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return QueryResponse(
            response="Sorry, I'm experiencing technical difficulties. Please try again.",
            intent="ERROR",
            entities={},
            agent_used="error_handler"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "service": "WhatsApp Agent",
        "agents": ["product_info", "inventory", "order", "comparison"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pathing:app", host="0.0.0.0", port=5000, reload=True)