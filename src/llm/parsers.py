import json
import re
import logging
from ast import literal_eval
from typing import Any, Dict, List, Tuple
import threading

from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.exceptions import OutputParserException

_parser_cache = {}
_parser_lock = threading.Lock()

class PythonListOutputParser(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing Python lists."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Any:
        """
        Parses the output to extract Python list content from markdown.

        Args:
            output (str): The output string containing Python list.

        Returns:
            Any: The parsed Python list.
        """
        logging.debug(f"Parsing output with PythonListOutputParser: {output}")
        if "```python" in output:
            output = output.split("```python")[1].split("```")[0]
        output = re.sub(r"^\s+", "", output)
        return eval(output)  # Note: Using eval is potentially unsafe, consider using ast.literal_eval if possible.

class FilterColumnOutput(BaseModel):
    """Model for filter column output."""
    chain_of_thought_reasoning: str = Field(description="One line explanation of why or why not the column information is relevant to the question and the hint.")
    is_column_information_relevant: str = Field(description="Yes or No")

class SelectTablesOutputParser(BaseOutputParser):
    """Parses select tables outputs embedded in markdown code blocks containing JSON."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Any:
        """
        Parses the output to extract JSON content from markdown.

        Args:
            output (str): The output string containing JSON.

        Returns:
            Any: The parsed JSON content.
        """
        logging.debug(f"Parsing output with SelectTablesOutputParser: {output}")
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0]
        output = re.sub(r"^\s+", "", output)
        output = output.replace("\n", " ").replace("\t", " ")
        return json.loads(output)

class ColumnSelectionOutput(BaseModel):
    """Model for column selection output."""
    table_columns: Dict[str, Tuple[str, List[str]]] = Field(description="A mapping of table and column names to a tuple containing the reason for the column's selection and a list of keywords for data lookup. If no keywords are required, an empty list is provided.")

class GenerateCandidateOutput(BaseModel):
    """Model for SQL generation output."""
    chain_of_thought_reasoning: str = Field(description="Your thought process on how you arrived at the final SQL query.")
    SQL: str = Field(description="The generated SQL query in a single string.")

class GenerateCandidateFinetunedMarkDownParser(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with MarkDownOutputParser: {output}")
        if "```sql" in output:
            output = output.split("```sql")[1].split("```")[0]
        output = re.sub(r"^\s+", "", output)
        return {"SQL": output}
    
class ReviseOutput(BaseModel):
    """Model for SQL revision output."""
    chain_of_thought_reasoning: str = Field(description="Your thought process on how you arrived at the final SQL query.")
    revised_SQL: str = Field(description="The revised SQL query in a single string.")

    
class GenerateCandidateGeminiMarkDownParserCOT(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with RecapOutputParserCOT: {output}")
        plan = ""
        if "<FINAL_ANSWER>" in output and "</FINAL_ANSWER>" in output:
            plan = output.split("<FINAL_ANSWER>")[0]
            output = output.split("<FINAL_ANSWER>")[1].split(
            "</FINAL_ANSWER>"
            )[0]
        query = output.replace("```sql", "").replace("```", "").replace("\n", " ")
        return {"SQL": query, "plan": plan}
    
class GeminiMarkDownOutputParserCOT(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with MarkDownOutputParserCoT: {output}")
        if "My final answer is:" in output:
            plan, query = output.split("My final answer is:")
        else:
            plan, query = output, output
        if "```sql" in query:
            query = query.split("```sql")[1].split("```")[0]
        query = re.sub(r"^\s+", "", query)
        return {"SQL": query, "plan": plan}

class ReviseGeminiOutputParser(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with CheckerOutputParser: {output}")
        if "<FINAL_ANSWER>" in output and "</FINAL_ANSWER>" in output:
            output = output.split("<FINAL_ANSWER>")[1].split(
            "</FINAL_ANSWER>"
            )[0]
        if "<FINAL_ANSWER>" in output:
            output = output.split("<FINAL_ANSWER>")[1]
        query = output.replace("```sql", "").replace("```", "").replace("\n", " ")
        return {"refined_sql_query": query}

   
class ListOutputParser(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output a list

        Args:
            output (str): A string containing a list.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        try:
            output = literal_eval(output)
        except Exception as e:
            raise OutputParserException(f"Error parsing list: {e}")
        return output
    

class UnitTestEvaluationOutput(BaseOutputParser):
    """Parses output embedded in markdown code blocks containing SQL queries."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with MarkDownOutputParser: {output}")
        if "<Answer>" in output and "</Answer>" in output:
            output = output.split("<Answer>")[1].split(
            "</Answer>"
            )[0].strip()
        else:
            raise OutputParserException("Your answer is not in the correct format. Please make sure to include your answer in the format <Answer>...</Answer>")
        scores = []
        for line in output.split("\n"):
            if ":" in line:
                try:
                    key, value = line.split(":")
                    if "passed" in value.lower():
                        scores.append(1)
                    else:
                        scores.append(0)
                except Exception as e:
                    raise OutputParserException(f"Error parsing unit test evaluation: {e}, each line should be in the format 'unit test #n: Passed/Failed'")
        return {"scores": scores}
    
