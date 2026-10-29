; ModuleID = 'pow_probe.dd43e78a8975eb2a-cgu.0'
source_filename = "pow_probe.dd43e78a8975eb2a-cgu.0"
target datalayout = "e-m:e-p:32:32-p10:8:8-p20:8:8-i64:64-i128:128-n32:64-S128-ni:1:10:20"
target triple = "wasm32-unknown-unknown"

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define dso_local noundef double @power(double noundef %x, double noundef %y) unnamed_addr #0 !guid !1 {
start:
  %_0 = tail call double @llvm.pow.f64(double %x, double %y)
  ret double %_0
}

; Function Attrs: mustprogress nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none)
declare double @llvm.pow.f64(double, double) #1

attributes #0 = { mustprogress nofree norecurse nosync nounwind willreturn memory(none) "target-cpu"="generic" }
attributes #1 = { mustprogress nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none) }

!llvm.ident = !{!0}

!0 = !{!"rustc version 1.99.0 (b940084d7 2026-09-28)"}
!1 = !{i64 -1905331015238824606}
