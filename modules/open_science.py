"""Functions for creating nodes for Open Science references of a bibframe work:
funding (GRANT), Conference (CF), Research Data (DATAC, ),
Preregistrations (PRREG), Reanalyses, Replications (REPY).
"""

import html
import re
import xml.etree.ElementTree as ET
from datetime import timedelta

import requests_cache
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, Namespace

import modules.helpers as helpers
import modules.mappings as mappings

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
