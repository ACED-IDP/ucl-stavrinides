import pathlib

import pytest


@pytest.fixture
def test_fixture_paths() -> list[str]:
    """Return a path to dummy data."""
    return [
        pathlib.Path(_) for _ in
        [
            'tests/fixtures/IDP_UCL_VS_dataset/dummy_data_30pid.csv',
            'tests/fixtures/IDP_UCL_VS_dataset/dummy_data_200pid.csv',
            'tests/fixtures/IDP_UCL_VS_dataset/dummy_data_500pid.csv',
        ]
    ]
