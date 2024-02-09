import logging
import pathlib
import sys
import traceback
import uuid
from typing import TextIO

import yaml
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.resource import Resource
from gen3_util import ACED_NAMESPACE
from pydantic import ValidationError

logger = logging.getLogger(__name__)

IDENTIFIER_USE = 'official'


PROJECT_ID = 'unknown-unknown'
if pathlib.Path('.g3t/config.yaml').exists():
    with open('.g3t/config.yaml') as f:
        config = yaml.safe_load(f)
        PROJECT_ID = config['gen3']['project_id']
else:
    logger.warning(f"No .g3t/config.yaml found. Using default project_id {PROJECT_ID}.")

# all resources identified by this system
SYSTEM = f"https://aced-idp.org/{PROJECT_ID}"


def populate_identifier(value: str, system: str = None, use: str = IDENTIFIER_USE) -> Identifier:
    """Populate a FHIR Identifier."""
    if not system or 'http' not in system:
        system = SYSTEM
    _ = Identifier(system=system, value=value, use=use)
    return _


def get_emitter(emitters: dict, emitter_name: str, output_path: str, verbose=False, file_mode="w") -> TextIO:
    """Returns emitter by name."""
    emitter = emitters.get(emitter_name, None)
    if not emitter:
        _ = pathlib.Path(output_path) / f"{emitter_name}.ndjson"
        emitter = open(_, file_mode)
        emitters[emitter_name] = emitter
        if verbose:
            logger.info(f"opened {emitter.name}")
    return emitter


def close_emitters(emitters: dict, verbose=False):
    """Close all emitters."""
    for emitter_name, emitter in emitters.items():
        emitter.close()
        if verbose:
            logger.info(f"closed {emitter.name}")


def mint_id(identifier: Identifier, resource_type: str) -> str:
    """Create a UUID from an identifier."""
    identifier_string = f"{identifier.system}|{identifier.value}"
    return str(uuid.uuid5(ACED_NAMESPACE, f"{PROJECT_ID}/{resource_type}/{identifier_string}"))


def get_official_identifier(resource: Resource) -> Identifier:
    """Get the official identifier."""
    _ = next(iter(_ for _ in resource.identifier if _.use == IDENTIFIER_USE), None)
    assert _, f"Could not find {IDENTIFIER_USE} identifier for {resource}"
    return _


def to_reference_identifier(resource: Resource) -> Reference:
    """Convert to FHIR."""
    _ = get_official_identifier(resource)
    return Reference(reference=f"{resource.resource_type}?identifier={_.system}|{_.value}")


def to_reference(resource: Resource) -> Reference:
    """Convert to FHIR."""
    return Reference(reference=f"{resource.resource_type}/{resource.id}")


def populate_codeable_concept(code: str, display: str, system: str = SYSTEM, text: str = None) -> CodeableConcept:
    """Populate a FHIR CodeableConcept."""
    if not text:
        text = display
    return CodeableConcept(**{
        'coding': [
                     {
                         'system': system,
                         'code': code,
                         'display': display
                     }
                 ],
        'text': text
    })


def print_transformation_error(e: ValidationError, index, path, record, verbose: bool = False):
    """Print validation error details.

    Parameters:
    - e (ValidationError): The validation error.
    - index (int): The index of the record.
    - path (str): The path to the file.
    - record (dict): The record that caused the error.
    """
    for error in e.errors():
        error['messages'] = []
        for location in error['loc']:
            if location not in record:
                msg = f"{location} not in record {path} line {index}"
            else:
                msg = f"{path} line {index} value {record[location]}"
            error['messages'].append(msg)
        if verbose:
            tb = traceback.format_exc()
            print(error, tb, file=sys.stderr)


def print_validation_error(e: ValidationError, index, path, record, verbose: bool = False):
    """Print validation error details.

    Parameters:
    - e (ValidationError): The validation error.
    - index (int): The index of the record.
    - path (str): The path to the file.
    - record (dict): The record that caused the error.
    """
    for error in e.errors():
        error['messages'] = []
        for location in error['loc']:
            if location not in record:
                msg = f"{location} not in record {path} line {index}"
            else:
                msg = f"{path} line {index} value {record[location]}"
            error['messages'].append(msg)
        if verbose:
            tb = traceback.format_exc()
            print(error, tb, file=sys.stderr)
