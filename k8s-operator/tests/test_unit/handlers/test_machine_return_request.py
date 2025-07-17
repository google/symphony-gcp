import asyncio
from logging import Logger
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.handlers.machine_return_request import (
    machine_return_request_handler_factory,
)
from gcp_symphony_operator.k8s.custom_objects import call_patch_namespaced_custom_object
from kubernetes.client import ApiException


@pytest.fixture
def handler(mock_config: Config, mock_logger: Logger) -> Any:
    """Fixture for the machine return request handler handler."""
    create_handler, update_handler = machine_return_request_handler_factory(
        mock_config, mock_logger
    )
    return create_handler, update_handler


class TestMachineReturnRequest:

    def test_machine_return_request_create_handler_api_exception(
        self, handler, mock_config
    ):
        """
        Test the create handler when an ApiException occurs during status update.
        This tests the edge case where the API call to update the status fails.
        """
        logger = MagicMock()

        create_handler, _ = handler

        meta = {"name": "test-request", "namespace": "default"}
        spec = {"requestId": "test-id", "machineIds": ["machine1", "machine2"]}
        status = None

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
            side_effect=ApiException(status=500, reason="API Error"),
        ):
            result = asyncio.run(
                create_handler(meta=meta, spec=spec, status=status, logger=logger)
            )

        assert result is not None
        assert result["phase"] == "InProgress"
        assert result["totalMachines"] == 2
        assert result["returnedMachines"] == 0
        assert result["failedMachines"] == 0
        assert len(result["machineEvents"]) == 2

        logger.error.assert_called_once()
        assert "Error updating status" in logger.error.call_args[0][0]

    async def test_machine_return_request_create_handler_invalid_input(
        self, handler, mock_config
    ):
        """
        Test the machine_return_request_create_handler with invalid input.
        This test verifies that the handler returns a 'Failed' status when
        the input lacks required fields (requestId or machineIds).
        """
        logger = Mock()
        create_handler, _ = handler

        meta = {"name": "test-request", "namespace": "default"}
        spec = {}  # Empty spec to trigger the validation failure
        status = None

        result = await create_handler(meta, spec, status, logger)

        assert result["phase"] == "Failed"
        assert result["totalMachines"] == 0
        assert result["returnedMachines"] == 0
        assert result["failedMachines"] == 0
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Failed"
        assert result["conditions"][0]["status"] == "True"
        assert "RequestValidationFailed" in result["conditions"][0]["reason"]
        assert "The request is invalid" in result["conditions"][0]["message"]
        assert result["machineEvents"] == {}

    def test_machine_return_request_create_handler_missing_fields(
        self, handler, mock_config
    ):
        """
        Test the create handler when required fields are missing from the spec.
        This tests the edge case where the requestId or machineIds are not provided.
        """
        logger = MagicMock()

        create_handler, _ = handler

        meta = {"name": "test-request", "namespace": "default"}
        spec = {}  # Empty spec to simulate missing fields
        status = None

        result = create_handler(meta, spec, status, logger)

        assert result is not None
        assert result["phase"] == "Failed"
        assert result["totalMachines"] == 0
        assert result["returnedMachines"] == 0
        assert result["failedMachines"] == 0
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Failed"
        assert "RequestValidationFailed" in result["conditions"][0]["reason"]
        assert "Missing required fields" in result["conditions"][0]["message"]

    def test_machine_return_request_create_handler_missing_required_fields(
        self, handler, mock_config
    ):
        """
        Test the create handler when required fields are missing in the spec.
        This tests the edge case where the spec is invalid due to missing requestId or machineIds.
        """
        logger = MagicMock()

        create_handler, _ = handler

        # Test case with missing requestId
        meta = {"name": "test-request", "namespace": "default"}
        spec = {"machineIds": ["machine1", "machine2"]}
        status = None

        result = asyncio.run(
            create_handler(meta=meta, spec=spec, status=status, logger=logger)
        )

        assert result is not None
        assert result["phase"] == "Failed"
        assert "Missing required fields" in result["conditions"][0]["message"]

        # Test case with missing machineIds
        spec = {"requestId": "test-id"}

        result = asyncio.run(
            create_handler(meta=meta, spec=spec, status=status, logger=logger)
        )

        assert result is not None
        assert result["phase"] == "Failed"
        assert "Missing required fields" in result["conditions"][0]["message"]

        # Test case with empty machineIds list
        spec = {"requestId": "test-id", "machineIds": []}

        result = asyncio.run(
            create_handler(meta=meta, spec=spec, status=status, logger=logger)
        )

        assert result is not None
        assert result["phase"] == "Failed"
        assert "Missing required fields" in result["conditions"][0]["message"]

    @pytest.mark.asyncio
    async def test_machine_return_request_handler_factory_1(self, handler, mock_config):
        """
        Tests the machine_return_request_handler_factory when the request is invalid.

        This test verifies that when the MachineReturnRequest is created with invalid
        or missing required fields (request_id or machine_ids), the handler returns
        a Failed status with appropriate error details.
        """
        mock_logger = MagicMock()

        # Create the handler
        create_handler, _ = handler(mock_config, mock_logger)

        # Prepare test data with invalid/missing fields
        meta = {"name": "test-request", "namespace": "default"}
        spec = {}  # Empty spec to simulate missing required fields
        status = None

        # Call the create handler
        result = await create_handler(meta, spec, status, mock_logger)

        # Assert the expected failure response
        assert result["phase"] == "Failed"
        assert result["totalMachines"] == 0
        assert result["returnedMachines"] == 0
        assert result["failedMachines"] == 0
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Failed"
        assert result["conditions"][0]["status"] == "True"
        assert "RequestValidationFailed" in result["conditions"][0]["reason"]
        assert "The request is invalid" in result["conditions"][0]["message"]
        assert isinstance(result["machineEvents"], dict)
        assert len(result["machineEvents"]) == 0

        # Verify that the logger.error was called
        mock_logger.error.assert_called_once()

    def test_machine_return_request_handler_factory_2(self, handler, mock_config):
        """
        Test the machine_return_request_handler_factory when valid request_id and
        machine_ids are provided.

        This test verifies that the create handler returns the expected initial status
        when given valid input parameters. It checks that the status is set to "InProgress"
        and that the correct number of machines are reflected in the status.
        """
        mock_logger = Mock()

        # Set up test data
        meta = {"name": "test-request", "namespace": "default"}
        spec = {"requestId": "test-id", "machineIds": ["machine1", "machine2"]}
        status = None

        # Get the create handler from the factory
        create_handler, _ = handler(mock_config, mock_logger)

        # Mock the call_patch_namespaced_custom_object_status function
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status"  # noqa: E501
        ) as mock_patch:
            # Call the create handler
            result = create_handler(meta, spec, status, mock_logger)

        # Assert that the result is None (because the actual update is done asynchronously)
        assert result is None

        # Verify that the patch function was called with the correct initial status
        mock_patch.assert_called_once()
        patch_call_args = mock_patch.call_args[1]
        assert patch_call_args["namespace"] == "default"
        assert patch_call_args["name"] == "test-request"
        assert patch_call_args["plural"] == mock_config.crd_return_request_plural

        initial_status = patch_call_args["patch_body"]["status"]
        assert initial_status["phase"] == "InProgress"
        assert initial_status["totalMachines"] == 2
        assert initial_status["returnedMachines"] == 0
        assert initial_status["failedMachines"] == 0
        assert len(initial_status["machineEvents"]) == 2
        assert "machine1" in initial_status["machineEvents"]
        assert "machine2" in initial_status["machineEvents"]

        # Verify that the logger was called with the correct info message
        mock_logger.info.assert_called_once_with(
            "MachineReturnRequest test-request created with requestId test-id for 2 machines"
        )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_1(self, handler, mock_config):
        """
        Test that the machine_return_request_update_handler returns None when status is None.
        This covers the case where the status is not present in the MachineReturnRequest.
        """
        logger = Mock()

        # Create the handler using the factory
        _, update_handler = handler

        # Prepare test data
        meta = {}
        spec = {}
        status = None
        kwargs = {}

        # Call the handler
        result = await update_handler(meta, spec, status, logger, **kwargs)

        # Assert that the result is None
        assert result is None

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_10(self, handler, mock_config):
        """
        Test machine_return_request_update_handler when:
        - status exists
        - current phase is not "Completed" or "Failed"
        - machine_id is not in existing_pod_names
        - machine_id is in machine_events and its status is "Completed"
        - completed_count + failed_count equals total_machines
        - some pods are completed and some failed
        - phase is "Completed" or "Failed"
        - triggerUpdate label exists and needs to be removed
        """
        logger = MagicMock()

        # Create the handler
        _, update_handler = handler

        # Prepare test data
        meta = {
            "name": "test-request",
            "namespace": "test-namespace",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Completed"},
                "machine2": {"status": "Failed"},
            },
        }

        # Mock necessary functions
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pod.return_value = MagicMock(items=[])

            # Call the handler
            result = await update_handler(meta, spec, status, logger)

            # Assertions
            assert result is None
            mock_patch_custom_object.assert_called_once()
            mock_patch_status.assert_called_once()

            # Check if the status was updated correctly
            status_patch = mock_patch_status.call_args[1]["patch_body"]["status"]
            assert status_patch["phase"] in ["Completed", "Failed"]
            assert status_patch["totalMachines"] == 2
            assert status_patch["returnedMachines"] == 1
            assert status_patch["failedMachines"] == 1

            # Check if the triggerUpdate label was removed
            labels_patch = mock_patch_custom_object.call_args[1]["patch_body"][
                "metadata"
            ]["labels"]
            assert "triggerUpdate" not in labels_patch
            assert labels_patch.get("symphony.waitingCleanup") == "True"

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_11(self, handler, mock_config):
        """
        Test that the machine_return_request_update_handler correctly handles a scenario where:
        - The status exists
        - The current phase is not "Completed" or "Failed"
        - The machine_id is not in existing_pod_names
        - The machine_id is in machine_events with a "Completed" status
        - The pod is already deleted (404 error)
        - Not all machines are processed yet
        - The phase becomes "Completed" or "Failed"
        - The triggerUpdate label exists and needs to be removed
        """
        logger = MagicMock()

        # Create the handler
        _, update_handler = handler

        # Prepare test data
        meta = {
            "name": "test-request",
            "namespace": "default",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Completed"},
                "machine2": {"status": "Pending"},
            },
        }

        # Mock Kubernetes API calls
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            # Set up mock responses
            mock_list_pods.return_value.items = []
            mock_delete_pod.side_effect = ApiException(status=404)

            # Call the handler
            await update_handler(meta, spec, status, logger)

        # Assertions
        assert mock_list_pods.called
        assert not mock_patch_pod.called
        assert mock_delete_pod.called
        assert mock_patch_custom_object.called
        assert mock_patch_status.called

        # Check if the triggerUpdate label was removed
        patch_body = mock_patch_custom_object.call_args[1]["patch_body"]
        assert "triggerUpdate" not in patch_body["metadata"]["labels"]

        # Verify the final status update
        status_patch = mock_patch_status.call_args[1]["patch_body"]["status"]
        assert status_patch["phase"] in ["Completed", "PartiallyCompleted"]
        assert status_patch["returnedMachines"] == 1
        assert status_patch["failedMachines"] == 0

        # Verify logger calls
        logger.info.assert_called_with(
            f"MachineReturnRequest {meta['name']} completed with status: {status_patch['phase']}"
        )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_12(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing pod names
        - Machine ID is in machine_events with status "Completed"
        - Pod is already deleted (ApiException with status 404)
        - All machines are processed (completed + failed = total)
        - All machines are successfully returned (failed_count = 0)
        - Phase is set to "Completed"
        - triggerUpdate label is not present
        """
        logger = MagicMock()
        _, update_handler = handler

        meta = {"namespace": "test-namespace", "name": "test-request", "labels": {}}
        spec = {"machineIds": ["machine1"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {"machine1": {"status": "Completed"}},
        }

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pods.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=404)

            await update_handler(meta, spec, status, logger)

            mock_patch_object.assert_called_once()
            mock_patch_status.assert_called_once()

            patch_body = mock_patch_status.call_args[1]["patch_body"]
            assert patch_body["status"]["phase"] == "Completed"
            assert patch_body["status"]["totalMachines"] == 1
            assert patch_body["status"]["returnedMachines"] == 1
            assert patch_body["status"]["failedMachines"] == 0
            assert patch_body["status"]["conditions"][0]["type"] == "AllPodsDeleted"

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_13(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing pod names
        - Machine ID is in machine events with status "Completed"
        - Pod deletion is successful (404 error, indicating pod already deleted)
        - All machines are processed (completed + failed == total)
        - No machines failed (failed_count == 0)
        - Final phase is not "Completed" or "Failed"
        """
        logger = MagicMock()
        _, update_handler = handler

        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {"machine1": {"status": "Completed"}},
        }

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pod.return_value.items = []
            mock_delete_pod.side_effect = AsyncMock(
                side_effect=Exception("Pod not found")
            )

            result = await update_handler(meta, spec, status, logger)

            assert result is None
            mock_list_pod.assert_called_once()
            mock_patch_pod.assert_not_called()
            mock_delete_pod.assert_not_called()
            mock_patch_custom_object.assert_called_once()
            mock_patch_status.assert_called_once()

            patch_status_call = mock_patch_status.call_args[1]
            assert patch_status_call["namespace"] == "test-namespace"
            assert patch_status_call["name"] == "test-return-request"
            assert patch_status_call["plural"] == mock_config.crd_return_request_plural

            patch_body = patch_status_call["patch_body"]
            assert patch_body["status"]["phase"] == "Completed"
            assert patch_body["status"]["totalMachines"] == 1
            assert patch_body["status"]["returnedMachines"] == 1
            assert patch_body["status"]["failedMachines"] == 0
            assert patch_body["status"]["conditions"][0]["type"] == "AllPodsDeleted"
            assert (
                patch_body["status"]["machineEvents"]["machine1"]["status"]
                == "Completed"
            )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_2(self, handler, mock_config):
        """
        Test that the machine_return_request_update_handler returns None when the status exists
        and the current phase is either 'Completed' or 'Failed'.
        """
        # Mock the necessary dependencies
        meta = {}
        spec = {}
        logger = MagicMock()

        # Test for 'Completed' phase
        status_completed = {"phase": "Completed"}
        _, update_handler = handler
        result_completed = await update_handler(meta, spec, status_completed, logger)
        assert result_completed is None

        # Test for 'Failed' phase
        status_failed = {"phase": "Failed"}
        result_failed = await update_handler(meta, spec, status_failed, logger)
        assert result_failed is None

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_3(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing_pod_names
        - Machine ID is in machine_events with status "Completed"
        - Pod deletion is successful (404 error indicating already deleted)
        - All machines are processed (completed + failed == total)
        - All machines are successfully returned (failed_count == 0)
        - Final phase is "Completed"
        - triggerUpdate label exists and should be removed
        """
        logger = MagicMock()

        # Create the handler using the factory
        _, update_handler = handler

        # Mock input data
        meta = {
            "name": "test-request",
            "namespace": "default",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Completed"},
                "machine2": {"status": "Pending"},
            },
        }

        # Mock Kubernetes API calls
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            # Set up mock behaviors
            mock_list_pod.return_value.items = []
            mock_delete_pod.side_effect = ApiException(status=404)

            # Call the handler
            await update_handler(meta, spec, status, logger)

            # Assertions
            assert mock_list_pod.called
            assert mock_patch_pod.called
            assert mock_delete_pod.called
            assert mock_patch_custom_object.called
            assert mock_patch_status.called

            # Check if the status update was called with the expected values
            status_call = mock_patch_status.call_args[1]["patch_body"]["status"]
            assert status_call["phase"] == "Completed"
            assert status_call["totalMachines"] == 2
            assert status_call["returnedMachines"] == 2
            assert status_call["failedMachines"] == 0

            # Check if the triggerUpdate label was removed
            labels_call = mock_patch_custom_object.call_args[1]["patch_body"][
                "metadata"
            ]["labels"]
            assert "triggerUpdate" not in labels_call
            assert labels_call.get("symphony.waitingCleanup") == "True"

            # Verify logger calls
            logger.info.assert_called_with(
                f"MachineReturnRequest {meta['name']} completed with status: Completed"
            )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_4(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - status exists
        - current phase is not "Completed" or "Failed"
        - machine_id is in existing_pod_names
        - machine_id is in machine_events with "Completed" status
        - pod deletion is successful (404 error, indicating pod already deleted)
        - all machines are processed (completed_count + failed_count == total_machines)
        - all machines are successfully returned (failed_count == 0)
        - final phase is "Completed"
        - triggerUpdate label exists and needs to be removed
        """
        logger = MagicMock()

        # Create the handler
        _, update_handler = handler

        # Mock input data
        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {"machine1": {"status": "Completed"}},
        }

        # Mock Kubernetes API calls
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object_status:

            # Set up mock returns
            mock_list_pods.return_value = MagicMock(
                items=[MagicMock(metadata=MagicMock(name="machine1"))]
            )
            mock_delete_pod.side_effect = ApiException(status=404)

            # Call the handler
            await update_handler(meta, spec, status, logger)

            # Verify API calls
            mock_list_pods.assert_called_once()
            mock_patch_pod.assert_called_once()
            mock_delete_pod.assert_called_once()
            mock_patch_custom_object.assert_called_once()
            mock_patch_custom_object_status.assert_called_once()

            # Verify the final status update
            status_update = mock_patch_custom_object_status.call_args[1]["patch_body"][
                "status"
            ]
            assert status_update["phase"] == "Completed"
            assert status_update["totalMachines"] == 1
            assert status_update["returnedMachines"] == 1
            assert status_update["failedMachines"] == 0

            # Verify label update
            label_update = mock_patch_custom_object.call_args[1]["patch_body"][
                "metadata"
            ]["labels"]
            assert "triggerUpdate" not in label_update
            assert label_update["symphony.waitingCleanup"] == "True"

    async def test_machine_return_request_update_handler_5(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler function when:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing pod names
        - Machine ID is in machine events with status "Failed"
        - A new machine ID is processed
        - API exception with status 404 occurs during pod deletion
        - All machines are processed (completed + failed == total)
        - No machines failed (failed_count == 0)
        - Final phase is "Completed"
        - TriggerUpdate label exists and should be removed
        """
        logger = MagicMock()
        _, update_handler = handler

        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Failed"},
                "machine2": {"status": "Pending"},
            },
        }

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pods.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=404)

            await update_handler(meta, spec, status, logger)

            assert mock_patch_pod.called
            assert mock_delete_pod.called
            assert mock_patch_custom_object.called
            assert mock_patch_status.called

            # Verify the final status update
            _, kwargs = mock_patch_status.call_args
            updated_status = kwargs["patch_body"]["status"]
            assert updated_status["phase"] == "Completed"
            assert updated_status["totalMachines"] == 2
            assert updated_status["returnedMachines"] == 2
            assert updated_status["failedMachines"] == 0

            # Verify label update
            _, kwargs = mock_patch_custom_object.call_args
            updated_labels = kwargs["patch_body"]["metadata"]["labels"]
            assert "triggerUpdate" not in updated_labels
            assert updated_labels["symphony.waitingCleanup"] == "True"

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_6(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - status exists
        - current phase is not Completed or Failed
        - machine_id is not in existing_pod_names
        - machine_id is not in machine_events
        - pod deletion returns 404 (already deleted)
        - all machines are processed (completed + failed == total)
        - all machines are successfully deleted (failed_count == 0)
        - final phase is Completed
        - triggerUpdate label exists and should be removed
        """
        logger = MagicMock()
        _, update_handler = handler

        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1"]}
        status = {"phase": "InProgress", "machineEvents": {}}

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pod.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=404)

            await update_handler(meta, spec, status, logger)

            mock_patch_pod.assert_called_once()
            mock_delete_pod.assert_called_once_with(
                name="machine1", namespace="test-namespace"
            )
            mock_patch_custom_object.assert_called_once()
            mock_patch_status.assert_called_once()

            patch_body = mock_patch_status.call_args[1]["patch_body"]
            assert patch_body["status"]["phase"] == "Completed"
            assert patch_body["status"]["totalMachines"] == 1
            assert patch_body["status"]["returnedMachines"] == 1
            assert patch_body["status"]["failedMachines"] == 0
            assert (
                "triggerUpdate"
                not in mock_patch_custom_object.call_args[1]["patch_body"]["metadata"][
                    "labels"
                ]
            )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_7(self, handler, mock_config):
        """
        Tests the machine_return_request_update_handler function for the case where:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing pod names
        - Machine ID is in machine events with status "Completed"
        - Machine ID is already in machine events
        - Pod deletion returns a 404 error (already deleted)
        - All machines are processed (completed + failed = total)
        - No machines failed (all completed successfully)
        - Final phase is "Completed"
        - The triggerUpdate label exists and needs to be removed
        """
        # Mock necessary dependencies and setup test data
        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Completed"},
                "machine2": {"status": "InProgress"},
            },
        }
        logger = MagicMock()

        # Mock Kubernetes API calls
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            # Setup mock returns
            mock_list_pods.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=404)
            _, update_handler = handler
            # Import and call the handler
            result = await update_handler(meta, spec, status, logger)

            # Assertions
            assert result is None  # The function doesn't return anything
            mock_patch_custom_object.assert_called_once()
            mock_patch_status.assert_called_once()

            # Check if the status was updated correctly
            status_patch = mock_patch_status.call_args[1]["patch_body"]["status"]
            assert status_patch["phase"] == "Completed"
            assert status_patch["totalMachines"] == 2
            assert status_patch["returnedMachines"] == 2
            assert status_patch["failedMachines"] == 0

            # Verify that triggerUpdate label was removed
            labels_patch = mock_patch_custom_object.call_args[1]["patch_body"][
                "metadata"
            ]["labels"]
            assert "triggerUpdate" not in labels_patch
            assert labels_patch.get("symphony.waitingCleanup") == "True"

            # Verify logger calls
            logger.info.assert_called_with(
                "MachineReturnRequest test-return-request completed with status: Completed"
            )

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_8(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - Status exists
        - Current phase is not "Completed" or "Failed"
        - Machine ID is not in existing pod names
        - Machine ID is in machine events with status "Completed"
        - API exception occurs when deleting pod (not 404)
        - All machines are processed (completed + failed = total)
        - No failures occurred
        - Phase is "Completed"
        - triggerUpdate label exists and should be removed
        """
        logger = MagicMock(spec=Logger)

        # Create handler
        _, update_handler = handler

        # Mock input data
        meta = {
            "namespace": "test-namespace",
            "name": "test-return-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {"machine1": {"status": "Completed"}},
        }

        # Mock Kubernetes API calls
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pods, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_patch_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_custom_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            # Configure mock behaviors
            mock_list_pods.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=500, reason="Test error")

            # Call the handler
            await update_handler(meta, spec, status, logger)

            # Verify the expected behaviors
            assert mock_list_pods.called
            assert not mock_patch_pod.called
            assert mock_delete_pod.called
            assert mock_patch_custom_object.called
            assert mock_patch_status.called

            # Verify the patch_custom_object call
            patch_body = mock_patch_custom_object.call_args[1]["patch_body"]
            assert "metadata" in patch_body
            assert "labels" in patch_body["metadata"]
            assert "symphony.waitingCleanup" in patch_body["metadata"]["labels"]
            assert "triggerUpdate" not in patch_body["metadata"]["labels"]

            # Verify the patch_status call
            status_body = mock_patch_status.call_args[1]["patch_body"]
            assert status_body["status"]["phase"] == "Completed"
            assert status_body["status"]["totalMachines"] == 1
            assert status_body["status"]["returnedMachines"] == 1
            assert status_body["status"]["failedMachines"] == 0
            assert "AllPodsDeleted" in status_body["status"]["conditions"][0]["type"]

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_9(self, handler, mock_config):
        """
        Test the machine_return_request_update_handler when:
        - status exists
        - current_phase is not "Completed" or "Failed"
        - machine_id is not in existing_pod_names
        - machine_id is in machine_events with status "Completed"
        - e.status is 404 when deleting the pod
        - all machines are processed (completed_count + failed_count == total_machines)
        - all machines failed (completed_count == 0)
        - phase is "Completed" or "Failed"
        - triggerUpdate label exists
        """
        logger = MagicMock()

        _, update_handler = handler

        meta = {
            "namespace": "test-namespace",
            "name": "test-request",
            "labels": {"triggerUpdate": "true"},
        }
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {
            "phase": "InProgress",
            "machineEvents": {
                "machine1": {"status": "Completed"},
                "machine2": {"status": "Completed"},
            },
        }

        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_list_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_list_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_delete_namespaced_pod",
            new_callable=AsyncMock,
        ) as mock_delete_pod, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_object, patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object_status",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch_status:

            mock_list_pod.return_value = MagicMock(items=[])
            mock_delete_pod.side_effect = ApiException(status=404)

            result = await update_handler(meta, spec, status, logger)

        assert result is None
        mock_patch_object.assert_called_once()
        mock_patch_status.assert_called_once()

        # Verify the final status update
        status_patch = mock_patch_status.call_args[1]["patch_body"]["status"]
        assert status_patch["phase"] == "Failed"
        assert status_patch["totalMachines"] == 2
        assert status_patch["returnedMachines"] == 2
        assert status_patch["failedMachines"] == 0
        assert status_patch["conditions"][0]["type"] == "AllPodsDeleted"

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_already_completed(
        self, handler, mock_config
    ):
        """
        Test that the handler returns None when the request is already completed.
        """
        meta = {"name": "test-request", "namespace": "default"}
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {"phase": "Completed"}
        logger = MagicMock()
        mrr_update_handler, _ = handler
        result = await mrr_update_handler(meta, spec, status, logger)

        assert result is None

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_already_failed(
        self, handler, mock_config
    ):
        """
        Test that the handler returns None when the request has already failed.
        """
        meta = {"name": "test-request", "namespace": "default"}
        spec = {"machineIds": ["machine1", "machine2"]}
        status = {"phase": "Failed"}
        logger = MagicMock()
        mrr_update_handler, _ = handler
        result = await mrr_update_handler(meta, spec, status, logger)

        assert result is None

    @pytest.mark.asyncio
    async def test_machine_return_request_update_handler_no_status(
        self, handler, mock_config
    ):
        """
        Test that the handler returns None when there is no status.
        """
        meta = {"name": "test-request", "namespace": "default"}
        spec = {"machineIds": ["machine1", "machine2"]}
        status = None
        logger = MagicMock()
        mrr_update_handler, _ = handler
        result = await mrr_update_handler(meta, spec, status, logger)

        assert result is None

    @pytest.mark.asyncio
    async def test_trigger_update_1(self, handler, mock_config):
        """
        Test that trigger_update function successfully patches the custom object
        and logs debug message on successful update.
        """
        logger = MagicMock()
        with patch(
            "gcp_symphony_operator.handlers.machine_return_request.call_patch_namespaced_custom_object",  # noqa: E501
            new_callable=AsyncMock,
        ) as mock_patch, patch(
            "gcp_symphony_operator.handlers.machine_return_request.logger.debug"
        ) as mock_debug:

            # Mock the necessary objects
            mock_meta = {"namespace": "test-namespace", "name": "test-name"}
            mock_config = AsyncMock()
            mock_config.crd_return_request_plural = "test-plural"

            # Create the trigger_update function (simulating its creation in the factory function)
            async def trigger_update():
                await asyncio.sleep(0.1)
                try:
                    await call_patch_namespaced_custom_object(
                        namespace=mock_meta["namespace"],
                        name=mock_meta["name"],
                        plural=mock_config.crd_return_request_plural,
                        patch_body={"metadata": {"labels": {"triggerUpdate": "true"}}},
                    )
                    logger.debug(f"Triggered update to for {mock_meta['name']}")
                except ApiException as e:
                    logger.error(f"Error triggering update: {e}")

            # Execute the function
            await trigger_update()

            # Verify the patch was called with correct arguments
            mock_patch.assert_called_once_with(
                namespace="test-namespace",
                name="test-name",
                plural="test-plural",
                patch_body={"metadata": {"labels": {"triggerUpdate": "true"}}},
            )

            # Verify the debug log was called
            mock_debug.assert_called_once_with("Triggered update to for test-name")

    @pytest.mark.asyncio
    async def test_trigger_update_api_exception(self, handler, mock_config):
        """
        Test the trigger_update function when an ApiException is raised during the patch operation.
        This tests the error handling for API call failures.
        """
        # Mock the necessary dependencies
        with patch(
            "gcp_symphony_operator.k8s.custom_objects.call_patch_namespaced_custom_object",
            new_callable=AsyncMock,
        ) as mock_patch:
            # Set up the mock to raise an ApiException
            mock_patch.side_effect = ApiException(
                status=500, reason="Internal Server Error"
            )

            # Create a mock logger
            mock_logger = AsyncMock()

            # Define the trigger_update function within the test
            async def trigger_update():
                await asyncio.sleep(
                    0.1
                )  # small delay to ensure the resource is created
                try:
                    # Make a small update to trigger the update handler
                    await call_patch_namespaced_custom_object(
                        namespace="test-namespace",
                        name="test-name",
                        plural="test-plural",
                        patch_body={"metadata": {"labels": {"triggerUpdate": "true"}}},
                    )
                    mock_logger.debug("Triggered update to for test-name")
                except ApiException as e:
                    mock_logger.error(f"Error triggering update: {e}")

            # Execute the function
            await trigger_update()

            # Assert that the error was logged
            mock_logger.error.assert_called_once_with(
                "Error triggering update: (500)\nReason: Internal Server Error\n"
            )
