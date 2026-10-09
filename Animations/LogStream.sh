#!/bin/bash
# cliss: An endless stream of fake service logs
clear
while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    LEVELS=("INFO" "WARN" "ERROR" "DEBUG")
    MSGS=("Starting service" "Connection successful" "Retrying..." "Timeout occurred" "Initialization complete")
    LEVEL=${LEVELS[$RANDOM % ${#LEVELS[@]}]}
    MSG=${MSGS[$RANDOM % ${#MSGS[@]}]}
    echo "$TIMESTAMP [$LEVEL] $MSG"
    sleep 0.5
done
