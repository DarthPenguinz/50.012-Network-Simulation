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
    'python3 sens.py 13 3 2',
    'python3 sens.py 14 3 2',
    'python3 sens.py 15 3 2',
    'python3 sens.py 16 3 2',
    'python3 sens.py 17 3 2',
    'python3 sens.py 18 3 2',
    'python3 sens.py 19 3 2',
    'python3 sens.py 20 3 2',
    'python3 sens.py 21 3 2',
    'python3 sens.py 22 3 2',
    'python3 sens.py 23 3 2',
    'python3 sens.py 24 3 2',
    'python3 sens.py 25 3 2',
    'python3 sens.py 26 3 2',
    'python3 sens.py 27 3 2',
    'python3 sens.py 28 3 2',
    'python3 sens.py 29 3 2',
    'python3 sens.py 30 3 2',
    'python3 sens.py 31 3 2',
    'python3 sens.py 32 3 2',
    'python3 sens.py 33 3 2',
    'python3 sens.py 34 3 2',
    'python3 sens.py 35 3 2',
    'python3 sens.py 36 3 2',
    'python3 sens.py 37 3 2',
    'python3 sens.py 38 3 2',
    'python3 sens.py 39 3 2',
    'python3 sens.py 40 3 2',
    'python3 sens.py 41 3 2',
    'python3 sens.py 42 3 2',
    'python3 sens.py 43 3 2',
    'python3 sens.py 44 3 2',
    'python3 sens.py 45 3 2',
    'python3 sens.py 46 3 2',
    'python3 sens.py 47 3 2',
    'python3 sens.py 48 3 2',
    'python3 sens.py 49 3 2',
    'python3 sens.py 50 3 2',
    'python3 sens.py 51 3 2',
    'python3 sens.py 52 3 2',
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
    
