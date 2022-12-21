from argparse import ArgumentParser, Namespace
from functools import cached_property
from pathlib import Path
from typing import Any, List, Literal, Union
import sys
import doctest
from importlib import import_module
from dataclasses import dataclass
from time import monotonic_ns
from types import ModuleType

from rich.text import Text
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.tree import Tree
from rich.box import HEAVY

from pint import UnitRegistry

OUT = Console(file=sys.stdout)
ERR = Console(file=sys.stderr)

POETRY_FILENAME = "pyproject.toml"
SETUP_FILENAME = "setup.py"
UREG = UnitRegistry()
Qty = UREG.Quantity


@dataclass(frozen=True)
class ModuleResult:
    target: str
    module_name: str
    module: ModuleType
    delta_t: Qty
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
    delta_t: Qty
    tests: doctest.TestResults

    @cached_property
    def name(self) -> str:
        return str(self.file_path)

    @cached_property
    def tests_passed(self) -> int:
        return self.tests.attempted - self.tests.failed


def now() -> Qty:
    return Qty(monotonic_ns(), "ns")


def percent(numerator: float, denominator: float) -> Text:
    if denominator == 0:
        return Text("-", style="bright black")

    number = round((numerator / denominator) * 100)

    string = f"{number}%"

    if number == 100:
        return Text(string, style="bold green")
    return Text(string, style="bold red")


def build_parser():
    parser = ArgumentParser(prog="doctest", description="Doctest driver")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set logging verbosity",
    )
    parser.add_argument(
        "-f",
        "--fail-fast",
        action="store_true",
        help="Quit after first failure",
    )
    parser.add_argument(
        "-e",
        "--empty",
        dest="empty",
        action="store_true",
        default=None,
        help="Only show empty files (those with no doctests) in results",
    )
    parser.add_argument(
        "-E",
        "--no-empty",
        dest="empty",
        action="store_false",
        default=None,
        help="Hide empty files (those with no doctests) in results",
    )
    parser.add_argument(
        "-p",
        "--panel",
        action="store_true",
        default=False,
        help="Print an ostentatious header panel before running tests",
    )
    parser.add_argument(
        "targets", nargs="+", help="Specific module names or file paths to run"
    )
    return parser


def get_args(argv: List[str]) -> Namespace:
    return build_parser().parse_args(argv[1:])


def is_poetry_root(dir: Path) -> bool:
    return (dir / POETRY_FILENAME).is_file()


def is_setup_py_root(dir: Path) -> bool:
    return (dir / SETUP_FILENAME).is_file() and not (
        dir / "__init__.py"
    ).is_file()


def is_package_root(dir: Path) -> bool:
    return is_poetry_root(dir) or is_setup_py_root(dir)


def to_module_name(file_path: Path) -> str:
    dir = file_path.parent
    while True:
        if is_package_root(dir):
            break
        if dir.parent == dir:
            raise Exception(
                f"Failed to find poetry file {POETRY_FILENAME} in "
                + f"ancestors of path {file_path}"
            )
        dir = dir.parent

    rel_path = file_path.relative_to(dir)
    return ".".join((rel_path.parent / rel_path.stem).parts)


def resolve_target(
    target: str,
) -> tuple[Literal["module"], str] | tuple[Literal["text_file"], Path]:
    path = Path(target).resolve()

    if not path.exists():
        return ("module", target)

    if not path.is_file():
        raise Exception(
            f"Expected `target` paths to be files, given {target!r}"
        )

    if path.suffix == ".py":
        return ("module", to_module_name(path))

    return ("text_file", path)


def test_targets(args: Namespace) -> list[Union[ModuleResult, TextFileResult]]:
    results = []

    for target in args.targets:
        result = test_target(target, args)

        if (
            args.empty is None
            or (args.empty is True and result.tests.attempted == 0)
            or (args.empty is False and result.tests.attempted != 0)
        ):
            results.append(result)

    return results


def test_target(target, args: Namespace) -> Union[ModuleResult, TextFileResult]:
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


def format_delta_t(delta_t: Qty, units: Any = "ms") -> str:
    return f"{delta_t.to(units):.2f~P}"


def has_errors(results) -> bool:
    return any(result.tests.failed > 0 for result in results)


def print_header_panel(args: Namespace) -> None:
    cwd = Path.cwd()
    tree = Tree(
        Text("Dr. T! These files need your help!", style=Style(italic=True))
    )

    for target in args.targets:
        try:
            item = str(Path(target).relative_to(cwd))
        except ValueError:
            item = target
        tree.add(item)

    OUT.print(
        Panel(
            tree,
            title=Text(
                "+++ Dr. Testerson +++",
                style=Style(bold=True),
            ),
            title_align="center",
            box=HEAVY,
            style=Style(color="black", bgcolor="red"),
        )
    )


def main(argv: List[str] = sys.argv):
    args = get_args(argv)

    if args.panel is True:
        print_header_panel(args)

    results = test_targets(args)

    if args.fail_fast is True and has_errors(results):
        ERR.print("[red]Failed... FAST. 🏎 🏎[/]")
        sys.exit(1)

    table = Table(title="Doctest Results")
    table.expand = True

    table.add_column("test")
    table.add_column("Δt", justify="right")
    table.add_column(Text("passed", style="bold green"), justify="right")
    table.add_column(Text("failed", style="bold red"), justify="right")
    table.add_column("%", justify="right")

    for result in sorted(results, key=lambda r: r.name):
        table.add_row(
            result.name,
            format_delta_t(result.delta_t),
            str(result.tests_passed),
            str(result.tests.failed),
            percent(
                result.tests_passed,
                result.tests.attempted,
            ),
        )

    # Add an empty row at the bottom with a line under it visually separate
    # the summary row
    table.add_row(None, None, None, None, None, end_section=True)

    total_delta_t: Qty = Qty(0, "ms")
    total_attempted: int = 0
    total_passed: int = 0
    total_failed: int = 0

    for result in results:
        total_delta_t += result.delta_t
        total_attempted += result.tests.attempted
        total_passed += result.tests_passed
        total_failed += result.tests.failed

    table.add_row(
        "[bold]Total[/]",
        format_delta_t(total_delta_t),
        str(total_passed),
        str(total_failed),
        percent(
            total_passed,
            total_attempted,
        ),
    )

    OUT.print(table)
