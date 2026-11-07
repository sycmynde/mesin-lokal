#!/data/data/com.termux/files/usr/bin/bash

MESIN="$HOME/mesin"
PIDFILE="$MESIN/nav/.trip_tracker.pid"
LOG="$MESIN/nav/.trip_tracker.log"

case "$1" in

start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "🟢 Trip Tracker sudah aktif (PID $(cat "$PIDFILE"))"
        exit 0
    fi

    cd "$MESIN" || exit 1

    nohup env PYTHONPATH="$MESIN" \
        "$MESIN/tools/trip_tracker.sh" \
        >> "$LOG" 2>&1 &

    PID=$!
    echo "$PID" > "$PIDFILE"

    echo "🚴 Trip Tracker dimulai."
    echo "   PID: $PID"
    ;;

stop)
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")

        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            echo "🛑 Trip Tracker dihentikan."
        else
            echo "⚪ Trip Tracker tidak aktif."
        fi

        rm -f "$PIDFILE"
    else
        echo "⚪ Trip Tracker tidak aktif."
    fi
    ;;

status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "🟢 Trip Tracker aktif (PID $(cat "$PIDFILE"))"
    else
        echo "⚪ Trip Tracker tidak aktif."
    fi
    ;;

*)
    echo "Pakai: $0 {start|stop|status}"
    ;;
esac
