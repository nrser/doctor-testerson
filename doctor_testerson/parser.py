from argparse import ArgumentParser, Namespace
from pathlib import Path


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
        "--only-empty",
        dest="empty",
        action="store_true",
        default=None,
        help="Only show empty files (those with no doctests) in results",
    )
    parser.add_argument(
        "-E",
        "--hide-empty",
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
        "-a",
        "--all",
        action="store_true",
        default=False,
        help="Test all package and doc files",
    )
    parser.add_argument(
        "targets",
        type=Path,
        nargs="*",
        default=[],
        help="Specific module names or file paths to run",
    )
    return parser


def get_args(argv: list[str]) -> Namespace:
    return build_parser().parse_args(argv[1:])
