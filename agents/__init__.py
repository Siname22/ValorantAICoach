# Inicializar todos los agentes para que se registren automáticamente
from .economy_coach import EconomyCoachAgent
from .match_analyst import MatchAnalystAgent
from .orchestrator import OrchestratorAgent
from .report_writer import ReportWriterAgent
from .role_coach import RoleCoachAgent
from .shared.registry import AgentRegistry

__all__ = [
    "AgentRegistry",
    "EconomyCoachAgent",
    "MatchAnalystAgent",
    "OrchestratorAgent",
    "ReportWriterAgent",
    "RoleCoachAgent",
]
