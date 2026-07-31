"""Configuration for certificate extraction and app behavior."""

from config.extraction_patterns import (
    get_date_patterns,
    get_id_patterns,
    get_name_patterns,
    get_course_patterns,
)

__all__ = [
    "get_date_patterns",
    "get_id_patterns",
    "get_name_patterns",
    "get_course_patterns",
]
