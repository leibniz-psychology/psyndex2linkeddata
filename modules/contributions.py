import xml.etree.ElementTree as ET

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef

import modules.helpers as helpers

# import modules.local_api_lookups as localapi
import modules.mappings as mappings

BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
WORKS = Namespace("https://w3id.org/zpid/resources/works/")
CONTENTTYPES = Namespace("https://w3id.org/zpid/vocabs/contenttypes/")
GENRES = Namespace("https://w3id.org/zpid/vocabs/genres/")
CM = Namespace("https://w3id.org/zpid/vocabs/carriermedia/")
PMT = Namespace("https://w3id.org/zpid/vocabs/mediacarriers/")
ISSUANCES = Namespace("https://w3id.org/zpid/vocabs/issuances/")
METHODS = Namespace("https://w3id.org/zpid/vocabs/methods/")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")
CONTENT = Namespace("http://id.loc.gov/vocabulary/contentTypes/")
MEDIA = Namespace("http://id.loc.gov/vocabulary/mediaTypes/")
CARRIER = Namespace("http://id.loc.gov/vocabulary/carriers/")


graph = Graph()

graph.bind("bf", BF)
graph.bind("pxc", PXC)
graph.bind("pxp", PXP)
graph.bind("works", WORKS)
graph.bind("contenttypes", CONTENTTYPES)
graph.bind("genres", GENRES)
graph.bind("pmt", PMT)
graph.bind("methods", METHODS)


def build_journal_person_contribution_node(contribution_id, agent_name, role):
    contribution_node = URIRef(str(contribution_id))
    graph.add((contribution_node, RDF.type, BF.Contribution))
    graph.add(
        (
            contribution_node,
            BF.role,
            URIRef(str(role)),
        )
    )
    agent_node = URIRef(str(contribution_node) + "_agent_new")
    graph.add((contribution_node, BF.agent, agent_node))
    graph.add((agent_node, RDFS.label, Literal(agent_name)))
    graph.add((agent_node, RDF.type, BF.Person))
    return contribution_node
