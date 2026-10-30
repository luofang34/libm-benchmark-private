#!/bin/bash
set -euo pipefail
unset CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_RUNNER
rustc -vV
valgrind --version
lscpu
result=0
for revision in upstream-base candidate; do
  for arch in disabled enabled; do
    extra=()
    if [ "$arch" = enabled ]; then extra=(--features arch); fi
    cd "/$revision"
    cargo bench --target aarch64-unknown-linux-gnu --bench '*icount*' \
      --no-default-features --features 'unstable unstable-float icount' \
      --features compiler_builtins/unmangled-names "${extra[@]}" -- \
      --home /evidence/gungraun-home --callgrind-limits=ir=5.0% \
      --save-summary --save-baseline="arch_$arch" 2>&1 |
      tee "/evidence/$revision-$arch.log" || result=1
  done
done
cargo clean
exit "$result"
