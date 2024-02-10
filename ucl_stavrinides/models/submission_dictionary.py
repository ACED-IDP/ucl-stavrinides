import pathlib
import re

import numpy as np
import pandas as pd


def spreadsheet_json_schema(input_path: pathlib.Path) -> dict:
    """Read spreadsheet, create schema."""
    df = read_excel_worksheet(input_path, 'sheet_main')
    df = df.replace({np.nan: ""})
    schema = create_jsonschema(df)
    return schema


def read_excel_worksheet(file_path, sheet_name) -> pd.DataFrame:
    """
    Read a specific worksheet from an Excel file and return its contents as a pandas DataFrame.

    Parameters:
    - file_path (str): The path to the Excel file.
    - sheet_name (str): The name of the worksheet to read.

    Returns:
    - pd.DataFrame: The contents of the specified worksheet as a DataFrame.
    """
    # Use the pandas read_excel function with the sheet_name parameter
    worksheet_data = pd.read_excel(file_path, sheet_name)
    return worksheet_data


def _map_type(dtype: str) -> str:
    """Common types to jsonschema types."""
    if 'int' in dtype:
        return 'integer'
    if 'float' in dtype:
        return 'number'
    if 'datetime' in dtype:
        return 'string'

    assert dtype in ['string', 'number', 'object', 'array', 'boolean', 'null'], f"unknown dtype {dtype}"

    return dtype


def _map_name(name):
    """Enforce legal (python) property name."""
    _ = re.search(r'[_a-zA-Z][_a-zA-Z0-9]*', name)
    if _ is None:
        raise Exception(f"illegal property name {name}")
    return name


def create_jsonschema(input_df,
                      name_column: str = 'Original Column name',
                      type_column: str = 'dtype',
                      description_column: str = 'Description'
                      ) -> dict:
    """
    Derive jsonschema from spreadsheet.

    Parameters:
    - input_df (pd.DataFrame): The input DataFrame to be split.
    - output_directory (Path): The directory to save the jsonschema.
    - name_column (str): The name of the column containing the submitted property name.
    - type_column (str): The name of the column containing the submitted type name.

    """

    schema = {
        "$id": "https://aced-idp.org/ucl-stravrinides/submission.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "submission",
        "type": "object",
        "description": "Raw tabular data submitted by UCL",
        "properties": {}
    }

    # Iterate through each row in the DataFrame, create property in schema
    for index, row in input_df.iterrows():
        name = _map_name(row[name_column])
        description = row[description_column]
        dtype = row[type_column]
        schema['properties'][name] = {
            "type": _map_type(dtype),
            "description": description
        }
    return schema