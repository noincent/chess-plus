import logging
from typing import Dict, List, Any

from llm.models import async_llm_chain_call
from pipeline.utils import node_decorator, get_last_node_result
from pipeline.pipeline_manager import PipelineManager
from runner.database_manager import DatabaseManager


@node_decorator(check_schema_status=False)
def response_generation(task: Any, tentative_schema: Dict[str, List[str]], execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a natural language response based on the SQL query results.
    """
    logging.info("Starting response generation")

    # # Get the SQL query from execution history
    # sql_query = None
    # for step in reversed(execution_history):
    #     if step["node_type"] in ["candidate_generation", "revision"] and "SQL" in step:
    #         sql_query = step["SQL"]
    #         break
    
    # if not sql_query:
    #     logging.error("No SQL query found in execution history")
    #     return {
    #         "response": "Error: Could not find SQL query.",
    #         "chain_of_thought_reasoning": "Failed to locate SQL query in execution history"
    #     }

    # # Get the query results
    # query_results = getattr(task, 'query_results', [])

    # sql_query = None
    # query_results = []
    
    # for step in reversed(execution_history):
    #     if step["node_type"] == "query_execution":
    #         query_results = step["results"]
    #     elif step["node_type"] in ["candidate_generation", "revision"] and "SQL" in step:
    #         sql_query = step["SQL"]
            
    #     if sql_query and query_results:  # Break if we have both
    #         break
     # Get the SQL query from execution history
    sql_query = None
    for step in reversed(execution_history):
        if step["node_type"] in ["candidate_generation", "revision"] and "SQL" in step:
            sql_query = step["SQL"]
            break
    
    if not sql_query:
        logging.error("No SQL query found in execution history")
        return {
            "response": "Error: Could not find SQL query.",
            "chain_of_thought_reasoning": "Failed to locate SQL query in execution history"
        }
    
    # Execute the query to get results
    try:
        query_results = DatabaseManager().execute_sql(sql=sql_query)
    except Exception as e:
        logging.error(f"Error executing SQL query: {str(e)}")
        return {
            "response": f"Error executing query: {str(e)}",
            "chain_of_thought_reasoning": "Failed to execute SQL query"
        }

    try:
        logging.info("Fetching prompt, engine, and parser from PipelineManager")
        prompt, engine, parser = PipelineManager().get_prompt_engine_parser()
        
        request_kwargs = {
            "QUESTION": task.question,
            "SQL": sql_query,
            "RESULTS": str(query_results)
        }
        
        logging.info("Initiating asynchronous LLM chain call for response generation")
        response = async_llm_chain_call(
            prompt=prompt,
            engine=engine,
            parser=parser,
            request_list=[request_kwargs],
            step="response_generation",
            sampling_count=1
        )
        
        if response and len(response) > 0:
            result = response[0][0]  # Get the first parsed response
            logging.info("Successfully generated response")
        else:
            logging.warning("No response generated from LLM")
            result = {
                "response": "Sorry, I couldn't generate a response for the query results.",
                "chain_of_thought_reasoning": "No response received from language model"
            }
            
    except Exception as e:
        logging.error(f"Error in response generation: {str(e)}")
        result = {
            "response": "An error occurred while generating the response.",
            "chain_of_thought_reasoning": f"Error during response generation: {str(e)}"
        }
    
    return result