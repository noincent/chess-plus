import logging
from typing import Dict, List
import concurrent.futures
from functools import partial

from database_utils.db_catalog.csv_utils import load_tables_description

from runner.database_manager import DatabaseManager
from workflow.system_state import SystemState
from workflow.agents.tool import Tool

import os
from dotenv import load_dotenv

load_dotenv()

class RetrieveContext(Tool):
    """
    Tool for retrieving context information based on the task's question and evidence.
    """

    def __init__(self, top_k: int):
        super().__init__()
        self.top_k = top_k
        
    def _run(self, state: SystemState):
        """
        Executes the context retrieval process.
        
        Args:
            state (SystemState): The current system state.
        """
        
        # Get conversation summary if available
        chat_context = ""
        if hasattr(state, 'chat_context') and state.chat_context:
            summary = state.chat_context.get_conversation_summary(max_entries=3)
            chat_context = "\n".join(summary.get('conversation', []))
        
        retrieved_columns = self._find_most_similar_columns(
            question=state.task.question,
            evidence=state.task.evidence,
            keywords=state.keywords,
            chat_context=chat_context,
            top_k=self.top_k
        )
        
        state.schema_with_descriptions = self._format_retrieved_descriptions(retrieved_columns)

    def _find_most_similar_columns(self, question: str, evidence: str, keywords: List[str], chat_context: str, top_k: int) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Finds the most similar columns based on the question and evidence using parallel processing.

        Args:
            question (str): The question string.
            evidence (str): The evidence string.
            keywords (List[str]): The list of keywords.
            chat_context (str): The chat context string.
            top_k (int): The number of top similar columns to retrieve.

        Returns:
            Dict[str, Dict[str, Dict[str, str]]]: A dictionary containing the most similar columns with descriptions.
        """
        logging.info("Finding the most similar columns")
        
        # Process keywords in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(keywords), 4)) as executor:
            process_func = partial(self._process_keyword_query, question=question, evidence=evidence, top_k=top_k)
            results = list(executor.map(process_func, keywords))
        
        # Merge results
        tables_with_descriptions = {}
        for result in results:
            for table_name, column_descriptions in result.items():
                if table_name not in tables_with_descriptions:
                    tables_with_descriptions[table_name] = {}
                for column_name, description in column_descriptions.items():
                    if (column_name not in tables_with_descriptions[table_name] or 
                        description["score"] > tables_with_descriptions[table_name][column_name]["score"]):
                        tables_with_descriptions[table_name][column_name] = description
        
        return tables_with_descriptions

    def _process_keyword_query(self, keyword: str, question: str, evidence: str, top_k: int) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Process a single keyword query.
        
        Args:
            keyword (str): The keyword to process.
            question (str): The question string.
            evidence (str): The evidence string.
            top_k (int): Number of top results to retrieve.
            
        Returns:
            Dict[str, Dict[str, Dict[str, str]]]: Retrieved descriptions for the keyword.
        """
        tables_with_descriptions = {}
        question_based_query = f"{question} {keyword}"
        evidence_based_query = f"{evidence} {keyword}"
        
        retrieved_question_based_query = DatabaseManager().query_vector_db(question_based_query, top_k=top_k)
        retrieved_evidence_based_query = DatabaseManager().query_vector_db(evidence_based_query, top_k=top_k)
        
        tables_with_descriptions = self._add_description(tables_with_descriptions, retrieved_question_based_query)
        tables_with_descriptions = self._add_description(tables_with_descriptions, retrieved_evidence_based_query)
        
        return tables_with_descriptions

    def _add_description(self, tables_with_descriptions: Dict[str, Dict[str, Dict[str, str]]], 
                         retrieved_descriptions: Dict[str, Dict[str, Dict[str, str]]]) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Adds descriptions to tables from retrieved descriptions.

        Args:
            tables_with_descriptions (Dict[str, Dict[str, Dict[str, str]]]): The current tables with descriptions.
            retrieved_descriptions (Dict[str, Dict[str, Dict[str, str]]]): The retrieved descriptions.

        Returns:
            Dict[str, Dict[str, Dict[str, str]]]: The updated tables with descriptions.
        """
        if retrieved_descriptions is None:
            logging.warning("No descriptions retrieved")
            return tables_with_descriptions
        for table_name, column_descriptions in retrieved_descriptions.items():
            if table_name not in tables_with_descriptions:
                tables_with_descriptions[table_name] = {}
            for column_name, description in column_descriptions.items():
                if (column_name not in tables_with_descriptions[table_name] or 
                    description["score"] > tables_with_descriptions[table_name][column_name]["score"]):
                    tables_with_descriptions[table_name][column_name] = description
        return tables_with_descriptions

    def _format_retrieved_descriptions(self, retrieved_columns: Dict[str, Dict[str, Dict[str, str]]]) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Formats retrieved descriptions by removing the score key.

        Args:
            retrieved_columns (Dict[str, Dict[str, Dict[str, str]]]): The retrieved columns with descriptions.

        Returns:
            Dict[str, Dict[str, Dict[str, str]]]: The formatted descriptions.
        """
        logging.info("Formatting retrieved descriptions")
        for column_descriptions in retrieved_columns.values():
            for column_info in column_descriptions.values():
                column_info.pop("score", None)
        return retrieved_columns

    def _get_updates(self, state: SystemState) -> Dict:
        return {"schema_with_descriptions": state.schema_with_descriptions}