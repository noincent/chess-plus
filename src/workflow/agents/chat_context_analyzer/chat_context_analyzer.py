from workflow.agents.agent import Agent
from workflow.agents.chat_context_analyzer.tool_kit.query_enhancement import QueryEnhancement
from workflow.agents.chat_context_analyzer.tool_kit.history_analyzer import HistoryAnalyzer
from workflow.chat_state import ChatSystemState
import logging

class ChatContextAnalyzer(Agent):
    """
    Agent responsible for analyzing chat context and enhancing queries with contextual information.
    Will be the first agent in the pipeline, before Information Retriever.
    """
    
    def __init__(self, config: dict):
        super().__init__(
            name="Chat Context Analyzer",
            task=("analyze conversation history and enhance the current query with database-specific context",
                  "first analyze conversation history, then enhance query with schema information"),
            config=config
        )
        
        self.tools = {
            "history_analyzer": HistoryAnalyzer(**config["tools"]["history_analyzer"]),
            "query_enhancement": QueryEnhancement(**config["tools"]["query_enhancement"])
        }

    def workout(self, state: ChatSystemState) -> ChatSystemState:
        """Override workout to ensure history analysis and query enhancement are called in sequence"""
        logging.info(f"[ChatContextAnalyzer] Running with question: {state.task.question}")
        
        # Call parent's workout method to handle agent conversation and tool selection
        return super().workout(state)