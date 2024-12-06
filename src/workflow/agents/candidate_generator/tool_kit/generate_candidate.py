from typing import Dict
from pydantic import BaseModel
import concurrent.futures
from functools import partial

from llm.models import async_llm_chain_call, get_llm_chain
from llm.prompts import get_prompt
from llm.parsers import get_parser
from workflow.system_state import SystemState
from workflow.sql_meta_info import SQLMetaInfo
from workflow.agents.tool import Tool

class GenerateCandidate(Tool):
    """
    Tool for generating candidate SQL queries based on the task's question and evidence.
    """

    class GeneratorConfig(BaseModel):
        template_name: str
        engine_config: Dict
        parser_name: str
        sampling_count: int
        input_file_path: str = None

    def __init__(self,
                generator_configs: list[Dict]):
        super().__init__()
        self.generator_configs = [self.GeneratorConfig(**config) for config in generator_configs]
        self.generators_queries = {}
        self.next_generator_to_use = "ALL"

    def _process_generator(self, generator_config, state: SystemState):
        """
        Process a single generator configuration.
        
        Args:
            generator_config (GeneratorConfig): The generator configuration to process.
            state (SystemState): The current system state.
        """
        if self.next_generator_to_use != "ALL" and generator_config.template_name != self.next_generator_to_use:
            return []
            
        request_list = []
        for i in range(generator_config.sampling_count):
            try:
                request_kwargs = {
                    "DATABASE_SCHEMA": state.get_schema_string(schema_type="complete"),
                    "QUESTION": state.task.question,
                    "HINT": state.task.evidence,
                }
                request_list.append(request_kwargs)
            except Exception as e:
                print(f"Error in creating request_kwargs for generator {generator_config.template_name}: {e}")
                continue
        
        try:
            response = async_llm_chain_call(
                prompt=get_prompt(template_name=generator_config.template_name),
                engine=get_llm_chain(**generator_config.engine_config),
                parser=get_parser(generator_config.parser_name),
                request_list=request_list,
                step=f"{self.tool_name}_{generator_config.engine_config['engine_name']}",
            )
            response = [res for sublist in response for res in sublist]
        except Exception as e:
            print(f"Error in generating SQL queries for generator {generator_config.template_name}: {e}")
            return []
            
        sql_meta_infos = []
        for res in response:
            if not res:
                continue
            try:
                sql_meta_info = SQLMetaInfo(**res)
                sql_meta_infos.append(sql_meta_info)
            except Exception as e:
                print(f"Error in creating SQLMetaInfo for generator {generator_config.template_name}: {e}")
                continue
        
        return sql_meta_infos

    def _run(self, state: SystemState):
        """
        Executes the candidate generation process using parallel processing.
        
        Args:
            state (SystemState): The current system state.
        """
        state.SQL_meta_infos[self.tool_name] = []
        for generator_config in self.generator_configs:
            self.generators_queries[generator_config.template_name] = []

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(self.generator_configs), 4)) as executor:
            # Create partial function with state parameter
            process_func = partial(self._process_generator, state=state)
            # Map the function to all generator configs
            results = list(executor.map(process_func, self.generator_configs))

        # Process results
        for generator_config, sql_meta_infos in zip(self.generator_configs, results):
            self.generators_queries[generator_config.template_name] = sql_meta_infos
            if sql_meta_infos:
                state.SQL_meta_infos[self.tool_name].extend(sql_meta_infos)

    def _get_updates(self, state: SystemState) -> Dict:
        SQL_meta_infos = state.SQL_meta_infos[self.tool_name]
        candidates = []
        for i in range(len(SQL_meta_infos)):
            SQL_meta_info = SQL_meta_infos[i]
            if SQL_meta_info.plan:
                candidates.append({
                    "chain_of_thought_reasoning": SQL_meta_info.chain_of_thought_reasoning,
                    "SQL": SQL_meta_info.SQL,
                    "plan": SQL_meta_info.plan
                })
            else:
                candidates.append({
                    "chain_of_thought_reasoning": SQL_meta_info.chain_of_thought_reasoning,
                    "SQL": SQL_meta_info.SQL
                })
        return {
            "node_type": self.tool_name,
            "generation_based_candidates": [{"template_name": generator_config.template_name, "candidates": [candidate.SQL for candidate in self.generators_queries[generator_config.template_name]]} for generator_config in self.generator_configs],
            "candidates": candidates
        }