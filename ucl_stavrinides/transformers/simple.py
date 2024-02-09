import pathlib
import re
import sys
from typing import Any, Optional

import numpy as np
import pandas
import yaml
from fhir.resources.age import Age
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.procedure import Procedure
from fhir.resources.reference import Reference
from fhir.resources.researchstudy import ResearchStudy
from fhir.resources.researchsubject import ResearchSubject
from fhir.resources.resource import Resource
from fhir.resources.specimen import Specimen
from pydantic import BaseModel, field_validator, ValidationError, ConfigDict

from ucl_stavrinides.models.submission import Submission
from ucl_stavrinides.transformers import populate_identifier, mint_id, populate_codeable_concept, to_reference, \
    get_official_identifier, close_emitters, print_transformation_error, get_emitter, print_validation_error, PROJECT_ID

with open("data/resources/observation_codings.yaml") as fp:
    ADDITIONAL_CODINGS = yaml.safe_load(fp)

with open("data/resources/observation_attributes.yaml") as fp:
    OBSERVATION_ATTRIBUTES = yaml.safe_load(fp)

with open("data/resources/ResearchStudy.yaml") as fp:
    RESEARCH_STUDY_PROPERTIES = yaml.safe_load(fp)


class DeconstructedID(BaseModel):
    """Split the id into component parts."""
    patient_id: str
    mri_area: Optional[int] = None
    time_points: Optional[list[str]] = None
    tissue_block: Optional[int] = None


