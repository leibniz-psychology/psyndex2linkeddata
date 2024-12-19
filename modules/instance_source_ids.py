import logging

from rdflib import Graph

import modules.helpers as helpers
import modules.identifiers as identifiers
import modules.namespace as ns

graph = Graph()

graph.bind("bf", ns.BF)
graph.bind("pxc", ns.PXC)
graph.bind("pxp", ns.PXP)
graph.bind("works", ns.WORKS)
graph.bind("contenttypes", ns.CONTENTTYPES)
graph.bind("genres", ns.GENRES)
graph.bind("pmt", ns.PMT)
graph.bind("methods", ns.METHODS)


def get_instance_doi(instance, record, graph):
    # read field DOI from the record
    doi = None
    try:
        doi_field = record.find("DOI").text
    except:
        doi_field = None
    if doi_field is not None:
        # check the doi for errors:
        # returns the checked thing and the type of the thing (doi, url, unknown)
        # so if it is really a doi, we can use it as a doi, if it is a url, we can use it as a url
        if helpers.check_for_url_or_doi(doi_field)[1] == "doi":
            doi = helpers.check_for_url_or_doi(doi_field)[0]
        else:
            logging.warning(f"Warning: DOI {doi_field} is not a valid DOI.")
            # should probably check if it is a valid url and then use it as a url?
        if doi is not None:
            # add it as an identifier of class bf:Doi
            identifiers.build_doi_identifier_node(instance, doi, graph)


def get_instance_urn(instance, record, graph):
    urn = None
    # read field URN from the record
    try:
        urn_field = record.find("URN").text
    except:
        urn_field = None
    if urn_field is not None:
        # add it as a n identifier of class bf:Urn!
        identifiers.build_urn_identifier_node(instance, urn_field.strip(), graph)


def get_instance_url(instance, record, graph):
    url = None
    # read field URLI from the record
    try:
        url_field = record.find("URLI").text
    except:
        url_field = None
    if url_field is not None:
        # check the url for errors:
        # returns the checked thing and the type of the thing (doi, url, unknown)
        # so if it is really a doi, we can use it as a doi, if it is a url, we can use it as a url
        if helpers.check_for_url_or_doi(url_field)[1] == "url":
            url = helpers.check_for_url_or_doi(url_field)[0]
        else:
            logging.warning(f"URL {str(url_field)} is not a valid URL.")
            # should probably check if it is a valid doi and then use it as a doi?
        if url is not None:
            identifiers.build_electronic_locator_node(instance, url, graph)
