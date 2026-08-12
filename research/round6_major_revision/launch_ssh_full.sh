#!/usr/bin/env bash
set -u

cd /home/lyy/ucc_paper_round6_20260712 || exit 2
mkdir -p research/round6_major_revision/logs

export XDG_CONFIG_HOME=/tmp/round6-xdg-config
export XDG_CACHE_HOME=/tmp/round6-xdg-cache
export MPLCONFIGDIR=/tmp/round6-mplconfig

./.venv/bin/python research/round6_major_revision/run_round6_experiments.py \
  --full --timeout-s 600 \
  > research/round6_major_revision/logs/ssh_full_600s.log 2>&1
status=$?

{
  printf 'full_status=%s\n' "$status"
  printf 'finished_at=%s\n' "$(date --iso-8601=seconds)"
} > research/round6_major_revision/logs/ssh_full_exit_status.txt

exit "$status"
