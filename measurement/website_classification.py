import json
from typing import Tuple
import requests
import os
import base64
from PIL import Image
from io import BytesIO



def encode_image(image_path=None):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None
        
def take_screenshot(url, driver, save_path):
    # skip if file already exists
    if os.path.exists(save_path):
        return None
    try:
        driver.get(url)
        screenshot = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(screenshot))
        image.save(save_path, format="PNG")
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    except Exception:
        return None


def classify_website_with_image(api_key, url, screenshot_path, prompt)->bool:
    base64_image = encode_image(screenshot_path)

    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }
    shopping_cls_prompt = prompt.format(url)

    payload = {
    "model": "gpt-4o-mini",
    "temperature": 0,
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": shopping_cls_prompt,
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    resp = response.json()
    
    
    try:
        classification = resp['choices'][0]['message']['content'].strip().replace('\n', '').replace('`', '').replace('\'', '\"').replace(",", "").replace('json', '')
        classification = json.loads(classification)
    except:
        print(resp)
        return -1
    return classification['is_shopping']


def classify_website_name_only(url)->bool:
    ## TODO: Implement the function
    return False