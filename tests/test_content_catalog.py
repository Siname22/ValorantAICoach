from backend.app.content.catalog import (
    AgentInfo,
    get_agent_info,
    get_all_agents,
    get_all_maps,
    resolve_agent_name,
    resolve_map_name,
)


def test_resolve_map_name_known_riot_paths():
    assert resolve_map_name("/Game/Maps/Ascent/Ascent") == "Ascent"
    assert resolve_map_name("/Game/Maps/Duality/Duality") == "Bind"
    assert resolve_map_name("/Game/Maps/Bonsai/Bonsai") == "Split"
    assert resolve_map_name("/Game/Maps/Triad/Triad") == "Haven"
    assert resolve_map_name("/Game/Maps/Port/Port") == "Icebox"
    assert resolve_map_name("/Game/Maps/Foxtrot/Foxtrot") == "Breeze"
    assert resolve_map_name("/Game/Maps/Canyon/Canyon") == "Fracture"
    assert resolve_map_name("/Game/Maps/Pitt/Pitt") == "Pearl"
    assert resolve_map_name("/Game/Maps/Jam/Jam") == "Lotus"
    assert resolve_map_name("/Game/Maps/Juliett/Juliett") == "Sunset"
    assert resolve_map_name("/Game/Maps/Infinity/Infinity") == "Abyss"


def test_resolve_map_name_display_name_and_unknown():
    assert resolve_map_name("Ascent") == "Ascent"
    assert resolve_map_name("ascent") == "Ascent"
    assert resolve_map_name("/Game/Maps/Custom/CustomMap") == "CustomMap"
    assert resolve_map_name("CustomMap") == "CustomMap"
    assert resolve_map_name("") == "Unknown"
    assert resolve_map_name(None) == "Unknown"


def test_resolve_agent_name_known_uuids():
    # Jett
    assert resolve_agent_name("add6443a-41bd-e414-f6ad-e58d267f4e95") == "Jett"
    # Case insensitive
    assert resolve_agent_name("ADD6443A-41BD-E414-F6AD-E58D267F4E95") == "Jett"
    # Cypher
    assert resolve_agent_name("117ed9e3-49f3-6512-3ccf-0cada7e3823b") == "Cypher"
    # Sova
    assert resolve_agent_name("320b2a48-4d9b-a075-30f1-1f93a9b638fa") == "Sova"
    # Omen
    assert resolve_agent_name("8e253930-4c05-31dd-1b6c-968525494517") == "Omen"


def test_resolve_agent_name_display_name_and_fallback():
    assert resolve_agent_name("Jett") == "Jett"
    assert resolve_agent_name("jett") == "Jett"
    assert resolve_agent_name("unknown-guid-123") == "unknown-guid-123"
    assert resolve_agent_name("") == "Unknown"
    assert resolve_agent_name(None) == "Unknown"


def test_get_agent_info():
    info = get_agent_info("add6443a-41bd-e414-f6ad-e58d267f4e95")
    assert isinstance(info, AgentInfo)
    assert info.name == "Jett"
    assert info.role == "Duelist"

    info_by_name = get_agent_info("omen")
    assert info_by_name is not None
    assert info_by_name.name == "Omen"
    assert info_by_name.role == "Controller"

    assert get_agent_info("non-existent") is None
    assert get_agent_info(None) is None


def test_get_all_agents_and_maps():
    agents = get_all_agents()
    assert len(agents) >= 20
    assert any(a.name == "Jett" for a in agents)
    assert any(a.name == "Sova" for a in agents)

    maps = get_all_maps()
    assert "Ascent" in maps
    assert "Bind" in maps
    assert "Haven" in maps
    assert "Icebox" in maps
