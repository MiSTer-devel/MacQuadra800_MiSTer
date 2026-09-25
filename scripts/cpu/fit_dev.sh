#!/usr/bin/env bash
# Generic archived fit of whatever is promoted in this checkout: fit_dev.sh <tag>.
# Records the core/cache/pipeline hashes, freezes and re-checks every tracked input,
# archives fresh reports, the rbf and the cross-domain timing under scratch/<tag>_fit_<date>/.
set -u
repo=/home/alans/mister/MacQuadra800_MiSTer
tag="${1:?tag}"
fit_out="$repo/scratch/${tag}_fit_$(date +%Y%m%d)"
cd "$repo" || exit 1

# User 2026-09-24: independent projects may run concurrently; never kill them.
# Preserve exclusive ownership of this checkout, including report generation.
exec 9>"$repo/.git/archived-fit.lock"
flock -n 9 || { echo 'Another archived Mac fit owns this checkout.' >&2; exit 3; }
build_args=()
if [[ "${2:-}" == --allow-other-projects ]]; then
  python3 - "$repo" <<'CHECK_PROCESSES'
import pathlib, sys
repo = pathlib.Path(sys.argv[1]).resolve()
for proc in pathlib.Path('/proc').iterdir():
    if not proc.name.isdigit(): continue
    try:
        if not (proc / 'comm').read_text().strip().startswith('quartus_'): continue
        cmd = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
        if (proc / 'cwd').resolve() == repo or 'MacQuadra800' in cmd:
            sys.exit('Mac Quartus process already active: ' + proc.name + ' ' + cmd)
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
CHECK_PROCESSES
  [[ $? -eq 0 ]] || exit 3
  build_args=(--no-wait)
elif pgrep -x 'quartus_.*' >/dev/null 2>&1; then
  echo 'Quartus process active; use --allow-other-projects only with authorization.' >&2
  exit 3
fi
if [[ -e "$fit_out/start.stamp" ]]; then
  echo "Refusing to reuse an existing fit directory: $fit_out" >&2
  exit 4
fi
mkdir -p "$fit_out"
{ grep -E '^(set_global_assignment -name VERILOG_MACRO|source configs/)' MacQuadra800.qsf; cat configs/cpu_release_lite.tcl configs/cpu_development.tcl; } > "$fit_out/FEATURES.txt"
fit_commit=$(git rev-parse HEAD)
printf '%s\n' "$fit_commit" > "$fit_out/commit.txt"

actual_cache=$(sha256sum rtl/ap68040/rtl/ap040_cache.v | cut -d' ' -f1)
actual_core=$(sha256sum rtl/ap68040/rtl/ap040_core.v | cut -d' ' -f1)
actual_pipe=$(sha256sum rtl/ap68040/experimental/ap040_pipeline_integer.sv | cut -d' ' -f1)
seed=$(grep -E '^set_global_assignment -name SEED' MacQuadra800.qsf | awk '{print $4}')
printf '%s\n' "core=$actual_core pipeline=$actual_pipe cache=$actual_cache seed=$seed (active profile recorded in FEATURES.txt)" > "$fit_out/IDENTITY_CHECK.txt"
# Burn the run stamp only after all identity and configuration checks pass.
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$fit_out/start.stamp"

# Freeze every tracked HDL/QSF/QIP/SDC input before the flow and compare the
# same complete manifest after all Quartus/STA/report work.
git ls-files -z '*.v' '*.sv' '*.qip' '*.qsf' '*.sdc' '*.tcl' | xargs -0 sha256sum > "$fit_out/tracked_before.sha256"
cp "$fit_out/tracked_before.sha256" "$fit_out/tracked.sha256"
sha256sum -c "$fit_out/tracked_before.sha256" > "$fit_out/source_check_before.log" 2>&1
before_rc=$?
printf '%s\n' "$before_rc" > "$fit_out/source_check_before.exit"
if [[ "$before_rc" -ne 0 ]]; then exit 2; fi

copy_fresh() {
  local src="$1" dst="$2"
  if [[ -f "$src" && "$src" -nt "$fit_out/start.stamp" ]]; then
    cp "$src" "$dst"
  fi
}

# Build in the current checkout. Keep going after failure so fresh map/fit/STA
# reports are still archived and every exit status is recorded.
set +e
bash scripts/build_only.sh "${build_args[@]}" > "$fit_out/build.log" 2>&1
build_rc=$?
printf '%s\n' "$build_rc" > "$fit_out/build.exit"

for f in MacQuadra800.map.rpt MacQuadra800.map.summary MacQuadra800.fit.rpt MacQuadra800.fit.summary MacQuadra800.sta.rpt MacQuadra800.sta.summary MacQuadra800.asm.rpt MacQuadra800.asm.summary; do
  copy_fresh "output_files/$f" "$fit_out/$f"
