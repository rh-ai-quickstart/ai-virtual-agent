"""
Feature flag utilities for backend configuration.

Centralizes boolean environment flag parsing to keep checks consistent
and readable across the codebase.
"""

import os


def _is_env_flag_true(env_value: str | None, default: bool = False) -> bool:
    """
    Interpret common truthy values from environment variables.

    Accepts: "1", "true", "yes", "on" (case-insensitive) as True.
    Empty or missing resolves to the provided default.
    """
    if env_value is None or env_value == "":
        return default
    normalized = env_value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def is_attachments_feature_enabled() -> bool:
    """
    Return True when attachments feature should be enabled.

    Convention in this project:
    - DISABLE_ATTACHMENTS=true disables attachments
    - any other value (including unset) enables attachments
    """
    disable_flag = os.getenv("DISABLE_ATTACHMENTS")
    return not _is_env_flag_true(disable_flag, default=False)
