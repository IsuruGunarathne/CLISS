#!/bin/bash
# cliss: A looping progress bar
clear
while true; do
    for i in {1..50}; do
        printf "\r[%-50s] %d%%" $(printf '#%.0s' $(seq 1 $i)) $((2*$i))
        sleep 0.05
    done
    echo
    sleep 1
done
