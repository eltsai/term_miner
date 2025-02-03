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
from glob import glob

from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModelForTokenClassification
import csv
import re

def html_str2list(html_str):
    # Step 1: Extract text from HTML
    soup = BeautifulSoup(html_str, 'html.parser')
    text = soup.get_text(separator=" ")
    
    if not text:
        return []

    # Step 2: Load pre-trained transformer model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModelForTokenClassification.from_pretrained("dbmdz/bert-large-cased-finetuned-conll03-english")

    # Step 3: Tokenize the text
    tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    # Step 4: Perform token classification to get token predictions
    outputs = model(**tokens)
    input_ids = tokens["input_ids"].squeeze().tolist()

    # Step 5: Decode tokens back to text and split sentences based on punctuation
    decoded_text = tokenizer.decode(input_ids)
    sentences = []
    current_sentence = []
    
    for token in decoded_text.split():
        current_sentence.append(token)
        if token.endswith(('.', '?', '!')):
            sentences.append(' '.join(current_sentence))
            current_sentence = []

    if current_sentence:
        sentences.append(' '.join(current_sentence))

    return sentences


def html_str2paragraphs_from_p(html_str):
    soup = BeautifulSoup(html_str, 'html.parser')
    
    # Extract paragraphs from <p> tags
    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
    
    return paragraphs


def save_to_csv(target_name, url, paragraphs):
    file_exists = os.path.isfile(target_name)
    
    with open(target_name, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writerow(['url', 'paragraph'])
        
        for paragraph in paragraphs:
            sanitized_paragraph = paragraph.replace('"', "'")  # Replace double quotes with single quotes
            writer.writerow([url, sanitized_paragraph])


def sanitize_paragraphs(paragraphs):
    paragraphs = [p for p in paragraphs if len(p.split()) > 10]
    paragraphs = list(set(paragraphs))
    paragraphs = [p.replace('\n', ' ') for p in paragraphs]
    paragraphs = [re.sub(r'\s{2,}', ' ', p) for p in paragraphs]
    return paragraphs


if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Sanitize terms.')
    parser.add_argument('--start', type=int, default=0, help='start index')
    parser.add_argument('--end', type=int, default=10000, help='end index')
    parser.add_argument('--target', type=str, default="sanitized_split1.csv", help='save name')
    args = parser.parse_args()
    p = load_measurement_config()
    dirs = glob(p['file_loc']['shopping_terms_dir'] + '/*/')
    print(f"Processing {len(dirs)} URLS from {p['file_loc']['shopping_terms_dir']}")
    target_name = p['file_loc']['sanitized_dir'] + '/' + args.target
    if os.path.exists(target_name):
        os.remove(target_name)
        print(f"Removed existing {target_name}")
    
    
    paragraph_cnt = 0
    with tqdm(total=len(dirs[args.start:args.end]), desc="Processing URLs") as pbar:
        for url_dir in dirs[args.start:args.end]:
            url = url_dir.split('/')[-2].replace('_', '/')
            html_files = glob(url_dir + '/*')
            # print(url, dirs.index(url_dir))
            
            for html_file in html_files:
                html = open(html_file).read()
                try:
                    paragraphs = html_str2paragraphs_from_p(html)
                    # filter out the paragraphs that have less than 10 words
                    paragraphs = sanitize_paragraphs(paragraphs)
                except:
                    print(f"Error processing {html_file}")
                if paragraphs:
                    save_to_csv(target_name, url, paragraphs)
                    paragraph_cnt += len(paragraphs)
            pbar.update(1)
    print(f'Finished processing {args.end - args.start} URLs with {paragraph_cnt} paragraphs')
    print(f'Saved to {target_name}')
    
    #######################################
    # Load EN Shopping Files and Extract TC
    #######################################
    
