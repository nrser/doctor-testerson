from argparse import Namespace
from pathlib import Path
from typing import Any
import sys

from rich.text import Text
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.tree import Tree
from rich.box import HEAVY
from rich.padding import Padding

from pint import Quantity

from .testing import Result, U

OUT = Console(file=sys.stdout)
ERR = Console(file=sys.stderr)


def percent(numerator: float, denominator: float) -> Text:
    if denominator == 0:
        return Text("-", style="bright black")

    number = round((numerator / denominator) * 100)

    string = f"{number}%"

    if number == 100:
        return Text(string, style="bold green")
    return Text(string, style="bold red")


def format_delta_t(delta_t: Quantity, units: Any = "ms") -> str:
    return f"{delta_t.to(units):.2f~P}"


def print_header_panel(args: Namespace) -> None:
    cwd = Path.cwd()
    tree = Tree(
        Text(
            "Dr. T! These files need your help!",
            style=Style(color="black", italic=True),
        ),
        guide_style=Style(color="black"),
    )

    if args.all:
        tree.add(
            Text.assemble(
                ("ALL", Style(bold=True)),
                f" ({len(args.targets)} files)",
                style=Style(color="black"),
            ),
        )
    else:
        for target in args.targets:
            try:
                item = Path(target).relative_to(cwd)
            except ValueError:
                item = target
            tree.add(Text(str(item), style=Style(color="black")))

    OUT.print(
        Padding(
            Panel(
                Group(tree),
                title=Text(
                    "+ Dr. Testerson +",
                    style=Style(color="white", bold=True),
                ),
                title_align="center",
                box=HEAVY,
                style=Style(bgcolor="red"),
            ),
            (1, 0),
        )
    )


def print_results(results: list[Result]) -> None:
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

    total_delta_t = 0 * U.ms
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
