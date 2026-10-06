"""Versioned content catalog for Valorant agents and maps.

Translates internal Riot IDs (such as asset URLs and character UUIDs)
into canonical display names and metadata for analytics and the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class AgentInfo:
    """Canonical metadata for a Valorant agent."""

    name: str
    role: str
    uuid: str


# Mapping of Riot map URLs / asset identifiers to canonical display names.
MAP_CATALOG: Final[dict[str, str]] = {
    "/Game/Maps/Ascent/Ascent": "Ascent",
    "/Game/Maps/Duality/Duality": "Bind",
    "/Game/Maps/Bonsai/Bonsai": "Split",
    "/Game/Maps/Triad/Triad": "Haven",
    "/Game/Maps/Port/Port": "Icebox",
    "/Game/Maps/Foxtrot/Foxtrot": "Breeze",
    "/Game/Maps/Canyon/Canyon": "Fracture",
    "/Game/Maps/Pitt/Pitt": "Pearl",
    "/Game/Maps/Jam/Jam": "Lotus",
    "/Game/Maps/Juliett/Juliett": "Sunset",
    "/Game/Maps/Infinity/Infinity": "Abyss",
    "/Game/Maps/HURM/HURM_Alley/HURM_Alley": "District",
    "/Game/Maps/HURM/HURM_Bowl/HURM_Bowl": "Kasbah",
    "/Game/Maps/HURM/HURM_Helix/HURM_Helix": "Drift",
    "/Game/Maps/HURM/HURM_HighTide/HURM_HighTide": "Glitch",
    "/Game/Maps/HURM/HURM_Yard/HURM_Yard": "Piazza",
    "/Game/Maps/Poveglia/Range": "The Range",
    "/Game/Maps/PovegliaV2/RangeV2": "The Range",
}

# Mapping of Riot agent UUIDs (normalized lowercase) to canonical metadata.
_AGENT_ENTRIES: Final[tuple[AgentInfo, ...]] = (
    AgentInfo(
        name="Astra", role="Controller", uuid="41fb69c1-4189-7b37-f117-bcaf1e96f1bf"
    ),
    AgentInfo(
        name="Breach", role="Initiator", uuid="5f8d3a7f-467b-97f3-062c-13acf203c006"
    ),
    AgentInfo(
        name="Brimstone", role="Controller", uuid="9f0d8ba9-4140-b941-57d3-a7ad57c6b417"
    ),
    AgentInfo(
        name="Chamber", role="Sentinel", uuid="22697a3d-45bf-8dd7-4fec-84a9e28c69d7"
    ),
    AgentInfo(
        name="Clove", role="Controller", uuid="1dbf2edd-4729-0984-3115-daa5eed44993"
    ),
    AgentInfo(
        name="Cypher", role="Sentinel", uuid="117ed9e3-49f3-6512-3ccf-0cada7e3823b"
    ),
    AgentInfo(
        name="Deadlock", role="Sentinel", uuid="cc8b64c8-4b25-4ff9-6e7f-37b4da43d235"
    ),
    AgentInfo(
        name="Fade", role="Initiator", uuid="dade69b4-4f5a-8528-247b-219e5a1facd6"
    ),
    AgentInfo(
        name="Gekko", role="Initiator", uuid="e370fa57-4757-3604-3648-499e1f642d3f"
    ),
    AgentInfo(
        name="Harbor", role="Controller", uuid="95b78ed7-4637-86d9-7e41-71ba8c293152"
    ),
    AgentInfo(name="Iso", role="Duelist", uuid="0e38b510-41a8-5780-5e8f-568b2a4f2d6c"),
    AgentInfo(name="Jett", role="Duelist", uuid="add6443a-41bd-e414-f6ad-e58d267f4e95"),
    AgentInfo(
        name="KAY/O", role="Initiator", uuid="601dbbe7-43ce-be57-2a40-4abd24953621"
    ),
    AgentInfo(
        name="Killjoy", role="Sentinel", uuid="1e58de9c-4950-5125-93e9-a0aee9f98746"
    ),
    AgentInfo(name="Neon", role="Duelist", uuid="bb2a4828-46eb-8cd1-e765-15848195d751"),
    AgentInfo(
        name="Omen", role="Controller", uuid="8e253930-4c05-31dd-1b6c-968525494517"
    ),
    AgentInfo(
        name="Phoenix", role="Duelist", uuid="eb93336a-449b-9c1b-0a54-a891f7921d69"
    ),
    AgentInfo(name="Raze", role="Duelist", uuid="f94c3b30-42be-e959-889c-5aa313dba261"),
    AgentInfo(
        name="Reyna", role="Duelist", uuid="a3bfb853-43b2-7238-a4f1-ad90e9e46bcc"
    ),
    AgentInfo(
        name="Sage", role="Sentinel", uuid="569fdd95-4d10-43ab-ca70-79becc718b46"
    ),
    AgentInfo(
        name="Skye", role="Initiator", uuid="6f2a04ca-43e0-be17-7f36-b3908627744d"
    ),
    AgentInfo(
        name="Sova", role="Initiator", uuid="320b2a48-4d9b-a075-30f1-1f93a9b638fa"
    ),
    AgentInfo(
        name="Tejo", role="Initiator", uuid="b444168c-4e35-8076-db47-ef9bf368f384"
    ),
    AgentInfo(
        name="Viper", role="Controller", uuid="707eab51-4836-f488-046a-cda6bf494859"
    ),
    AgentInfo(
        name="Vyse", role="Sentinel", uuid="efba5359-4016-a1e5-7626-b1ae76895940"
    ),
    AgentInfo(name="Yoru", role="Duelist", uuid="7f94d92c-4234-0a36-9646-3a87eb8b5c89"),
)

AGENT_BY_UUID: Final[dict[str, AgentInfo]] = {
    agent.uuid.lower(): agent for agent in _AGENT_ENTRIES
}

AGENT_BY_NAME: Final[dict[str, AgentInfo]] = {
    agent.name.lower(): agent for agent in _AGENT_ENTRIES
}


def resolve_map_name(map_id_or_name: str | None) -> str:
    """Resolve a Riot map path or name to its canonical display name.

    If already a known map name or unrecognizable path, safely cleans up or
    falls back to the original string.
    """
    if not map_id_or_name:
        return "Unknown"

    cleaned = map_id_or_name.strip()
    # Check exact catalog match
    if cleaned in MAP_CATALOG:
        return MAP_CATALOG[cleaned]

    # Check case-insensitive match on catalog keys or values
    lowered = cleaned.lower()
    for raw_key, display_name in MAP_CATALOG.items():
        if lowered == raw_key.lower() or lowered == display_name.lower():
            return display_name

    # If it looks like a path e.g. /Game/Maps/Something/Something, extract last segment
    if "/" in cleaned:
        segments = [seg for seg in cleaned.split("/") if seg]
        if segments:
            return segments[-1]

    return cleaned


def resolve_agent_name(character_id_or_name: str | None) -> str:
    """Resolve a Riot agent UUID or name to its canonical display name."""
    if not character_id_or_name:
        return "Unknown"

    cleaned = character_id_or_name.strip()
    lowered = cleaned.lower()

    if lowered in AGENT_BY_UUID:
        return AGENT_BY_UUID[lowered].name

    if lowered in AGENT_BY_NAME:
        return AGENT_BY_NAME[lowered].name

    return cleaned


def get_agent_info(character_id_or_name: str | None) -> AgentInfo | None:
    """Retrieve full metadata for an agent by UUID or name."""
    if not character_id_or_name:
        return None

    cleaned = character_id_or_name.strip().lower()
    if cleaned in AGENT_BY_UUID:
        return AGENT_BY_UUID[cleaned]
    if cleaned in AGENT_BY_NAME:
        return AGENT_BY_NAME[cleaned]

    return None


def get_all_agents() -> list[AgentInfo]:
    """Return all known agents sorted alphabetically by name."""
    return sorted(_AGENT_ENTRIES, key=lambda agent: agent.name)


def get_all_maps() -> list[str]:
    """Return unique canonical map names sorted alphabetically."""
    return sorted(set(MAP_CATALOG.values()))
