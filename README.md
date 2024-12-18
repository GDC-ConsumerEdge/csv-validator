# CSV Validator

This code is intended to assist in building CSV-schema-validating workflows. It is intended to be used to validate CSVs
adhering to source of truth requirements used in the Hydration and Rollout Manager (HRM) workflow. It makes heavy use
of [Pydantic](https://github.com/pydantic/pydantic) to do the heavy lifting of validating schemas, providing a few
things out of the box:

* An opinionated Pydantic model structure to define and validate the schema of arbitrary user-defined CSV data AND
  HRM-required data
* A CLI workflow (for CI/CD and local dev)
* Ability to load external, user-provided schema models and check an aribtray CSV file against them
* Optional coercion of data into a prescriptive, normalized structure serialization, dumping this as an output file

In order to write models that integrate with this module and CLI, you should (ideally) have some experience with Python
3.12. You will need to develop comfort writing Pydantic models by becoming familiar with the
docs – [start here](https://docs.pydantic.dev/latest/) and then read
the [concepts](https://docs.pydantic.dev/latest/concepts/models/).

## Requirements

* Python 3.12+
* Pydantic

## Installation

Ensure you're using Python 3.12.

The software (in `src/csv_validator`) is a module that may be installed using `setuptools`. To install the CLI to a
virtual environment, do the following:

```shell
# create virtualenv
python3 -m venv .
source bin/activate

# install requirements
python3 -m pip install -r requirements.txt

# alternatively - from root, install directly (if not developing further)
python3 -m pip install .

# then invoke the CLI one of two ways:
validate_csv --help
python3 -m csv_validator --help
```

_Note_: If you are developing this further, see [Development](#Development) below.

### Docker Install

See the Dockerfile for installing this module into a container.

## Layout

The main library code is in the [csv_validator](src/csv_validator) module. The [model.py](src/csv_validator/model.py)
file contains a basic `BaseCluster` model from which all models may (or rather _should_) subclass.

It does a few things for free:

* It checks required fields, such as `cluster_name`, `cluster_group`, and `cluster_tags`
* Provides (very) basic definitions of valid cluster groups and tags which should (and likely _must_) be extended
    * It likely must be extended because the basic set provides an _example_ list of cluster groups
    * For an example of how to extend the `ClusterBase` via subclassing, see the _example_
      model: [models/example_model.py](./models/example_model.py#L82), `class NewBase`, line 82.

## Included Examples

There are example models included that demonstrate how to consume and extend this tool:

* [models/example_model.py](./models/example_model.py)
* [models/cluster_registry.py](models/cluster_registry.py)
* [models/platform.py](./models/platform.py)

Each of these models has a set of both valid and invalid CSVs which may be used to demonstrate the functionality of the
model. CSVs live in `sources_of_truth`. As an example, to validate a valid "cluster registry" CSV and to see how it
behaves with an invalid CSV, run the following:

Valid:

```shell
$ validate_csv -v -m models/cluster_registry.py sources_of_truth/cluster_registry/cluster_reg_sot_valid.csv
INFO    CSV is valid
```

Invalid:

```shell
$ validate_csv -v -m models/cluster_registry.py sources_of_truth/cluster_registry/cluster_reg_sot_invalid.csv WARNING Optional field 'platform_repository_sync_interval' is not present in sources_of_truth/cluster_registry/cluster_reg_sot_invalid.csv
WARNING Optional field 'platform_repository_branch' is not present in sources_of_truth/cluster_registry/cluster_reg_sot_invalid.csv
WARNING Optional field 'workload_repository_branch' is not present in sources_of_truth/cluster_registry/cluster_reg_sot_invalid.csv
ERROR   Line 2, cluster US75911CLS01, column 'cluster_group', error: 'Input should be 'prod-us', 'nonprod-us', 'prod-au' or 'nonprod-au'', received 'prod-foobar'
ERROR   Line 3, cluster US41273, column 'workload_repository_sync_interval', error: 'String should match pattern '^[0-9]*[hms]$'', received '300foo'
ERROR   Line 4, cluster US64150CLS01, column 'cluster_group', error: 'Input should be 'prod-us', 'nonprod-us', 'prod-au' or 'nonprod-au'', received 'not-real'
ERROR   Line 5, cluster US21646CLS01   , column 'cluster_tags', error: 'Input should be '24/7', 'corp', 'drivethru', 'drivethruduallane' or 'donotupgrade'', received 'ThisIsInvalid'
ERROR   Line 8, cluster name unknown, column 'cluster_name', error: 'String should have at least 1 character', received ''
ERROR   Line 13, cluster AU98342CLS01, column 'cluster_group', error: 'Input should be 'prod-us', 'nonprod-us', 'prod-au' or 'nonprod-au'', received 'prod-nz'
ERROR   Line 15, cluster AU73291CLS01, column 'cluster_tags', error: 'Input should be '24/7', 'corp', 'drivethru', 'drivethruduallane' or 'donotupgrade'', received 'ThisTagIsInvalid'
```

Each of the models has a source of truth counterpart including both valid and invalid data for testing and demonstration
purposes.

## Extending the Base Model

For a functional example of extending the base, see the example
model: [models/example_model.py](./models/example_model.py), `class NewBase`.

### The Base Model

The base model, `class BaseCluster`, provides a reference implementation of a Pydantic model for the required columns
in any source of truth CSV file, including columns:

* `cluster_name`
* `cluster_group`
* `cluster_tags`

The base model valid groups and tags are stubbed and incomplete. In order to use them fully, an engineer must perform
either of the below steps:

1. Update the `ValudClusterGroups` and `ValidTags` enumerations in the `csv_validator` module _in place_, or
2. Subclass `BaseCluster`, implementing new enumerations, fully articulating all the possible valid tags and cluster
   groups. An example of this is demonstrated in [models/example_model.py](./models/example_model.py).

## Writing Your Own Models

There are numerous examples of how one may write their own models:

* [models/example_model.py](./models/example_model.py) shows how to create a new BaseCluster by subclassing it to
  customize valid groups and tags, then uses it to validate a number of example CSV columns each with unique properties
* [models/cluster_registry.py](models/cluster_registry.py) which subclasses and is based on the `BaseCluster` model (
  in [models/cluster_registry.py](./models/cluster_registry.py))
* [models/platform.py](./models/platform.py) which subclasses and is based on the `BaseCluster` model (
  in [models/cluster_registry.py](./models/cluster_registry.py))

This CSV validator is a Python module, providing a CLI, workflow, and things to import and use in model development.
Notice its utilization in the examples - one may import from, extend, and update this library. The goal was (and is)
enabling users to write extensible, flexible, consumable Python code. It is expected that you utilize it in the way that
best suits your needs. In order to fully maximize the capability of this app, familiarity with Python is greatly
beneficial.

### Using `BaseCluster` directly

*Note*: this presumes you have followed the installation instructions above and have the CLI (in the `csv_validator`
module) installed into your development environment.

1. Start by updating [csv_validator/model.py](src/csv_validator/model.py). The `BaseCluster` class refers to
   enumerations, `ValidClusterGroups` and `ValidTags`. These are stubbed. Enumerate (quite literally) the values that
   are valid _for your use case_.

```python
class ValidClusterGroups(enum.StrEnum):
    """ Contains all values considered to be valid cluster group names """
    prod_us = 'prod-us'
    nonprod_us = 'nonprod-us'
    prod_au = 'prod-au'
    nonprod_au = 'nonprod-au'
    # adding groups
    prod_ca = 'prod-ca'
    prod_mx = 'prox-mx'
    prod_uk = 'prod-uk'
    ...
```

Do the same for tags:

```python
class ValidTags(enum.StrEnum):
    """ Contains all values considered to be valid tags """
    TwentyFourSeven = '24/7'
    DriveThru = 'drivethru'
    Corp = 'corp'
    DoNotUpgrade = 'donotupgrade'
    # adding tags
    Franchise = 'franchise'
    ...
```

2. Create a model python file - in this example `custom.py`. Import the `BaseCluster`, `pydantic`.

```python
import pydantic

from csv_validator.model import BaseCluster
```

3. Create a custom model. Be sure it uses the class name `SourceOfTruthModel` and that it subclasses `BaseCluster`

```python
class SourceOfTruthModel(BaseCluster):
    my_field: str
```

This creates a new *required* column called `my_field` using a type str.

Validating schema models are simply Pydantic models. There is no magic to the model - it must simply be valid usage of
Pydantic in Python code - it's that simple. For more information, refer to the
Pydantic [documentation](https://docs.pydantic.dev/latest/)
on [models](https://docs.pydantic.dev/latest/concepts/models/)

4. Provide a CSV that provides this column, while adhering to the model `BaseCluster`. Remember, we're using inheritance
   here to combine the `BaseCluster` with your custom `SourceOfTruthModel`. Let's use `custom.csv` as the name.

```text
cluster_name,cluster_group,cluster_tags,my_field
my-cluster,prod-us,"corp",this is my field
```

5. Run the CLI importing the model (`custom.py`) against the CSV

```shell
validate_csv -m path/to/custom.py path/to/custom.csv
```

It should exit 0 if okay - you can run `-v` for extra verbosity to verify!

```shell
$ validate_csv -m path/to/custom.py path/to/custom.csv
INFO    CSV is valid
```

## Development

Install the module in editable mode with dev dependencies:

```shell
pip install -e .[dev]
```

Need to wipe your virtualenv to install from scratch?

```shell
# ensure you're in the virtualenv
source bin/activate
pip uninstall -y csv_validator
pip uninstall -y -r <(pip freeze)
pip install -e .[dev]
```

### Tests

Pylint and mypy checks are expected to pass:

```shell
pylint src
mypy src
```

Run unit tests from the repository root.

**Note:** Ensure tests are run with csv_validator installed to current Python environment/virtualenv.
See [installation](#installation) section.

```shell
python3 -m unittest tests/*.py -v
```

### Docker

Build the container:

```shell
docker build --pull --no-cache  -t csv-validator .
```

Test the container:

```shell
$ docker run -it csv-validator --help
usage: validate_csv [-h] [-m MODULE_OR_PYTHON_FILE] [-o output_source_of_truth.csv] [-v] SOURCE_OF_TRUTH.CSV

Validate source of truth CSV schemas and data using built-in and dynamically-imported validation models

...
```

## Troubleshooting

An error similar to the following may occur while executing the command `python3 -m pip install` if you have multiple
`python` versions installed.

<span style="color:red">ERROR: Package hydrate requires a different Python: 3.11.9 not in >=3.12</span>

If so, execute the following command to point `python3` to the correct version.

```shell
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
```
