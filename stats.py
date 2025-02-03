# load config from config.py
from config import load_measurement_config 
from glob import glob
import ast
import pandas as pd


p = load_measurement_config()
####################################
# Load stats from measurement
####################################

import ast

def extract_other_stats(file_content: str) -> dict:
    """
    Extract 'Other stats' from the given file content and return it as a dictionary.
    
    Args:
        file_content (str): The string content of the file.

    Returns:
        dict: A dictionary containing 'Other stats'.
    """
    start_keyword = "Other stats:"
    start_index = file_content.find(start_keyword)
    
    if start_index == -1:
        raise ValueError("'Other stats' not found in the file content")
    
    other_stats_str = file_content[start_index + len(start_keyword):].strip()
    
    other_stats_dict = ast.literal_eval(other_stats_str)
    
    return other_stats_dict


print(f'Main Directory: {p["file_loc"]["main_dir"]}')

file_regex = p['file_loc']['stats_loc']
file_names = glob(file_regex.format('*', '*'))

# File content:
# Languages: defaultdict(<class 'int'>, {})
# Other stats: {'accessible': 59, 'english': 50, 'is_shopping': 14, 'error_urls': ['ozon.ru', 'cisco.com', 'jomodns.com', 'imdb.com', 'msftconnecttest.com', 'edgecdn.ru', 'sciencedirect.com', 'researchgate.net', 'nr-data.net', 'o365filtering.com', 'azureedge.net', 'facebook.net', 'youtube-nocookie.com', 'cmediahub.ru', 'rubiconproject.com', 'cedexis.net', 'washingtonpost.com', 'dzeninfra.ru', 'byteoversea.net', 'canva.com', 'wixsite.com', 'alicdn.com', 'issuu.com', 'mtgglobals.com', 'cdngslb.com', 'espn.com', 'atomile.com', 'vungle.com', 'media-amazon.com', 'reuters.com', 'rlcdn.com', 'godaddy.com', 'ttdns2.com', 'tiktokv.us', 'amazon.co.uk', 'samsungqbe.com', 'alibabadns.com', 'wiley.com', 'arubanetworks.com', 'googletagservices.com', 'wbx2.com']}
english_shopping_websites ={
    'accessible': 0,
    'english': 0,
    'is_shopping': 0,
}
indices = [(f.split('_')[-2], f.split('_')[-1][:-4]) for f in file_names]
start, end = min([int(i[0]) for i in indices]), max([int(i[1]) for i in indices])

for file_name in file_names:
    with open(file_name, 'r') as f:
        file_content = f.read()
        other_stats = extract_other_stats(file_content)
        for k, v in other_stats.items():
            if k == 'error_urls':
                continue
            english_shopping_websites[k] += v

print(f"From Tranco list top {start} to {end}: {english_shopping_websites}")    

shopping_terms_dir = p['file_loc']['shopping_terms_dir']
# get dirs under shopping_terms_dir
url_terms_dirs = glob(shopping_terms_dir + '/*')
print(f"Number of English Shopping Website with T&Cs: {len(url_terms_dirs)}")
# get file number in each dir
file_nums = sum([len(glob(f'{d}/*')) for d in url_terms_dirs])
print(f"Number of T&Cs in all English Shopping Website: {file_nums}")

# get sanitized terms from sanitized_dir
sanitized_dir = p['file_loc']['sanitized_dir']
sanitized_files = glob(sanitized_dir + '/*')
# load the csv files, count the number of paragraphs and urls
paragraph_cnt = 0
url_cnt = 0
for file_name in sanitized_files:
    # load the csv file
    data = pd.read_csv(file_name)
    paragraph_cnt += len(data)
    url_cnt += len(data['url'].unique())
print(f"Number of URLs from sanitized terms: {url_cnt}")
print(f"Number of paragraphs from sanitized terms: {paragraph_cnt}")
    