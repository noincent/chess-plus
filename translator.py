from typing import Optional, Tuple
import sqlparse
import re
from anthropic import Anthropic

class SQLTranslator:
    def __init__(self):
        self.client = Anthropic()
        
    def create_prompt(self, sqlite_query: str) -> str:
        return f"""Translate this SQLite query to MySQL syntax. Only respond with the translated query, no explanations:

{sqlite_query}

Remember these translation rules:
- AUTOINCREMENT becomes AUTO_INCREMENT
- || string concatenation becomes CONCAT()
- Boolean true/false become 1/0
- LIMIT x OFFSET y becomes LIMIT y, x
- datetime('now') becomes NOW()
- Handle any other syntax differences appropriately"""

    def validate_query(self, query: str) -> Optional[str]:
        """Basic validation to ensure query is well-formed"""
        try:
            parsed = sqlparse.parse(query)
            if not parsed or not parsed[0].tokens:
                return "Invalid SQL syntax"
                
            dangerous_patterns = [
                r"(?i)DROP\s+",
                r"(?i)DELETE\s+(?!FROM)",
                r"(?i)TRUNCATE\s+",
                r"(?i)ALTER\s+",
                r"--",
                r"#[^\n]*",
                r"/\*.*?\*/",
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
        warnings = []
        
        # Validate input query
        validation_error = self.validate_query(sqlite_query)
        if validation_error:
            raise ValueError(f"Invalid input query: {validation_error}")
            
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
        except Exception as e:
            raise RuntimeError(f"LLM translation failed: {str(e)}")
            
        # Validate translated query
        validation_error = self.validate_query(mysql_query)
        if validation_error:
            raise ValueError(f"Invalid translated query: {validation_error}")
            
        # Verify translation
        verification_error = self.verify_translation(sqlite_query, mysql_query)
        if verification_error:
            warnings.append(verification_error)
            
        return mysql_query, warnings