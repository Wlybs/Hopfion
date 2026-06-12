#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY="$SCRIPT_DIR/simulation_quiet_hours.py"
POLL_SECONDS="${QUIET_HOURS_POLL_SECONDS:-10}"

usage() {
    printf 'usage: %s --mx3 FILE --table FILE -- COMMAND [ARG ...]\n' "$0" >&2
    exit 2
}

mx3=""
table=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mx3)
            [[ $# -ge 2 ]] || usage
            mx3="$2"
            shift 2
            ;;
        --table)
            [[ $# -ge 2 ]] || usage
            table="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            usage
            ;;
    esac
done
[[ -n "$mx3" && -n "$table" && $# -gt 0 ]] || usage

wait_until_start_allowed() {
    while [[ "$(python3 "$POLICY" start-action)" != "start" ]]; do
        local remaining sleep_for
        remaining="$(python3 "$POLICY" seconds-until-start)"
        sleep_for=60
        if (( remaining < sleep_for )); then
            sleep_for="$remaining"
        fi
        if (( sleep_for < 1 )); then
            sleep_for=1
        fi
        printf '[quiet-hours] New Mumax run waits until 03:00 Asia/Singapore (%ss remaining).\n' \
            "$remaining"
        sleep "$sleep_for"
    done
}

wait_until_start_allowed
started_at="$(TZ=Asia/Singapore date --iso-8601=seconds)"
"$@" &
child_pid=$!

forward_signal() {
    local signal="$1"
    kill "-$signal" "$child_pid" 2>/dev/null || true
}
trap 'forward_signal TERM' TERM
trap 'forward_signal INT' INT

while true; do
    state="$(ps -o state= -p "$child_pid" 2>/dev/null | tr -d ' ' || true)"
    if [[ -z "$state" || "$state" == "Z" ]]; then
        break
    fi
    action="$(python3 "$POLICY" running-action \
        --started "$started_at" --mx3 "$mx3" --table "$table")"
    if [[ "$action" == "pause" ]]; then
        if ! kill -STOP "$child_pid" 2>/dev/null; then
            continue
        fi
        printf '[quiet-hours] Mumax PID %s paused; resume boundary is 03:00 Asia/Singapore.\n' \
            "$child_pid"
        wait_until_start_allowed
        kill -CONT "$child_pid" 2>/dev/null || true
        printf '[quiet-hours] Mumax PID %s resumed.\n' "$child_pid"
    fi
    sleep "$POLL_SECONDS"
done

set +e
wait "$child_pid"
exit_code=$?
set -e
exit "$exit_code"
