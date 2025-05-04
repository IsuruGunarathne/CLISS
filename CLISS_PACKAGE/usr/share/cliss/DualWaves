#!/bin/bash

clear
t=0
cols=$(tput cols)
rows=$(tput lines)
amplitude=$((rows / 4))
frequency=0.05
speed=0  # Set to 0 for static, >0 for slow motion

while true; do
    clear
    for ((x = 0; x < cols; x++)); do
        # First wave
        y1=$(awk -v x="$x" -v t="$t" -v a="$amplitude" -v f="$frequency" 'BEGIN {
            print int(a * sin(f * x + t));
        }')
        
        # Second wave with slight phase shift
        y2=$(awk -v x="$x" -v t="$t" -v a="$amplitude" -v f="$frequency" 'BEGIN {
            print int(a * sin(f * x + t + 3.14));  # Phase shift of pi (180 degrees)
        }')

        # Draw both waves
        row1=$(( (rows / 2) + y1 ))
        row2=$(( (rows / 2) + y2 ))

        tput cup "$row1" "$x"
        printf "~"

        tput cup "$row2" "$x"
        printf "*"

        sleep 0.001  # Smooth drawing
    done

    t=$(awk -v t="$t" -v s="$speed" 'BEGIN { print t + s }')
    sleep 0.05
done
