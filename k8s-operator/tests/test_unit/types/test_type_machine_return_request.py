import datetime

import pytest
from gcp_symphony_operator.api.v1.types.machine_return_request import (
    MachineDetails,
    MachineReturnRequestStatus,
)


class TestMachineReturnRequest:

    def test_validate_timezone_2(self):
        """
        Test that validate_timezone method returns the input datetime when it has
        timezone information.
        This test covers the case where the input datetime is not None and has tzinfo.
        """
        test_datetime = datetime.datetime.now(datetime.timezone.utc)
        result = MachineDetails.validate_timezone(test_datetime)
        assert result == test_datetime

    def test_validate_timezone_2_2(self):
        """
        Test that validate_timezone method returns the input datetime when it includes
        timezone information.

        This test ensures that when a datetime object with timezone information is passed to the
        validate_timezone method, it is returned unchanged without raising any exceptions.
        """
        # Create a datetime object with timezone information
        test_datetime = datetime.datetime.now(datetime.timezone.utc)

        # Call the validate_timezone method
        result = MachineReturnRequestStatus.validate_timezone(test_datetime)

        # Assert that the result is the same as the input
        assert result == test_datetime
        # Assert that the result has timezone information
        assert result.tzinfo is not None

    def test_validate_timezone_raises_error_for_naive_datetime(self):
        """
        Test that validate_timezone raises a ValueError when given a naive datetime.
        This test covers the path where v is not None and v.tzinfo is None.
        """
        naive_datetime = datetime.datetime.now()
        with pytest.raises(ValueError, match="must include timezone information"):
            MachineDetails.validate_timezone(naive_datetime)

    def test_validate_timezone_raises_value_error_when_tzinfo_is_none(self):
        """
        Test that validate_timezone raises a ValueError when the datetime has no
        timezone information.

        This test checks the behavior of the validate_timezone method when given a datetime
        object without timezone information (tzinfo is None). It should raise a ValueError
        with a specific message.
        """
        # Create a datetime object without timezone information
        dt_without_tz = datetime.datetime.now()

        # Assert that calling validate_timezone with a datetime without timezone raises ValueError
        with pytest.raises(
            ValueError, match="lastUpdateTime must include timezone information"
        ):
            MachineReturnRequestStatus.validate_timezone(dt_without_tz)

    def test_validate_timezone_with_naive_datetime(self):
        """
        Test that validate_timezone raises a ValueError when given a naive datetime
        (datetime without timezone information).
        """
        naive_datetime = datetime.datetime.now()
        with pytest.raises(
            ValueError, match="lastUpdateTime must include timezone information"
        ):
            MachineReturnRequestStatus(lastUpdateTime=naive_datetime)

    def test_validate_timezone_without_timezone_info(self):
        """
        Test that validate_timezone raises a ValueError when given a datetime
        without timezone information.
        """
        naive_datetime = datetime.datetime.now()
        with pytest.raises(ValueError) as exc_info:
            MachineDetails.validate_timezone(naive_datetime)
        assert (
            str(exc_info.value)
            == "returnRequestTime and returnCompletionTime must include timezone information"
        )
