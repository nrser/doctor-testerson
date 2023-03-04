from argparse import Namespace
from functools import cached_property
from pathlib import Path
import doctest
from importlib import import_module
from dataclasses import dataclass
from time import monotonic_ns
from types import ModuleType

from pint import UnitRegistry, Quantity

U = UnitRegistry()

from .project import resolve_target


@dataclass(frozen=True)
class ModuleResult:
    target: str
    module_name: str
    module: ModuleType
    delta_t: Quantity
    tests: doctest.TestResults

    @cached_property
    def name(self) -> str:
        return self.module_name

    @cached_property
    def tests_passed(self) -> int:
        return self.tests.attempted - self.tests.failed


@dataclass(frozen=True)
class TextFileResult:
    target: str
    file_path: Path
    delta_t: Quantity
    tests: doctest.TestResults

    @cached_property
    def name(self) -> str:
        return str(self.file_path)

    @cached_property
    def tests_passed(self) -> int:
        return self.tests.attempted - self.tests.failed


Result = ModuleResult | TextFileResult


def now() -> Quantity:
    return monotonic_ns() * U.ns


def has_errors(results: list[Result]) -> bool:
    return any(result.tests.failed > 0 for result in results)


def test_targets(args: Namespace) -> list[Result]:
    results = []

    for target in args.targets:
        result = test_target(target, args)

        if (
            args.empty is None
            or (args.empty is True and result.tests.attempted == 0)
            or (args.empty is False and result.tests.attempted != 0)
        ):
            results.append(result)

            if args.fail_fast and result.tests.failed > 0:
                return results

    return results


def test_target(target, args: Namespace) -> Result:
    """
    #### Parameters ####

    -   `target` — one of:

        1.  A module name, such as `splatlog.splat_logger`.

        2.  A path to a Python file (`.py`), such as `splatlog/splat_logger.py`.

            This path may be relative to the current directory or absolute.

        3.  A path to a text file.
    """
    option_flags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS

    if args.fail_fast is True:
        option_flags = option_flags | doctest.FAIL_FAST

    resolution = resolve_target(target)

    if resolution[0] == "module":
        return test_module(target, resolution[1], option_flags)
    elif resolution[0] == "text_file":
        return test_text_file(target, resolution[1], option_flags)
    else:
        raise TypeError(
            f"Expected 'module' or 'text_file' test type, got {resolution[0]!r}"
        )


def test_module(target, module_name: str, option_flags: int) -> ModuleResult:
    module = import_module(module_name)

    t_start = now()
    results = doctest.testmod(module, optionflags=option_flags)
    delta_t = now() - t_start

    return ModuleResult(
        target=target,
        module_name=module_name,
        module=module,
        delta_t=delta_t,
        tests=results,
    )


def test_text_file(
    target, file_path: Path, option_flags: int
) -> TextFileResult:
    t_start = now()
    results = doctest.testfile(
        filename=str(file_path),
        optionflags=option_flags,
        module_relative=False,
    )
    delta_t = now() - t_start

    return TextFileResult(
        target=target,
        file_path=file_path,
        delta_t=delta_t,
        tests=results,
    )
