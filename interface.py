import os
import sys
import json
from pathlib import Path
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from threading import Lock

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

from dotenv import load_dotenv
from workflow.team_builder import build_team
from workflow.chat_state import ChatSystemState
from workflow.system_state import SystemState
from runner.database_manager import DatabaseManager
from runner.logger import Logger
from runner.task import Task
from chat.session import ChatSession, ChatMessage
from workflow.agents.response_generator.response_generator import ResponseGenerator
from workflow.agents.response_generator.response_formatter import ResponseFormatter

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class CHESSInterface:
    """Interface for the CHESS system with integrated chat and response generation."""
    
    def __init__(self, config_name: str = "CHESS_IR_CG_UT", db_mode: str = 'dev'):
        """Initialize the CHESS Interface with response generation capabilities."""
        self._setup_logging()
        self._load_environment()
        self._verify_environment()
        
        self.db_mode = db_mode  # Make sure this is set before any database operations
        self.config_name = config_name
        self.config = self._load_config()
        
        # Create results directory first
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path("results") / "interactive" / timestamp
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Logger with required parameters
        Logger(
            db_id="interface",
            question_id="init",
            result_directory=str(self.results_dir)
        )
        
        # Initialize components
        self.active_sessions: Dict[str, ChatSession] = {}
        response_generator_config = self.config.get('team_agents', {}).get('response_generator', {})
        self.response_generator = ResponseGenerator(response_generator_config)
        self.response_formatter = ResponseFormatter()
        
        # Set number of workers
        self.num_workers = self.config.get('num_workers', 1)
        logging.info(f"Setting number of workers to: {self.num_workers}")
        
        # Add num_workers to config for RunManager
        self.config['num_workers'] = self.num_workers
        
        # Build the team
        try:
            self.team = build_team(self.config)
            logging.info(f"Successfully initialized CHESS with {config_name} configuration")
        except Exception as e:
            logging.error(f"Error building team: {e}")
            raise

        # Add thread safety for session management
        self._sessions_lock = Lock()

    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('chess_interface.log')
            ]
        )

    def _load_environment(self):
        """Load environment variables."""
        load_dotenv(override=True)
        self.db_root_path = os.getenv("DB_ROOT_PATH")
        if not self.db_root_path:
            raise EnvironmentError("DB_ROOT_PATH environment variable not set")

    def _verify_environment(self):
        """Verify that all required environment variables and paths exist."""
        required_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'DB_ROOT_PATH': self.db_root_path,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        db_root = Path(self.db_root_path)
        if not db_root.exists():
            raise EnvironmentError(f"DB_ROOT_PATH does not exist: {db_root}")

    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration file."""
        config_path = Path("run") / "configs" / f"{self.config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path) as f:
            import yaml
            return yaml.safe_load(f)

    def _verify_database(self, db_id: str) -> bool:
        """
        Verify that the database exists and is properly preprocessed.
        
        Args:
            db_id (str): Database identifier
            
        Returns:
            bool: True if database is properly set up, False otherwise
        """
        # Initialize DatabaseManager before verification
        DatabaseManager(db_mode=self.db_mode, db_id=db_id)
        
        db_path = Path(self.db_root_path) / f"{self.db_mode}_databases" / db_id
        
        # Check if database exists
        if not db_path.exists():
            logging.error(f"Database directory not found: {db_path}")
            return False
        
        # Check for SQLite file
        if not (db_path / f"{db_id}.sqlite").exists():
            logging.error(f"SQLite database file not found: {db_path / f'{db_id}.sqlite'}")
            return False
        
        # Check for preprocessed files
        preprocessed_path = db_path / "preprocessed"
        if not preprocessed_path.exists():
            logging.error(f"Preprocessed directory not found: {preprocessed_path}")
            return False
        
        required_files = [f"{db_id}_lsh.pkl", f"{db_id}_minhashes.pkl"]
        for file in required_files:
            if not (preprocessed_path / file).exists():
                logging.error(f"Required preprocessed file not found: {preprocessed_path / file}")
                return False
        
        return True

    def list_available_databases(self) -> List[str]:
        """
        List all available databases in the specified mode.
        
        Returns:
            List[str]: List of database names
        """
        db_path = Path(self.db_root_path) / f"{self.db_mode}_databases"
        return [d.name for d in db_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

    def start_chat_session(self, db_id: str) -> str:
        """
        Start a new chat session for a specific database.
        
        Args:
            db_id (str): Database identifier
            
        Returns:
            str: Session identifier
        """
        if not self._verify_database(db_id):
            raise ValueError(f"Database {db_id} is not properly set up")
            
        session_id = str(uuid.uuid4())
        
        # Get chat settings from config
        chat_settings = self.config.get('chat_settings', {})
        window_size = chat_settings.get('memory', {}).get('window_size', 10)
        max_history = chat_settings.get('context', {}).get('max_history_messages', 50)
        
        # Create new session
        with self._sessions_lock:
            self.active_sessions[session_id] = ChatSession(
                session_id=session_id,
                db_id=db_id,
                window_size=window_size,
                max_history=max_history
            )
        
        return session_id

    def end_chat_session(self, session_id: str):
        """
        End a chat session and save its history.
        
        Args:
            session_id (str): Session identifier
        """
        with self._sessions_lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.save(str(self.results_dir))
                del self.active_sessions[session_id]

    def chat_query(self, session_id: str, question: str, evidence: str = "") -> Dict[str, Any]:
        """Process a chat query and return results."""
        try:
            session = self._get_session(session_id)
            logging.info(f"Processing query for session {session_id}: {question[:100]}...")
            
            # Create initial state
            state = ChatSystemState(
                task=Task(
                    question_id=uuid.uuid4().hex,
                    db_id=session.db_id,
                    question=question,
                    evidence=evidence
                ),
                tentative_schema={},
                execution_history=[],
                chat_context=session.context,
                chat_memory=session.history.messages,
                chat_session_id=session_id
            )
            
            logging.info(f"Created state with context: {session.context.get_conversation_summary()}")
            logging.info(f"Current message history size: {len(session.history.messages)}")
            
            # Use invoke() method to execute the graph
            result = self.team.invoke(state)
            
            # Create response dictionary
            response_dict = {
                "status": "success" if not result.get('errors') else "error",
                "sql_query": result.get('query_result', {}).get('sql_query'),
                "results": result.get('query_result', {}).get('results'),
                "natural_language_response": result.get('response_data', {}).get('response', "No response generated"),
                "execution_history": result.get('execution_history', [])
            }
            
            # Create and add chat message to session
            message = ChatMessage(
                content=question,
                role="user",
                sql_query=response_dict["sql_query"],
                query_result=response_dict["results"],
                response=response_dict["natural_language_response"]
            )
            
            logging.info("Adding response to session")
            logging.debug(f"SQL Query: {response_dict['sql_query']}")
            session.add_message(message)
            
            logging.info(f"Updated session context: {session.context.get_conversation_summary()}")
            
            return response_dict
            
        except Exception as e:
            logging.error(f"Error in chat_query: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "execution_history": []
            }
            
            # Add error message to session
            error_message = ChatMessage(
                content=question,
                role="user",
                response=f"Error: {str(e)}"
            )
            logging.info("Adding error message to session")
            session.add_message(error_message)
            
            return error_response

    def _format_result(self, state: SystemState) -> Dict[str, Any]:
        """Format the state results into a consistent response structure."""
        # Get the latest SQL execution result
        sql_result = state.get_latest_execution_result()
        sql_query = state.get_latest_sql_query()
        
        if state.errors:
            return {
                "status": "error",
                "error": " | ".join(state.errors.values()),
                "execution_history": state.execution_history
            }
        
        return {
            "status": "success",
            "sql_query": sql_query,
            "results": sql_result,
            "natural_language_response": state.response_data.get("response", "No response generated"),
            "reasoning": state.response_data.get("reasoning", "No reasoning provided"),
            "execution_history": state.execution_history
        }

    def _handle_error(self, error: Union[str, Exception]) -> str:
        """
        Generate a user-friendly error message.
        
        Args:
            error (Union[str, Exception]): The error to handle
            
        Returns:
            str: User-friendly error message
        """
        error_str = str(error)
        
        # Common error patterns and their user-friendly messages
        error_patterns = {
            'no such table': "I couldn't find one of the tables I was trying to query. This might be because I misunderstood which tables contain the information you're looking for.",
            'no such column': "I tried to use a column that doesn't exist in the database. Could you please rephrase your question using different terms?",
            'syntax error': "I made a mistake in forming the query. Could you try rephrasing your question?",
            'execution timed out': "The query took too long to complete. Could you try asking for something more specific?"
        }
        
        for pattern, message in error_patterns.items():
            if pattern.lower() in error_str.lower():
                return message
                
        # Generic error message
        return (
            f"I encountered an issue: {error_str}. "
            "Could you please try rephrasing your question? "
            "If you're asking about specific data, try being more specific about what you're looking for."
        )

    def get_session_response_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the response history for a session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            List[Dict[str, Any]]: List of messages with responses
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
            
        session = self.active_sessions[session_id]
        return [
            {
                'question': msg.content,
                'response': msg.response,
                'timestamp': msg.timestamp.isoformat(),
                'has_sql': bool(msg.sql_query)
            }
            for msg in session.history.messages
        ]

    def get_last_response(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last response from a session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Last message and response if available
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
            
        session = self.active_sessions[session_id]
        if not session.history.messages:
            return None
            
        last_msg = session.history.messages[-1]
        return {
            'question': last_msg.content,
            'response': last_msg.response,
            'timestamp': last_msg.timestamp.isoformat(),
            'sql_query': last_msg.sql_query,
            'has_results': bool(last_msg.query_result)
        }


    def _process_query(self, state: ChatSystemState, session: ChatSession) -> Dict[str, Any]:
        """
        Process a query with the CHESS team.
        
        Args:
            state (ChatSystemState): Current system state
            session (ChatSession): Active chat session
            
        Returns:
            Dict[str, Any]: Query results and response
        """
        # Initialize DatabaseManager with the current session's database
        DatabaseManager(db_mode=self.db_mode, db_id=session.db_id)
        
        # Setup thread configuration
        thread_id = f"{datetime.now().isoformat()}_{session.db_id}_{state.task.question_id}"
        thread_config = {
            "configurable": {
                "thread_id": thread_id,
                "chat_context": session.context.get_summary(),
                "chat_history": session.context.get_conversation_summary(max_entries=3)
            }
        }
        
        # Process through team
        final_state = None
        for state_dict in self.team.stream(state, thread_config, stream_mode="values"):
            final_state = state_dict

        if not final_state:
            return {
                "error": "No results generated",
                "status": "error"
            }

        # Extract results
        sql_query = self._extract_sql_query(final_state['execution_history'])
        if not sql_query:
            return {
                "error": "No valid SQL query was generated",
                "status": "error",
                "execution_history": final_state['execution_history']
            }

        # Execute query
        try:
            results = DatabaseManager().execute_sql(sql=sql_query)
            formatted_results = self.format_results(results)
            
            # Add execution results to state history with explicit structure
            final_state['execution_history'].append({
                "tool_name": "sql_execution",
                "sql_query": sql_query,
                "execution_result": formatted_results,  # This should be a list of dicts
                "status": "success"
            })
            
            # Add debug logging
            logging.debug(f"Adding SQL execution results to history: {formatted_results}")
            
            return {
                "sql_query": sql_query,
                "results": formatted_results,
                "status": "success",
                "execution_history": final_state['execution_history'],
                "chat_context": session.context.get_summary()
            }
        except Exception as e:
            logging.error(f"Error executing SQL: {e}")
            final_state['execution_history'].append({
                "tool_name": "sql_execution",
                "sql_query": sql_query,
                "error": str(e),
                "status": "error"
            })
            return {
                "sql_query": sql_query,
                "error": str(e),
                "status": "error",
                "execution_history": final_state['execution_history']
            }

    def _extract_sql_query(self, execution_history: List[Dict[str, Any]]) -> Optional[str]:
        """Extract the final SQL query from execution history."""
        # First try evaluation step
        for step in reversed(execution_history):
            if step.get("tool_name") == "evaluate" and "selected_candidate" in step:
                return step["selected_candidate"].strip()
        
        # Try candidate generation
        for step in reversed(execution_history):
            if step.get("tool_name") == "generate_candidate":
                candidates = step.get("candidates", [])
                if candidates and isinstance(candidates[0], dict) and "SQL" in candidates[0]:
                    return candidates[0]["SQL"].strip()
        
        # Try final_SQL
        for step in reversed(execution_history):
            if "final_SQL" in step and isinstance(step["final_SQL"], dict):
                return step["final_SQL"].get("PREDICTED_SQL", "").strip()
                
        return None

    @staticmethod
    def format_results(results: List[tuple]) -> List[Dict[str, Any]]:
        """Format query results into a more readable structure."""
        if not results:
            return []

        formatted = []
        for row in results:
            if isinstance(row, tuple):
                formatted.append({f"column_{i}": str(value) for i, value in enumerate(row)})
            else:
                formatted.append({"column_0": str(row)})

        logging.debug(f"Formatted results: {formatted}")
        return formatted

    def get_chat_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the chat session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Dict[str, Any]: Session summary
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
            
        session = self.active_sessions[session_id]
        return session.get_context_summary()

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active chat sessions.
        
        Returns:
            List[Dict[str, Any]]: List of session summaries
        """
        with self._sessions_lock:
            return [
                {
                    "session_id": session_id,
                    "db_id": session.db_id,
                    "message_count": len(session.history.messages)
                }
                for session_id, session in self.active_sessions.items()
            ]

    def _get_session(self, session_id: str) -> ChatSession:
        """
        Get an active chat session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            ChatSession: Active chat session
            
        Raises:
            ValueError: If session ID is invalid
        """
        with self._sessions_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Invalid session ID: {session_id}")
        
            return self.active_sessions[session_id]

