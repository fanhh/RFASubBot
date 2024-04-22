#!/bin/bash
# Start the first process
python3 bot.py &
# Start the second process
python3 background_worker.py &

# Wait for all processes to exit
wait

# Optionally, capture the exit status of all background processes
exit_status=$?
echo "Processes have exited with status $exit_status"

# Exit with the status of the last process to exit
exit $exit_status