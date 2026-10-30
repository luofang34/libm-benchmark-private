"""Export the pinned pow-only libm, optionally applying the exp/exp2 overlay."""

import argparse
import difflib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

BASE_REVISION = "ef357e6075c6d7eca9d2fd72412e43fb5fc1a5ff"
ARM_REVISION = "2ee4b0d45680a9880412c1d186224b08652c35f6"
EXPERIMENT = Path(__file__).resolve().parent
REPOSITORY = EXPERIMENT.parent.parent


def source_files(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "libm").rglob("*"))
        if path.is_file()
    }


def apply_overlay(destination):
    math = destination / "libm/src/math"
    for function in ("exp", "exp2"):
        shutil.copyfile(math / f"{function}.rs", math / f"{function}_fdlibm.rs")
    shutil.copytree(EXPERIMENT / "overlay", destination, dirs_exist_ok=True)
    module = math / "mod.rs"
    source = module.read_text()
    start = source.index("#[cfg_attr(", source.index("// Keep table costs"))
    stop = source.index("mod pow;", start) + len("mod pow;")
    selection = source[start:stop]
    predicate_start = selection.index("not(") + len("not(")
    predicate_stop = selection.index("),\n    path")
    predicate = selection[predicate_start:predicate_stop].replace("\n    ", "\n")
    for function in ("exp", "exp2"):
        replacement = selection.replace("pow_fdlibm.rs", f"{function}_fdlibm.rs")
        replacement = replacement.replace("mod pow;", f"mod {function};")
        source = source.replace(f"mod {function};", replacement, 1)
    source = source.replace("// Private modules", f"#[cfg({predicate})]\nmod exp_shared;\n\n// Private modules", 1)
    module.write_text(source)


def write_patch(before, after, destination):
    chunks = []
    for path in sorted(before.keys() | after.keys()):
        previous = before.get(path, b"")
        current = after.get(path, b"")
        if previous == current:
            continue
        chunks.append(f"diff --git a/{path} b/{path}\n")
        if path not in before:
            chunks.append("new file mode 100644\n")
        elif path not in after:
            chunks.append("deleted file mode 100644\n")
        chunks.extend(difflib.unified_diff(
            previous.decode().splitlines(keepends=True),
            current.decode().splitlines(keepends=True),
            fromfile=f"a/{path}" if path in before else "/dev/null",
            tofile=f"b/{path}" if path in after else "/dev/null",
        ))
    destination.write_text("".join(chunks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--variant", choices=("base", "candidate"), default="candidate")
    parser.add_argument("--patch", type=Path, help="Also write an applicable unified patch")
    args = parser.parse_args()
    if args.destination.exists() and any(args.destination.iterdir()):
        parser.error("destination must be absent or empty")
    args.destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(
        ["git", "archive", BASE_REVISION, "libm", ".rustfmt.toml"], cwd=REPOSITORY
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(args.destination, filter="data")
    before = source_files(args.destination)
    if args.variant == "candidate":
        apply_overlay(args.destination)
    after = source_files(args.destination)
    if args.patch:
        write_patch(before, after, args.patch)
    manifest = {
        "base_revision": BASE_REVISION,
        "arm_revision": ARM_REVISION,
        "variant": args.variant,
        "source_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in after.items()},
    }
    (args.destination / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(args.destination.resolve())


if __name__ == "__main__":
    main()
