clear
while true; do
  FILE=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1).c
  ACTIONS=("Compiling" "Linking" "Building" "Installing" "Processing" "Scanning")
  STATUS=("OK" "DONE" "FAILED" "SKIPPED" "UPDATED")
  COLOR_GREEN="\e[32m"
  COLOR_RED="\e[31m"
  COLOR_YELLOW="\e[33m"
  COLOR_RESET="\e[0m"

  ACTION=${ACTIONS[$RANDOM % ${#ACTIONS[@]}]}
  STATUS_CHOICE=${STATUS[$RANDOM % ${#STATUS[@]}]}

  case $STATUS_CHOICE in
    OK|DONE|UPDATED) COLOR=$COLOR_GREEN ;;
    FAILED) COLOR=$COLOR_RED ;;
    *) COLOR=$COLOR_YELLOW ;;
  esac

  printf "%s %s ... [${COLOR}%s${COLOR_RESET}]\n" "$ACTION" "$FILE" "$STATUS_CHOICE"
  sleep $(awk -v min=0.1 -v max=0.7 'BEGIN{srand(); print min+rand()*(max-min)}')
done
