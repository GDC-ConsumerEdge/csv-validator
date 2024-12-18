###############################################################################
# Copyright 2024 Google, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
import argparse
import csv
import importlib
import importlib.util
import logging
import os
import pathlib
import sys
import types
from typing import IO, Self, Type, Optional, cast, Tuple

import pydantic
from csv_validator.model import BaseCluster


class LazyFileType(argparse.FileType):
    """Subclasses `argparse.FileType` in order to provide a way to lazily open
    files for reading/writing from arguments.  Initializes the same as the
    parent, but provides `open` method which returns the file object.

    Usage:
    ```
    parser = argparse.ArgumentParser()
    parser.add_argument('f', type=LazyFileType('w'))
    args = parser.parse_args()

    with args.f.open() as f:
        for line in foo:
            ...
    ```

    Provides an alternate constructor for use with the `default` kwarg to
    `ArgumentParser.add_argument`.

    Usage:
    ```
    parser.add_argument('-f', type=LazyFileType('w'),
                        default=LazyFileType.default('some_file.txt')
    ```
    """

    def __call__(self, string: str) -> Self:  # type: ignore
        self.filename = string  # pylint: disable=attribute-defined-outside-init

        if 'r' in self._mode or 'x' in self._mode:
            if not pathlib.Path(self.filename).exists():
                m = (f"can't open {self.filename}:  No such file or directory: "
                     f"'{self.filename}'")
                raise argparse.ArgumentTypeError(m)

        return self

    def open(self) -> IO:
        """Opens and returns file for reading
                :rtype: io.TextIOWrapper
        """
        return open(self.filename, self._mode, self._bufsize, self._encoding,
                    self._errors)

    @classmethod
    def default(cls, string: str, **kwargs) -> Self:
        """Alternate constructor for a default argument to argparse argument

        Args:
            string: filename to open
            **kwargs: arguments to `__init__`

        Returns:
            instance of `LazyFileType`
        """
        inst = cls(**kwargs)
        inst.filename = string  # pylint: disable=attribute-defined-outside-init
        return inst


def get_validator_module(v_mod: str) -> types.ModuleType:
    """Takes a validator module as a string, either a path to a Python file or
    a module name.  If the path is a file (any file), it tries to convert the
    path into a module and load it.  If the string isn't a path, it tries to
    import the module directly.  The imported module is returned. Raises a
    `RuntimeError` if module import fails.

    Returns:
        object: module
    """
    p = pathlib.Path(v_mod)

    try:
        if p.is_file():
            module_name = p.stem
            spec = importlib.util.spec_from_file_location(module_name,
                                                          str(p.absolute()))
            module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(module)  # type: ignore
        else:
            module = importlib.import_module(v_mod)
    except ModuleNotFoundError as e:
        raise RuntimeError('error loading module') from e

    return module


def setup_logger(verbosity: int) -> logging.Logger:
    """Sets up logger, setting log level higher for increased verbosity

    Args:
        verbosity: int as the level of expected verbosity; higher = more verbose

    Returns:
        logger
    """
    # sets up a default standard out logger and level
    log_format = "%(levelname)-7s %(message)s"
    logging.basicConfig(stream=sys.stdout, format=log_format)
    logger = logging.getLogger()

    if verbosity == 1:
        logger.setLevel(logging.INFO)
    elif verbosity >= 2:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARN)

    return logger


