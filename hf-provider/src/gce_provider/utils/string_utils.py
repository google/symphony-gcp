import uuid


def generate_unique_id(length=64) -> str:
    """
    Generates a unique, random identifier that is 16 characters long.
    """
    if length < 4:
        raise ValueError("Length must be at least 4")
    return str(uuid.uuid4())[:length]
