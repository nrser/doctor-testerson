import sys
import logging

from .parser import get_args
from .project import iter_all_files
from .testing import test_targets, has_errors
from .output import print_header_panel, print_results, ERR

_LOG = logging.getLogger(__package__)


def main(argv: list[str] = sys.argv):
    logging.basicConfig(stream=sys.stderr)

    args = get_args(argv)

    if args.all:
        if args.targets:
            _LOG.warning("TARGETS ignored with --all")
        args.targets = list(iter_all_files())

    if args.panel is True:
        print_header_panel(args)

    results = test_targets(args)
    had_errors = has_errors(results)

    if args.fail_fast is True and had_errors:
        ERR.print("[red]Failed... FAST. 🏎 🏎[/]")
    else:
        print_results(results)

    sys.exit(1 if had_errors else 0)


if __name__ == "__main__":
    main()
