import os
import sys

def set_root_directory(root_dir_name='iBot'):
    # Get the directory of the current script
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Navigate up until we find the root directory
    root_dir = current_dir
    while os.path.basename(root_dir) != root_dir_name:
        parent = os.path.dirname(root_dir)
        if parent == root_dir:  # We've reached the top without finding the root_dir_name
            raise Exception(f"Could not find root directory '{root_dir_name}'")
        root_dir = parent
    
    # Change the current working directory to the root
    os.chdir(root_dir)
    
    # Add root directory to the Python path
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    print(f"Working directory set to: {os.getcwd()}")

# Example usage
if __name__ == "__main__":
    set_root_directory('iBot')
