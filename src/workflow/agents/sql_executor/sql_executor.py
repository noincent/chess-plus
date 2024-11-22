import logging
from typing import Dict, Optional
from workflow.agents.agent import Agent
from workflow.agents.tool import Tool
from workflow.system_state import SystemState
from database_utils.execution import execute_sql, ExecutionStatus

class SQLExecutorTool(Tool):
    """Tool for executing the final SQL query and storing results."""

    def _run(self, state: SystemState) -> None:
        try:
            logging.info("---START: sql_executor_tool---")
            logging.debug(f"SQL Executor State: {vars(state)}")
            
            # Get the latest SQL from the state (after revision)
            key_to_execute = list(state.SQL_meta_infos.keys())[-1]
            sql_candidates = state.SQL_meta_infos[key_to_execute]
            
            if not sql_candidates:
                logging.error("No SQL candidates found")
                state.errors[self.tool_name] = "No SQL candidates found"
                return

            # Select best query (first syntactically correct one)
            best_query = None
            for sql_meta_info in sql_candidates:
                if hasattr(sql_meta_info, 'execution_status') and \
                   sql_meta_info.execution_status == ExecutionStatus.SYNTACTICALLY_CORRECT:
                    best_query = sql_meta_info.SQL
                    logging.info(f"Selected syntactically correct query: {best_query}")
                    break
            
            # Fallback to first query if none marked as correct
            if not best_query and sql_candidates:
                best_query = sql_candidates[0].SQL
                logging.info(f"Falling back to first query: {best_query}")
            
            if not best_query:
                logging.error("No valid SQL query found")
                state.errors[self.tool_name] = "No valid SQL query found"
                return

            # Execute the selected query
            logging.info(f"Executing SQL query: {best_query}")
            result = execute_sql(
                db_path=f"data/dev/dev_databases/{state.task.db_id}/{state.task.db_id}.sqlite",
                sql=best_query,
                fetch="all",
                timeout=60
            )
            
            # Store results in state
            query_result = {
                'sql_query': best_query,
                'results': result,
                'status': 'success' if result is not None else 'error',
                'error': None
            }
            state.update_query_result(query_result)
            logging.info(f"Query execution result: {query_result}")

        except Exception as e:
            error_msg = f"Error executing SQL: {str(e)}"
            logging.error(error_msg)
            state.errors[self.tool_name] = error_msg
        finally:
            logging.info(f"---END: sql_executor_tool---")

    def _get_updates(self, state: SystemState) -> Dict:
        """Return updates for logging."""
        if hasattr(state, 'query_result'):
            updates = {
                'executed_query': state.query_result.get('sql_query'),
                'status': state.query_result.get('status'),
                'results': state.query_result.get('results')
            }
            logging.info(f"SQL Executor updates: {updates}")
            return updates
        return {}

class SQLExecutor(Agent):
    """Agent responsible for executing the final SQL query."""
    
    def __init__(self, config: dict):
        super().__init__(
            name="SQL Executor",
            task="execute the final SQL query and store results",
            config=config
        )
        
        self.tools = {
            "sql_executor": SQLExecutorTool()
        }
        logging.info(f"Initialized {self.name} agent with tools: {list(self.tools.keys())}") 