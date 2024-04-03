import os

# Define the commands to run in new terminal windows, including the arguments

curr_dir = os.path.dirname(os.path.abspath(__file__))

general_commands = [
    "cd " + curr_dir,
    f"source {curr_dir}/virtualenvs/bin/activate"
]

commands = [
    'python3 sens.py 1 3',
    'python3 sens.py 2 5',
    'python3 sens.py 3 7',
    'python3 host.py 1',
    'python3 host.py 2',
    'python3 main.py 10'
]

# Open a new terminal window for each command
for cmd in commands:
    os.system(f"osascript -e 'tell app \"Terminal\" to do script \"{general_commands[0]} ; {general_commands[1]} ; {cmd}\"'")
    
