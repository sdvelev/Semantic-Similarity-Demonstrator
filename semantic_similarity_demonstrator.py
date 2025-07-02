import requests
import urllib.parse
import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON
from PIL import Image
from io import BytesIO
from sematch.semantic.similarity import EntitySimilarity

GRAPHDB_REPOSITORY_URL = "http://localhost:7200/repositories/human_similarity"
WIKIDATA_SEARCH_API_URL = "https://www.wikidata.org/w/api.php"
DBPEDIA_SPARQL_URL = "https://dbpedia.org/sparql"

def sparql_query(query):
    sparql = SPARQLWrapper(GRAPHDB_REPOSITORY_URL)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

def get_entity_qid(label):
    if label.upper().startswith("P"):
        return label
    params = {
        'action': 'wbsearchentities',
        'language': 'en',
        'format': 'json',
        'search': label
    }
    response = requests.get(WIKIDATA_SEARCH_API_URL, params=params).json()
    if response['search']:
        return response['search'][0]['id']
    return None

def is_valid_image_url(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                Image.open(BytesIO(response.content))
                return True
    except Exception:
        pass
    return False

def get_person_qid_by_label(label):
    query = f'''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?person WHERE {{
      ?person rdfs:label "{label}"@en .
    }} LIMIT 1
    '''
    results = sparql_query(query)
    bindings = results["results"]["bindings"]
    if bindings:
        return bindings[0]["person"]["value"].split('/')[-1]
    return None

def get_property_values(qid, properties):
    filters = []
    for prop in properties:
        if not prop.upper().startswith('P'):
            continue
        prop_code = prop
        filters.append(f"OPTIONAL {{ wd:{qid} wdt:{prop_code} ?val_{prop_code} }}")
    if not filters:
        return {}

    query = f'''
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    SELECT * WHERE {{
      {' '.join(filters)}
    }}
    '''
    print(query)
    results = sparql_query(query)
    values = {}
    if results['results']['bindings']:
        for key, val in results['results']['bindings'][0].items():
            values[key.replace('val_', '')] = val['value']
    print(values)
    return values

def get_matching_humans(properties_dict):
    filters = []
    for prop, val in properties_dict.items():
        filters.append(f"?person wdt:{prop} <{val}> .")

    query = f'''
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?person ?label WHERE {{
      ?person wdt:P31 wd:Q5 .
      {' '.join(filters)}
      ?person rdfs:label ?label .
      FILTER(LANG(?label) = 'en')
    }} LIMIT 100
    '''
    print(query)
    results = sparql_query(query)
    return [(r['person']['value'].split('/')[-1], r['label']['value']) for r in results['results']['bindings']]

def get_image_url_from_dbpedia(label):
    resource = label.strip().replace(' ', '_')
    sparql = SPARQLWrapper(DBPEDIA_SPARQL_URL)
    sparql.setQuery(f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dbr: <http://dbpedia.org/resource/>

    SELECT ?img WHERE {{
      VALUES ?person {{ dbr:{resource} }}
      OPTIONAL {{ ?person dbo:thumbnail ?img }}
      OPTIONAL {{ ?person foaf:depiction ?img }}
      FILTER(bound(?img))
    }} LIMIT 1
    """)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        if bindings:
            return bindings[0]["img"]["value"]
    except Exception as e:
        print("DBpedia image fetch error:", e)
    return None

st.title("Semantic Similarity Demonstrator")
st.subheader("Similar People in Wikidata5m graph dataset")
st.image("./docs/sources/img/logo.png", caption="Sematch: semantic similarity framework")

person_label = st.text_input("**Enter a person's name (e.g., Albert Einstein):**")
if person_label:
    searched_img = get_image_url_from_dbpedia(person_label)
    if searched_img:
        with st.columns(3)[1]:
            st.image(searched_img, caption=person_label, width=150)

prop_input = st.text_input("**Enter Wikidata properties to match (e.g., P19, P106):**")
limit = st.slider("**How many people to compare to?**", 1, 20, 10)

if st.button("Find and Compare") and person_label:
    with st.spinner("Comparing from Wikidata5m..."):
        person_qid = get_person_qid_by_label(person_label)
        if not person_qid:
            st.error("Could not find the specified person in Wikidata5m.")
        else:
            properties = [p.strip() for p in prop_input.split(',') if p.strip()]
            prop_values = get_property_values(person_qid, properties)
            if not prop_values:
                st.warning("No matching property values found for the person.")
            else:
                matches = get_matching_humans(prop_values)
                print(matches)
                matches = [m for m in matches if m[0] != person_qid]

                sim = EntitySimilarity()
                rows = []
                for qid, label in matches:
                    dbpedia_uri = f"http://dbpedia.org/resource/{urllib.parse.quote(label.replace(' ', '_'))}"
                    target_dbpedia = f"http://dbpedia.org/resource/{urllib.parse.quote(person_label.replace(' ', '_'))}"
                    try:
                        score = sim.similarity(dbpedia_uri, target_dbpedia)
                    except:
                        score = 0.0
                    img = get_image_url_from_dbpedia(label)
                    rows.append((label, score, img))

                rows.sort(key=lambda x: -x[1])

                st.subheader(f"Top {limit} similar people to {person_label}")
                counter = 1
                for name, score, img in rows[:limit]:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if img and is_valid_image_url(img):
                            st.image(img, width=80)
                    with col2:
                        st.markdown(f"**{counter}. {name}**\n\nSimilarity: {score:.4f}")
                        counter += 1
