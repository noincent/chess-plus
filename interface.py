import os
import sys
import json
from pathlib import Path
import uuid
import logging

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

from dotenv import load_dotenv
from typing import Dict, Any, List

from runner.database_manager import DatabaseManager
from runner.logger import Logger
from pipeline.workflow_builder import build_pipeline
from pipeline.pipeline_manager import PipelineManager
from runner.task import Task

class SQLInterface:
    def __init__(self, db_mode: str = 'dev'):
        """
        Initialize the SQL Interface.
        
        Args:
            db_mode (str): The database mode ('dev' or 'train')
        """
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('sql_interface.log')
            ]
        )
        # Load environment variables
        load_dotenv(override=True)

        # Verify environment variables
        self._verify_environment()
        
        self.db_mode = db_mode
        self.pipeline_nodes = 'keyword_extraction+entity_retrieval+context_retrieval+column_filtering+table_selection+column_selection+candidate_generation+revision+response_generation'
        
        # Create results directory
        self.results_dir = Path("results/interactive")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Default pipeline setup
        self.pipeline_setup = {
            "keyword_extraction": {
                "engine": "gpt-4o-mini",
                "temperature": 0.2
            },
            "entity_retrieval": {
                "mode": "ask_model"
            },
            "context_retrieval": {
                "mode": "vector_db",
                "top_k": 5
            },
            "column_filtering": {
                "engine": "gpt-4o-mini",
                "temperature": 0.0
            },
            "table_selection": {
                "mode": "ask_model",
                "engine": "gpt-4o-mini",
                "temperature": 0.0,
                "sampling_count": 1
            },
            "column_selection": {
                "mode": "ask_model",
                "engine": "claude-3-5-sonnet-20240620",
                "temperature": 0.0,
                "sampling_count": 1
            },
            "candidate_generation": {
                "engine": "claude-3-5-sonnet-20240620",
                "temperature": 0.0,
                "sampling_count": 1
            },
            "revision": {
                "engine": "claude-3-5-sonnet-20240620",
                "temperature": 0.0,
                "sampling_count": 1
            },
            "response_generation": {
                "engine": "claude-3-5-sonnet-20240620",
                "temperature": 0.0,
                "sampling_count": 1
            }
        }
        
        try:
            # Initialize PipelineManager with setup
            self._init_pipeline_manager()
            
            # Build the pipeline
            self.app = build_pipeline(self.pipeline_nodes)
        except Exception as e:
            logging.error(f"Error initializing pipeline: {e}")
            raise

    def _verify_environment(self):
        """Verify that all required environment variables are set."""
        required_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'DB_ROOT_PATH': os.getenv('DB_ROOT_PATH'),
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        # Verify DB_ROOT_PATH exists
        db_root = Path(required_vars['DB_ROOT_PATH'])
        if not db_root.exists():
            raise EnvironmentError(f"DB_ROOT_PATH does not exist: {db_root}")

    def _init_pipeline_manager(self):
        """Initialize the PipelineManager with the current setup."""
        logging.info("Initializing PipelineManager")
        PipelineManager(self.pipeline_setup)

    def _verify_database(self, db_id: str) -> bool:
        """Verify that the database exists and is properly preprocessed."""
        db_path = Path(os.getenv("DB_ROOT_PATH")) / f"{self.db_mode}_databases" / db_id
        
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
        Lists all available databases in the specified mode.
        
        Returns:
            List[str]: List of database names
        """
        db_path = Path(os.getenv("DB_ROOT_PATH")) / f"{self.db_mode}_databases"
        return [d.name for d in db_path.iterdir() if d.is_dir() and not d.name.startswith('__')]

    def query(self, question: str, db_id: str, evidence: str = "") -> Dict[str, Any]:
        """Process a natural language question and return the SQL query result."""
        # Verify database
        if not self._verify_database(db_id):
            return {
                "error": f"Database {db_id} is not properly set up",
                "status": "error"
            }
            
        # Generate a unique question ID
        question_id = str(uuid.uuid4())
        
        try:
            # Initialize Logger
            Logger(db_id=db_id, 
                  question_id=question_id, 
                  result_directory=str(self.results_dir))
            
            # Initialize DatabaseManager with current db_id
            db_manager = DatabaseManager(db_mode=self.db_mode, db_id=db_id)
            
            # Create task object
            task_data = {
                "question_id": question_id,
                "db_id": db_id,
                "question": question,
                "evidence": evidence
            }
            task = Task(task_data)
            
            # Initialize state
            initial_state = {
                "keys": {
                    "task": task,
                    "tentative_schema": db_manager.get_db_schema(),
                    "execution_history": []
                }
            }
            
            # Run pipeline
            for state in self.app.stream(initial_state):
                continue
                
            final_state = state['__end__']
            
            # Extract results
            execution_history = final_state["keys"]["execution_history"]
            
            # Find the last successful SQL generation
            sql_query = None
            for step in reversed(execution_history):
                if step["node_type"] in ["candidate_generation", "revision"] and "SQL" in step:
                    sql_query = step["SQL"]
                    break
                    
            if not sql_query:
                return {
                    "error": "No SQL query was generated",
                    "status": "error",
                    "execution_history": execution_history
                }
            
            # Execute query and get results
            try:
                results = db_manager.execute_sql(sql=sql_query)
                # Add results to task for response generation
                task.query_results = results
                
                # Find the response in execution history
                response = None
                for step in reversed(execution_history):
                    if step["node_type"] == "response_generation" and "response" in step:
                        response = step["response"]
                        break
                        
                return {
                    "sql_query": sql_query,
                    "results": results,
                    "response": response,
                    "status": "success",
                    "execution_history": execution_history
                }
            except Exception as e:
                logging.error(f"Error executing SQL: {e}")
                return {
                    "sql_query": sql_query,
                    "error": str(e),
                    "status": "error",
                    "execution_history": execution_history
                    }
                
        except Exception as e:
            logging.error(f"Pipeline error: {e}")
            return {
                "error": f"Pipeline error: {str(e)}",
                "status": "error"
            }

def format_results(results: List[tuple]) -> str:
    """Format the results in a readable way."""
    if not results:
        return "No results found"
        
    # If results is a list of tuples, convert to readable format
    formatted = []
    for row in results:
        if isinstance(row, tuple):
            formatted.append(" | ".join(str(item) for item in row))
        else:
            formatted.append(str(row))
    
    return "\n".join(formatted)

if __name__ == "__main__":
    interface = SQLInterface()
    
    # List available databases
    print("Available databases:")
    databases = interface.list_available_databases()
    for idx, db in enumerate(databases):
        print(f"{idx + 1}. {db}")
    
    # Get user input
    db_id = input("\nEnter database name: ")
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
            
        print("\nProcessing your question...")
        
        # Process question
        result = interface.query(question, db_id)
        
        # Display results
        print("\nSQL Query:")
        print(result["sql_query"])
        
        if result["status"] == "success":
            print("\nQuery Results:")
            print(format_results(result["results"]))
            print("\nResponse:")
            print(result["response"])
        else:
            print(f"Error: {result['error']}")
            
        if "execution_history" in result:
            # Save execution history to file
            history_file = Path("results/interactive/last_query_history.json")
            with history_file.open('w') as f:
                json.dump(result["execution_history"], f, indent=2)
            print(f"\nFull execution history saved to {history_file}")