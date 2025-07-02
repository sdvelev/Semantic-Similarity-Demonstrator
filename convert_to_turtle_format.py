input_file = "wikidata5m_human_subgraph.txt"
output_file = "wikidata5m_human_subgraph.ttl"


def to_uri(qid, is_property=False):
    if is_property:
        return f"<http://www.wikidata.org/prop/direct/{qid}>"
    else:
        return f"<http://www.wikidata.org/entity/{qid}>"

triple_counter = 0
with open(input_file, "r", encoding="utf-8") as fin, \
        open(output_file, "w", encoding="utf-8") as fout:
    fout.write("@prefix wd: <http://www.wikidata.org/entity/> .\n")
    fout.write("@prefix wdt: <http://www.wikidata.org/prop/direct/> .\n\n")

    for line in fin:
        subject, predicate, object = line.strip().split("\t")
        triple = f"{to_uri(subject)} {to_uri(predicate, is_property=True)} {to_uri(object)} .\n"
        fout.write(triple)
        triple_counter += 1

print(f"Turtle file with {triple_counter} triples written to: {output_file}.")
