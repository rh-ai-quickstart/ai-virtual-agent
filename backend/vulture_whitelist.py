"""Vulture whitelist — suppress false positives for abstract/interface params."""

# BaseRunner.stream abstract method parameters are implemented by subclasses
session_id  # noqa
prompt  # noqa

# GoogleHotelsTool._run accepts budget from the Pydantic schema; reserved for
# future SerpApi price-filter support.
budget  # noqa
