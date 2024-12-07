import os
import sys
from pathlib import Path
import logging
from typing import Dict, Optional
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from interface import CHESSInterface
from threading import Lock
import time
import yaml
from translator import SQLTranslator


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

# Store interfaces per user
user_interfaces: Dict[str, CHESSInterface] = {}
interfaces_lock = Lock()

# Store active sessions
active_sessions: Dict[str, str] = {}  # Maps frontend_session_id to chess_session_id
sessions_lock = Lock()

def get_user_interface(user_id: str) -> CHESSInterface:
    """Get or create a CHESSInterface instance for a user."""
    with interfaces_lock:
        if user_id not in user_interfaces:
            # Use the default config name but create a unique interface
            user_interfaces[user_id] = CHESSInterface(
                config_name="CHESS_IR_CG_UT",
                db_mode='dev'
            )
        return user_interfaces[user_id]

class SessionRequest(BaseModel):
    db_id: str = "wtl_employee_tracker"  # Default database ID
    user_id: str

class QueryRequest(BaseModel):
    prompt: str
    session_id: str  # Frontend must provide the session ID from /create_session
    user_id: str = "default"  # Make user_id optional with a default value

@app.post("/create_session")
async def create_session(request: SessionRequest):
    """Create a new chat session."""
    try:
        # Generate a unique session ID for the frontend
        frontend_session_id = str(uuid.uuid4())
        
        # Get or create user's interface
        interface = get_user_interface(request.user_id)
        
        # Create a new CHESS session
        chess_session_id = interface.start_chat_session(request.db_id)
        
        # Store the mapping
        with sessions_lock:
            active_sessions[frontend_session_id] = chess_session_id
        
        return {
            "session_id": frontend_session_id,
            "db_id": request.db_id,
            "user_id": request.user_id
        }
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.post("/generate")
async def query(request: QueryRequest):
    """Handle a query request."""
    try:
        with sessions_lock:
            if request.session_id not in active_sessions:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired session ID. Please create a new session."
                )
            chess_session_id = active_sessions[request.session_id]

        # Get the user's interface
        interface = get_user_interface(request.user_id)

        # Process the query using the user's interface
        response = interface.chat_query(
            session_id=chess_session_id,
            question=request.prompt
        )

        # Create a new translator instance for this request
        sql_translator = SQLTranslator()

        # Translate SQL query if present
        if 'sql_query' in response:
            try:
                mysql_query, warnings = sql_translator.translate(response['sql_query'])
                if warnings:
                    logging.warning(f"SQL translation warnings: {warnings}")
                response['sql_query'] = mysql_query
            except Exception as e:
                logging.error(f"SQL translation error: {e}")
                raise HTTPException(status_code=500, detail="SQL translation failed")

        return {"result": response}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Optionally, add an endpoint to explicitly end sessions
@app.post("/end_session/{session_id}")
async def end_session(session_id: str):
    """
    End a chat session explicitly.
    """
    with sessions_lock:
        if session_id in active_sessions:
            # Could add cleanup logic for the CHESS session here if needed
            del active_sessions[session_id]
            return {"message": "Session ended successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)