def main():
    """Main function for command-line interface."""
    try:
        interface = CHESSInterface()
    except Exception as e:
        print(f"Error initializing CHESS: {e}")
        return

    # List available databases
    print("Available databases:")
    databases = interface.list_available_databases()
    for idx, db in enumerate(databases, 1):
        print(f"{idx}. {db}")

    # Get database selection
    session_id = None  # Track the session ID outside the question loop
    while True:
        db_choice = input("\nEnter database number or name (or 'quit' to exit): ")
        if db_choice.lower() == 'quit':
            if session_id:  # Clean up session before quitting
                interface.end_chat_session(session_id)
            return
        if db_choice.lower() == 'back':
            if session_id:  # Clean up session before switching databases
                interface.end_chat_session(session_id)
                session_id = None
            break

        # Convert number to database name if needed
        try:
            if db_choice.isdigit():
                idx = int(db_choice) - 1
                if 0 <= idx < len(databases):
                    db_id = databases[idx]
                else:
                    print("Invalid database number")
                    continue
            else:
                db_id = db_choice
                if db_id not in databases:
                    print("Database not found")
                    continue
        except Exception as e:
            print(f"Error selecting database: {e}")
            continue

        # Process questions for selected database
        while True:
            question = input("\nEnter your question (or 'back' to change database, 'quit' to exit): ")
            if question.lower() == 'quit':
                if session_id:  # Clean up session before quitting
                    interface.end_chat_session(session_id)
                return
            if question.lower() == 'back':
                if session_id:  # Clean up session before switching databases
                    interface.end_chat_session(session_id)
                    session_id = None
                break

            print("\nProcessing your question...")
            try:
                # Create a chat session only if one doesn't exist
                if session_id is None:
                    logging.info(f"Starting new chat session {session_id} for database: {db_id}")
                    session_id = interface.start_chat_session(db_id)
                
                # Use chat_query instead of query
                result = interface.chat_query(session_id, question)
                
                if result["status"] == "success":
                    print("\nSQL Query:")
                    print(result["sql_query"])
                    print("\nResults:")
                    for row in result["results"]:
                        print(row)
                    print("\nResponse:")
                    print(result.get("natural_language_response", "No response generated"))
                else:
                    print(f"\nError: {result.get('error', 'Unknown error')}")

                # Save execution history
                history_file = interface.results_dir / f"{db_id}_{uuid.uuid4()}.json"
                with open(history_file, 'w') as f:
                    json.dump(result.get("execution_history", []), f, indent=2, cls=DateTimeEncoder)
                print(f"\nExecution history saved to: {history_file}")

            except Exception as e:
                print(f"Error processing question: {e}")

if __name__ == "__main__":
    main()