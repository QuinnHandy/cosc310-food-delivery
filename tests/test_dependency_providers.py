"""Guards for #106: every repository/service provider lives in app/api/dependencies.py."""

import importlib
import inspect
import pkgutil

import app.api.dependencies as dependencies
import app.api.routes as routes_package
from app.main import app

PROVIDER_PREFIXES = ("get_",)
PROVIDER_SUFFIXES = ("_repository", "_service")

# Every provider the app wires up, by name.
EXPECTED_PROVIDERS = {
    "get_restaurant_repository",
    "get_restaurant_service",
    "get_menu_repository",
    "get_menu_service",
    "get_user_repository",
    "get_session_repository",
    "get_auth_service",
    "get_customer_service",
    "get_cart_repository",
    "get_cart_service",
    "get_order_repository",
    "get_order_service",
    "get_checkout_service",
}


def _route_modules():
    for info in pkgutil.iter_modules(routes_package.__path__):
        yield importlib.import_module(f"app.api.routes.{info.name}")


def test_dependencies_module_builds_every_repository_and_service():
    missing = {name for name in EXPECTED_PROVIDERS if not hasattr(dependencies, name)}
    assert not missing


def test_no_route_module_defines_its_own_provider():
    duplicates = []
    for module in _route_modules():
        for name, func in inspect.getmembers(module, inspect.isfunction):
            is_provider = name.startswith(PROVIDER_PREFIXES) and name.endswith(PROVIDER_SUFFIXES)
            if is_provider and func.__module__ == module.__name__:
                duplicates.append(f"{module.__name__}.{name}")
    assert not duplicates


def test_routes_only_depend_on_the_shared_providers():
    """Every provider a route function asks for with Depends(...) comes from dependencies.py."""
    shared = {getattr(dependencies, name) for name in EXPECTED_PROVIDERS}
    used = set()
    for module in _route_modules():
        for _, func in inspect.getmembers(module, inspect.isfunction):
            if func.__module__ != module.__name__:
                continue
            for param in inspect.signature(func).parameters.values():
                call = getattr(param.default, "dependency", None)
                if call is not None:
                    used.add(call)
    providers_used = {
        call for call in used
        if getattr(call, "__name__", "").startswith(PROVIDER_PREFIXES)
        and getattr(call, "__name__", "").endswith(PROVIDER_SUFFIXES)
    }
    assert providers_used  # the routes really do use providers
    assert providers_used <= shared


def test_one_override_replaces_the_menu_repository_everywhere(tmp_path):
    """The menu repository used to need an override in menus.py and in restaurants.py."""
    sentinel = object()
    app.dependency_overrides[dependencies.get_menu_repository] = lambda: sentinel
    try:
        resolved = app.dependency_overrides[dependencies.get_menu_repository]()
    finally:
        app.dependency_overrides.pop(dependencies.get_menu_repository, None)
    assert resolved is sentinel
