"""
This script converts reduced person data into RDF format using the rdflib library.
Input is a csv file of about 40k people who have published something that is indexed in PSYNDEX,
and who had an affiliation in a German-speaking country at the time of publication.
Columns of the csv: uuid, is psychologist (Y,N,U), given name, family name, name variants (separated by
semicolons in format "family name, given name(s)"), ORCID, PsychAuthorsID. 
The script creates a graph of persons data in RDF format and serializes it to a file.
It will also generate uris for each person based on their uuid, following the pattern 
"https://w3id.org/zpid/authorities/agents/persons/p_ekjfjf1485857" where the last part is a base58
encoding of the uuid, which is web-safe and can be used in URIs and is also human-readable due to the
use of the prefix "p_" and avoidance of confusable characters like 0 and O.

Modules:
    datetime.timedelta: For representing time durations.
    tqdm.auto.tqdm: For displaying progress bars.
    dateparser: For parsing dates from strings.
    requests_cache: For caching HTTP requests.
    dateparser.search.search_dates: For searching dates in strings.
    rdflib.Graph: For creating and manipulating RDF graphs.
    rdflib.Literal: For creating RDF literals.
    rdflib.namespace: For defining RDF namespaces.
    rdflib.URIRef: For creating RDF URI references.
    re: For regular expressions.
    csv: For reading and writing CSV files.

Namespaces:
    PERSONS: Namespace for person URIs.
    LOCID: Namespace for Library of Congress identifiers.
    QUAL: Namespace for qualifications.
    BF: Namespace for bibliographic framework.
    SCHEMA: Namespace for schema.org.
    GNDO: Namespace for GND ontology.
    PXC: Namespace for custom ontology classes.
    PXP: Namespace for custom ontology properties.
    GENDER: Namespace for gender vocabulary.

Graph:
    authority_persons: RDF graph for persons data.

Bindings:
    The script binds several namespaces to prefixes for use in the RDF graph.
"""
from datetime import timedelta
from encodings.base64_codec import base64_encode
from os import name
import uuid
import base58
from venv import create
from numpy import add
from tqdm.auto import tqdm
import dateparser
import requests_cache
# import modules.dicts as dicts
from dateparser.search import search_dates
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, Namespace

# from rdflib import BNode
from rdflib import URIRef

# import xml.etree.ElementTree as ET
import re
import csv


# Namespaces
PERSONS = Namespace("https://w3id.org/zpid/authorities/agents/persons/")
LOCID = Namespace("http://id.loc.gov/vocabulary/identifiers/") # gnd, orcid
QUAL = Namespace("https://w3id.org/zpid/vocabs/qualifications/")
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
SCHEMA = Namespace("https://schema.org/")
GNDO = Namespace("https://d-nb.info/standards/elementset/gnd#")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")
GENDER = Namespace("https://w3id.org/zpid/vocabs/gender/")



# load data from sources/personen.csv:
persons = []
with open("personen_uuid.csv", "r", encoding="utf-8") as file: 
    # the csv is tab separated!
    # the columns: uuid, isPsych, Nachname, GND, Vorname, GND_Var, Varianten, ORCID, PsychAuthorsID
    reader = csv.DictReader(file, delimiter="\t")
    # I want a list of dictionaries, where each dictionary represents a person. One person has the following fields:
    # example for how it should look like: {'uuid': '699dee28-d2e4-4a7f-a361-a045e8c21635', 'isPsych': 'U', 'Nachname': 'Aach', 'GND': '134173937', 'Vorname': 'Mirko', 'GND_Var': '', 'Varianten': '', 'ORCID': '0000-0002-9333-5912', 'PsychAuthorsID': ''}
    for row in reader:
        persons.append(row)
    # print(persons[0])



# create a graph of psychauthor persons:

authority_persons = Graph()

# bind namespaces:
authority_persons.bind("locid", LOCID)
authority_persons.bind("persons", PERSONS)
authority_persons.bind("bf", BF)
authority_persons.bind("schema", SCHEMA)
authority_persons.bind("gndo", GNDO)
authority_persons.bind("pxc", PXC)
authority_persons.bind("pxp", PXP)
authority_persons.bind("gender", GENDER)
authority_persons.bind("qualifications", QUAL)


