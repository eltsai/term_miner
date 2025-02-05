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
from tqdm import tqdm
from glob import glob

from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import math
import faiss

import pandas as pd
from utils import read_file_contents
from openai import OpenAI
from random import sample


if __name__ == "__main__": 
    parser = argparse.ArgumentParser(description='Clustering and topic modeling.')
    parser.add_argument('--split', type=int, default=1, help='Split to process')
    parser.add_argument('--cluster', type=bool, default=False, help='Cluster paragraphs')
    parser.add_argument('--chunk-num', type=int, default=10, help='Cluster chunks')
    parser.add_argument('--topic', type=bool, default=False, help='Topic modeling')
    parser.add_argument('--is-financial', type=bool, default=False, help='Query GPT-4o to see if the paragraph a financial term.')
    parser.add_argument('--eps', type=float, default=0.3, help='DBSCAN eps')
    parser.add_argument('--sample-max-size', type=int, default=20, help='Max size of the sample from each cluster.')
    parser.add_argument('--chunk-index-start', type=int, default=0, help='Chunk index')
    parser.add_argument('--chunk-index-end', type=int, default=1, help='Chunk index')
    args = parser.parse_args()
    
    p = load_measurement_config()
    print(p)
    
    split = args.split
    sanitized_dir = p['file_loc']['sanitized_dir']
    file_names = p['file_loc']['sanitized_files']
    file_name = sanitized_dir + '/' + file_names[split]
    data = pd.read_csv(file_name)
    url_cnt = data['url'].nunique()
    print(f"Processing Split {split}: {file_names[split]}, {len(data)} paragraphs from {url_cnt} URLs")
    
    #######################################
    # Clustering
    #######################################
    if args.cluster:
        num_chunks = args.chunk_num
        chunk_size = math.ceil(len(data) / num_chunks)
        
        
        
        # Split the data into 5 chunks
        for chunk_idx in range(num_chunks):
            embeddings = []
            chunk_data = data.iloc[chunk_idx * chunk_size: (chunk_idx + 1) * chunk_size]
            print(f"Processing chunk {chunk_idx+1}/{num_chunks} with {len(chunk_data)} paragraphs")
            
            
            embedding_loc = p['file_loc']['embedding_dir']+f'/embedding_split{split}_chunk{chunk_idx+1}.pkl'
            
            if os.path.exists(embedding_loc):
                
                with open(embedding_loc, 'rb') as f:
                    embeddings = pickle.load(f)
                    print(f"Loaded embeddings from {embedding_loc}")
            else:
                print("Generating embeddings using T5...")
                model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1')
                
                # Generate embeddings for the current chunk
                for paragraph in tqdm(chunk_data['paragraph']):
                    embeddings.append((paragraph, model.encode(paragraph, convert_to_tensor=True)))
                
                # Save embeddings after processing the chunk
                with open(embedding_loc, 'wb') as f:
                    pickle.dump(embeddings, f)
                    
            #######################################
            # Clustering for each chunk
            #######################################
            embeddings_only = np.array([e[1].cpu() for e in embeddings], dtype=np.float32)

            faiss.normalize_L2(embeddings_only)
            
            # Create a faiss index for flat cosine similarity search
            index = faiss.IndexFlatIP(embeddings_only.shape[1])
            index.add(embeddings_only)

            D, I = index.search(embeddings_only, len(embeddings_only)) 
            cosine_distances = 1 - D
            
            for eps in tqdm(eps_values, total=len(eps_values)):
                # DBSCAN clustering
                dbscan = DBSCAN(eps=eps, min_samples=5, metric='precomputed')
                labels = dbscan.fit_predict(cosine_distance)

                # Save the clusters and the texts
                clusters = {}
                for i, label in enumerate(labels):
                    if label not in clusters:
                        clusters[int(label)] = [embeddings[i][0]]
                    clusters[int(label)].append(embeddings[i][0])
                
                # Save clusters to a directory named based on chunk index
                save_dir = p['file_loc']['cluster_dir']+f'/split{split}/chunk{chunk_idx+1}'
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)

                with open(f"{save_dir}/eps_{eps}.json", 'w') as f:
                    json.dump(clusters, f)
                    print(f"Saved clusters for chunk {chunk_idx+1} to {save_dir}/eps_{eps}.json")
                    
    #######################################
    # Filter Out Non-Financial Clusters
    # Note: This is a separate step from clustering
    #       You can also filter financial terms one-by-one, and then cluster
    #######################################
    eps = args.eps
    split = args.split
    random_sample_size = args.sample_max_size
    API_KEY = read_file_contents((p['openai']['api_key_loc']))
    os.environ["OPENAI_API_KEY"] = API_KEY
    client = OpenAI()
    if args.is_financial:
        
        financial_binary_prompt = read_file_contents(p['prompt_loc']['financial_term_binary'])
        

        save_loc = p['file_loc']['cluster_dir']+f'/split{split}/eps_{eps}_filtered.json'
        if os.path.exists(save_loc):
            print(f"Already processed {save_loc}")
            sys.exit(0)
        with open(save_loc, 'w') as target_f:
            for chunk_idx in range(args.chunk_index_start, args.chunk_index_end):
                cluster_loc = p['file_loc']['cluster_dir']+f'/split{split}/chunk{chunk_idx}/eps_{eps}.json'
                print(f"Loading clusters from {cluster_loc}")
                with open(cluster_loc, 'r') as f:
                    clusters = json.load(f)
                    print(f"Loaded {len(clusters)} clusters")
                    for cluster_id, paragraphs in clusters.items():
                        if 2 < len(paragraphs) < 1000:
                            full_paragraphs = paragraphs
                            if len(paragraphs) > random_sample_size:
                                # randomly select
                                paragraphs = sample(paragraphs, random_sample_size)
                            try:
                                response = client.chat.completions.create(
                                    model='gpt-4o',
                                    messages=[
                                        {"role": "user", "content": financial_binary_prompt.format('\n'.join(paragraphs))},
                                    ],
                                    response_format={
                                        "type": "json_object"
                                    }
                                )
                                response_data = json.loads(response.choices[0].message.content)
                                # print(response_data)
                                if response_data['classification'] == 1:
                                    target_f.write(json.dumps({'cluster_id': cluster_id, 'paragraphs': full_paragraphs})+'\n')
                                    
                            except Exception as e:
                                print(e)
                                continue
            
    #######################################
    # Topic Modeling
    #######################################
    if args.topic:
        malicious_term_prompt = read_file_contents(p['prompt_loc']['malicious_financial_term_classification'])
        current_taxonomy = read_file_contents(p['prompt_loc']['malicious_financial_term_taxonomy'])

        save_loc = p['file_loc']['cluster_dir']+f'/split{split}/eps_{eps}_with_topics.json'

        if os.path.exists(save_loc):
            print(f"Already processed {save_loc}")
            sys.exit(0)

        with open(save_loc, 'w') as target_f:
            cluster_loc = p['file_loc']['cluster_dir']+f'/split{split}/eps_{eps}_filtered.json'
            print(f"Loading clusters from {cluster_loc}")
            with open(cluster_loc, 'r') as f:
                for line in f:
                    data = json.loads(line.strip()) 
                    cluster_id, paragraphs = data['cluster_id'], data['paragraphs']
                    full_paragraphs = paragraphs
                    if len(paragraphs) > random_sample_size:
                        # randomly select
                        paragraphs = sample(paragraphs, random_sample_size)
                    
                    try:
                        response = client.chat.completions.create(
                            model='gpt-4o',
                            messages=[
                                {"role": "user", "content": malicious_term_prompt.format(taxonomy=current_taxonomy, document_list='\n'.join(paragraphs))},
                            ],
                            response_format={
                                "type": "json_object"
                            }
                        )
                        response_data = json.loads(response.choices[0].message.content)
                        if response_data['category'].lower() != 'benign':
                            target_f.write(json.dumps({'cluster_id': cluster_id, 
                                                        'paragraphs': full_paragraphs,
                                                        'category': response_data['category'],
                                                    })+'\n')
                            
                    except Exception as e:
                        print(e)
                        continue