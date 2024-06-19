# ## Function: Create Topics, Weighted Topics from CT
#
# CTs - controlled terms from our own thesaurus - are added like this. Some are always weighted (=more important) and have an added class pxc:WeightedTopic (a subclass of bf:Topic), some are not.
#
# We use the label that is supplied in the CT field to look up the URI of the controlled term in our SKOSMOS API. We also add the preflabels from skosmos here directly.
#
#
# ```turtle
# <Work> a bf:Work;
#     bf:subject [a bf:Topic, pxc:WeightedTopic;  # topic, weighted
#         # a skos:Concept;
#         # owl:sameAs <https://w3id.org/zpid/vocabs/terms/35365>;
#         rdfs:label "Ontologies"@en, "Ontologien"@de;
#         bf:source <https://w3id.org/zpid/vocabs/terms>;
#     ];
#     bf:subject [a bf:Topic;  # a non-weighted topic
#         # a skos:Concept;
#         # owl:sameAs <https://w3id.org/zpid/vocabs/terms/60135>;
#         rdfs:label "Semantic Networks"@en, "Semantische Netzwerke"@de;
#         bf:source <https://w3id.org/zpid/vocabs/terms>;
#     ];
#     # PSYNDEX subject heading classification - not done yet
#     bf:classification [ a bf:Classification, pxc:SubjectHeading, skos:Concept;
#         rdfs:label "Professional Psychological & Health Personnel Issues"@en;
#         bf:code "3400";
#         owl:sameAs <https://w3id.org/zpid/vocabs/class/3400>;
#         bf:source <https://w3id.org/zpid/vocabs/class>;
#     ].
# ```


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


def add_controlled_terms(work_uri, record, records_bf):
    # get the controlled terms from the field CT:
    topiccount = 0
    for topic in record.findall("CT"):
        # get the content of the CT field:
        controlled_term_string = mappings.replace_encodings(topic.text.strip())
        # we need to split the string into these possible parts:
        # "|e English Label" for the English label,
        # "|d Deutsches Label" for the German label, and
        # "|g x", which, if it exists, indicates that this Topic is also weighted and should get an additional class (beside bf:Topic) of either "PXC.WeightedTopic"
        # we will use the get_Subfield function, which takes the subfield name as the parameter and returns the content of that subfield if it exists, or None if it doesn't.
        # initialize variables for the controlled term string parts:
        controlled_term_string_english = helpers.get_subfield(
            controlled_term_string, "e"
        )
        controlled_term_string_german = helpers.get_subfield(
            controlled_term_string, "d"
        )
        term_weighting = helpers.get_subfield(controlled_term_string, "g")
        if term_weighting is not None and term_weighting == "x":
            controlled_term_weighted = True
        else:
            controlled_term_weighted = False
        topiccount += 1
        # create a blank node for the controlled term and make it a class bf:Topic:
        controlled_term_node = URIRef(str(work_uri) + "#topic" + str(topiccount))
        # a ct node is a bf:Topic (and a skos:Concept - albeit without a uri identifier, because the CT "code" is not exported, only the labels); sometimes it is also a pxc:WeightedTopic:
        records_bf.add((controlled_term_node, RDF.type, BF.Topic))
        # records_bf.add((controlled_term_node, RDF.type, SKOS.Concept))
        # uncomment for export to real graph (not needed for migration to pxr):
        # add source to the controlled term node (bf:source <https://w3id.org/zpid/vocabs/terms>):
        # records_bf.add(
        #     (
        #         controlled_term_node,
        #         BF.source,
        #         URIRef("https://w3id.org/zpid/vocabs/terms"),
        #     )
        # )
        # get uri from lookup in skosmos api:
        try:
            controlled_term_uri = localapi.get_concept_uri_from_skosmos(
                controlled_term_string_english, "terms"
            )
        except:
            controlled_term_uri = None
        if controlled_term_weighted:
            records_bf.add((controlled_term_node, RDF.type, PXC.WeightedTopic))
        # add the controlled term string to the controlled term node:
        records_bf.add(
            (
                controlled_term_node,
                RDFS.label,
                Literal(controlled_term_string_english),
            )
        )
        records_bf.add(
            (
                controlled_term_node,
                SKOS.prefLabel,
                Literal(controlled_term_string_english, lang="en"),
            )
        )
        records_bf.add(
            (
                controlled_term_node,
                SKOS.prefLabel,
                Literal(controlled_term_string_german, lang="de"),
            )
        )
        records_bf.add((controlled_term_node, OWL.sameAs, URIRef(controlled_term_uri)))

        # attach the controlled term node to the work node:
        records_bf.add((work_uri, BF.subject, controlled_term_node))
