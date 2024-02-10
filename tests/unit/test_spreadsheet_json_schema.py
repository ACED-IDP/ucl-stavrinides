from ucl_stavrinides.models.submission_dictionary import spreadsheet_json_schema


def test_spreadsheet_json_schema(data_dictionary_input_path):
    """Ensure we can create jsonschema from spreadsheet."""
    schema = spreadsheet_json_schema(data_dictionary_input_path)
    assert schema, f"should have loaded {data_dictionary_input_path}"
    assert 'title' in schema, f"should have title in {schema}"
    assert 'properties' in schema, f"should have properties in {schema}"
    assert '$id' in schema, f"should have id in {schema}"
    expected_id = "https://aced-idp.org/ucl-stravrinides/submission.schema.json"
    assert schema['$id'] == expected_id, f"should have id in {schema}"
    expected_keys = ['Annotated_Cancer_Area', 'BxPreDiag', 'Epi_Count', 'Epithelial_Area', 'Epithelial_Area_Percentage',
                     'Epithelial_Stromal_Ratio', 'Gleason_3_Area', 'Gleason_4_Area', 'Gleason_5_Area',
                     'Gleason_Primary', 'Gleason_Secondary', 'Grade_Group', 'Inflammatory_Area',
                     'Inflammatory_Area_Percentage', 'Irani_Gscore', 'Lumen_Area', 'Lumen_Density',
                     'Lumen_Density_Gland', 'Lymphocyte_Count', 'Lymphocyte_Percentage', 'Normal_Area', 'PIN_Area',
                     'Stroma_Count', 'Stromal_Area', 'Stromal_Area_Percentage', 'Tissue_Area', 'adcMean', 'adcn',
                     'adcu', 'ageDiagM', 'ageDiagY', 'align', 'best', 'bestVol', 'focality', 'gleason', 'id', 'level',
                     'likert', 'loc', 'mccl', 'months.diag', 'pirads', 'ppsa', 'precise', 'prvol', 'psaBx', 'side',
                     't2Vol', 'ucl', 'zone']
    actual_keys = sorted(schema['properties'].keys())
    print(actual_keys)
    assert actual_keys == expected_keys, "did not find expected keys"
