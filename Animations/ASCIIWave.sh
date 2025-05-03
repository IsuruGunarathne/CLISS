#!/bin/bash
clear
PHASE=0
while true; do
    let "PHASE+=1"
    for i in $(seq 0 70); do
        POS=$(( ( (i + PHASE) % 20 ) ))
        printf "%*s\n" "$POS" "~"
    done
    sleep 0.02
    clear
done
