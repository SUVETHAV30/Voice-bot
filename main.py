from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph_agent import SearchAgent

app = FastAPI(title="LiveKit Search Agent", version="1.0.0")
search_agent = SearchAgent()

class SearchRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    return {"message": "LiveKit Search Agent API", "status": "running"}

@app.post("/search")
async def search_endpoint(request: SearchRequest):
    try:
        print(f"Received search query: {request.query}")

        async def response_generator():
            async for chunk in search_agent.run(request.query):
                # Each chunk is yielded as plain text
                yield chunk  

        return StreamingResponse(response_generator(), media_type="text/plain")

    except Exception as e:
        print(f"Search endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
