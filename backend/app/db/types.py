import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_class: type[enum.Enum], name: str, **kwargs) -> SAEnum:
    """Map Python enums to existing PostgreSQL ENUM types by value, not name."""
    return SAEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        **kwargs,
    )
