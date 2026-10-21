# boardly/config.py
"""Layered configuration with collections.ChainMap."""
from collections import ChainMap
from typing import Any


# Three real config layers. In production these come from defaults.py, env, and
# a per-user DB row. Here we use module-level dicts for clarity.
DEFAULTS: dict[str, Any] = {
    "db_url": "sqlite:///dev.db",
    "log_level": "INFO",
    "max_tickets": 1000,
    "feature_flags": {"export_csv": False},
}

ENV: dict[str, Any] = {
    "db_url": "postgres://prod/boardly",
    "log_level": "DEBUG",
}

USER: dict[str, Any] = {
    "max_tickets": 500,
    "feature_flags": {"export_csv": True},
}


def build_config() -> ChainMap:
    """Layer USER > ENV > DEFAULTS. Reads fall through to lower layers."""
    return ChainMap(USER, ENV, DEFAULTS)


def with_override(base: ChainMap, **overrides: Any) -> ChainMap:
    """Push a temporary override layer; the underlying layers are untouched."""
    return base.new_child(overrides)


def lookup(key: str, config: ChainMap) -> Any:
    """Read through the chain. Raises KeyError if no layer has the key."""
    return config[key]


def provenance(key: str, config: ChainMap) -> str:
    """Return the name of the layer that actually provided the value."""
    for i, layer in enumerate(config.maps):
        if key in layer:
            return f"layer {i}: {layer!r}"
    return "not present"


if __name__ == "__main__":
    cfg = build_config()
    print("db_url ->", lookup("db_url", cfg))
    print("log_level ->", lookup("log_level", cfg))
    print("max_tickets ->", lookup("max_tickets", cfg))
    print("default-only 'feature_flags' ->", cfg["feature_flags"])

    print("\n--- provenance ---")
    print("db_url from:", provenance("db_url", cfg))
    print("max_tickets from:", provenance("max_tickets", cfg))

    print("\n--- write goes to the first layer ---")
    cfg["max_tickets"] = 9999
    print("USER after write:", USER)

    print("\n--- new_child: push a layer ---")
    cfg2 = with_override(cfg, max_tickets=7, log_level="ERROR")
    print("override view -> max_tickets:", cfg2["max_tickets"])
    print("override view -> log_level:", cfg2["log_level"])
    print("base unchanged -> max_tickets:", cfg["max_tickets"])

    print("\n--- parents: pop the top layer ---")
    cfg3 = cfg2.parents
    print("after parents, max_tickets:", cfg3["max_tickets"])

    print("\n--- delete goes to the first layer only ---")
    del cfg["max_tickets"]
    print("USER after delete:", USER)
    print("config now sees:", cfg["max_tickets"])   # falls through to DEFAULTS
