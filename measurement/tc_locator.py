# Fetch T&C and related policy pages.
import requests
import re
from bs4 import BeautifulSoup
from typing import Optional, Tuple, List
import validators

import os
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from utils import html_language



positive_regex = [
    "terms",
    "return",
    "refund",
    "terms.*?conditions",
    "terms.*?of.*?use",
    "terms.*?of.*?service",
    "terms.*?of.*?sale",
    "terms.*?of.*?conditions",
    "terms.*?and.*?conditions",
    "terms.*?&.*?conditions",
    "conditions.*?of.*?use",
    "intellectual.*property.*policy",
    "return[s]?.*?policy",
    "refund[s]?.*?policy",
    "return.*?and.*?refund.*?policy",
    "cancellation.*?and.*?returns",
    "cancellation.*?returns",
    "prohibited.*conduct",
    "electronic.*communication.*policy",
    "dmca.*copyright.*notification",
    "safety.*guideline",
    "requests.*from.*law.*enforcement",
    "bonus.*terms.*apply",
    "community.*rules",
    "gift.*card.*policy",
    "contact.*us.*here",
    "shipping.*policy",
    "delivery.*shipping",
    "warranty",
    "end.*user.*license",
    "user.*?agreement",
    "payment.*terms",
    "content.*policy",
]

negative_regex = [
    "privacy.*?policy",
    "cookie.*?policy",
    "privacy.*?notice",
    "sale.*?tax.*?policy",
    "prohibited.*?items",
    "1099.*?k.*?form",
    "privacy",
]

def match_link_regex_list(link: str, url:str) -> bool:
    link_unique = link.replace(url, '')
    for pattern in negative_regex:
        if re.search(pattern, link_unique):
            return False
    for pattern in positive_regex:
        if re.search(pattern, link_unique):
            return True
    return False

def match_target_regex_list(string: str) -> bool:
    """
    Determine if a string matches any of the regexes in pattern_list.
    """
    # TODO - speed it up with multiprocessing
    for pattern in positive_regex:
        if re.search(pattern, str(string).lower()):
            return True
    return False


def list_all_hyperlinks(html_str: str, url: str) -> List[str]:
    """
    Extract and return all hyperlinks (href attributes) and onclick events from the given HTML string.
    Handles cases where the href contains 'javascript:void(0);' by inspecting the onclick attribute.

    Args:
        html_str (str): The HTML content as a string.
        url (str): The base URL to resolve relative links.

    Returns:
        List[str]: A list of valid URLs found in the href attributes of <a> tags or onclick events.
    """
    soup = BeautifulSoup(html_str, 'html.parser')
    anchor_tags = soup.find_all('a', href=True)
    links = []
    
    # Ensure URL starts with http or https
    if 'https://' not in url and 'http://' not in url:
        url = 'https://' + url

    for tag in anchor_tags:
        href = tag.get('href')
        # Check if href is javascript:void(0); and try to extract the onclick link
        if href and 'javascript:void(0);' in href:
            onclick = tag.get('onclick')
            if onclick:
                link = find_onclick_link(onclick)
                if validators.url(link):
                    links.append(link)
        elif href:
            # Resolve relative links
            if href.startswith('/'):
                href = url + href
            if validators.url(href):
                links.append(href)

    return links

def find_onclick_link(onclick_str: str) -> Optional[str]:
    """
    Extract the URL from an onclick event string.
    
    Args:
        onclick_str (str): The onclick event as a string.

    Returns:
        Optional[str]: The extracted URL if present, otherwise None.
    """
    # This is a placeholder logic, needs to be updated according to the onclick patterns you want to handle.
    # Example: extract URL from patterns like window.location.href = '...'
    match = re.search(r"(https?://[^\s'\"]+)", onclick_str)
    return match.group(0) if match else None


def fetch_html(url: str) -> str:
    """
    Fetch the HTML content of the given URL if the content is HTML.
    
    Args:
        url (str): The URL to fetch the content from.
    
    Returns:
        str: The HTML content as a string, or None if the content is not HTML.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Check if the content type is HTML
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            return response.text
        else:
            # Not an HTML content type (e.g., could be a PDF or other file)
            return None
    except requests.RequestException:
        return None


def fetch_all_tc_links(html: str, url: str, max_depth: int = 3) -> dict:
    """
    Iteratively fetch all T&C links from the HTML content using positive and negative regex, 
    with a limit on the maximum depth of recursion.

    Args:
        html (str): The initial HTML content.
        url (str): The URL of the page to start from.
        max_depth (int): The maximum depth to fetch links from. Defaults to 3.

    Returns:
        dict: A dictionary where the keys are T&C links and the values are the corresponding HTML content.
    """
    link_candidates = list_all_hyperlinks(html, url)
    pending_links = [l for l in link_candidates if match_link_regex_list(l, url)]
    visited = set()
    tc_link2html = {}
    while max_depth > 0:
        new_matched_links = set()
        for link in pending_links:
            if link not in visited:
                visited.add(link)
                html_content = fetch_html(link)
                if html_content:
                    language = html_language(html_content)
                    if not language or not language.lower().startswith('en'):
                        continue
                    tc_link2html[link] = html_content    
                    new_links = list_all_hyperlinks(html_content, url)
                    new_links = [l for l in new_links if l not in visited and match_link_regex_list(l, url)]
                    new_matched_links.update(new_links)
        pending_links = new_matched_links
        if not pending_links:
            break
        max_depth -= 1
    return tc_link2html
