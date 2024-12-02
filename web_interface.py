import os
import sys
from pathlib import Path
import logging
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from interface import CHESSInterface

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

# Create FastAPI app
app = FastAPI(title="CHESS Web Interface")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize CHESS interface
chess_interface = CHESSInterface()

# Store active sessions
active_sessions: Dict[str, str] = {}  # Maps db_id to session_id

class QueryRequest(BaseModel):
    prompt: str
    db_id: Optional[str] = None

@app.post("/generate")
async def query(request: QueryRequest):
    """
    Handle a query request.
    
    Args:
        request (QueryRequest): The query request containing the prompt and optional database ID
    
    Returns:
        dict: The response from CHESS
    """
    try:
        db_id = 'wtl_employee_tracker'
        if request.db_id:
            db_id = request.db_id
        # Get or create session for this database
        if db_id not in active_sessions:
            session_id = chess_interface.start_chat_session(db_id)
            active_sessions[db_id] = session_id
        else:
            session_id = active_sessions[db_id]
            

        # Process the query using the CHESS interface
        response = chess_interface.chat_query(
            session_id=session_id,
            question=request.prompt
        )

        return {"result": response["natural_language_response"]}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)