# ucl-stavrinides User Guide

## Overview

`ucl_stavrinides` is a command-line tool designed to manage the metadata. The tool provides various commands, each serving a specific purpose. Below, you'll find a brief guide on how to use the available commands.

## Getting Started


**Clone the Repository:** Clone the forked repository to your local machine using the following command:

```bash
git clone https://github.com/ACED-IDP/ucl-stavrinides
python3 -m venv venv ; source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```
**Install Dependencies**: Ensure you have the necessary dependencies installed.
The installation process will install gen3 tracker utility, see [how to configure it](https://aced-idp.github.io/getting-started/).

**Verify installation**: Run the following command to verify the installation:

```bash
g3t ping
msg: 'Configuration OK: Connected using profile:xxxx'
endpoint: https://aced-idp.org
username: your-email@institution.edu
```

### Global Options

- `--help`: Display information about the available commands and options.

## Commands

### `transform`

The `transform` reads lines from the csv and creates resources representing data for a specific subject and time point.

#### Usage:

```bash
ucl_stavrinides transform --help
Usage: ucl_stavrinides transform [OPTIONS] INPUT_PATH [OUTPUT_PATH]

  Transform csv based on data dictionary to FHIR.

  INPUT_PATH: where to read spreadsheet. required, (convention data/raw/XXXX.xlsx)
  OUTPUT_PATH: where to write FHIR. default: META/


```

#### Configuration:

The transformations are based on the data dictionary and the following resources:

```shell
data/resources/
├── ResearchStudy.yaml
├── observation_attributes.yaml
└──  observation_codings.yaml


$head -5 data/resources/ResearchStudy.yaml
# This file contains the properties of the ResearchStudy resource
---
status: active
description: ACED IDP UCL Stravrinides Project

$ head -10  data/resources/observation_attributes.yaml
# this file contains the list of attributes that are used to create Observation on [Condition, Specimen] resources.
# The key is the name of the FHIR resource and the values are the fields from the data dictionary.
---
Condition:
- ageDiagY
- align
- ppsa
- BxPreDiag
...

 head -11  data/resources/observation_codings.yaml
# The coding systems are used to enhance the value set for the observation resources
# The key is the name of the attribute in the data dictionary and the value is a list of coding systems
---
gleason:
- system: http://snomed.info/sct
  code: '372278000'
  display: Gleason score
prvol:
- system: https://loinc.org/
  code: 15325-4
  display: Prostate specific Ag/Prostate volume calculated
...

```



#### Example:

##### Transforming a csv file to FHIR

```bash
$ ucl_stavrinides transform tests/fixtures/IDP_UCL_VS_dataset/dummy_data_30pid.csv
Transformed tests/fixtures/IDP_UCL_VS_dataset/dummy_data_30pid.csv into META

$ g3t utilities meta validate
resources:
  summary:
    Procedure: 160
    Specimen: 160
    Observation: 6696
    ResearchStudy: 1
    Condition: 30
    ResearchSubject: 30
    Patient: 30
msg: OK

```

##### Uploading the FHIR resources to the server

```bash
$ g3t commit -m "Initial upload"
$ g3t push

```

##### Adding dummy image files

See [dummy file generation](tests/fixtures/IDP_UCL_VS_dataset-files/README.md).

###### association a file with a specimen
```shell
# find all specimen identifiers, and add the file to the index in parallel
$ cat META/Specimen.ndjson | jq -r '.identifier[0].value' | xargs -P 8 -L 1 -I SPECIMEN g3t add --specimen SPECIMEN tests/fixtures/IDP_UCL_VS_dataset-files/dummy_data_30pid/SPECIMEN_mri_guided_prostate_biopsy.jpeg
# create metadata for the files
$ g3t utilities meta create
```

###### commit and push the files
```shell
$ g3t commit -m "Add image files"
$ g3t push
```

###### confirm the files are uploaded
```shell
$ g3t status

remote:
  resource_counts:
    Condition: 30
    DocumentReference: 160
    FamilyMemberHistory: 0
    Medication: 0
    MedicationAdministration: 0
    Observation: 6696
    Patient: 30
    ResearchStudy: 1
    ResearchSubject: 30
    Specimen: 160
    Substance: 0
    Task: 0

```


### `dictionary`

The `dictionary` is a design stage utility that reads the master data dictionary and creates a corresponding python class.

#### Usage:

```bash
$ ucl_stavrinides dictionary --help
Usage: ucl_stavrinides dictionary [OPTIONS] [INPUT_PATH] [OUTPUT_PATH]

  Code generation. Create python model class from dictionary spreadsheet.

  Use this command to track changes to the data dictionary.
  INPUT_PATH: where to read master spreadsheet default: data/raw/DetroitROCS_cancer_subtypes_2023-09-25.xlsx
  OUTPUT_PATH: where to write per subject csvs default: data/resources/submission.schema.json

```

#### Example:

```bash
ucl_stavrinides dictionary
Transformed docs/IDP_UCL_VS_data_dictionary-IDP_Mapping.xlsx into jsonschema file in data/resources/submission.schema.json
Use this command to generate pydantic model from schema:
datamodel-codegen  --input data/resources/submission.schema.json --input-file-type jsonschema  --output ucl_stavrinides/models/submission.py
```


Feel free to explore additional functionalities and options by referring to the [aced documentation](https://aced-idp.github.io/)
