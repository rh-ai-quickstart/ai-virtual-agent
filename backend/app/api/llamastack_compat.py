"""
Version-independent helpers for llama-stack-client API changes.

The Model object changed between 0.3.x and 0.6.1:
  - identifier -> id
  - provider_resource_id -> custom_metadata["provider_resource_id"]
  - model_type -> custom_metadata["model_type"]
  - provider_id -> custom_metadata["provider_id"] or owned_by
  - metadata -> custom_metadata
"""


def get_model_id(model) -> str:
    return getattr(model, "identifier", None) or getattr(model, "id", "unknown")


def get_model_type(model) -> str | None:
    for attr in ("api_model_type", "model_type"):
        val = getattr(model, attr, None)
        if val is not None:
            return val
    meta = getattr(model, "custom_metadata", None) or {}
    return meta.get("model_type")


def get_provider_resource_id(model) -> str:
    val = getattr(model, "provider_resource_id", None)
    if val is not None:
        return str(val)
    meta = getattr(model, "custom_metadata", None) or {}
    return str(meta.get("provider_resource_id", "unknown"))


def get_provider_id(model) -> str:
    val = getattr(model, "provider_id", None)
    if val is not None:
        return str(val)
    meta = getattr(model, "custom_metadata", None) or {}
    return str(meta.get("provider_id", getattr(model, "owned_by", "unknown")))


def get_model_metadata(model) -> dict:
    val = getattr(model, "metadata", None)
    if val is not None:
        return val
    return getattr(model, "custom_metadata", None) or {}
