from typing import Any, Optional, Tuple

def validate_int_in_range(
    value: Any,
    default: int,
    min_value: int,
    max_value: int,
    config_name: str,
) -> Tuple[int, Optional[str]]:
    """Validate an integer setting and return its value and any deferred warning."""
    if isinstance(value, bool):
        parsed_value = None
    elif isinstance(value, int):
        parsed_value = value
    elif isinstance(value, str):
        try:
            parsed_value = int(value)
        except ValueError:
            parsed_value = None
    else:
        parsed_value = None

    if parsed_value is not None and min_value <= parsed_value <= max_value:
        return parsed_value, None

    warning = (
        f"Invalid {config_name} value {value!r}; expected an integer from "
        f"{min_value} to {max_value}. Using default value of {default}."
    )

    return default, warning