def uuid_to_base58(string_uuid):
    # this expects a uuid object, but if you have a string, you can convert it to a uuid object like this:
    u = uuid.UUID(string_uuid)
    return base58.b58encode(u.bytes).decode('utf-8')

def short_encode_uuid(u):
    """
    Encode a given uuid as a shortened, url-safe and human-friendly base58 version.
    Args: 
        uuid: The uuid of the person.
    Returns:
        short_id: the encoded, shorter version to be used for uris.
    """
    short_id = uuid_to_base58(u)
    return short_id
    

def create_person_uri(u):
    """
    Create a URI for a person based on their uuid.
    Args:
        uuid: The uuid of the person.
    Returns:
        The URI for the person.
    """
    # first, convert the uuid to a base58 representation:
    person_id = short_encode_uuid(u)
    # then, create the URI:
    person_uri = PERSONS[f"p_{person_id}"]
    return person_uri

def create_preferred_name_node(graph, person_uri, family_name, given_name):
    """
    Create a preferred name RDF node for a person.
    Args:
        given_name: The given name of the person.
        family_name: The family name of the person.
    Returns:
        The preferred name for the person as a set of nodes 
        using gndo:preferredNameEntititypreferredNameEntityForThePerson,
        schema:givenName, and schema:familyName. The name object will be class/type
        gndo:NameOfThePerson. As the uri of the node, uses the uri of the person
        with the suffix "#prefname".
    """
    try:
        # authority_persons.add((person_uri, SCHEMA.name, Literal(name)))
        # hash node for the name:
        preferred_name_node = URIRef(person_uri + "#prefname")
        # print(preferred_name_node)
        graph.set((preferred_name_node, RDF.type, GNDO.NameOfThePerson))
        graph.add((preferred_name_node, SCHEMA.givenName, Literal(given_name)))
        graph.add((preferred_name_node, SCHEMA.familyName, Literal(family_name)))
        graph.add(
            (person_uri, GNDO.preferredNameEntityForThePerson, preferred_name_node)
        )
    except:
        print("couldn't add prefname")


def split_name_variants(name_variants):
    """
    Split the name variants by comma. Should be called from within 
    another function that expects the name variants to be a List. We use it in 
    create_name_variants_nodes.
    Args:
        name_variants: A List of name variants of the person, comma-serated into family name, given name.
    Returns:
        A list of tuples containing family name and given name.
    """
    split_variants = []
    # the List may contain: nothing (an empty string), or one name in the form "Doe, John", so "Family name, Given name".
    for variant in name_variants:  # iterate over the list of name variants
        # split by comma:
        name_parts = variant.split(", ")
        family_name = name_parts[0].strip() # the family name is the first part
        try:
            given_name = name_parts[1].strip()  # extract given name if available, it's the second part
        except IndexError:
            # if there's no given name, handle gracefully
            print(f"{family_name} has no given name")
            given_name = ""
        split_variants.append((family_name, given_name))
    return split_variants # example where name_variants is :
    # returns [('Doe', ' John'), ('Doe', ' Johnny'), ('Doe', ' Jonathan')]

def create_name_variants_nodes(graph, person_uri, name_variants):
    """
    Create name variants for a person, if available. Will create a node for each name variant.
    Args:
        person_uri: The URI of the person.
        name_variants: The name variants of the person as a List of strings, each string
        is a name variant in the format "family name, given name(s)". The function will
        split the name variants by comma.".
    Returns:
        The name variants for the person as a set of nodes using
        gndo:variantNameEntityForThePerson, schema:givenName, and
        schema:familyName. Give them the class/type gndo:NameOfThePerson.
        As the uri of the nodes, use the uri of the person with the suffix
        "#varname_{index+1}" where index is the index of the name variant.
    """
    split_variants = split_name_variants(name_variants)
    for index, (family_name, given_name) in enumerate(split_variants): # expects a list of tuples
        # that look like this: [(family name, given name), (family name, given name)]
        try:
            # hash node for the name:
            variant_name_node = URIRef(f"{person_uri}#varname_{index+1}")
            graph.set((variant_name_node, RDF.type, GNDO.NameOfThePerson))
            graph.add((variant_name_node, SCHEMA.givenName, Literal(given_name)))
            graph.add((variant_name_node, SCHEMA.familyName, Literal(family_name)))
            graph.add(
                (person_uri, GNDO.variantNameEntityForThePerson, variant_name_node)
            )
        except:
            print("couldn't add varname")


