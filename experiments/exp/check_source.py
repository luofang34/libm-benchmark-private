"""Check shared data, unchanged pow arithmetic, and pinned Arm coefficients."""

import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from prepare import ARM_REVISION, BASE_REVISION, EXPERIMENT, REPOSITORY


def pinned(path):
    return subprocess.check_output(["git", "show", f"{BASE_REVISION}:{path}"], cwd=REPOSITORY).decode()


def table_bytes(source, name, width):
    body = source.split(f"{name}:", 1)[1].split("= [", 1)[1].split("];", 1)[0]
    values = [int(word, 16) for word in re.findall(r"0x[0-9a-fA-F]+", body)]
    assert len(values) == 128 * width
    return struct.pack(f"<{len(values)}Q", *values)


def main():
    overlay = EXPERIMENT / "overlay/libm/src/math"
    arm = REPOSITORY / "experiments/pow/vendor/optimized-routines"
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=arm, text=True).strip()
    assert revision == ARM_REVISION
    data = (overlay / "exp_shared/table.rs").read_text()
    baseline_table = pinned("libm/src/math/pow/table.rs")
    exp_data = table_bytes(data, "EXP_TAB", 2)
    assert exp_data == table_bytes(baseline_table, "EXP_TAB", 2)
    log_data = table_bytes((overlay / "pow/table.rs").read_text(), "LOG_TAB", 3)
    assert log_data == table_bytes(baseline_table, "LOG_TAB", 3)
    assert "static EXP_TAB" in data
    baseline_pow = pinned("libm/src/math/pow/exp.rs")
    candidate_pow = (overlay / "pow/exp.rs").read_text()
    assert candidate_pow.split("#[inline]", 1)[1] == baseline_pow.split("#[inline]", 1)[1]
    assert "use super::super::exp_shared::table::" in candidate_pow
    c_source = (arm / "math/exp_data.c").read_text()
    for rust_name, c_name, order in [("EXP_POLY", ".poly", "EXP"), ("EXP2_POLY", ".exp2_poly", "EXP2")]:
        c_body = c_source.split(f"{c_name} = {{", 1)[1]
        c_body = c_body.split(f"#elif N == 128 && {order}_POLY_ORDER == 5 && !{order}_POLY_WIDE", 1)[1].split("#elif", 1)[0]
        c_coefficients = [float.fromhex(value) for value in re.findall(r"0x[0-9a-f.]+p[+-]?\d+", c_body) if value != "0x1p-15"]
        rust_body = data.split(f"{rust_name}:", 1)[1].split("= [", 1)[1].split("];", 1)[0]
        rust_coefficients = [float(value.strip()) for value in rust_body.split(",") if value.strip()]
        assert rust_coefficients == c_coefficients
    files = {
        path.relative_to(EXPERIMENT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((EXPERIMENT / "overlay").rglob("*.rs"))
    }
    print(json.dumps({
        "base_revision": BASE_REVISION,
        "arm_revision": ARM_REVISION,
        "pow_arithmetic_unchanged": True,
        "exp_table_bytes": len(exp_data),
        "log_table_bytes": len(log_data),
        "exp_table_sha256": hashlib.sha256(exp_data).hexdigest(),
        "log_table_sha256": hashlib.sha256(log_data).hexdigest(),
        "arm_polynomial_coefficients_exact": True,
        "overlay_sha256": files,
    }, indent=2))


if __name__ == "__main__":
    main()
