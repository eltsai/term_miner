import yaml
import os

from utils import read_file_contents
    
    
####################################
# Load config file
####################################
def read_ymal_file(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_measurement_config(file_path='./configs/measurement.yaml'):
    config = read_ymal_file(file_path)
    return config

p = load_measurement_config()
print(f"Reading API key from {p['openai']['api_key_loc']}...")
api_key = read_file_contents(p['openai']['api_key_loc'])

def create_dirs(p):
    dir_names = [v for k, v in p['file_loc'].items() if 'dir' in k]
    for dir_name in dir_names:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"Created directory: {dir_name}")
            
create_dirs(p)