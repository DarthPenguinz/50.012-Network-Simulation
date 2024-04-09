import os

# Define the commands to run in new terminal windows, including the arguments

curr_dir = os.path.dirname(os.path.abspath(__file__))

general_commands = [
    "cd " + curr_dir,
    f"source {curr_dir}/virtualenvs/bin/activate"
]

commands = [
    'python3 sens.py 3 3 2',
    'python3 sens.py 4 3 2',
    'python3 sens.py 5 3 2',
    'python3 sens.py 6 3 2',
    'python3 sens.py 7 3 2',
    'python3 sens.py 8 3 2',
    'python3 sens.py 9 3 2',
    'python3 sens.py 10 3 2',
    'python3 sens.py 11 3 2',
    'python3 sens.py 12 3 2',
    'python3 cluster.py 1 2 0.01',
    'python3 cluster.py 2 2 0.01',
    'python3 cluster.py 3 2 0.01',
    'python3 cluster.py 4 2 0.01',
    'python3 cluster.py 5 2 0.01',
    'python3 main.py 0.01 100'
]

# Open a new terminal window for each command
for cmd in commands:
    os.system(f"osascript -e 'tell app \"Terminal\" to do script \"{general_commands[0]} ; {general_commands[1]} ; {cmd}\"'")
    
