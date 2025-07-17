from common.utils import list_utils


def test_flatten():
    # flatten should return a simple array as-is
    test = [1, 2, 3, 4, 5]
    result = list_utils.flatten(test)
    assert test == result

    # flatten should flatten an array
    test = [1, 2, [3, 4], 5]
    expected = [1, 2, 3, 4, 5]
    result = list_utils.flatten(test)
    assert result == expected

    # flatten should not recurse
    test = [1, 2, [3, [4, 5]], 6]
    expected = [1, 2, 3, [4, 5], 6]
    result = list_utils.flatten(test)
    assert result == expected

    # flatten should leave a dict as-is
    test = {"key": "value"}
    expected = {"key": "value"}
    result = list_utils.flatten(test)
    assert result == expected