class TransformationResults(BaseModel):
    """Summarize the transformation results."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    parsed_count: int
    emitted_count: int
    validation_errors: list[ValidationError]
    transformer_errors: list[ValidationError]


def split_id(id_str) -> None | DeconstructedID:
    """Format: XXX_Y_Z_H, where:
    XXX is patient ID,
    Y is the MRI area number,
    Z are the time points (A or B), which may occur multiple times,
    H is the tissue block number in case of multiple biopsy blocks per area"""

    # Define a regular expression pattern to match the specified format
    pattern = r"^(?P<patient_id>[^_]+)_(?P<mri_area>[^_]+)_(?P<time_points>[AB_]+)(?:_(?P<tissue_block>[^_]+))?$"

    # Try to match the pattern with the provided ID
    match = re.match(pattern, id_str)

    # If there is a match, create a PatientInfo Pydantic model
    if match:
        groups = match.groups()
        deconstructed_id = DeconstructedID(
            patient_id=match.group("patient_id"),
            mri_area=match.group("mri_area"),
            time_points=match.group("time_points").split("_"),
            tissue_block=match.group("tissue_block") if match.group("tissue_block") else None
        )
        return deconstructed_id
    else:
        # otherwise None
        return None


def generic_prostate_cancer_condition(subject: Reference) -> Condition:
    """Create a generic prostate cancer condition."""
    _ = {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed",
                "display": "confirmed"
            }]
        },
        "category": [{
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                    "code": "encounter-diagnosis",
                    "display": "Encounter Diagnosis"
                },
                {
                    "system": "http://snomed.info/sct",
                    "code": "439401001",
                    "display": "Diagnosis"
                }]
        }],
        "severity": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "24484000",
                "display": "Severe"
            }]
        },
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "399068003",
                "display": "Malignant tumor of prostate"
            }],
            "text": "Malignant tumor of prostate"
        },
        "bodySite": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "41216001",
                "display": "Prostatic structure (body structure)"
            }],
            "text": "Prostatic structure (body structure)"
        }],
        "subject": subject
    }
    return Condition(**_)


class SimpleTransformer(Submission):
    """Performs the most simple transformation possible."""
    deconstructed_id: DeconstructedID = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # TODO replace with @computed when we migrate to pydantic +2
        self.deconstructed_id = split_id(self.id)

    @field_validator('id')
    def must_have_valid_id(cls, v):
        """Deconstruct the ID."""
        _ = split_id(v)
        if not _:
            raise ValueError('Invalid ID')
        return v

    def transform(self, research_study: ResearchStudy = None) -> list[Resource]:
        """Transform the data to FHIR."""
        return self.to_fhir(self.deconstructed_id, research_study=research_study)

    def to_fhir(self, deconstructed_id: DeconstructedID, research_study: ResearchStudy) -> [Resource]:
        """Convert to FHIR."""
        try:

            exception_msg_part = 'Patient'
            identifier = populate_identifier(value=deconstructed_id.patient_id)
            patient = Patient(id=mint_id(identifier=identifier, resource_type='Patient'),
                              identifier=[identifier],
                              active=True)

            if research_study:
                exception_msg_part = 'ResearchSubject'
                identifier = populate_identifier(value=deconstructed_id.patient_id)
                research_subject = ResearchSubject(
                    id=mint_id(identifier=identifier, resource_type='ResearchSubject'),
                    identifier=[identifier],
                    status="active",
                    study={'reference': f"ResearchStudy/{research_study.id}"},
                    subject={'reference': f"Patient/{patient.id}"}
                )

            exception_msg_part = 'Procedure'

            time_points = '_'.join(deconstructed_id.time_points)
            lesion_identifier = f"{deconstructed_id.mri_area}_{time_points}"
            if deconstructed_id.tissue_block:
                lesion_identifier += f"_{deconstructed_id.tissue_block}"

            identifier = populate_identifier(value=f"{deconstructed_id.patient_id}/{lesion_identifier}")
            procedure = Procedure(id=mint_id(identifier=identifier, resource_type='Procedure'),
                                  identifier=[identifier],
                                  status="completed",
                                  subject=to_reference(patient))
            procedure.code = populate_codeable_concept(system="http://snomed.info/sct", code="312250003",
                                                       display="Magnetic resonance imaging")

            exception_msg_part = 'Specimen'
            identifier = populate_identifier(value=f"{deconstructed_id.patient_id}/{lesion_identifier}")
            specimen = Specimen(id=mint_id(identifier=identifier, resource_type='Specimen'),
                                identifier=[identifier],
                                collection={'procedure': to_reference(procedure)},
                                subject=to_reference(patient))

            exception_msg_part = 'Condition'
            condition = generic_prostate_cancer_condition(subject=to_reference(patient))
            identifier = populate_identifier(value=f"{deconstructed_id.patient_id}/{condition.code.text}")
            condition.id = mint_id(identifier=identifier, resource_type='Condition')
            condition.identifier = [identifier]
            condition.onsetAge = Age(
                value=self.ageDiagM,
                code="m",
                system="http://unitsofmeasure.org",
                unit="months"
            )

            # TODO confirm these fields as Observations of the Specimen
            specimen_observations = self.create_observations(subject=patient, focus=specimen,
                                                             attributes=OBSERVATION_ATTRIBUTES['Specimen'])
            condition_observations = self.create_observations(subject=patient, focus=condition,
                                                              attributes=OBSERVATION_ATTRIBUTES['Condition'])

        except Exception as e:
            print(f"Error transforming {self.id} to {exception_msg_part}: {e}", file=sys.stderr)
            raise e

        patient_graph = [patient, specimen, procedure, condition]
        if research_study:
            patient_graph.append(research_subject)

        return patient_graph + specimen_observations + condition_observations

    def create_observations(self, subject, focus, attributes) -> list[Observation]:
        """Create observations."""
        observations = []
        for attribute in attributes:

            value = getattr(self, attribute)
            if not value:
                continue

            field_info = self.model_fields.get(attribute)
            assert field_info, f"Could not find field info for {attribute}"

            subject_identifier = get_official_identifier(subject).value
            focus_identifier = get_official_identifier(focus).value
            identifier = populate_identifier(value=f"{subject_identifier}-{focus_identifier}-{attribute}")
            id_ = mint_id(identifier=identifier, resource_type='Observation')

            observation = Observation(
                id=id_,
                identifier=[identifier],
                status="final",
                subject=to_reference(subject),
                focus=[to_reference(focus)],
                category=[populate_codeable_concept(system="http://terminology.hl7.org/CodeSystem/observation-category",
                                                    code="laboratory", display="Laboratory")],
                code=populate_codeable_concept(code=attribute,
                                               display=field_info.description),
            )

            _ = self.additional_observation_codings(attribute)
            if _:
                observation.code.coding.extend(_)

            # the annotations are often decorated with Optional, so cast to string and check for the type
            field_type = str(field_info.annotation)
            if 'int' in field_type:
                observation.valueInteger = getattr(self, attribute)
            elif 'float' in field_type:
                observation.valueQuantity = {
                    "value": getattr(self, attribute),
                }
            else:
                observation.valueString = getattr(self, attribute)

            observations.append(observation)

        return observations

    def additional_observation_codings(self, attribute) -> list[dict]:
        """Additional codings for the observation."""

        if attribute in ADDITIONAL_CODINGS:
            return ADDITIONAL_CODINGS[attribute]
        return []


def transform_csv(input_path: pathlib.Path, output_path: pathlib.Path, already_seen: set = set(), verbose: bool = False) -> TransformationResults:
    """Transform a CSV file to FHIR resources."""

    emitters = {}

    df = pandas.read_csv(input_path)
    df = df.replace({np.nan: None})
    records = df.to_dict(orient='records')

    parsed_count = 0
    emitted_count = 0
    validation_errors = []
    transformer_errors = []

    try:
        research_study = ResearchStudy(**RESEARCH_STUDY_PROPERTIES)
        identifier = populate_identifier(value=PROJECT_ID)
        id_ = mint_id(identifier=identifier, resource_type='ResearchStudy')
        research_study.id = id_
        research_study.identifier = [identifier]
        already_seen.add(research_study.id)
        get_emitter(emitters, research_study.resource_type, output_path, verbose=False).write(research_study.json() + "\n")
        emitted_count += 1

    except ValidationError as e:
        transformer_errors.append(e)
        print_transformation_error(e, parsed_count, input_path, RESEARCH_STUDY_PROPERTIES, verbose)
        raise e

    for record in records:

        try:
            transformer = SimpleTransformer(**record)
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
                get_emitter(emitters, resource.resource_type, output_path, verbose=False).write(resource.json() + "\n")
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
