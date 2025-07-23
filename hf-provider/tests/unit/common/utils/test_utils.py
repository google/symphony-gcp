from gke_provider.k8s import utils
import pytest


def test_generate_unique_id_valid():
    """Test generating a unique ID with a valid length."""
    unique_id = utils.generate_unique_id(length=16)
    assert len(unique_id) == 16


def test_generate_unique_id_invalid_length():
    """Test generating a unique ID with an invalid length."""
    with pytest.raises(ValueError):
        utils.generate_unique_id(length=2)
