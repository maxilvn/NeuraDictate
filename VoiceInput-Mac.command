#!/bin/zsh
# Launch NeuraDictate fully headless — no terminal visible
DIR="$(cd "$(dirname "$0")" && pwd -P)"
nohup python3 "$DIR/start.py" </dev/null >/dev/null 2>&1 &
disown
# Close this terminal window immediately
osascript -e 'tell application "Terminal"
    if (count of windows) > 0 then
        close front window
    end if
end tell' &>/dev/null &
exit 0
