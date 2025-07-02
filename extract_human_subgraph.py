HUMAN_WIKIDATA_ITEM = "Q5"
INSTANCE_OF_WIKIDATA_PROPERTY = "P31"

input_file = "wikidata5m_transductive_train.txt"
output_file = "wikidata5m_human_subgraph.txt"

human_entities = set()

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        subject, predicate, object = line.strip().split("\t")
        if predicate == INSTANCE_OF_WIKIDATA_PROPERTY and object == HUMAN_WIKIDATA_ITEM:
            human_entities.add(subject)

print(f"Found {len(human_entities)} human entities.")

line_counter = 0
with open(input_file, "r", encoding="utf-8") as fin, \
     open(output_file, "w", encoding="utf-8") as fout:
    for line in fin:
        subject, _, _ = line.strip().split("\t")
        if subject in human_entities:
            fout.write(line)
            line_counter += 1

print(f"There are {line_counter} lines in {output_file}.")
