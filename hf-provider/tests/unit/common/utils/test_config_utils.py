import pytest

from common.utils.config_utils import validate_int_in_range


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        (1, 1),
        ("1999", 1999),
    ],
)
def test_validate_int_in_range_accepts_in_range_integers(value, expected):
    assert validate_int_in_range(
        value,
        default=10,
        min_value=1,
        max_value=1999,
        config_name="LOG_MAX_FILE_SIZE",
    ) == (expected, None)


@pytest.mark.parametrize(
    "value",
    [None, "invalid", 0, 2000, -1, 1.5, True, [], {}],
)
def test_validate_int_in_range_defers_warning_until_after_logging_setup(value, caplog):
    result, warning = validate_int_in_range(
        value,
        default=10,
        min_value=1,
        max_value=1999,
        config_name="LOG_MAX_FILE_SIZE",
    )

    assert result == 10
    assert warning is not None
    assert "LOG_MAX_FILE_SIZE" in warning
    assert "Using default value of 10" in warning
    assert caplog.text == ""