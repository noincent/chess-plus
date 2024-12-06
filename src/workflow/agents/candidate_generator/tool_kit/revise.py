from typing import Dict
import concurrent.futures
from functools import partial

from llm.models import async_llm_chain_call, get_llm_chain
from llm.prompts import get_prompt
from llm.parsers import get_parser
from database_utils.execution import ExecutionStatus
from workflow.system_state import SystemState
from workflow.sql_meta_info import SQLMetaInfo
from workflow.agents.tool import Tool

class Revise(Tool):
    """
    Tool for correcting a SQL query that returns empty set or has a syntax error.
    """

    def __init__(self, template_name: str = None, engine_config: str = None, parser_name: str = None):
        super().__init__()
        self.template_name = template_name
        self.engine_config = engine_config
        self.parser_name = parser_name
        

    def _process_batch(self, batch_data, state: SystemState):
        """
        Process a batch of SQL queries for revision.
        
        Args:
            batch_data (list): List of (index, SQL_meta_info) tuples to process
            state (SystemState): The current system state
        """
        request_list = []
        for index, target_SQL_meta_info in batch_data:
            try:
                request_kwargs = {
                    "DATABASE_SCHEMA": state.get_schema_string(schema_type="complete"),
                    "QUESTION": state.task.question,
                    "HINT": state.task.evidence,
                    "QUERY": target_SQL_meta_info.SQL,
                    "RESULT": self.get_formatted_execution_result(target_SQL_meta_info)
                }
                request_list.append(request_kwargs)
            except Exception as e:
                print(f"Error in Checker while creating request list: {e}")
                continue

        try:
            # Create a prompt and engine for each request
            prompts = [get_prompt(template_name=self.template_name) for _ in request_list]
            engines = [get_llm_chain(**self.engine_config) for _ in request_list]
            parser = get_parser(self.parser_name)
            
            # Process requests in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(request_list)) as executor:
                futures = []
                for prompt, engine, request in zip(prompts, engines, request_list):
                    future = executor.submit(
                        async_llm_chain_call,
                        prompt=prompt,
                        engine=engine,
                        parser=parser,
                        request_list=[request],
                        step=f"{self.tool_name}_parallel"
                    )
                    futures.append(future)
                
                # Gather results
                responses = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        responses.extend(result[0])
                    except Exception as e:
                        print(f"Error in parallel LLM call: {e}")
                        continue
                
            return responses
        except Exception as e:
            print(f"Error in Checker while getting response: {e}")
            return []

    def _run(self, state: SystemState):
        """
        Executes the SQL revision process using parallel processing.
        
        Args:
            state (SystemState): The current system state.
        """
        try:
            key_to_refine = list(state.SQL_meta_infos.keys())[-1]
            target_SQL_meta_infos = state.SQL_meta_infos[key_to_refine]
        except Exception as e:
            print(f"Error in Checker: {e}")
            return

        if key_to_refine.startswith(self.tool_name):
            id = int(key_to_refine[len(self.tool_name)+1:])
            SQL_id = self.tool_name + "_" + str(id+1)
        else:
            SQL_id = self.tool_name + "_1"
        state.SQL_meta_infos[SQL_id] = []

        # Mark queries that need fixing
        for SQL_meta_info in target_SQL_meta_infos:
            try:
                execution_status = SQL_meta_info.execution_status
                if execution_status != ExecutionStatus.SYNTACTICALLY_CORRECT:
                    SQL_meta_info.need_fixing = True
            except Exception:
                SQL_meta_info.need_fixing = True

        need_fixing_SQL_meta_infos = [(index, target_SQL_meta_info) for index, target_SQL_meta_info in enumerate(target_SQL_meta_infos) if target_SQL_meta_info.need_fixing]
        
        # Split into batches for parallel processing
        batch_size = 5  # Process 5 queries per batch
        batches = [need_fixing_SQL_meta_infos[i:i + batch_size] for i in range(0, len(need_fixing_SQL_meta_infos), batch_size)]
        
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(batches), 4)) as executor:
            process_func = partial(self._process_batch, state=state)
            all_responses = list(executor.map(process_func, batches))
        
        # Flatten responses
        response = [item for sublist in all_responses for item in sublist]
        
        # Process results
        index = 0
        for target_SQL_meta_info in target_SQL_meta_infos:
            try:
                if target_SQL_meta_info.need_fixing:
                    refinement_response = response[index]
                    index += 1
                    if "SELECT" not in refinement_response["refined_sql_query"]:
                        refinement_response = {
                            "refined_sql_query": target_SQL_meta_info.SQL
                        }
                else:
                    refinement_response = {
                        "refined_sql_query": target_SQL_meta_info.SQL
                    }
            except Exception as e:
                print(f"Error in Checker while updating SQL meta info: {e}")
                refinement_response = {
                    "refined_sql_query": target_SQL_meta_info.SQL
                }
            
            if "refined_sql_query" in refinement_response:
                if refinement_response["refined_sql_query"]:
                    state.SQL_meta_infos[SQL_id].append(SQLMetaInfo(**{
                        "SQL": refinement_response["refined_sql_query"]
                    }))
                    
    def get_formatted_execution_result(self, target_SQL_meta_info: SQLMetaInfo) -> str:
        try:
            execution_result = target_SQL_meta_info.execution_result
            return {
                "execution_result": execution_result
            }
        except Exception as e:
            return {
                "execution_result": str(e)
            }
        
    def need_to_fix(self, state: SystemState) -> bool:  
        key_to_check = list(state.SQL_meta_infos.keys())[-1]
        SQL_meta_infos = state.SQL_meta_infos[key_to_check]
        needs_fixing = False
        for SQL_meta_info in SQL_meta_infos:
            try:
                execution_status = SQL_meta_info.execution_status
                if execution_status != ExecutionStatus.SYNTACTICALLY_CORRECT:
                    SQL_meta_info.need_fixing = True
                    needs_fixing = True
            except Exception:
                SQL_meta_info.need_fixing = True
                needs_fixing = True
                
        if self.fixing == self.max_fixing:
            return False
        self.fixing += 1

        return needs_fixing    
        
    def _get_updates(self, state: SystemState) -> Dict:
        original_SQL_id = list(state.SQL_meta_infos.keys())[-2]
        refined_SQL_id = list(state.SQL_meta_infos.keys())[-1]
        target_SQL_meta_infos = state.SQL_meta_infos[refined_SQL_id]
        candidates = []
        for target_SQL_meta_info in target_SQL_meta_infos:
            candidates.append({
                "refined_query": target_SQL_meta_info.SQL
            })
        return {
            "original_SQL_id": original_SQL_id,
            "refined_SQL_id": refined_SQL_id,
            "candidates": candidates
        }