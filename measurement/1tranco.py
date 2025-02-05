import requests
import os
import sys
import zipfile
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from collections import defaultdict
from PIL import Image
from io import BytesIO
import base64
import json
from tqdm import tqdm
import argparse

from website_classification import (
    encode_image,
    take_screenshot,
    classify_website_with_image
)

from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config import load_measurement_config
from utils import get_top_tranco_sites, fetch_html, read_file_contents, html_language, save_to_json, save_stats

def entc(tranco_list, p):
    classifer, mode=p['measurement']['classifier'].split('@')
    print(f"Using {classifer} classifier in {mode} mode")

    if mode == 'image': # if using vision api, use selenium to take screenshots
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=Service(f'{project_root}/chrome/chromedriver'), options=chrome_options)
        
        websites_data = []
        language_dict = defaultdict(int)
        other_stats = {
            'accessible':0,
            'english': 0,
            'is_shopping': 0,
            'error_urls': [],
        }
    chunk_cnt, current_end = 0, start
    
    entc_path = p['file_loc']['entc_website_loc']
    stats_path = p['file_loc']['stats_loc']
        
    for index, url in enumerate(tqdm(tranco_list, desc="Processing websites")):
        if (index+1) % 100 == 0:
            current_start = start + chunk_cnt*100
            current_end = start + (1+chunk_cnt)*100
            chunk_cnt += 1
            save_to_json(websites_data, entc_path.format(current_start, current_end))
            save_stats(language_dict, other_stats, stats_path.format(current_start, current_end))

            websites_data = []
            language_dict = defaultdict(int)
            other_stats = {
                'accessible':0,
                'english': 0,
                'is_shopping': 0,
                'error_urls': [],
            }
            print(f"Saved {current_start} to {current_end}")
        try:
            html = fetch_html(f'https://{url}')
        except Exception as e:
            print(f"Error: {e}")
            other_stats['error_urls'].append(url)
            continue
        if not html:
            other_stats['error_urls'].append(url)
            continue
        other_stats['accessible'] += 1
        
        language = html_language(html)
        
        if not language or not language.lower().startswith('en'):
            continue
        
        other_stats['english'] += 1
        
        screenshot_path = os.path.join(p['file_loc']['screenshot_dir'], f'{url}.png')
        screenshot = take_screenshot(f'https://{url}', driver, screenshot_path)
        
        prompt = read_file_contents(p['prompt_loc']['website_classification_image'])
        api_key = read_file_contents(p['openai']['api_key_loc'])
        try:
            classification = classify_website_with_image(api_key, url, screenshot_path, prompt)
        except Exception as e:
            print(f"Error: {e}")
            other_stats['error_urls'].append(url)
            continue
        
        if classification == 1:
            other_stats['is_shopping'] += 1
            
        websites_data.append({
            'url': url,
            'language': language,
            'is_shopping': classification,
            'html': html,
        })
        

    if websites_data:
        current_start = current_end
        current_end = end + chunk_cnt*100
        print(f"Saving {current_start} to {current_end} to file {entc_path.format(current_start, current_end)}")
        save_to_json(websites_data, entc_path.format(current_start, current_end))
        save_stats(language_dict, other_stats, stats_path.format(current_start, current_end))
        
        
    if mode == 'image':
        driver.quit()

if __name__ == "__main__":  
    parser = argparse.ArgumentParser(description='Filter English shopping websites.')
    parser.add_argument('--start', type=int, default=0, help='start index')
    parser.add_argument('--end', type=int, default=100, help='end index')
    parser.add_argument('--load-fcw', type=bool, default=False, help='Load the FCWs dataset.')
    parser.add_argument('--load-flos', type=bool, default=False, help='Load the FLOS dataset.')
    args = parser.parse_args()
    p = load_measurement_config()
    start, end = args.start, args.end
    #######################################
    # Load the FCWs dataset
    #######################################
    if args.load_fcw:
        data = pd.read_json(p['file_loc']['fcw_loc'],
                            orient='records', lines=True)
        url_list = data['domain'].tolist()[args.start:args.end]
        print(f"Number of sites: {len(url_list)} from FCWs, saving to {p['file_loc']['entc_website_loc'].format(start, end)}")
        entc(url_list, p)
    #######################################
    # Load the FLOS dataset
    #######################################
    elif args.load_flos:
        data = pd.read_csv(p['file_loc']['flos_loc'])
        url_list = data['Online shop URL'].tolist()
        url_list = [url.replace('https://', '').replace('http://', '') for url in url_list]
        start, end = 0, len(url_list)
        print(f"Number of sites: {len(url_list)} from FLOS, saving to {p['file_loc']['entc_website_loc'].format(start, end)}")
        entc(url_list, p)
    else:
        url_list = get_top_tranco_sites(start=start, 
                                        end=end,
                                        file_loc=p['file_loc']['tranco'])
        print(f"First 10 websites in the list: {url_list[:10]}")
        print(f"Extracting Enlish Shopping Websites from Tranco list {start} to {end}...")
        entc(url_list, p)
        
    

