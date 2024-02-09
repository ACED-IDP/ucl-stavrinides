import numpy as np
import pandas
from pydantic import ValidationError

from ucl_stavrinides.models.submission import Submission
from ucl_stavrinides.transformers import print_validation_error


def test_submission_dictionary():
    """Was the submission model created correctly?"""
    from ucl_stavrinides.models.submission import Submission
    _ = Submission.schema()
    assert _, "do not have a schema"
    expected_keys = ['Annotated_Cancer_Area', 'BxPreDiag', 'Epi_Count', 'Epithelial_Area', 'Epithelial_Area_Percentage',
                     'Epithelial_Stromal_Ratio', 'Gleason_3_Area', 'Gleason_4_Area', 'Gleason_5_Area',
                     'Gleason_Primary', 'Gleason_Secondary', 'Grade_Group', 'Inflammatory_Area',
                     'Inflammatory_Area_Percentage', 'Irani_Gscore', 'Lumen_Area', 'Lumen_Density',
                     'Lumen_Density_Gland', 'Lymphocyte_Count', 'Lymphocyte_Percentage', 'Normal_Area', 'PIN_Area',
                     'Stroma_Count', 'Stromal_Area', 'Stromal_Area_Percentage', 'Tissue_Area', 'adcMean', 'adcn',
                     'adcu', 'ageDiagM', 'ageDiagY', 'align', 'best', 'bestVol', 'focality', 'gleason', 'id', 'level',
                     'likert', 'loc', 'mccl', 'months.diag', 'pirads', 'ppsa', 'precise', 'prvol', 'psaBx', 'side',
                     't2Vol', 'ucl', 'zone']
    actual_keys = sorted(_['properties'].keys())
    assert actual_keys == expected_keys, "do not have expected keys"


def test_submission_dummy_data(test_fixture_paths):
    """Can we read the dummy data?"""
    for dummy_data_path in test_fixture_paths:
        assert dummy_data_path.exists(), f"do not have {dummy_data_path}"
        df = pandas.read_csv(dummy_data_path)
        df = df.replace({np.nan: None})
        records = df.to_dict(orient='records')
        c = 1
        for record in records:
            try:
                _ = Submission(**record)
                c += 1
            except ValidationError as e:
                print_validation_error(e, c, dummy_data_path, record)
                raise e
