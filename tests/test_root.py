from backend.main import app, read_root


def test_read_root() -> None:
    assert read_root() == {"name": "ValorantAICoach", "status": "running"}


def test_root_route_is_registered() -> None:
    custom_routes = [
        route
        for route in app.routes
        if getattr(route, "include_in_schema", False) and route.path == "/"
    ]

    assert len(custom_routes) == 1
    assert custom_routes[0].methods == {"GET"}
