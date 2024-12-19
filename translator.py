from typing import Optional, Tuple
import sqlparse
import re
from anthropic import Anthropic
import json
import os
from datetime import datetime
import traceback

class SQLTranslator:
    def __init__(self):
        self.client = Anthropic()
        self.log_dir = os.path.join(os.path.dirname(__file__), "logs", "translations")
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _create_log_file(self) -> str:
        """Create a unique log file name based on timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return os.path.join(self.log_dir, f"translation_{timestamp}.json")
        
    def _log_translation_attempt(self, log_data: dict):
        """Save translation attempt details to a log file"""
        log_file = self._create_log_file()
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        return log_file

    def create_prompt(self, sqlite_query: str) -> str:
        return f"""
Translate the following SQLite query into MySQL syntax. Respond with only the translated query and nothing else. Do not include any explanations or concatenated strings in the output. Do NOT include any comments in the output. Do NOT use \n or '+' to concatenate strings in the output.

{sqlite_query}

Key translation rules to follow:
- Replace AUTOINCREMENT with AUTO_INCREMENT.
- Replace || string concatenation with CONCAT().
- Replace Boolean true/false with 1/0.
- Convert LIMIT x OFFSET y to LIMIT y, x.
- Replace datetime('now') with NOW().
- Adapt any other SQLite-specific syntax to its MySQL equivalent as necessary.
"""



    def validate_query(self, query: str) -> Optional[str]:
        """Basic validation to ensure query is well-formed and remove comments"""
        try:
            # Remove SQL comments
            # Remove single line comments (both -- and #)
            query = re.sub(r'--[^\n]*|#[^\n]*', '', query)
            # Remove multi-line comments
            query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
            
            parsed = sqlparse.parse(query)
            if not parsed or not parsed[0].tokens:
                return "Invalid SQL syntax"
                
            dangerous_patterns = [
                r"(?i)DROP\s+",
                r"(?i)DELETE\s+(?!FROM)",
                r"(?i)TRUNCATE\s+",
                r"(?i)ALTER\s+"
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, query):
                    return f"Query contains potentially dangerous pattern: {pattern}"
            
            return None
            
        except Exception as e:
            return f"Query validation failed: {str(e)}"

    def verify_translation(self, sqlite_query: str, mysql_query: str) -> Optional[str]:
        """Verify the translation looks reasonable"""
        core_elements = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY']
        for element in core_elements:
            if (element.upper() in sqlite_query.upper()) != (element.upper() in mysql_query.upper()):
                return f"Translation error: {element} clause mismatch"
        
        sqlite_tables = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sqlite_query, re.IGNORECASE)
        mysql_tables = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', mysql_query, re.IGNORECASE)
        if set(sqlite_tables) != set(mysql_tables):
            return "Translation error: table names don't match"
            
        return None

    def translate(self, sqlite_query: str) -> Tuple[str, list]:
        """
        Translate SQLite query to MySQL using Anthropic's Claude
        Returns: (translated_query, list_of_warnings)
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "input_query": sqlite_query,
            "status": "started",
            "warnings": [],
            "errors": None,
            "translated_query": None
        }
        
        try:
            # Validate input query
            validation_error = self.validate_query(sqlite_query)
            if validation_error:
                log_data["status"] = "validation_error"
                log_data["errors"] = f"Invalid input query: {validation_error}"
                self._log_translation_attempt(log_data)
                raise ValueError(log_data["errors"])
                
            # Generate prompt and get LLM response
            prompt = self.create_prompt(sqlite_query)
            try:
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                mysql_query = message.content[0].text.strip()
                log_data["translated_query"] = mysql_query
                
            except Exception as e:
                log_data["status"] = "llm_error"
                log_data["errors"] = f"LLM translation failed: {str(e)}\n{traceback.format_exc()}"
                self._log_translation_attempt(log_data)
                raise RuntimeError(log_data["errors"])
                
            # Validate translated query
            validation_error = self.validate_query(mysql_query)
            if validation_error:
                log_data["status"] = "validation_error"
                log_data["errors"] = f"Invalid translated query: {validation_error}"
                self._log_translation_attempt(log_data)
                raise ValueError(log_data["errors"])
                
            # Verify translation
            verification_error = self.verify_translation(sqlite_query, mysql_query)
            if verification_error:
                log_data["warnings"].append(verification_error)
            
            log_data["status"] = "success"
            log_file = self._log_translation_attempt(log_data)
            return mysql_query, log_data["warnings"]
            
        except Exception as e:
            if "status" not in log_data or log_data["status"] == "started":
                log_data["status"] = "unexpected_error"
                log_data["errors"] = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
                self._log_translation_attempt(log_data)
            raise