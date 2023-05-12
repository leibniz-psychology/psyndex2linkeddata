#!/usr/bin/env python3
# this script adapted from https://github.com/FlorianRupp/kim-workshop-23-cicd
# originally designed for generating ontology rdf/ttl from human-readable markdown files with code blocks.
with open("ontology.md", "r", encoding="utf-8") as f:
    with open("ontology.ttl", "w", encoding="utf-8") as out:
        in_code = False
        for line in f:
            if (
                line.startswith("~~~")
                or line.startswith("```")
                or line.startswith("```r")
            ):
                in_code = not in_code
                continue
            if in_code:
                out.write(line)
