from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
import sqlite3
import os

from agent.graph_hybrid import app as agent_app

api = FastAPI(
    title="Retail Analytics Copilot API",
    description="REST API for Hybrid RAG + Text-to-SQL Retail Analytics Agent",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    question: str
    format_hint: Optional[str] = ""

class QueryResponse(BaseModel):
    id: Optional[str] = "custom_query"
    final_answer: Any
    sql: str
    confidence: float
    explanation: str
    citations: List[str]

@api.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Retail Analytics Copilot API",
        "docs_url": "/docs",
        "health": "/health"
    }

@api.get("/health")
def healthcheck():
    db_path = "data/northwind.sqlite"
    db_exists = os.path.exists(db_path)
    db_connected = False
    
    if db_exists:
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            db_connected = True
        except Exception:
            pass
            
    return {
        "status": "healthy" if db_connected else "degraded",
        "database_exists": db_exists,
        "database_connected": db_connected
    }

@api.post("/api/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    initial_state = {
        "question": req.question,
        "format_hint": req.format_hint or "",
        "router_decision": "",
        "retrieved_docs": [],
        "sql_query": "",
        "sql_result": "",
        "sql_error": None,
        "retry_count": 0,
        "final_answer": "",
        "explanation": "",
        "citations": []
    }
    
    try:
        final_state = agent_app.invoke(initial_state)
        
        confidence = 0.5
        if final_state.get('sql_result') and not final_state.get('sql_error'):
            confidence += 0.3
        if final_state.get('retrieved_docs'):
            confidence += 0.1
        if final_state.get('retry_count', 0) > 0:
            confidence -= 0.2
        confidence = max(0.0, min(1.0, confidence))

        return QueryResponse(
            id="api_query",
            final_answer=final_state.get("final_answer", "Error"),
            sql=final_state.get("sql_query", ""),
            confidence=round(confidence, 2),
            explanation=final_state.get("explanation", ""),
            citations=final_state.get("citations", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/api/schema")
def get_schema():
    db_path = "data/northwind.sqlite"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file missing.")
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        
        schema_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}');")
            cols = [{"column": col[1], "type": col[2]} for col in cursor.fetchall()]
            schema_info[table] = cols
            
        conn.close()
        return {"tables": schema_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)
