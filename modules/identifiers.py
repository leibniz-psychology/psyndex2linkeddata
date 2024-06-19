import xml.etree.ElementTree as ET
from rdflib import OWL, SKOS, Literal, URIRef, Namespace, Graph, RDF, RDFS
import modules.helpers as helpers
import modules.local_api_lookups as localapi
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

# ### Building identifier nodes for DOIs
#
# Should probably refactor to be more general, so we can use it for other identifiers as well. Needs a parameter for the identifier type.


def build_doi_identifier_node(instance, doi, graph):
    # print(f"bf:identifiedBy > bf:Doi > rdf:value: {doi}.")
    # we use the doi itself as part of the doi node uri to make it a unique node,
    # otherwise all doi values will be added to the same node.
    # make node for the identifier:
    identifier_node = URIRef("https://doi.org/" + doi)
    # give it class bf:Doi:
    graph.add((identifier_node, RDF.type, BF.Doi))
    # give it the doi as a literal value:
    graph.add((identifier_node, RDF.value, Literal(doi)))
    # attach it to the instance with bf:identifiedBy:
    graph.add((instance, BF.identifiedBy, identifier_node))


def build_urn_identifier_node(instance, urn, graph):
    # print(f"bf:identifiedBy > bf:Urn > rdf:value: {urn}.")
    # we use the urn itself as part of the urn node uri to make it a unique node,
    # otherwise all urn values will be added to the same node.
    # make node for the identifier:
    identifier_node = URIRef(urn)
    # may change this into a clickable url later, prefixed with "https://nbn-resolving.org/urn:"
    # give it class bf:Urn:
    graph.add((identifier_node, RDF.type, BF.Urn))
    # give it the urn as a literal value:
    graph.add((identifier_node, RDF.value, Literal(urn)))
    # attach it to the instance with bf:identifiedBy:
    graph.add((instance, BF.identifiedBy, identifier_node))


# ### Building "Links" as electronic locator nodes for an instance
def build_electronic_locator_node(instance, url, graph):
    # make it a uri that we can add directly! example: https://id.loc.gov/ontologies/bibframe.html#p_electronicLocator
    locator_node = URIRef(url)
    # add it to the instance_node of relationship_node via bf:electronicLocator
    # directly as a uri! No intermediary class node with a rdf:value
    # records_bf.set((locator_node, RDF.value, Literal(url, datatype=XSD.anyURI)))
    # attach it to the instance with bf:electronicLocator:
    graph.set((instance, BF.electronicLocator, locator_node))


# def make_identifier_node(resource_uri, type_prefix="BF", identifier_type="Identifier", identifier_value, identifier_node_name):
#     """
#     Create an identifier node for a resource.

#     Args:
#         resource_uri (rdflib.URIRef): The URI of the resource.
#         type_prefix (str): The prefix for the identifier type. Defaults to "BF".
#         identifier_type (rdflib.URIRef): The type of the identifier. Defaults to "Identifier".
#         identifier_value (str): The value of the identifier.
#         identifier_node_name (str): The name of the identifier node.

#     Returns:
#         rdflib.BNode: The identifier node.
#     """
#     identifier_node = URIRef(f"{resource_uri}/identifiers/{prefix}")
#     grant_bf.add((identifier_node, RDF.type, identifier_type))
#     grant_bf.add((resource_uri, BF.identifiedBy, identifier_node))
#     grant_bf.add((identifier_node, RDF.value, Literal(identifier_value)))
#     return identifier_node
