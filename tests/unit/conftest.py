from typing import List

import pytest


@pytest.fixture
def python_source_directories() -> List[str]:
    """Directories to scan with flake8."""
    return ["ucl_stavrinides", "tests"]


@pytest.fixture
def data_dictionary_input_path() -> str:
    """Path to the data dictionary."""
    return "docs/IDP_UCL_VS_data_dictionary-IDP_Mapping.xlsx"
