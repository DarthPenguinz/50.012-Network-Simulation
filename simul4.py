import os

# Define the commands to run in new terminal windows, including the arguments

curr_dir = os.path.dirname(os.path.abspath(__file__))

general_commands = [
    "cd " + curr_dir,
    f"source {curr_dir}/virtualenvs/bin/activate"
]

# Sens id, frequency, send retries
# clusterid, send retries, send interval 
# server send interval, buffer size
commands = [
    'python3 sens.py 2 3 2',
    'python3 cluster.py 1 2 0.01',
    'python3 cluster.py 2 2 0.01',
    'python3 main.py 0.01 100'
]

# Open a new terminal window for each command
for cmd in commands:
    os.system(f"osascript -e 'tell app \"Terminal\" to do script \"{general_commands[0]} ; {general_commands[1]} ; {cmd}\"'")
    
