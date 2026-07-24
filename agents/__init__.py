# Inicializar todos los agentes para que se registren automáticamente
from .match_analyst import MatchAnalystAgent
from .orchestrator import OrchestratorAgent
from .shared.registry import AgentRegistry

__all__ = ["AgentRegistry", "MatchAnalystAgent", "OrchestratorAgent"]
