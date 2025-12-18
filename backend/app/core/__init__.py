"""
Core functionality package - utilities, feature flags, exceptions, etc.
"""

from .feature_flags import is_attachments_feature_enabled

__all__ = [
    "is_attachments_feature_enabled",
]