def create_psychologist_status_node(person_uri,is_psychologist, graph):
    """
    Create a node for the psychologist status of a person.
    Args:
        is_psychologist: The psychologist status of the person.
    Returns:
        The psychologist status for the person as a node using
        pxp:isPsychologist that is boolean: True if the person is a psychologist,
        False if the person is not a psychologist, and None if the psychologist
        status is unknown.
    """
    if is_psychologist == "Y":
        psychologist_status = True
    elif is_psychologist == "N":
        psychologist_status = False
    else:
        psychologist_status = None
    if psychologist_status is not None:
        try:
            graph.add((person_uri, PXP.isPsychologist, Literal(psychologist_status, datatype=XSD.boolean)))
        except:
            print("couldn't add isPsychologist")
    else:
        return None



def create_orcid_node(graph, person_uri, orcid):
    """
    Create a node for the ORCID of a person.
    Args:
        orcid: The ORCID of the person.
    Returns:
        The ORCID for the person as a node using bf:identifiedBy, 
        type/class: locid:orcid, and the literal value of the orcid itself
        using rdf:value.
        The node uri should be the uri of the person with the suffix "#orcid".
    """
    # if it is empty, don't add it:
    if not orcid:
        return
    try:
        # check if the orcid is valid:
        # if not, return None:
        if not re.match(r"^(\d{4}-){3}\d{3}(\d|X)$", orcid):
            print(f"{orcid} is not a valid ORCID")
            return None
        # hash node for the orcid:
        orcid_node = URIRef(person_uri + "#orcid")
        graph.set((orcid_node, RDF.type, LOCID.orcid))
        graph.add((orcid_node, RDF.value, Literal(orcid)))
        graph.add((person_uri, BF.identifiedBy, orcid_node))
    except:
        print("couldn't add orcid")

def create_psychauthors_id_node(graph, person_uri, psychauthors_id):
    """
    Create a node for the PsychAuthors ID of a person.
    Args:
        psychauthors_id: The PsychAuthors ID of the person.
    Returns:
        The PsychAuthors ID for the person as a node using pxp:psychAuthorsID
        and the literal value of the PsychAuthors ID itself using rdf:value.
        The node uri should be the uri of the person with the suffix "#psychauthorsid".
    """
    # if it is empty, don't add it:
    if not psychauthors_id:
        return
    try:
        # check if the psychauthors_id is valid: format is "p0" + 4 digits + 2 capital letters, e.g. p00775PG, p07407ML
        if not re.match(r"^p0\d{4}[A-Z]{2}$", psychauthors_id):
            print(f"{psychauthors_id} is not a valid PsychAuthors ID")
            return None
        # hash node for the psychauthors_id:
        psychauthors_id_node = URIRef(person_uri + "#psychauthorsid")
        # type/class: pxc:PsychAuthorsID
        graph.set((psychauthors_id_node, RDF.type, PXC.PsychAuthorsID))
        graph.add((psychauthors_id_node, RDF.value, Literal(psychauthors_id)))
        graph.add((person_uri, BF.identifiedBy, psychauthors_id_node))
    except:
        print("couldn't add psychauthorsid")


def create_gnd_id_node(graph, person_uri, gnd_id):
    """
    Create a node for the GND ID of a person.
    Args:
        gnd_id: The GND ID of the person.
    Returns:
        The GND ID for the person as a node using bf:identifiedBy,
        type/class: locid:gnd, and the literal value of the GND ID itself
        using rdf:value.
        The node uri should be the uri of the person with the suffix "#gnd".
    """
    # if it is empty, don't add it:
    if not gnd_id:
        return
    try:
        gnd_id_node = URIRef(person_uri + "#gndid")
        graph.set((gnd_id_node, RDF.type, LOCID.gnd))
        graph.add((gnd_id_node, RDF.value, Literal(gnd_id)))
        graph.add((person_uri, BF.identifiedBy, gnd_id_node))
    except:
        print("couldn't add gnd")
    
