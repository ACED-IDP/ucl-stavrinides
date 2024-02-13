"""Factory for creating a game character."""
import logging
import pathlib
from importlib.resources import Resource
from typing import Any, Callable

from typing import Protocol

import numpy as np
import pandas
import yaml
from fhir.resources.condition import Condition
from fhir.resources.reference import Reference
from fhir.resources.researchstudy import ResearchStudy
from pydantic import BaseModel, ConfigDict, ValidationError

from g3t_etl import TransformerHelper, get_emitter, print_transformation_error, print_validation_error, close_emitters

logger = logging.getLogger(__name__)


with open("templates/ResearchStudy.yaml") as fp:
    RESEARCH_STUDY = yaml.safe_load(fp)

with open("templates/Condition.yaml") as fp:
    CONDITION = yaml.safe_load(fp)

with open("templates/Observation.yaml") as fp:
    OBSERVATION = yaml.safe_load(fp)

_project_id = 'unknown-unknown'
if pathlib.Path('.g3t/config.yaml').exists():
    with open('.g3t/config.yaml') as f:
        config = yaml.safe_load(f)
        _project_id = config['gen3']['project_id']
else:
    logger.warning(f"No .g3t/config.yaml found. Using default project_id {_project_id}.")

helper = TransformerHelper(project_id=_project_id)


class Transformer(Protocol):
    """Basic representation of an ETL transformer."""

    def transform(self, research_study: ResearchStudy = None) -> list[Resource]:
        """Let the character make a noise."""


transformers: list[Callable[..., Transformer]] = []
default_dictionary_path: None


def default_transformer():
    """Default transformer."""
    return transformers[0]


def register(transformer: Callable[..., Transformer], _default_dictionary_path: str) -> None:
    """Register a new transformer."""
    transformers.append(transformer)
    global default_dictionary_path
    default_dictionary_path = _default_dictionary_path


def unregister(transformer: Callable[..., Transformer]) -> None:
    """Unregister a transformer."""
    transformers.remove(transformer)


class TransformationResults(BaseModel):
    """Summarize the transformation results."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    parsed_count: int
    emitted_count: int
    validation_errors: list[ValidationError]
    transformer_errors: list[ValidationError]


def template_condition(subject: Reference) -> Condition:
    """Create a generic prostate cancer condition."""
    CONDITION['subject'] = subject
    return Condition(**CONDITION)


def transform_csv(input_path: pathlib.Path,
                  output_path: pathlib.Path,
                  already_seen: set = None,
                  verbose: bool = False) -> TransformationResults:
    """Transform a CSV file to FHIR templates."""

    if already_seen is None:
        already_seen = set()

    emitters = {}

    df = pandas.read_csv(input_path)
    df = df.replace({np.nan: None})
    records = df.to_dict(orient='records')

    parsed_count = 0
    emitted_count = 0
    validation_errors = []
    transformer_errors = []

    try:
        research_study = ResearchStudy(**RESEARCH_STUDY)
        identifier = helper.populate_identifier(value=_project_id)
        id_ = helper.mint_id(identifier=identifier, resource_type='ResearchStudy')
        research_study.id = id_
        research_study.identifier = [identifier]
        already_seen.add(research_study.id)
        get_emitter(emitters, research_study.resource_type, str(output_path), verbose=False).write(research_study.json() + "\n")
        emitted_count += 1

    except ValidationError as e:
        transformer_errors.append(e)
        print_transformation_error(e, parsed_count, input_path, RESEARCH_STUDY, verbose)
        raise e

    for record in records:

        try:
            transformer = default_transformer()(**record, helper=helper)
            parsed_count += 1
        except ValidationError as e:
            validation_errors.append(e)
            print_validation_error(e, parsed_count, input_path, record, verbose)
            raise e

        try:
            resources = transformer.transform(research_study=research_study)
            assert resources is not None, f"transformer {transformer.id} returned None"
            assert len(resources) > 0, f"transformer {transformer.id} returned empty list"
            for resource in resources:
                if resource.id in already_seen:
                    continue
                already_seen.add(resource.id)
                get_emitter(emitters, resource.resource_type, str(output_path), verbose=False).write(resource.json() + "\n")
                emitted_count += 1
        except ValidationError as e:
            transformer_errors.append(e)
            print_transformation_error(e, parsed_count, input_path, record, verbose)
            raise e

    close_emitters(emitters)

    return TransformationResults(
        parsed_count=parsed_count,
        emitted_count=emitted_count,
        validation_errors=validation_errors,
        transformer_errors=transformer_errors
    )
