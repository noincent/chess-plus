from typing import TypeVar, cast    
from workflow.chat_state import ChatSystemState
from workflow.agents.tool import Tool
import logging
T = TypeVar('T', bound=ChatSystemState)

class ChatTool(Tool):
    """Base class for tools that need chat functionality."""
    
    def __call__(self, state: T) -> T:
        # Safely handle both SystemState and ChatSystemState
        if not hasattr(state, 'chat_context'):
            logging.warning(f"{self.tool_name} expected ChatSystemState but received {type(state).__name__}")
            return super().__call__(state)
            
        chat_state = cast(ChatSystemState, state)
        return super().__call__(chat_state)
    
    def _get_chat_context_summary(self, state: ChatSystemState) -> str:
        """Helper method to safely get chat context summary."""
        if state.chat_context:
            return state.get_context_summary()
        return "No chat context available" 