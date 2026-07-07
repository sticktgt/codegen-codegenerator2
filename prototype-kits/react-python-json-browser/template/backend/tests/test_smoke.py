from app.main import app


def test_health_route_exists():
    routes = [getattr(route, "path", None) for route in app.routes]
    assert "/health" in routes
