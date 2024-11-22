from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

from workflow.agents.agent import Agent
from workflow.agents.tool import Tool
from workflow.system_state import SystemState
from llm.models import get_llm_chain, call_engine
from llm.prompts import get_prompt
from llm.parsers import get_parser, OutputParserException
from workflow.agents.response_generator.response_types import (
    QueryContext,
    ResponseMetadata,
    GeneratedResponse,
    ResponseTemplates
)

class GenerateResponseTool(Tool):
    """Tool for generating natural language responses."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        engine_config = config.get("engine_config", {})
        self.engine = get_llm_chain(
            engine_config.get("engine_name", "gpt-4o-mini"),
            engine_config.get("temperature", 0)
        )
        self.prompt = get_prompt("response_generation")
        self.parser = get_parser("response_generation")

    def _run(self, state: SystemState) -> None:
        """Required implementation of the abstract _run method."""
        # Add debug logging
        logging.debug(f"Response Generator State: {vars(state)}")
        
        # Get the latest SQL info from execution history
        sql_meta_info = None
        
        # First check execution history for SQL results
        for step in reversed(state.execution_history):
            if step.get("tool_name") == "sql_execution":
                sql_meta_info = {
                    'SQL': step.get('sql_query'),
                    'execution_result': step.get('results', []),
                    'status': step.get('status'),
                    'error': step.get('error')
                }
                break
        
        # If not found in execution history, check query_result
        if not sql_meta_info and hasattr(state, 'query_result'):
            query_result = state.query_result
            if isinstance(query_result, dict):
                sql_meta_info = {
                    'SQL': query_result.get('sql_query'),
                    'execution_result': query_result.get('results', []),
                    'status': query_result.get('status'),
                    'error': query_result.get('error')
                }
        
        if not sql_meta_info:
            state.errors[self.tool_name] = "No SQL query information found"
            return

        # Add logging to debug the SQL meta info
        logging.info(f"SQL from SQL Meta Info from response generator in _run method: {sql_meta_info.get('SQL')}")
        
        # Check for execution errors
        if sql_meta_info.get("status") == "error" or sql_meta_info.get("error"):
            error_msg = sql_meta_info.get("error", "Unknown error during SQL execution")
            state.errors[self.tool_name] = f"SQL execution error: {error_msg}"
            return

        context = self._prepare_context(state, sql_meta_info)
        
        # Add logging to debug the context
        logging.debug(f"Prepared Context: {context.to_dict()}")
        
        try:
            # Get raw response from engine
            raw_response = call_engine(
                message=self.prompt.format(context=context.to_dict()),
                engine=self.engine
            )
            
            # Add logging for raw response
            logging.debug(f"Raw LLM Response:\n{raw_response}")
            
            # Clean up duplicated lines while preserving JSON structure
            cleaned_response = self._clean_response(raw_response)
            
            try:
                parsed_response = self.parser.parse(cleaned_response)
                # Check if required fields exist before accessing
                if not parsed_response.get("reasoning"):
                    parsed_response["reasoning"] = "No reasoning provided"
                if not parsed_response.get("response"):
                    parsed_response["response"] = "I apologize, but I couldn't generate a proper response."
                
                state.response_data = {
                    "response": parsed_response["response"],
                    "reasoning": parsed_response["reasoning"],
                    "context_used": context.to_dict(),
                    "metadata": self._generate_metadata(parsed_response, state)
                }
            except OutputParserException as parse_error:
                # Fallback response with JSON format
                logging.error(f"Parser error: {str(parse_error)}")
                fallback_response = json.dumps({
                    "reasoning": f"Error occurred while parsing the response: {str(parse_error)}",
                    "response": "I apologize, but I encountered an issue formatting my response. Please try rephrasing your question."
                })
                try:
                    parsed_response = self.parser.parse(fallback_response)
                    state.response_data = {
                        "response": parsed_response["response"],
                        "reasoning": parsed_response["reasoning"],
                        "context_used": context.to_dict()
                    }
                except:
                    state.response_data = {
                        "response": "System error occurred",
                        "reasoning": error_msg,
                        "context_used": context.to_dict()
                    }
                
        except Exception as e:
            error_msg = str(e)
            state.errors[self.tool_name] = f"Error generating response: {error_msg}"
            # Provide a fallback response in JSON format
            fallback_response = json.dumps({
                "reasoning": f"Error occurred while generating response: {error_msg}",
                "response": "I apologize, but I encountered an issue processing your request. Could you please try rephrasing your question?"
            })
            try:
                parsed_response = self.parser.parse(fallback_response)
                state.response_data = {
                    "response": parsed_response["response"],
                    "reasoning": parsed_response["reasoning"],
                    "context_used": context.to_dict()
                }
            except:
                state.response_data = {
                    "response": "System error occurred",
                    "reasoning": error_msg,
                    "context_used": context.to_dict()
                }

    def _get_updates(self, state: SystemState) -> Dict[str, Any]:
        """Required implementation of the abstract _get_updates method."""
        if self.tool_name in state.errors:
            return {
                "status": "error",
                "error": state.errors[self.tool_name]
            }
        
        return {
            "response": state.response_data.get("response"),
            "reasoning": state.response_data.get("reasoning"),
            "context_used": state.response_data.get("context_used")
        }

    def _get_latest_sql_meta_info(self, state: SystemState) -> Optional[Dict[str, Any]]:
        """Get the most recent SQL query information from state."""
        # First check if there's a direct query_result in state
        if hasattr(state, 'query_result'):
            query_result = state.query_result
            if isinstance(query_result, dict):
                return {
                    'SQL': query_result.get('sql_query'),
                    'execution_result': query_result.get('results', []),
                    'status': query_result.get('status'),
                    'error': query_result.get('error')
                }

        # Fallback to checking execution history
        for step in reversed(state.execution_history):
            if step.get("tool_name") == "sql_execution":
                logging.debug(f"Found SQL execution step: {step}")
                execution_result = step.get("execution_result", [])
                
                # Convert execution result to expected format if needed
                if execution_result and isinstance(execution_result[0], dict):
                    # Extract values from the column_X format
                    query_results = [list(row.values()) for row in execution_result]
                else:
                    query_results = execution_result

                return {
                    "SQL": step.get("sql_query"),
                    "execution_result": query_results,
                    "status": step.get("status"),
                    "error": step.get("error")
                }
        return None

    def _prepare_context(self, state: SystemState, sql_meta_info: Dict[str, Any]) -> QueryContext:
        """Prepare context for response generation."""
        # Get previous result and ensure it's in the correct format
        previous_result = None
        if hasattr(state, 'chat_context'):
            last_result = state.chat_context.last_query_result
            if isinstance(last_result, list):
                # Convert tuple results to a more readable format
                if last_result and isinstance(last_result[0], tuple):
                    results = [list(item) for item in last_result]
                else:
                    results = last_result
                previous_result = {"results": results}
            elif isinstance(last_result, dict):
                previous_result = last_result

        # Create QueryContext with properly formatted data
        return QueryContext(
            question=state.task.question,
            sql_query=sql_meta_info.get('SQL', 'No SQL query available'),
            query_results=sql_meta_info.get('execution_result', []),
            current_topic=state.chat_context.current_topic if hasattr(state, 'chat_context') else None,
            referenced_tables=state.chat_context.referenced_tables if hasattr(state, 'chat_context') else [],
            referenced_columns=state.chat_context.referenced_columns if hasattr(state, 'chat_context') else [],
            previous_result=previous_result,
            question_context=state.chat_context.question_context if hasattr(state, 'chat_context') else {}
        )

    def _generate_metadata(self, parsed_response: Dict[str, str], state: SystemState) -> Dict[str, Any]:
        """Generate metadata about the response."""
        metadata = ResponseMetadata(
            tables_mentioned=state.chat_context.referenced_tables if hasattr(state, 'chat_context') else [],
            columns_mentioned=state.chat_context.referenced_columns if hasattr(state, 'chat_context') else [],
            referenced_previous_query='previous' in parsed_response['reasoning'].lower(),
            contains_aggregates=any(term in parsed_response['reasoning'].lower() 
                                  for term in ['average', 'count', 'sum', 'max', 'min']),
            response_type="direct_answer" if parsed_response['response'] else "error"
        )
        return metadata.to_dict()  # Convert to dict before returning

    def _clean_response(self, raw_response: str) -> str:
        """
        Cleans the raw LLM response by removing duplicate 'reasoning' and 'response' entries.

        Args:
            raw_response (str): The raw response string from the LLM.

        Returns:
            str: The cleaned response string.
        """
        logging.debug("Cleaning raw LLM response to remove duplicate reasoning and response entries.")
        # Split the response into lines
        lines = raw_response.split('\n')
        cleaned_lines = []
        reasoning_found = False
        response_found = False

        for line in lines:
            if '"reasoning":' in line:
                if not reasoning_found:
                    cleaned_lines.append(line)
                    reasoning_found = True
                else:
                    logging.debug("Duplicate 'reasoning' entry found and removed.")
                    continue
            elif '"response":' in line:
                if not response_found:
                    cleaned_lines.append(line)
                    response_found = True
                else:
                    logging.debug("Duplicate 'response' entry found and removed.")
                    continue
            else:
                cleaned_lines.append(line)
        
        cleaned_response = '\n'.join(cleaned_lines)
        logging.debug(f"Cleaned Response:\n{cleaned_response}")
        return cleaned_response

class ResponseGenerator(Agent):
    """Agent responsible for generating natural language responses with context awareness."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the response generator."""
        name = "Response Generator"
        task = "Generate natural language responses for database query results"
        super().__init__(name=name, task=task, config=config)
        
        # Initialize tools
        self.tools = {
            "generate_response": GenerateResponseTool(
                self.tools_config.get("generate_response", {})
            )
        }