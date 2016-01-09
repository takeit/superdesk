#!/bin/bash
script_dir=$(readlink -e $(dirname "$0"))

tmux new-session -s vpp || true

sn=$(tmux display-message -p "#S")

tmux new-window -n "docker" -c $script_dir
tmux new-window -n "client" -c $script_dir/client
tmux new-window -n "server" -c $script_dir/server
