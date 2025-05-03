#!/bin/bash
clear
while true; do
    echo "$(shuf -n 1 /usr/share/dict/words | tr -dc 'A-Za-z0-9' | fold -w 80 | head -n 1)"
    sleep 0.1
done
