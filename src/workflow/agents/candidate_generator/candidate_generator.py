from workflow.agents.agent import Agent
from workflow.system_state import SystemState
import logging
import threading

from workflow.agents.candidate_generator.tool_kit.generate_candidate import GenerateCandidate
from workflow.agents.candidate_generator.tool_kit.revise import Revise

class CandidateGenerator(Agent):
    """
    Agent responsible for generating candidate sql queries.
    """
    
    def __init__(self, config: dict):
        super().__init__(
            name="Candidate Generator",
            task=("generate candidate sql queries",
                  "generate sql queries based on task evidence and schema information"),
            config=config
        )

        self.tools = {
            "generate_candidate": GenerateCandidate(**config["tools"]["generate_candidate"])
        }
        
        # Only add revise tool if it's in the config
        if "revise" in config["tools"]:
            self.tools["revise"] = Revise(**config["tools"]["revise"])

    def __call__(self, state: SystemState) -> SystemState:
        logging.info(f"\n{'='*50}\nCandidate Generator Called\n{'='*50}")
        logging.info(f"Current Thread ID: {threading.current_thread().name}")
        logging.info(f"State ID: {id(state)}")
        logging.info(f"Execution History Length: {len(state.execution_history)}")
        logging.info(f"Last Tool in History: {state.execution_history[-1]['tool_name'] if state.execution_history else 'None'}")
        
        # Log the full execution history tools
        logging.info("Full Execution History:")
        for idx, step in enumerate(state.execution_history):
            logging.info(f"{idx}. {step.get('tool_name', 'unknown')}")
            
        result = super().__call__(state)
        logging.info(f"{'='*50}\nCandidate Generator Finished\n{'='*50}\n")
        return result
