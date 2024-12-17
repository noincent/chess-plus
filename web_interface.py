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
import re


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
                config_name="wtl",
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

        text = request.prompt

        # Split prompt and instructions, and pass instructions as evidence
        parts = text.split("INSTRUCTIONS:")
        prompt = parts[0].strip()
        instructions = parts[1].strip() if len(parts) > 1 else ""
        
        # Extract date from instructions if present
        date_match = re.search(r"today's date is (.*?)\n", instructions)
        date_info = f"\n[DATE]\n{date_match.group(1)}" if date_match else ""
        
        # Format the prompt part with date
        formatted_prompt = f"[EMPLOYEE_ID]\n{request.user_id}{date_info}\n\n[QUESTION]\n{prompt}"

        # Process the query using the user's interface with instructions as evidence
        response = interface.chat_query(
            session_id=chess_session_id,
            question=formatted_prompt,
            evidence=instructions
        )

        # Extract just the SQL query from the response
        sql_query = response.get('sql_query', '')
        if not sql_query:
            raise HTTPException(status_code=400, detail="No SQL query was generated")

        # Create a new translator instance for this request
        sql_translator = SQLTranslator()

        # Translate SQL query
        try:
            mysql_query, warnings = sql_translator.translate(sql_query)
            if warnings:
                logging.warning(f"SQL translation warnings: {warnings}")
            # Return in format compatible with frontend
            return {
                "result": {
                    "sql_query": mysql_query
                }
            }
        except Exception as e:
            logging.error(f"SQL translation error: {e}")
            raise HTTPException(status_code=500, detail="SQL translation failed")

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