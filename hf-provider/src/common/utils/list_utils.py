from typing import TypeVar, Union

T = TypeVar("T")


def flatten(arr: list[Union[T, list[T]]]) -> list[T]:
    """
    Flattens a list such that any elements that are themselves lists are
    dereferenced and appended to the result
    """
    if not isinstance(arr, list):
        return arr

    result = []
    for item in arr:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result