def create_uuid_node(graph, person_uri, uuid):
    """
    Create a node for the UUID of a person.
    Args:
        uuid: The UUID of the person.
    Returns:
        The UUID for the person as a node using bf:identifiedBy,
        and the literal value of the UUID itself using rdf:value.
        The node uri should be the uri of the person with the suffix "#uuid".
    """
    # if it is empty, don't add it:
    if not uuid:
        return
    try:
        uuid_node = URIRef(person_uri + "#uuid")
        graph.set((uuid_node, RDF.type, BF.Local))
        graph.add((uuid_node, RDF.value, Literal(uuid)))
        graph.add((person_uri, BF.identifiedBy, uuid_node))
    except:
        print("couldn't add uuid")

## The loop:

# go through all the persons in the list persons from the csv file (remember that each person is a dictionary)
for person in tqdm(persons): 
    # to only do the first 10 persons, you can do this:
#for person in tqdm(persons[:1000]):
    # create the person uri:
    person_uri = create_person_uri(person["uuid"]) 
    # add the person to the graph:
    authority_persons.add((person_uri, RDF.type, SCHEMA.Person))
    authority_persons.add((person_uri, RDF.type, BF.Person))
    # add the given name and family name:
    create_preferred_name_node(authority_persons, person_uri, family_name=person["Nachname"], given_name=person["Vorname"])
    # like above, but access the columns by their name, not by their index. "Nachname" and "Vorname":

    # I have two lists of name variants: one from the GND and one from our own local variant list. How can I add both together?
    # and then add them to the graph with the same function?
    # the create_name_variants_nodes function expects a string with semicolon-separated name variants in the format "family name, given name(s)".
    # both lists look the same. We can just add them together and then call the function.

    # create an empty List for all the name variants where we will split the names into along semicolon:
    name_variants = []

    # add the GND variants to the name variants list:
    # the GND variants are in the field "GND_Var" and are separated by semicolons, 
    # we'll split them along the comma later (into given and family name):
    if person["GND_Var"]:
        # split the name variants by semicolon:
        gnd_variants = person["GND_Var"].split(";")
        # add the name variants to the list - but don't split into family and given name yet:
        for name in gnd_variants:
            # add the name to the list:
            name_variants.append(name)
    
    # add the local variants to the name variants list:
    # the local variants are in the field "Varianten" and are separated by semicolons,
    # we'll split them along the comma later (into given and family name):
    if person["Varianten"]:
        # split the name variants by semicolon:
        local_variants = person["Varianten"].split(";")
        # add the name variants to the list - but don't split into family and given name yet:
        for name in local_variants:
            # add the name to the list:
            name_variants.append(name)

    # now check if the prefname is in the name variants list and remove it, if it is:
    # the preferred name is in the field "Vorname" and "Nachname":
    prefname = person["Nachname"] + ", " + person["Vorname"]
    # check if the preferred name is in the name variants list:
    if prefname in name_variants:
        # remove it from the list:
        name_variants.remove(prefname)
    # now we have a list of name variants that are not the preferred name.
    # finally, remove duplicates from the name variants list:
    name_variants = list(set(name_variants))

    
    # add the GND variants:

    create_name_variants_nodes(authority_persons, person_uri, name_variants) #rewrite to accept a List of names

    # todo: in the end, we need to remove duplicates from the name variants - any variants that are duplicates
    # of each other and also of the preferred name. We can do this by creating a set of all the name variants
    # and then checking if the preferred name is in the set. If it is, we can remove it from the set.


    # add the name variants from our own local variant list:
    # create_name_variants_nodes(authority_persons, person_uri, person["Varianten"])
    
    # add more name variants from GND_Var (we'll delete them later if they are duplicates):
    #create_name_variants_nodes(authority_persons, person_uri, person["GND_Var"])

    # add the ORCID:
    create_orcid_node(authority_persons, person_uri, person["ORCID"])
    # add the PsychAuthors ID:
    create_psychauthors_id_node(authority_persons, person_uri, person["PsychAuthorsID"])
    # add GND id:
    create_gnd_id_node(authority_persons, person_uri, person["GND"])
    # add the uuid as well:
    create_uuid_node(authority_persons, person_uri, person["uuid"])
    
    # add the psychologist status:
    create_psychologist_status_node(person_uri, person["isPsych"], authority_persons)        

# serialize the graph to an RDF file:
authority_persons.serialize("persons_new.ttl", format="turtle") # why does this take very long?

    
