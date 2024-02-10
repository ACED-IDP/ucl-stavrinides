import pathlib

from gen3_util.meta.validator import validate

from ucl_stavrinides.transformers.simple import transform_csv


def test_transform_dummy_data(test_fixture_paths):
    """Transform the dummy data to FHIR, store in test fixture."""
    validation_errors = []
    transformer_errors = []
    emitted_count = 0
    parsed_count = 0
    for input_path in test_fixture_paths:

        output_path = pathlib.Path('tests/fixtures/IDP_UCL_VS_dataset-FHIR') / input_path.stem

        output_path.mkdir(parents=True, exist_ok=True)

        assert input_path.exists(), f"File must exist {input_path}"

        results = transform_csv(input_path, output_path)

        parsed_count += results.parsed_count
        emitted_count += results.emitted_count
        validation_errors.extend(results.validation_errors)
        transformer_errors.extend(results.transformer_errors)

        validate(config=None, directory_path=output_path)

    print(f"emitted {emitted_count} resources out of {parsed_count} input resources")
    assert len(validation_errors) == 0, f"validation_errors errors {transformer_errors}"
    assert len(transformer_errors) == 0, f"transformer_errors errors {transformer_errors}"