done

# Only a newly assembled RBF may be archived; include the source commit in its
# name to prevent an old artifact from being mistaken for this fit.
if [[ -f output_files/MacQuadra800.rbf && output_files/MacQuadra800.rbf -nt "$fit_out/start.stamp" ]]; then
  rbf="$fit_out/MacQuadra800_${tag}_${fit_commit:0:7}.rbf"
  cp output_files/MacQuadra800.rbf "$rbf"
  sha256sum "$rbf" > "$fit_out/rbf.sha256"
fi

# Run timing reports from this same project checkout only after a fresh,
# successful fitter summary exists. Never run STA against a stale or partial DB.
fit_summary=output_files/MacQuadra800.fit.summary
fit_ready=0
if [[ -f "$fit_summary" && "$fit_summary" -nt "$fit_out/start.stamp" ]] && \
   grep -Eiq 'status[^[:alnum:]]*:.*successful|fitter.*successful|successful.*fitter|full compilation.*successful' "$fit_summary"; then
  fit_ready=1
fi
. scripts/local.env
if [[ "$fit_ready" -eq 1 && -n "${QUARTUS_BIN:-}" ]]; then
  "$QUARTUS_BIN/quartus_sta" -t scripts/cpu/timequest_cross_domain.tcl ${tag} > "$fit_out/cross.log" 2>&1
  cross_rc=$?
  "$QUARTUS_BIN/quartus_sta" -t scripts/cpu/timequest_worst_paths.tcl "$fit_out/cpu_timing" > "$fit_out/cpu_timing.log" 2>&1
  cpu_rc=$?
elif [[ "$fit_ready" -eq 0 ]]; then
  cross_rc=77; cpu_rc=77
  echo 'SKIPPED: fresh MacQuadra800.fit.summary with successful fitter status not present; stale/partial STA forbidden.' > "$fit_out/cross.log"
  echo 'SKIPPED: fresh MacQuadra800.fit.summary with successful fitter status not present; stale/partial STA forbidden.' > "$fit_out/cpu_timing.log"
else
  cross_rc=127; cpu_rc=127
  echo 'SKIPPED: QUARTUS_BIN missing.' > "$fit_out/cross.log"
  echo 'SKIPPED: QUARTUS_BIN missing.' > "$fit_out/cpu_timing.log"
fi
printf '%s\n' "$cross_rc" > "$fit_out/cross.exit"
printf '%s\n' "$cpu_rc" > "$fit_out/cpu_timing.exit"

# Cross-domain TCL writes these exact files under the current checkout's scratch.
copy_fresh scratch/cross_sys2ram_${tag}.txt "$fit_out/cross_sys2ram.txt"
copy_fresh scratch/cross_ram2sys_${tag}.txt "$fit_out/cross_ram2sys.txt"
copy_fresh "$fit_out/cpu_timing/worst_paths.txt" "$fit_out/worst_paths.txt"
copy_fresh "$fit_out/cpu_timing/worst_detail.txt" "$fit_out/worst_detail.txt"
grep -E -n 'RAM|M10K|ALM|Total registers|slack|Slack|Critical Warning|Error' "$fit_out"/*.rpt "$fit_out"/*.summary "$fit_out"/worst_*.txt > "$fit_out/resource_timing_extract.txt" 2>/dev/null || true

# Verify the complete tracked-input manifest after the entire flow, including
# report generation. A changed tracked HDL/QSF/QIP/SDC file fails the fit.
git ls-files -z '*.v' '*.sv' '*.qip' '*.qsf' '*.sdc' '*.tcl' | xargs -0 sha256sum > "$fit_out/tracked_after.sha256"
if cmp -s "$fit_out/tracked_before.sha256" "$fit_out/tracked_after.sha256"; then
  after_rc=0
else
  after_rc=1
fi
printf '%s\n' "$after_rc" > "$fit_out/source_check_after.exit"
if [[ "$after_rc" -eq 0 ]]; then
  echo 'tracked HDL/QSF/QIP/SDC unchanged across complete flow' > "$fit_out/source_check_after.log"
else
  echo 'tracked HDL/QSF/QIP/SDC changed during complete flow' > "$fit_out/source_check_after.log"
  diff -u "$fit_out/tracked_before.sha256" "$fit_out/tracked_after.sha256" > "$fit_out/source_check_after.diff" || true
fi
set -e

# Preserve the build result while making the safety checks visible to callers.
if [[ "$build_rc" -ne 0 || "$cross_rc" -ne 0 || "$cpu_rc" -ne 0 || "$after_rc" -ne 0 ]]; then
  exit 1
fi
exit 0
