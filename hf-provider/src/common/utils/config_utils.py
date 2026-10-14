from typing import Optional, Tuple

def validate_int_in_range(
    value: str, 
    default: int,
    min_value: int,
    max_value: int,
    config_name: str,
) -> Tuple[int, Optional[str]]:
    """Validate an integer setting and return its value and any deferred warning."""
    try:
        parsed_value = int(value)
    except ValueError:
        parsed_value = None

    if parsed_value is not None and min_value <= parsed_value <= max_value:
        return parsed_value, None

    warning = (
        f"Invalid {config_name} value {value!r}; expected an integer from "
        f"{min_value} to {max_value}. Using default value of {default}."
    )

    return default, warning
