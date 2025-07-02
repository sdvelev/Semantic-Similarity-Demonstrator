import re
import requests
import time
import sys

BATCH_SIZE = 50
MAX_RETRIES = 3
SLEEP_BETWEEN_RETRIES = 5

input_file = "wikidata5m_human_subgraph.ttl"
output_file = "wikidata5m_subgraph_labels.ttl"

def extract_qids_from_ttl(filename):
    qids = set()
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            matches = re.findall(r'entity/(Q\d+)', line)
            qids.update(matches)
    return sorted(qids)

def fetch_labels(qids):
    labels = {}
    counter = 0
    total = len(qids)

    for i in range(0, total, BATCH_SIZE):
        batch = qids[i:i+BATCH_SIZE]
        ids = "|".join(batch)
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": ids,
            "format": "json",
            "props": "labels",
            "languages": "en"
        }

        success = False
        retries = 0
        while not success and retries < MAX_RETRIES:
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                for qid in batch:
                    label = data.get("entities", {}).get(qid, {}).get("labels", {}).get("en", {}).get("value")
                    if label:
                        labels[qid] = label
                        counter += 1
                        print(f"{counter}/{total}: {qid} → {label}")
                success = True
            except requests.exceptions.RequestException as e:
                retries += 1
                print(f"Warning: Error fetching batch {i//BATCH_SIZE+1}: {e}. Retry {retries}/{MAX_RETRIES}...")
                time.sleep(SLEEP_BETWEEN_RETRIES)

        if not success:
            print(f"Error: Skipping batch starting at index {i} after {MAX_RETRIES} failed attempts.")

    return labels

def write_labels_ttl(labels, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n')
        f.write('@prefix wd: <http://www.wikidata.org/entity/> .\n\n')
        for qid, label in labels.items():
            label_safe = label.replace('"', '\\"')
            triple = f'<http://www.wikidata.org/entity/{qid}> rdfs:label "{label_safe}"@en .\n'
            f.write(triple)

if __name__ == "__main__":
    try:
        print("Extracting Q-IDs...")
        qids = extract_qids_from_ttl(input_file)
        print(f"Found {len(qids)} unique Q-IDs.")

        print("Fetching labels from Wikidata...")
        labels = fetch_labels(qids)
        print(f"Retrieved {len(labels)} labels.")

    except KeyboardInterrupt:
        print("\nInterrupted: Saving partial results...")

    finally:
        print(f"Writing {output_file}...")
        write_labels_ttl(labels, output_file)
