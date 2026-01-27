from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from graph import process_message
import uvicorn
import os

app = FastAPI(title="Legal AI LangGraph Service", version="3.0")

class ProcessRequest(BaseModel):
    thread_id: str
    message: str

class ProcessResponse(BaseModel):
    result: dict

import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/process", response_model=ProcessResponse)
async def process_endpoint(request: ProcessRequest):
    try:
        logger.info(f"Processing message for thread_id: {request.thread_id}")
        response_data = process_message(request.thread_id, request.message)
        return {"result": response_data}
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
