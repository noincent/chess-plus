from workflow.agents.agent import Agent
from workflow.agents.chat_context_analyzer.tool_kit.query_enhancement import QueryEnhancement
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
            task="analyze conversation history and enhance the current query with relevant context",
            config=config
        )
        
        self.tools = {
            "query_enhancement": QueryEnhancement(**config["tools"]["query_enhancement"])
        }

    def workout(self, state: ChatSystemState) -> ChatSystemState:
        """Override workout to ensure query enhancement is called"""
        logging.info(f"[ChatContextAnalyzer] Running with question: {state.task.question}")
        
        # Always call query enhancement first
        self.tools["query_enhancement"](state)
        
        logging.info(f"[ChatContextAnalyzer] Completed enhancement. Enhanced question: {state.task.question}")
        
        # Call parent's workout method to maintain the agent's conversation flow
        return super().workout(state)