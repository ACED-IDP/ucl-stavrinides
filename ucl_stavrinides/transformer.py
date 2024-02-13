import logging
import re
import sys
from typing import Any, Optional

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
from pydantic import BaseModel, field_validator
from pydantic.fields import FieldInfo

from g3t_etl import factory
from g3t_etl.factory import OBSERVATION
from ucl_stavrinides.submission import Submission

logger = logging.getLogger(__name__)

# TODO - move to factory
with open("templates/Condition.yaml") as fp:
    CONDITION = yaml.safe_load(fp)


def template_condition(subject: Reference) -> Condition:
    """Create a generic prostate cancer condition."""
    CONDITION['subject'] = subject
    return Condition(**CONDITION)


class DeconstructedID(BaseModel):
    """Split the id into component parts."""
    patient_id: str
    mri_area: Optional[int] = None
    time_points: Optional[list[str]] = None
    tissue_block: Optional[int] = None


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


def additional_observation_codings(field, field_info: FieldInfo) -> list[dict]:
    """Additional codings for the observation."""

    if 'code' in field_info.json_schema_extra:
        return [{
            "system": field_info.json_schema_extra['coding_system'],
            "code": field_info.json_schema_extra['coding_code'],
            "display": field_info.json_schema_extra['coding_display']
        }]
    return []


class SimpleTransformer(Submission):
    """Performs the most simple transformation possible."""
    deconstructed_id: DeconstructedID = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa
        super().__init__(**kwargs, )
        # TODO replace with @computed when we migrate to pydantic +2
        self.deconstructed_id = split_id(self.id)
        self._helper = kwargs['helper']

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
        exception_msg_part = None
        research_subject = None
        try:

            exception_msg_part = 'Patient'
            identifier = self._helper.populate_identifier(value=deconstructed_id.patient_id)
            patient = Patient(id=self._helper.mint_id(identifier=identifier, resource_type='Patient'),
                              identifier=[identifier],
                              active=True)

            if research_study:
                exception_msg_part = 'ResearchSubject'
                identifier = self._helper.populate_identifier(value=deconstructed_id.patient_id)
                research_subject = ResearchSubject(
                    id=self._helper.mint_id(identifier=identifier, resource_type='ResearchSubject'),
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

            identifier = self._helper.populate_identifier(value=f"{deconstructed_id.patient_id}/{lesion_identifier}")
            procedure = Procedure(id=self._helper.mint_id(identifier=identifier, resource_type='Procedure'),
                                  identifier=[identifier],
                                  status="completed",
                                  subject=self._helper.to_reference(patient))
            procedure.code = self._helper.populate_codeable_concept(system="http://snomed.info/sct", code="312250003",
                                                                    display="Magnetic resonance imaging")

            exception_msg_part = 'Specimen'
            identifier = self._helper.populate_identifier(value=f"{self.id}")
            specimen = Specimen(id=self._helper.mint_id(identifier=identifier, resource_type='Specimen'),
                                identifier=[identifier],
                                collection={'procedure': self._helper.to_reference(procedure)},
                                subject=self._helper.to_reference(patient))

            exception_msg_part = 'Condition'
            condition = template_condition(subject=self._helper.to_reference(patient))
            identifier = self._helper.populate_identifier(value=f"{deconstructed_id.patient_id}/{condition.code.text}")
            condition.id = self._helper.mint_id(identifier=identifier, resource_type='Condition')
            condition.identifier = [identifier]
            condition.onsetAge = Age(
                value=self.ageDiagM,
                code="m",
                system="http://unitsofmeasure.org",
                unit="months"
            )

            # TODO confirm these fields as Observations of the Specimen
            specimen_observations = self.create_observations(subject=patient, focus=specimen)
            condition_observations = self.create_observations(subject=patient, focus=condition)

        except Exception as e:
            print(f"Error transforming {self.id} to {exception_msg_part}: {e}", file=sys.stderr)
            raise e

        patient_graph = [patient, specimen, procedure, condition]
        if research_study and research_subject:
            patient_graph.append(research_subject)

        return patient_graph + specimen_observations + condition_observations

    def create_observations(self, subject, focus) -> list[Observation]:
        """Create observations."""
        observations = []

        observation_fields = {}
        for field, field_info in self.model_fields.items():
            if not field_info.json_schema_extra:
                continue
            if 'observation_subject' in field_info.json_schema_extra:
                if field_info.json_schema_extra['observation_subject'] == focus.resource_type:
                    observation_fields[field] = field_info

        # for all attributes in raw record ...
        for field, field_info in observation_fields.items():

            # that are not null ...
            value = getattr(self, field)
            if not value:
                continue

            # and create an observation
            subject_identifier = self._helper.get_official_identifier(subject).value
            focus_identifier = self._helper.get_official_identifier(focus).value
            identifier = self._helper.populate_identifier(value=f"{subject_identifier}-{focus_identifier}-{field}")
            id_ = self._helper.mint_id(identifier=identifier, resource_type='Observation')
            more_codings = additional_observation_codings(field, field_info)

            if 'code' in OBSERVATION:
                del OBSERVATION['code']
            observation = Observation(**OBSERVATION, code=self._helper.populate_codeable_concept(code=field,
                                                                                                 display=field_info.description))
            observation.id = id_
            observation.identifier = [identifier]
            observation.subject = self._helper.to_reference(subject)
            observation.focus = [self._helper.to_reference(focus)]
            if more_codings:
                observation.code.coding.extend(more_codings)

            # the annotations are often decorated with Optional, so cast to string and check for the type
            field_type = str(field_info.annotation)
            if 'int' in field_type:
                observation.valueInteger = getattr(self, field)
            elif 'float' in field_type or 'decimal' in field_type or 'number' in field_type:
                observation.valueQuantity = self.to_quantity(field, field_info)
            else:
                observation.valueString = getattr(self, field)

            observations.append(observation)

        return observations

    def to_quantity(self, field, field_info) -> dict:
        """Convert to FHIR Quantity."""
        _ = {
            "value": getattr(self, field),
        }
        if field_info.json_schema_extra:
            if 'uom_system' in field_info.json_schema_extra:
                _['system'] = field_info.json_schema_extra['uom_system']
                _['code'] = field_info.json_schema_extra['uom_code']
                _['unit'] = field_info.json_schema_extra['uom_unit']
        return _


def register() -> None:
    factory.register(SimpleTransformer, "docs/IDP_UCL_VS_data_dictionary-IDP_Mapping.xlsx")
