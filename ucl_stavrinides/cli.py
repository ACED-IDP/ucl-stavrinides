import sys
from pathlib import Path

import click
import orjson

from ucl_stavrinides.models.submission_dictionary import spreadsheet_json_schema
from ucl_stavrinides.transformers.simple import transform_csv


@click.group()
def cli():
    """Manage ucl-stavrinides metadata."""
    pass


@cli.command('transform')
@click.argument('input_path', type=click.Path(exists=True, dir_okay=False),
                default=None, required=True)
@click.argument('output_path', type=click.Path(dir_okay=True), default='META', required=False)
@click.option('--verbose', default=False, show_default=True, is_flag=True,
              help='verbose output')
def transform_csv_cli(input_path: str, output_path: str, verbose: bool):
    """Transform csv based on data dictionary to FHIR.

    \b
    INPUT_PATH: where to read spreadsheet. required, (convention data/raw/XXXX.xlsx)
    OUTPUT_PATH: where to write FHIR. default: META/
    """
    transformation_results = transform_csv(input_path=input_path, output_path=output_path, verbose=verbose)
    if not transformation_results.transformer_errors and not transformation_results.validation_errors:
        click.secho(f"Transformed {input_path} into {output_path}", fg='green', file=sys.stderr)
    else:
        click.secho(f"Error transforming {input_path}")
        if verbose:
            click.secho(f"Validation errors: {transformation_results.validation_errors}", fg='red')
            click.secho(f"Transformer errors: {transformation_results.transformer_errors}", fg='red')


@cli.command('dictionary')
@click.argument('input_path', type=click.Path(),
                default='docs/IDP_UCL_VS_data_dictionary-IDP_Mapping.xlsx', required=False)
@click.argument('output_path', type=click.Path(), default='data/resources/submission.schema.json', required=False)
@click.option('--verbose', default=False, show_default=True, is_flag=True,
              help='verbose output')
def spreadsheet_json_schema_cli(input_path: str, output_path: str, verbose):
    """Code generation. Create python model class from dictionary spreadsheet.

    \b
    Use this command to track changes to the data dictionary.
    INPUT_PATH: where to read master spreadsheet default: data/raw/DetroitROCS_cancer_subtypes_2023-09-25.xlsx
    OUTPUT_PATH: where to write per subject csvs default: data/resources/submission.schema.json
    """
    try:
        input_path = Path(input_path)
        assert input_path.exists(), f"Spreadsheet not found at {input_path},"\
                                    " please see README in docs/ for instructions."
        schema = spreadsheet_json_schema(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as fp:
            fp.write(orjson.dumps(schema, option=orjson.OPT_INDENT_2).decode())

        click.secho(f"Transformed {input_path} into jsonschema file in {output_path}",
                    fg='green', file=sys.stderr)
        cmd = f"datamodel-codegen  --input {output_path} --input-file-type jsonschema  "\
              "--output ucl_stavrinides/models/submission.py"
        click.secho("Use this command to generate pydantic model from schema:", fg='green', file=sys.stderr)
        print(cmd)
    except Exception as e:
        click.secho(f"Error splitting {input_path} into {output_path}: {e}", fg='red')
        if verbose:
            raise e