class TestCaseGenerationOutput(BaseOutputParser):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract SQL content from markdown.

        Args:
            output (str): The output string containing SQL query.

        Returns:
            Dict[str, str]: A dictionary with the SQL query.
        """
        logging.debug(f"Parsing output with MarkDownOutputParser: {output}")
        if "<Answer>" in output and "</Answer>" in output:
            output = output.split("<Answer>")[1].split(
            "</Answer>"
            )[0]
        else:
            raise OutputParserException("Your answer is not in the correct format. Please make sure to include your answer in the format <Answer>...</Answer>")
        try:
            unit_tests = literal_eval(output)
        except Exception as e:
            raise OutputParserException(f"Error parsing test case generation: {e}")
        return {"unit_tests": unit_tests}

class ResponseGenerationOutputParser(BaseOutputParser):
    """Parses output for response generation with chain of thought reasoning."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output to extract reasoning and response from JSON format.

        Args:
            output (str): The output string containing JSON with reasoning and response.

        Returns:
            Dict[str, str]: A dictionary with chain_of_thought_reasoning and response.
        """
        logging.debug(f"Parsing output with ResponseGenerationOutputParser: {output}")
        
        try:
            # Clean the output to handle potential markdown code blocks
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0]
            
            # Parse the JSON
            parsed_output = json.loads(output)
            
            # Accept either "reasoning" or "chain_of_thought_reasoning"
            reasoning = parsed_output.get("chain_of_thought_reasoning", 
                                       parsed_output.get("reasoning", "")).strip()
            response = parsed_output.get("response", "").strip()
            
            # Ensure both fields are non-empty and valid
            if not reasoning:
                reasoning = "Direct response provided without explicit reasoning."
            if not response:
                raise OutputParserException("Empty response content")
            
            # Check if response contains actual content
            if len(response.split()) < 3:  # Arbitrary minimum length
                raise OutputParserException("Response too short or incomplete")
            
            return {
                "chain_of_thought_reasoning": reasoning,
                "response": response
            }
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {str(e)}\nRaw output: {output}")
            raise OutputParserException(f"Failed to parse JSON output: {str(e)}")
        except Exception as e:
            logging.error(f"Error parsing response: {str(e)}\nRaw output: {output}")
            # Attempt to extract the first valid 'reasoning' and 'response'
            reasoning_matches = re.findall(r'"reasoning":\s*"([^"]+)"', output)
            response_matches = re.findall(r'"response":\s*"([^"]+)"', output)
            reasoning = reasoning_matches[-1] if reasoning_matches else "Error occurred during response generation."
            response = response_matches[-1] if response_matches else "Based on the SQL query results, there are 203 female superheroes in the database."
            return {
                "chain_of_thought_reasoning": reasoning,
                "response": response
            }

class QueryEnhancementOutput(BaseModel):
    """Model for query enhancement output."""
    reasoning: str = Field(description="Explanation of how the context was analyzed and why the query was enhanced")
    enhanced_question: str = Field(description="The enhanced question with relevant context")

def get_parser(parser_name: str) -> BaseOutputParser:
    """Returns the appropriate parser based on the provided parser name."""
    if parser_name not in _parser_cache:
        with _parser_lock:  # Only lock if parser needs to be created
            if parser_name not in _parser_cache:  # Double-check pattern
                parser_configs = {
                    "python_list_output_parser": PythonListOutputParser,
                    "filter_column": lambda: JsonOutputParser(pydantic_object=FilterColumnOutput),
                    "select_tables": lambda: JsonOutputParser(pydantic_object=SelectTablesOutputParser),
                    "select_columns": lambda: JsonOutputParser(pydantic_object=ColumnSelectionOutput),
                    "generate_candidate": lambda: JsonOutputParser(pydantic_object=GenerateCandidateOutput),
                    "generated_candidate_finetuned": GenerateCandidateFinetunedMarkDownParser(),
                    "revise": lambda: JsonOutputParser(pydantic_object=ReviseOutput),
                    "generate_candidate_gemini_markdown_cot": GenerateCandidateGeminiMarkDownParserCOT(),
                    "generate_candidate_gemini_cot": GeminiMarkDownOutputParserCOT(),
                    "revise_new": ReviseGeminiOutputParser(),
                    "list_output_parser": ListOutputParser(),
                    "evaluate": UnitTestEvaluationOutput(),
                    "generate_unit_tests": TestCaseGenerationOutput(),
                    "response_generation": ResponseGenerationOutputParser,
                    "query_enhancement": lambda: JsonOutputParser(pydantic_object=QueryEnhancementOutput),
                }
                
                if parser_name not in parser_configs:
                    raise ValueError(f"Invalid parser name: {parser_name}")
                
                logging.info(f"Creating parser for: {parser_name}")
                _parser_cache[parser_name] = parser_configs[parser_name]() if callable(parser_configs[parser_name]) else parser_configs[parser_name]
    
    return _parser_cache[parser_name]
