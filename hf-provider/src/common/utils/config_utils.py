import logging

def validate_int_in_range(
    value: str, 
    default: int,
    min_value: int,
    max_value: int,
    config_name: str,
) -> int:
    """Return an integer setting within bounds, or log and use its default."""
    try:
        parsed_value = int(value)
    except ValueError:
        parsed_value = None

    if parsed_value is not None and min_value <= parsed_value <= max_value:
        return parsed_value

    logging.getLogger(__name__).warning(
        "Invalid %s value %r; expected an integer from %d to %d. Using default %d.",
        config_name,
        value,
        min_value,
        max_value,
        default,
    )

    return default
