from app.main import app


def main():
    routes = [getattr(route, "path", None) for route in app.routes]
    routes = [path for path in routes if path]

    assert "/health" in routes, f"Expected /health route, got: {routes}"

    print("Smoke check passed")
    print("Routes:")
    for route in sorted(routes):
        print(f"- {route}")


if __name__ == "__main__":
    main()
