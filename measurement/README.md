# Data Collection and Clustering Module

## Objective

To collect T&Cs from Enlish shopping (`entc`) websites.

To determine if a website is mainly in English: We first check the HTML `lang` attribute to determine the language. If it's not present, we use the `langdetect` package as a fallback.

To determine if a website is a shopping website: Selenium with a Chrome Driver.
We use gpt-4o-mini + image of top page as default. See the `measurement.classifier` entry in `configs/measurement.yaml`:
```
measurement:
  classifier: 'gpt-4o-mini@image'
```

Download the [chrome driver](https://chromedriver.storage.googleapis.com/index.html?path=114.0.5735.90/) and install under `./chrome/` following [this github gist](https://gist.github.com/mikesmullin/2636776).

## Instruction
### 1. Filter English shopping websites from the Tranco list Top websites

**Usage example**:
```
python measurement/1tranco.py --start=0 --end=10000
```

This script processes a list of websites (from the Tranco list), checks their accessibility and language, takes screenshots, classifies them as shopping or non-shopping websites using a vision-based classifier, and saves the results.

Input:
* Tranco website list (start and end indices for a subset of websites).
* Configuration file with file locations and classifier settings (config.py).
* OpenAI API key for website classification.
* Prompts and file paths from configuration.
Output:
* JSON files containing website data (URL, language, shopping classification) - `./data/tranco/entc_websites_{start}_{end}`. The results is save in a chunk size of 100 .
* Statistics on website accessibility, language, and classification - `./data/tranco/stats/tranco_{start}_{end}`.
* Screenshots of websites, if required - `./data/tranco/screenshots/`.

### 2. Fetch T&C from English Shopping Websites

**Usage example**:

```
python measurement/2fetch_terms.py --start=0 --end=10000
```

In this step, we fetch the T&C pages from the English shopping websites.

We employ an iterative approach using a positive and negative regex list (`positive_regex` and `negative_regex` in `./measurement/tc_locator.py`) to identify the links to Terms & Conditions (T&C) pages as follows:

1. Identify links that match the positive regex and do not match the negative regex.
2. For each identified T&C page, extract links that comply with the positive regex and do not trigger the negative regex.
3. Repeat this process until no further links can be found.

The results are saved in `./data/tranco/shopping_terms/{url}/{term_url.html}`

### 3. Sanitize Sentences
Use `stats.py` to check how many English shopping websites we collected:
```
$ python stats.py
From Tranco list top 0 to 100000: {'accessible': 61466, 'english': 38674, 'is_shopping': 8482}
Number of English Shopping Website with T&Cs: 8251
Number of T&Cs in all English Shopping Website: 75972
```
We then split terms into paragraphs.
```
python measurement/3sanitize_terms.py --start=0 --end=2100 --target=sanitized_split1.csv
python measurement/3sanitize_terms.py --start=2100 --end=4200 --target=sanitized_split2.csv
python measurement/3sanitize_terms.py --start=4200 --end=6300 --target=sanitized_split3.csv
python measurement/3sanitize_terms.py --start=6300 --end=8400 --target=sanitized_split4.csv
```


### 4. Clustering and Topic Modeling for Terms & Conditions**

This module clusters paragraphs extracted from **Terms & Conditions (T&C)** pages of shopping websites and performs topic modeling to identify financial and malicious financial terms.

Usage Example
```bash
python measurement/4cluster.py --split=0 --cluster=True --chunk-num=5 --is-financial=True --eps=0.21
```

**Arguments**
- `--split` (`int`, default: `1`)  
  Specifies which data split to process.
- `--cluster` (`bool`, default: `True`)  
  Enables clustering of extracted paragraphs.
- `--chunk-num` (`int`, default: `10`)  
  Number of chunks to divide the data into for processing. Adjust based on available computational resources.
- `--is-financial` (`bool`, default: `True`)  
  Queries GPT-4o to determine if a cluster contains financial terms.
- `--eps` (`float`, default: `0.3`)  
  Epsilon value for DBSCAN clustering.
- `--topic` (`bool`, default: `False`)  
  Enables topic modeling after clustering.
- `--sample-max-size` (`int`, default: `20`)  
  Maximum sample size from each cluster for GPT-4o classification.
- `--chunk-index-start` (`int`, default: `0`)  
  Start index for chunk processing in the topic modeling stage.
- `--chunk-index-end` (`int`, default: `1`)  
  End index for chunk processing in the topic modeling stage.

---

**Workflow**

**4.1. Clustering T&C Paragraphs**
If `--cluster=True`, the script performs the following steps:
1. Loads **sanitized T&C paragraphs** from the specified data split.
2. Splits the data into **chunks** (default: `--chunk-num=10`).
3. **Embeddings Generation:**
   - Uses the **T5-based SentenceTransformer (`mixedbread-ai/mxbai-embed-large-v1`)** to encode paragraphs.
   - Saves generated embeddings for future reuse.
4. **Clustering with DBSCAN:**
   - Computes **cosine similarity** between paragraph embeddings.
   - Applies **DBSCAN clustering** across different epsilon values (`--eps`).
   - Saves clusters to `./data/clusters/split{split}/chunk{chunk_idx}/eps_{eps}.json`.

---

**4.2. Identifying Financial Terms in Clusters**
If `--is-financial=True`, the script:
1. Loads **clustered paragraphs** from `./data/clusters/split{split}/eps_{eps}.json`.
2. **Samples paragraphs** (max: `--sample-max-size`) and queries GPT-4o to classify clusters as **financial or non-financial**.
3. Saves **financial clusters** to `./data/clusters/split{split}/eps_{eps}_filtered.json`.

---

**4.3. Topic Modeling for Malicious Financial Terms**
If `--topic=True`, the script:
1. Loads **filtered financial clusters** from `./data/clusters/split{split}/eps_{eps}_filtered.json`.
2. Queries GPT-4o using a **predefined financial term taxonomy**.
3. Categorizes clusters as **benign or malicious financial terms**.
4. Saves results to `./data/clusters/split{split}/eps_{eps}_with_topics.json`.


---

**Output Files**
- `./data/clusters/split{split}/chunk{chunk_idx}/eps_{eps}.json`  
  Raw DBSCAN cluster assignments for each chunk.

- `./data/clusters/split{split}/eps_{eps}_filtered.json`  
  Clusters classified as containing financial terms.

- `./data/clusters/split{split}/eps_{eps}_with_topics.json`  
  Clusters classified as containing malicious financial terms based on topic modeling.

