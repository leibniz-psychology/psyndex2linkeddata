from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, Namespace
from rdflib import BNode
from rdflib import URIRef
import xml.etree.ElementTree as ET
import re
import csv


# Namespaces
SCHEMA = Namespace("https://schema.org/")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")

# load data from source_tables/psychauthors-dump-2022-02/psychauthors.kerndaten.csv


# create a graph of psychauthor persons:

psychauthors = Graph()

# bind namespaces:
psychauthors.bind("schema", SCHEMA)
psychauthors.bind("pxc", PXC)
psychauthors.bind("pxp", PXP)

# create a dictionary of all persons with their ID as key
persons = {}
with open(
    "psychauthors/source_tables/psychauthors-dump-2022-02/psychauthors.kerndaten.csv",
    newline="",
    encoding="utf-8",
) as csvfile:
    reader = csv.DictReader(csvfile, delimiter=",")
    for row in reader:
        # add the row to the dictionary:
        persons[row["id"]] = row
        # print the id:
# create a dictionary of all institutions with their ID as key
# institutions = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.institut.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         institutions[row['id']] = row


# create a dictionary of all titles with their ID as key
# titles = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.titel.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         titles[row['id']] = row

# create a dictionary of all cities in stadt.csv with their ID as key
# cities = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.stadt.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         cities[row['id']] = row

# walk through all persons and create a person node for each person

for person_id in persons:
    # get the psychauthors ID of the person from field 'code':
    psychauthorsId = persons[person_id]["code"]

    # create a URI for the person:
    person_uri = URIRef("https://w3id.org/zpid/people/psychauthors/" + psychauthorsId)
    # add the person to the graph as a schema:Person:
    psychauthors.add((person_uri, RDF.type, SCHEMA.Person))

    # if the person has a family name, save it as a variable - using try:
    try:
        familyName = persons[person_id]["nachname"]
    except:
        pass

    # if the person has a given name, save it as a variable - using try:
    try:
        givenName = persons[person_id]["vorname"]
    except:
        pass
    # create a combined name from family name and given name - using try:
    try:
        name = familyName + ", " + givenName
    except:
        pass
    # add the name to the graph as a schema:name:
    try:
        psychauthors.add((person_uri, SCHEMA.name, Literal(name)))
    except:
        pass

    # try to find geb_name and save into a variable, if it exists:
    try:
        geb_name = persons[person_id]["geb_name"]
    except:
        pass

    # try to find initial and save into a variable, if it exists:
    try:
        initial = persons[person_id]["initial"]
    except:
        pass

    

# serialize the graph as turtle:
psychauthors.serialize(destination="psychauthors/psychauthors.ttl", format="turtle")
