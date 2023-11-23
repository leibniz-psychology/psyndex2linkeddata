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
import mappings


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

# --- crossref api --- #
# set up friendly session by adding mail in request:
CROSSREF_FRIENDLY_MAIL = "&mailto=ttr@leibniz-psychology.org"
# for getting a list of funders from api ():
CROSSREF_API_URL = "https://api.crossref.org/funders?query="

urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}

# and a cache for the crossref api:
session_fundref = requests_cache.CachedSession(
    ".cache/requests",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)


## --- Grants --- ##


# function to build the nodes for grant/funding from STAR field GRANT
def get_bf_grants_module(work_uri, record):
    """this function takes a string and returns a funder (name and fundref doi), a list of grant number, a note with grant holder and info"""
    for grant in record.findall("GRANT"):
        # point zero: remove html entities from the field:
        grantfield = html.unescape(grant.text)
        # if the field contains these, skip it - don't even create a fundinfregerence node:
        if (
            "projekt deal" in grantfield.lower()
            or "open access funding" in grantfield.lower()
        ):
            continue
        # point one: pipe all text in the field through the DD-Code replacer function:
        grantfield = mappings.replace_encodings(grantfield)
        # make a new graph for the grant node and subnodes:
        grant_bf = Graph()
        # bind the needed namespaces:
        grant_bf.bind("bf", BF)
        grant_bf.bind("bflc", BFLC)
        grant_bf.bind("pxc", PXC)
        grant_bf.bind("pxp", PXP)
        # add a blank node for a new Contribution:
        funding_contribution_node = BNode()
        # records_bf.add((funding_contribution_node, RDF.type, BF.Contribution))
        grant_bf.add((funding_contribution_node, RDF.type, PXC.FundingReference))
        # add a blank node for the funder agent:
        funder_node = BNode()
        grant_bf.add((funder_node, RDF.type, BF.Agent))
        # add the funder agent node to the funding contribution node:
        grant_bf.add((funding_contribution_node, BF.agent, funder_node))
        # add a role to the funding contribution node:
        grant_bf.add(
            (
                funding_contribution_node,
                BF.role,
                URIRef("http://id.loc.gov/vocabulary/relators/spn"),
            )
        )

        # first, use anything before the first "|" as the funder:
        # but because the database is still messy, use a default funder name in case there
        # is no name in the field:
        funder_name = "FUNDERNAME NOT FOUND"
        # funder = {"funder_name": grantfield.split("|")[0].strip(), "funder_id": None}
        funder_name = grantfield.split("|")[0].strip()
        # add the funder name to the funder node:
        grant_bf.add((funder_node, RDFS.label, Literal(funder_name)))
        # try to look up this funder name in the crossref funder registry:
        # if there is a match, add the crossref funder id as an identifier:
        crossref_funder_id = None
        crossref_funder_id = get_crossref_funder_id(funder_name)
        if crossref_funder_id is not None:
            # add a blank node for the identifier:
            crossref_funder_id_node = BNode()
            # use our custim identifier class FundRefDoi (subclass of bf:Doi):
            grant_bf.add((crossref_funder_id_node, RDF.type, PXC.FundRefDoi))
            grant_bf.add((funder_node, BF.identifiedBy, crossref_funder_id_node))
            # add the crossref funder id as a literal to the identifier node:
            grant_bf.add(
                (crossref_funder_id_node, RDF.value, Literal(crossref_funder_id))
            )

        # then check the rest for a grant number:
        if "|n " in grantfield:
            grants = grantfield.split("|n ")[1].split(" |")[0]
            grants = extract_grant_numbers(grants)
            # add the grant number to the funding contribution node:
            for grant_id in grants:
                # add a blank node for the grant (class pxc:Grant via pxp:grant)
                grant_node = BNode()
                grant_bf.add((grant_node, RDF.type, PXC.Grant))
                # add the grant node to the funding contribution node:
                grant_bf.add((funding_contribution_node, PXP.grant, grant_node))

                # add a blank node for the identifier:
                grant_identifier_node = BNode()
                # records_bf.add((grant_identifier_node, RDF.type, BF.Identifier))
                grant_bf.add((grant_identifier_node, RDF.type, PXC.GrantId))
                grant_bf.add(
                    (grant_identifier_node, RDF.value, Literal(grant_id.strip()))
                )
                # add the identifier node to the grant node:
                grant_bf.add((grant_node, BF.identifiedBy, grant_identifier_node))
        else:
            grants = None
        # then check the rest for a grant name:
        if "|i " in grantfield:
            funding_info = grantfield.split("|i ")[1].split(" |")[0]
        else:
            funding_info = None
        if "|e " in grantfield:
            funding_recipient = (
                "Recipient(s): " + grantfield.split("|e ")[1].split(" |")[0]
            )
            # add the funding_recipient to the funding_info, if there is any:
            if funding_info is not None:
                funding_info = funding_info + ". " + funding_recipient
            else:
                funding_info = funding_recipient

        # add the funding_info (with data from |i and |e to the funding contribution node as a bf:note:
        funding_info_node = BNode()
        grant_bf.add((funding_info_node, RDF.type, BF.Note))
        grant_bf.set((funding_info_node, RDFS.label, Literal(funding_info)))
        grant_bf.add((funding_contribution_node, BF.note, funding_info_node))
        # add the funding contribution node to the work node:
        # grant_bf.add((work_uri, BF.contribution, funding_contribution_node))
        return grant_bf


def extract_grant_numbers(subfield_n_string):
    """Function takes a string and returns a list of award numbers"""
    # first, split the string on "," or ";" or "and": (first replacing all semicolons and "ands" with commas)")
    subfield_n_string = subfield_n_string.replace(" and ", ", ")
    subfield_n_string = subfield_n_string.replace(" und ", ", ")
    subfield_n_string = subfield_n_string.replace(" & ", ", ")
    subfield_n_string = subfield_n_string.replace(";", ",")
    subfield_n_string = subfield_n_string.split(", ")
    return subfield_n_string


def replace_common_fundernames(funder_name):
    """Acceptd a funder name that crossref api may not recognize, at least not as the first hit,
    and replace it with a string that will supply the right funder as the first hit"""
    # if the funder_name is in the list of funder names to replace (in index 0), then replace it with what is in index 1:
    for funder in mappings.funder_names_replacelist:
        if funder_name == funder[0]:
            funder_name = funder[1]
    return funder_name


def get_crossref_funder_id(funder_name):
    """Takes a funder name and returns the crossref funder id (Doi) for that funder name
    using the crossref api (specifically the funder (fundref) endpoint).
    """
    funder_name = replace_common_fundernames(funder_name)
    # construct the api url:
    crossref_api_url = CROSSREF_API_URL + funder_name + CROSSREF_FRIENDLY_MAIL
    # make a request to the crossref api:
    # crossref_api_request = requests.get(crossref_api_url)
    # make request to api:
    crossref_api_request = session_fundref.get(crossref_api_url, timeout=20)
    crossref_api_response = crossref_api_request.json()
    # result_count = int(crossref_api_response["message"]["total-results"])
    # if the request was successful, get the json response:

    if (
        crossref_api_request.status_code == 200
        and crossref_api_response["message"]["total-results"] >= 1
    ):
        # return the number of results:
        # print("Treffer: " + str(crossref_api_response["message"]["total-results"]))
        # return the first hit:
        # print("Erster Treffer: " + crossref_api_response["message"]["items"][0]["name"])
        # print("DOI: " + "10.13039" + crossref_api_response["message"]["items"][0]["id"])
        return "10.13039/" + crossref_api_response["message"]["items"][0]["id"]
