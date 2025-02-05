import requests
import os
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
import argparse
from config import load_measurement_config
from glob import glob
import json
from tc_locator import fetch_all_tc_links
from tqdm import tqdm
    

if __name__ == "__main__":  
    parser = argparse.ArgumentParser(description='Fetch T&Cs from English shopping websites.')
    parser.add_argument('--start', type=int, default=0, help='start index')
    parser.add_argument('--end', type=int, default=10000, help='end index')
    args = parser.parse_args()
    start, end = args.start, args.end
    p = load_measurement_config()
    
    #######################################
    # Load EN Shopping Files and Extract TC
    #######################################

    
    file_regex = p['file_loc']['entc_website_loc']
    file_names = glob(file_regex.format('*', '*'))
    file_names = [f for f in file_names if int(f.split('_')[-2]) >= start and int(f.split('_')[-1].split('.')[0]) <= end]
    
    print(f"Processing {len(file_names)} files from {p['file_loc']['entc_website_loc']}")
    
    #######################################
    # Save Fecthed TCs
    #######################################
    
    save_dir = p['file_loc']['shopping_terms_dir']
    
    has_terms = 0
    terms_cnt = 0
    
    
    for file_name in file_names:
        # load json 
        print(file_name, file_names.index(file_name))
        data = json.load(open(file_name))
        for row in tqdm(data, total=len(data)):
            if row['is_shopping']:
                try:
                    url, html = row['url'], row['html']
                    url = url.replace('https://', '').replace('http://', '')
                    url_dir = os.path.join(save_dir, url.replace('/', '_'))
                    if os.path.exists(url_dir):
                        continue
                    tc_link2html = fetch_all_tc_links(html, url)
                    if tc_link2html:
                        has_terms += 1
                        os.makedirs(url_dir, exist_ok=True)
                        for tc_link, tc_html in tc_link2html.items():
                            terms_cnt += 1
                            tc_link = tc_link.replace('https://', '').replace('http://', '').replace('/', '_')
                            try:
                                with open(os.path.join(url_dir, tc_link[:255]), 'w') as f:
                                    f.write(tc_html)
                            except:
                                print(f"Error saving {tc_link}")
                                continue
                except:
                    print(f"Error processing {url}")
                    continue
    print(f"Found {has_terms} websites with T&Cs, and {terms_cnt} T&Cs in total")
    #######################################
    # Saved: shopping_terms_dir/{url}/{tc_link}
    #######################################
        
    
    

