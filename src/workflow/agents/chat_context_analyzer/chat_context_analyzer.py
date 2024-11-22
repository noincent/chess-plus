from workflow.agents.agent import Agent
from workflow.agents.chat_context_analyzer.tool_kit.query_enhancement import QueryEnhancement

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