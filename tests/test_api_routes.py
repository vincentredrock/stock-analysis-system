from app.main import app


def _route_map():
    routes = {}
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        routes.setdefault(path, set()).update(methods - {"HEAD", "OPTIONS"})
    return routes


def test_rest_api_route_inventory():
    routes = _route_map()
    expected = {
        "/api/v1/users": {"POST"},
        "/api/v1/users/me": {"GET"},
        "/api/v1/sessions": {"POST"},
        "/api/v1/sessions/current": {"DELETE"},
        "/api/v1/token-refreshes": {"POST"},
        "/api/v1/stocks": {"GET"},
        "/api/v1/stocks/{symbol}": {"GET"},
        "/api/v1/stocks/{symbol}/quotes/latest": {"GET"},
        "/api/v1/stocks/{symbol}/prices": {"GET"},
        "/api/v1/stocks/{symbol}/sync-status": {"GET"},
        "/api/v1/stock-sync-jobs": {"POST"},
        "/api/v1/stock-sync-jobs/{job_id}": {"GET"},
        "/api/v1/watchlists": {"GET", "POST"},
        "/api/v1/watchlists/{watchlist_id}": {"GET", "PATCH", "DELETE"},
        "/api/v1/watchlists/{watchlist_id}/items/{symbol}": {"PUT", "DELETE"},
        "/api/v1/watchlists/{watchlist_id}/quotes": {"GET"},
    }

    for path, methods in expected.items():
        assert routes[path] == methods


def test_legacy_action_routes_are_not_registered():
    routes = _route_map()
    legacy_paths = {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/refresh",
        "/api/v1/auth/me",
        "/api/v1/stocks/search",
        "/api/v1/stocks/{symbol}/quote",
        "/api/v1/stocks/{symbol}/history",
        "/api/v1/stocks/{symbol}/sync",
        "/api/v1/watchlists/{watchlist_id}/items",
    }

    assert not (legacy_paths & set(routes))
