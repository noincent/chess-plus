from typing import List, Dict, Any, Union
import re
from datetime import datetime

class ResponseFormatter:
    """Formats query results and responses for natural language output."""

    @staticmethod
    def format_number(value: Union[int, float]) -> str:
        """Format numbers with appropriate separators and decimal places."""
        if isinstance(value, int):
            return f"{value:,}"
        return f"{value:,.2f}"

    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage values."""
        return f"{value:.1f}%"

    @staticmethod
    def format_date(date_str: str) -> str:
        """Format dates in a natural way."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%B %d, %Y")
        except ValueError:
            return date_str

    @staticmethod
    def format_list(items: List[Any], conjunction: str = "and") -> str:
        """Format a list of items naturally."""
        if not items:
            return ""
        if len(items) == 1:
            return str(items[0])
        if len(items) == 2:
            return f"{items[0]} {conjunction} {items[1]}"
        return f"{', '.join(str(item) for item in items[:-1])}, {conjunction} {items[-1]}"

    @staticmethod
    def format_query_results(results: List[Dict[str, Any]], 
                           limit: int = 5, 
                           include_count: bool = True) -> str:
        """
        Format query results for natural language output.
        
        Args:
            results: List of result dictionaries
            limit: Maximum number of results to include in detail
            include_count: Whether to include total count
            
        Returns:
            Formatted string describing the results
        """
        if not results:
            return "No results found."

        total_count = len(results)
        formatted_results = []

        # Format limited number of results
        for result in results[:limit]:
            formatted_items = []
            for key, value in result.items():
                # Clean up key name
                key = key.replace('_', ' ').title()
                
                # Format value based on type
                if isinstance(value, (int, float)):
                    formatted_value = ResponseFormatter.format_number(value)
                elif isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
                    formatted_value = ResponseFormatter.format_date(value)
                else:
                    formatted_value = str(value)
                    
                formatted_items.append(f"{key}: {formatted_value}")
                
            formatted_results.append(", ".join(formatted_items))

        # Build response
        response = []
        if include_count:
            response.append(f"Found {ResponseFormatter.format_number(total_count)} results.")
            
        if formatted_results:
            if total_count > limit:
                response.append(f"Here are the first {limit} results:")
            response.extend([f"- {result}" for result in formatted_results])
            
            if total_count > limit:
                response.append(f"... and {total_count - limit} more results.")

        return "\n".join(response)

    @staticmethod
    def format_comparison(value1: Union[int, float], 
                         value2: Union[int, float], 
                         label1: str = "first value", 
                         label2: str = "second value") -> str:
        """Format a comparison between two values."""
        diff = value1 - value2
        percent_change = (diff / value2) * 100 if value2 != 0 else 0
        
        comparison = f"The {label1} ({ResponseFormatter.format_number(value1)}) "
        if diff > 0:
            comparison += f"is {ResponseFormatter.format_number(abs(diff))} higher than "
        elif diff < 0:
            comparison += f"is {ResponseFormatter.format_number(abs(diff))} lower than "
        else:
            comparison += "is the same as "
            
        comparison += f"the {label2} ({ResponseFormatter.format_number(value2)})"
        
        if percent_change != 0:
            comparison += f", a {ResponseFormatter.format_percentage(abs(percent_change))} "
            comparison += "increase" if percent_change > 0 else "decrease"
            
        return comparison