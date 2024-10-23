
import os

# Change the working directory to iBot/
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
print(f"Current working directory: {os.getcwd()}")