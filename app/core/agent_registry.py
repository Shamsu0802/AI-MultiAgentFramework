from typing import Dict, Any, List


class AgentRegistry:

    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}

    # --------------------------------------------------
    # Register an Agent
    # --------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        agent_class: Any
    ):
        """
        Register an agent in the framework.

        The registry stores:
        - Agent name
        - Agent description
        - Agent class
        """

        if not name:
            raise ValueError(
                "Agent name cannot be empty."
            )

        if not description:
            raise ValueError(
                "Agent description cannot be empty."
            )

        if name in self._agents:
            raise ValueError(
                f"Agent '{name}' is already registered."
            )

        self._agents[name] = {
            "name": name,
            "description": description,
            "class": agent_class
        }

    # --------------------------------------------------
    # Unregister an Agent
    # --------------------------------------------------

    def unregister(self, name: str):
        """
        Remove an agent from the registry.
        """

        if name not in self._agents:
            raise ValueError(
                f"Agent '{name}' is not registered."
            )

        del self._agents[name]

    # --------------------------------------------------
    # Check if Agent Exists
    # --------------------------------------------------

    def has_agent(self, name: str) -> bool:
        """
        Check whether an agent is registered.
        """

        return name in self._agents

    # --------------------------------------------------
    # Get Agent Class
    # --------------------------------------------------

    def get_agent(self, name: str):
        """
        Return the registered agent class.

        The Orchestrator can use this class to create
        an agent instance when the agent is required.
        """

        if name not in self._agents:
            raise ValueError(
                f"Agent '{name}' is not registered."
            )

        return self._agents[name]["class"]

    # --------------------------------------------------
    # Create Agent Instance
    # --------------------------------------------------

    def create_agent(self, name: str):
        """
        Create and return an instance of a registered agent.
        """

        agent_class = self.get_agent(name)

        return agent_class()

    # --------------------------------------------------
    # Get Agent Information
    # --------------------------------------------------

    def get_agent_info(self, name: str) -> Dict[str, Any]:
        """
        Return information about a specific agent.
        """

        if name not in self._agents:
            raise ValueError(
                f"Agent '{name}' is not registered."
            )

        agent = self._agents[name]

        return {
            "name": agent["name"],
            "description": agent["description"]
        }

    # --------------------------------------------------
    # List All Registered Agents
    # --------------------------------------------------

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Return information about all registered agents.

        This information will later be passed to the
        Planner Agent so that the Planner can dynamically
        decide which agents are required.
        """

        return [
            {
                "name": agent["name"],
                "description": agent["description"]
            }
            for agent in self._agents.values()
        ]

    # --------------------------------------------------
    # Get Planner Context
    # --------------------------------------------------

    def get_available_agents_for_planner(
        self
    ) -> List[Dict[str, str]]:
        """
        Return the agents that are currently available
        to the Planner Agent.

        The Planner will use this information to
        dynamically select the required agents.

        The Planner does NOT receive the agent classes.
        It only receives their names and descriptions.
        """

        return [
            {
                "name": agent["name"],
                "description": agent["description"]
            }
            for agent in self._agents.values()
        ]

    # --------------------------------------------------
    # Count Registered Agents
    # --------------------------------------------------

    def count(self) -> int:
        """
        Return the number of registered agents.
        """

        return len(self._agents)