import os
import requests
import zipfile
import pandas as pd
from bs4 import BeautifulSoup
import langdetect
import json

####################################
# File operations
####################################
def read_file_contents(file_path:str)->str:
    """
    Reads the contents of a file.

    :param file_path: The path to the file to read.
    :return: The contents of the file as a string.
    """
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"An error occurred: {e}")
        
def save_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def save_stats(language_dict, other_stats, filename):
    with open(filename, 'w') as f:
        f.write(f'Languages: {language_dict}\n')
        f.write(f'Other stats: {other_stats}\n')


    
    
####################################
# Measurement
####################################
def get_top_tranco_sites(start, end, file_loc):
    url = 'https://tranco-list.eu/top-1m.csv.zip'
    response = requests.get(url)
    response.raise_for_status()

    if not os.path.exists(file_loc):
        with open(file_loc, 'wb') as f:
            f.write(response.content)

    with zipfile.ZipFile(file_loc, 'r') as zip_ref:
        zip_ref.extractall()

    df = pd.read_csv(file_loc, header=None, names=['Rank', 'Domain'])
    top_n_sites = df.head(end)

    return top_n_sites['Domain'].tolist()[start:]

def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None
    
    
def html_language(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    html_tag = soup.find('html')
    if html_tag and html_tag.has_attr('lang'):
        return html_tag['lang']
    
    meta_tag = soup.find('meta', attrs={'http-equiv': 'Content-Language'})
    if meta_tag and meta_tag.has_attr('content'):
        return meta_tag['content']
    
    # use langdetect to detect language in main text
    text = soup.get_text()
    try:
        return langdetect.detect(text)
    except:
        return None
    
    return None