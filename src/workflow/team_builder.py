import logging
from typing import Dict, Any

from langgraph.graph import END, StateGraph
from workflow.system_state import SystemState
from workflow.chat_state import ChatSystemState

from workflow.agents.information_retriever.information_retriever import InformationRetriever
from workflow.agents.schema_selector.schema_selector import SchemaSelector
from workflow.agents.candidate_generator.candidate_generator import CandidateGenerator
from workflow.agents.unit_tester.unit_tester import UnitTester
from workflow.agents.response_generator.response_generator import ResponseGenerator
from workflow.agents.sql_executor.sql_executor import SQLExecutor
from workflow.agents.chat_context_analyzer.chat_context_analyzer import ChatContextAnalyzer

from workflow.agents.evaluation import ExecutionAccuracy

AGENT_CLASSES = {
    "chat_context_analyzer": ChatContextAnalyzer,
    "information_retriever": InformationRetriever,
    "schema_selector": SchemaSelector,
    "candidate_generator": CandidateGenerator,
    "unit_tester": UnitTester,
    "sql_executor": SQLExecutor,
    "response_generator": ResponseGenerator
}

class CHESSTeamBuilder:
    def __init__(self, config: Dict[str, any]) -> None:
        state_class = ChatSystemState if config.get("enable_chat", False) else SystemState
        self.team = StateGraph(state_class)
        self.config = config
        logging.info(f"Initialized TeamBuilder with {state_class.__name__}")

    def build(self):
        # Get configured agents
        agents = {agent_name: agent_config for agent_name, agent_config in self.config["team_agents"].items() 
                  if agent_name in AGENT_CLASSES}
        
        # Add agents and set up connections
        self._add_agents(agents)
        agent_names = list(agents.keys())
        self.team.set_entry_point("chat_context_analyzer")
        
        # Create sequential connections between agents
        connections = [
            ("chat_context_analyzer", "information_retriever"),
            ("information_retriever", "candidate_generator"),
            ("candidate_generator", "sql_executor"),
            ("sql_executor", "response_generator"),
        ]
        self._add_connections(connections)

    def _add_agents(self, agents: Dict[str, Dict[str, Any]]) -> None:
        """
        Adds agents to the team.

        Args:
            agents (dict): A dictionary of agent names and their configurations.
        """
        for agent_name, agent_config in agents.items():
            if agent_name in AGENT_CLASSES:
                agent = AGENT_CLASSES[agent_name](config=agent_config)
                self.team.add_node(agent_name, agent)
                logging.info(f"Added agent: {agent_name}.")

    def _add_connections(self, connections: list) -> None:
        """
        Adds connections between agents in the team.

        Args:
            connections (list): A list of tuples, each containing (source_agent, destination_agent).
        """
        for src, dst in connections:
            if src not in self.team.nodes or dst not in self.team.nodes:
                logging.warning(f"Skipping invalid connection {src} -> {dst}: One or both agents not found")
                continue
            self.team.add_edge(src, dst)
            logging.info(f"Added connection from {src} to {dst}")

def build_team(config: Dict[str, any]) -> StateGraph:
    """
    Builds and compiles the pipeline based on the provided tools.

    Args:
        pipeline_tools (str): A string of pipeline tool names separated by '+'.

    Returns:
        StateGraph: The compiled team.
    """

    builder = CHESSTeamBuilder(config)
    builder.build()
    team = builder.team.compile()
    logging.info("Team built and compiled successfully")
    return team
