"""Functions for creating nodes for Open Science references of a bibframe work:
funding (GRANT), Conference (CF), Research Data (DATAC, ),
Preregistrations (PRREG), Reanalyses, Replications (REPY).
"""

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, Namespace
from rdflib import BNode
from rdflib import URIRef
import requests_cache
from datetime import timedelta
import xml.etree.ElementTree as ET
import html
import re
import modules.mappings as mappings
import modules.helpers as helpers


# --- namespaces --- #
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = Namespace("http://id.loc.gov/ontologies/bflc/")
MADS = Namespace("http://www.loc.gov/mads/rdf/v1#")
SCHEMA = Namespace("https://schema.org/")
WORKS = Namespace("https://w3id.org/zpid/resources/works/")
INSTANCES = Namespace("https://w3id.org/zpid/resources/instances/")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")
LANG = Namespace("http://id.loc.gov/vocabulary/iso639-2/")
LOCID = Namespace("http://id.loc.gov/vocabulary/identifiers/")
ROLES = Namespace("https://w3id.org/zpid/vocabs/roles/")