def parse_args() -> argparse.Namespace:
    """
    Constructs an argument parser, parses args, and returns the arg namespace.
    Returns:
        object: argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description='Validate source of truth CSV schemas and data using '
                    'built-in and dynamically-imported validation models')
    parser.add_argument(
        'source',
        metavar='SOURCE_OF_TRUTH.CSV',
        type=LazyFileType(),
        default=LazyFileType('source_of_truth.csv'),
        help='Path to source of truth CSV file')
    parser.add_argument(
        '-m', '--validator-module',
        metavar='MODULE_OR_PYTHON_FILE',
        help='Module name or path to Python file containing source of truth '
             'model; if not provided, only the required default columns are '
             'validated using the internal validation model')
    parser.add_argument(
        '-o', '--output',
        metavar='output_source_of_truth.csv',
        type=LazyFileType(mode='w'),
        help='Optional file to dump validated, normalized data output from '
             'the validation model as CSV')
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        help='increase output verbosity; -vv for max verbosity',
        default=0)
    return parser.parse_args()


# pylint: disable-next=too-few-public-methods
class CLI:
    """Contains the CLI workflow.
    """
    _source: LazyFileType
    _output: LazyFileType
    _verbose: int
    _logger: logging.Logger
    _model: Type[pydantic.BaseModel]
    _validator_module: Optional[str]
    _reader: csv.DictReader
    _writer: Optional[csv.DictWriter]
    _in_fp: IO
    _out_fp: Optional[IO]

    def __init__(self, *, source: LazyFileType, output: LazyFileType,
                 verbose: int, logger: logging.Logger,
                 validator_module: Optional[str] = None):
        self._source = source
        self._output = output
        self._verbose = verbose
        self._logger = logger
        self._validator_module = validator_module
        self._out_fp = None
        self._writer = None

    # pylint: disable-next=too-many-branches
    def run(self) -> int:
        """Entry point for CLI; implements CLI workflow.

        Returns:
            CLI exit code as int
        """
        # Set the model to use going forward. Defaults to BaseCluster. If one is
        # provided via args, import and set.
        try:
            model = self._load_model_dynamic()
        except RuntimeError:
            return 1

        self._model = cast(Type[pydantic.BaseModel],
                           model if model else BaseCluster)

        # Begin reading the source CSV
        self._logger.debug(f"Using source file '{self._source.filename}'")
        try:
            self._in_fp = self._source.open()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._logger.exception('Error opening source file', exc_info=e)
            return 1

        # Set up CSV reader - presume 'excel' dialect, read in strictly.
        # Let's exit if it can't be parsed.
        self._reader = csv.DictReader(self._in_fp, dialect='excel', strict=True)

        try:
            error: bool = self._validate_csv_fields()
        except RuntimeError:
            return 1

        # If user set output CSV, set up to use it
        try:
            self._setup_csv_writer()
        except RuntimeError:
            return 1

        while True:
            # loop over rows
            try:
                row: dict[str, str] = next(self._reader)
            except csv.Error as e:
                self._logger.exception(
                    f'Encountered CSV parsing error, row '
                    f'{self._reader.line_num}, {self._in_fp.name}', exc_info=e)
                error = True
                break
            except StopIteration:
                self._logger.debug(
                    f'Reached end of CSV; {self._reader.line_num} rows')
                break

            if self._reader.line_num % 100 == 0:
                self._logger.info(
                    f'Processed {self._reader.line_num} rows in source')

            clus, row_error = self._validate_csv_row(row)

            if row_error:
                error = True
            elif self._writer and isinstance(clus, pydantic.BaseModel):
                # Dump the model directly to the CSV writer.  The model's
                # serialization functions handle making each field CSV-ready.
                # If a field isn't dumping well, add a serializer to the model.
                # See `BaseCluster` for an example.
                self._writer.writerow(clus.model_dump())

        self._in_fp.close()
        try:
            # we handle the type inference issue with this try/except
            self._out_fp.close()  # type: ignore
        except AttributeError:
            pass

        if error:
            self._logger.info('CSV is invalid')
            if self._out_fp:
                # We had validation errors, so no need to keep the output CSV
                # file as it is incomplete
                self._logger.info(
                    "Encountered validation errors making output CSV "
                    "incomplete; deleting...")
                os.remove(self._out_fp.name)
            return -1

        self._logger.info("CSV is valid")
        return 0

    def _load_model_dynamic(self) \
            -> Optional[Type[pydantic.BaseModel]]:
        """If self.validator_module is set, this method attempts to dynamically
        load the module path with a call to `get_validator_module`.  It expects
        to find an attribute, specifically a class, by the name
        `SourceOfTruthModel` inside the loaded module.

        Returns:
            pydantic.BaseModel subclass as a dynamically loaded class from the
            provided validator module path or None if self.validator_module
            doesn't exist

        Raises:
            RuntimeError: if any issues were encountered dynamically loading the
            module and accessing its `SourceOfTruthModel` attribute
        """
        if not self._validator_module:
            return None

        self._logger.debug(
            f"Loading validator module '{self._validator_module}'")

        try:
            validator_mod = get_validator_module(self._validator_module)
        except RuntimeError as e:
            self._logger.exception(
                f'Error dynamically loading validator '
                f'{self._validator_module}. '
                f'Check filename/path.', exc_info=e)
            raise e

        model: Type[pydantic.BaseModel]
        try:
            model = validator_mod.SourceOfTruthModel
        except AttributeError as e:
            self._logger.exception(
                f'Error accessing "SourceOfTruthModel" from loaded module '
                f'({self._validator_module}). Ensure validator model contains '
                f'this class.', exc_info=e)
            raise RuntimeError("no attribute 'SourceOfTruthModel'") from e

        if not isinstance(model, type):
            self._logger.error(f'Dynamically loaded `SourceOfTruthModel` object'
                               f' from {self._validator_module} is not a class')
            raise RuntimeError('SourceOfTruthModel is not a class')

        return model

    def _validate_csv_fields(self) -> bool:
        """Validates the fields of a CSV and signals if required fields are
        not present

        Returns:
            bool: whether validation error in CSV fields was encountered
        """
        # Iterate over the expected/required fields from the model and alert
        # if any are missing in the CSV
        validation_error = False
        try:
            if not self._reader.fieldnames:
                self._logger.error('Missing CSV field names - is file empty?')
                raise RuntimeError('missing CSV field names')

            for name, field, in self._model.model_fields.items():
                if name not in self._reader.fieldnames:
                    if field.is_required() is False:
                        self._logger.warning(
                            f"Optional field '{name}' is not present in "
                            f"{self._in_fp.name}")
                    else:
                        validation_error = True
                        self._logger.error(
                            f"Required field '{name}' is not present in "
                            f"{self._in_fp.name}")
        except UnicodeDecodeError as e:
            self._logger.exception(
                'Unicode decoding issues parsing CSV fieldnames',
                exc_info=e)
            raise RuntimeError('unicode decode error') from e

        return validation_error

    def _validate_csv_row(self, row: dict[str, str]) \
            -> Tuple[Optional[pydantic.BaseModel], bool]:
        """Given a row from a CSV, validate it against the model

        Args:
            row: CSV row as a dict in the form of {field_name: value}

        Returns:
            tuple: (pydantic_model_object or None, validation_error)
        """
        try:
            # Validate the row against the model
            clus = self._model(**row)  # type: ignore
        except pydantic.ValidationError as e:
            # Oops, it didn't validate. Iterate over the validation errors
            # for each row and write some useful details to the self.logger.
            # Set validation_error to `True` so we know to exit with a non-0
            # status
            for pydantic_err in e.errors():
                c = f"cluster {row['cluster_name']}" if row.get(
                    'cluster_name') else 'cluster name unknown'
                self._logger.error(
                    f"Line {self._reader.line_num}, {c}, column '"
                    f"{pydantic_err['loc'][0]}', "
                    f"error: '{pydantic_err['msg']}', received '"
                    f"{pydantic_err['input']}'")
            return None, True
        except TypeError:
            self._logger.error(
                f'Line {self._reader.line_num}, {row['cluster_name']}, error: encountered '
                f'Python TypeError, this usually means the CSV is malformed; please check this '
                f'row for extra fields or syntax errors.')
            return None, True

        return clus, False

    def _setup_csv_writer(self) -> None:
        """If an output file is provided, use it, and set up the writer;
        otherwise, no-op.
        """
        if self._output:
            self._logger.debug(f"Using output file '{self._output.filename}'")
            try:
                self._out_fp = self._output.open()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self._logger.exception('Error opening output file', exc_info=e)
                raise RuntimeError('error opening file for writing') from e

            # uses the model's expected fields as the fields to use in the
            # output CSV
            self._writer = csv.DictWriter(
                self._out_fp, self._model.model_fields.keys(), dialect='excel')
            self._writer.writeheader()


def main() -> int:
    """Main entry point of the validator CLI - delegates CLI workflow and
    logic to CLI class.

    Returns:
        object: int exit code
    """
    args = parse_args()

    logger = setup_logger(args.verbose)

    cli = CLI(source=args.source, validator_module=args.validator_module,
              output=args.output, verbose=args.verbose, logger=logger)

    return cli.run()


if __name__ == '__main__':
    sys.exit(main())
