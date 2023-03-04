from pathlib import Path
from typing import Generator, Iterable, Literal
import tomli

POETRY_FILENAME = "pyproject.toml"
SETUP_FILENAME = "setup.py"


def iter_py_files_from_packages(
    packages: list[dict],
) -> Generator[Path, None, None]:
    for index, package in enumerate(packages):
        match package:
            case {"include": include, "from": from_}:
                # I guess..?
                glob = f"{from_}/{include}"
            case {"include": include}:
                glob = include
            case _:
                raise ValueError(
                    "unexpected value for {}:packages[{}] = {!r}".format(
                        POETRY_FILENAME,
                        index,
                        package,
                    )
                )

        for path in Path(".").glob(glob):
            if path.is_dir():
                yield from path.glob("**/*.py")
            elif path.suffix == ".py":
                yield path


def iter_py_files() -> Generator[Path, None, None]:
    with Path(POETRY_FILENAME).open("rb") as file:
        py_project = tomli.load(file)

    match py_project:
        case {"tool": {"poetry": {"packages": packages}}}:
            yield from iter_py_files_from_packages(packages)
        case {"tool": {"poetry": {"name": str(name)}}}:
            for path in (Path("src", name), Path(name)):
                if path.is_dir():
                    yield from path.glob("**/*.py")


def list_py_files() -> list[Path]:
    return list(iter_py_files())


def iter_doc_files() -> Iterable[Path]:
    return Path(".").glob("docs/content/**/*.md")


def iter_all_files() -> Iterable[Path]:
    yield from iter_py_files()
    yield from iter_doc_files()


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
