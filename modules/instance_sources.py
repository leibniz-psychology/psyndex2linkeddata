# """ This module holds any functions that build 'sources' for the different issuance types of instances.
# - For Journal Articles: functions for the journal title, volume, issue, issn, pages and article numbers
# - for Authored and edited Books: book series and volume number (series enumeration), maybe edition
# - for Chapters: Book title and other reference data about the encompassing book
# """


# Books (their Instances) can pe part of a monographic series - or even part of more than one series (usually that is a subseries of a bigger series). We currently store the title of that series, along with the volume number of the current book within that series, in field SE. Numbering is usually separated with a comma (but not always, sigh.)
# Also, there are cases where there is no numbering at all, or a strange one that is actually the issue and volume like from a journal?
#
# What we want is something like this - a regular case where there is a series title and a volume number that follows the title after a comma:
#
# ```r
# Works:0396715_work a bf:Work;
#     # omitted: info about the work of the book itself (contributions, abstract, topics etc.)
# pxp:hasInstanceBundle
#     [
#         # omitted: info about the instance of the book itself (publisher, date, etc.)
#         bflc:relationship [a bflc:Relationship;
#         bf:hasSeries [
#                 a bf:Instance;
#                 bf:title [ a bf:Title; bf:mainTitle "Psychologie im Schulalltag"];
#                 # we don't index the series itself - so no local identifiers and no work except to say that
#                 # the work is of subclass series and it is uncontrolled/not indexed.
#                 bf:instanceOf [a bf:Series, bflc:Uncontrolled];
#             ];
#             # volume in series belongs into the relationship, not the series instance:
#             # based on https://github.com/lcnetdev/bibframe-ontology/issues/100
#             bf:seriesEnumeration "Band 5";
#         ];
#     ] .
# ```
#

import logging
import re
import xml.etree.ElementTree as ET
from ast import expr

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef

import modules.helpers as helpers
import modules.identifiers as identifiers
import modules.local_api_lookups as localapi
import modules.mappings as mappings

BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = Namespace("http://id.loc.gov/ontologies/bflc/")
WORKS = Namespace("https://w3id.org/zpid/resources/works/")
INSTANCEBUNDLES = Namespace("https://w3id.org/zpid/resources/instancebundles/")
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
graph.bind("bflc", BFLC)
graph.bind("pxc", PXC)
graph.bind("pxp", PXP)
graph.bind("works", WORKS)
graph.bind("instancebundles", INSTANCEBUNDLES)
graph.bind("contenttypes", CONTENTTYPES)
graph.bind("genres", GENRES)
graph.bind("pmt", PMT)
graph.bind("methods", METHODS)


def split_pages(page_string):
    # split into (page_start, page_end) or article_no
    # return all three
    # optional/later: calculate extent from page_start and page_end
    # example input:
    # "i-iii", "E14-E23", "B97-B109", "S389-S405", "F1-F9", "I/117-I/129", "e12655", "e66", "Art. 1"
    # "5-19", "122", "Insgesamt 162" (dann nicht splitten, sondern als extent zurückgeben!)
    # "No. e94617", "tgaa050", "No. 000010151520210111","No. 310", "No. 2", "No e99675"
    page_start = None
    page_end = None
    extent = None
    article_number = None

    startswith_lowercaseletter = re.search("^[a-z]", page_string)

    if "-" in page_string:
        try:
            pagination = page_string.split("-", maxsplit=1)
            page_start = pagination[0]
            page_end = pagination[1]
        except:
            pass

    elif page_string.startswith("Insgesamt"):
        try:
            extent = page_string.split(" ")[1]
        except:
            extent = None
    elif page_string.isdigit():
        extent = page_string
    elif (
        startswith_lowercaseletter
        or page_string.startswith("No")
        or page_string.startswith("Art")
    ):  # or any other letter, like t
        if startswith_lowercaseletter:
            try:
                # get the whole string as the article number
                article_number = page_string
            except:
                article_number = None
        else:
            try:
                article_number = page_string.split(" ", maxsplit=1)[1]
            except:
                article_number = None
    else:
        logging.warning("couldn't properly parse PAGE field: " + page_string)
    return page_start, page_end, extent, article_number


def split_series_title_volume(series_statement):
    if "," in series_statement:
        split_statement = series_statement.split(", ", maxsplit=1)

        if (
            split_statement[-1].startswith("Vol")
            or split_statement[-1].startswith("Band")
            or split_statement[-1].isdigit()
        ):
            series_volume = split_statement[-1].split(" ", maxsplit=1)[-1]
            series_title = split_statement[0]
        else:
            series_title = series_statement
            series_volume = None

    else:
        series_title = series_statement
        series_volume = None
    return series_title, series_volume


# a function to fetch JT, JBD, JFT, PAGE, ISSN, EISSN
def fetch_journal_info(record):
    # get JT as journal_title
    try:
        journal_title = record.find("JT").text
    except:
        journal_title = None
    # get JBD as journal_volume
    try:
        journal_volume = record.find("JBD").text
    except:
        journal_volume = None
    # JHFT as journal_issue
    try:
        journal_issue = record.find("JHFT").text
    except:
        journal_issue = None
    # split PAGE into (page_start and page_end) or article_no
    try:
        page_string = record.find("PAGE").text
        try:
            page_start, page_end, extent, article_number = split_pages(page_string)
        except:
            page_start = None
            page_end = None
            extent = None
            article_number = None
    except:
        page_string = None
    # get ISSN and EISSN (and fetch the issnL for them via an API?)
    try:
        print_issn = record.find("ISSN").text
    except:
        print_issn = None
    try:
        online_issn = record.find("EISSN").text
    except:
        online_issn = None
    # return them all:
    return (
        journal_title,
        journal_volume,
        journal_issue,
        page_start,
        page_end,
        extent,
        article_number,
        print_issn,
        online_issn,
    )


# a function to generate a relationship node for journal articles
def build_journal_relationship(
    resource_node,
    graph,
    journal_title,
    journal_volume,
    journal_issue,
    page_start,
    page_end,
    article_no,
    issn,
    eissn,
):
    # node for relationship:
    if journal_title is not None:
        series_enumeration = ""
        series_statement = journal_title
        relationship_node = URIRef(resource_node + "#journalrel")
        graph.add((resource_node, BFLC.relationship, relationship_node))
        graph.set((relationship_node, RDF.type, BFLC.Relationship))
        # the journal itself, including title and issns:
        journal_node = URIRef(relationship_node + "_journal")
        graph.add((relationship_node, BF.relatedTo, journal_node))
        graph.add((journal_node, RDF.type, BF.Serial))
        graph.add((journal_node, RDF.type, BF.Hub))
        # graph.set((journal_node, RDF.type, BF.Uncontrolled))
        title_node = URIRef(journal_node + "_title")
        graph.add((journal_node, BF.title, title_node))
        graph.set((title_node, RDF.type, BF.Title))
        graph.set((title_node, BF.mainTitle, Literal(journal_title)))
        # issn: if there are two, and one is eissn, we can be pretty sure that the other (ISSN) is the issnL!
        # if there is only one, it is always "ISSN", and we can't even be sure it is the print issn
        # solution: just take what they give us:
        # - if there are two, label the ISSN one with qualifier print, EISSN with online.
        #  If there is only one, and it is ISSN, don't give a qualifier at all,
        # if it is EISSN give it online.
        # then do a sparql query over the result later to check any that only have eissn, but do have a mt of print, and other discrepancies.
        if issn is not None:
            # series_statement = series_statement + " " + issn
            # make an Expression node:
            # expression_node = URIRef(journal_node + "_print")
            # graph.add((expression_node, RDF.type, BF.Work))
            # graph.add((expression_node, RDF.type, BF.Serial))
            # graph.add((journal_node, BF.hasExpression, expression_node))
            # identifiers.build_issn_identifier_node(expression_node, issn, "print", graph)
            identifiers.build_issn_identifier_node(journal_node, issn, "print", graph)
        if eissn is not None:
            # series_statement = series_statement + " " + eissn
            # make an Expression node: no, we don't, we'll ad the id to the instancebundle for now. We'll have a qualifier, anyway (differentiating expressions is only needed for the authority jpurnal hub)
            # expression_node = URIRef(journal_node + "_online")
            # graph.add((expression_node, RDF.type, BF.Work))
            # graph.add((expression_node, RDF.type, BF.Serial))
            # graph.add((journal_node, BF.hasExpression, expression_node))
            # identifiers.build_issn_identifier_node(expression_node, eissn, "online", graph)
            identifiers.build_issn_identifier_node(journal_node, eissn, "online", graph)
            # add a seriesstatement that collates all the stuff in one convenient string?
        if journal_volume is not None:
            graph.add((relationship_node, PXP.inVolume, Literal(journal_volume)))
            series_enumeration = series_enumeration + " " + journal_volume
        if journal_issue is not None:
            series_enumeration = series_enumeration + "(" + journal_issue + ")"
            graph.add((relationship_node, PXP.inIssue, Literal(journal_issue)))
        if page_start is not None:
            series_enumeration = series_enumeration + ", p. " + page_start
            graph.add((relationship_node, PXP.pageStart, Literal(page_start)))
        if page_end is not None:
            graph.add((relationship_node, PXP.pageEnd, Literal(page_end)))
            series_enumeration = series_enumeration + "-" + page_end
        if article_no is not None:
            series_enumeration = series_enumeration + ", Article number: " + article_no
            identifiers.build_articleno_identifier_node(
                relationship_node, article_no, graph
            )
        graph.add((resource_node, BF.seriesStatement, Literal(series_statement)))
        if series_enumeration != "":
            graph.add(
                (
                    relationship_node,
                    BF.seriesEnumeration,
                    Literal((series_enumeration).strip()),
                )
            )


def fetch_book_series_info(record):
    # get SE and split into series_title and series_volume
    # examples:
    #
    try:
        series_title_volume = record.find("SE").text
        if series_title_volume is not None and series_title_volume != "":
            try:
                series_title, series_volume = split_series_title_volume(
                    series_title_volume
                )
            except:
                series_title = None
                series_volume = None
    except:
        series_title_volume = None
        series_title = None
        series_volume = None
    return (series_title, series_volume)


def build_series_relationship(resource_node, graph, series_title, series_volume):
    if series_title is not None:
        series_statement = series_title
        graph.add((resource_node, BF.seriesStatement, Literal(series_statement)))
        relationship_node = URIRef(resource_node + "#seriesrel")
        graph.add((resource_node, BFLC.relationship, relationship_node))
        graph.set((relationship_node, RDF.type, BFLC.Relationship))
        # the series itself:
        series_node = URIRef(relationship_node + "_series")
        graph.add((relationship_node, BF.relatedTo, series_node))
        graph.add((series_node, RDF.type, BF.Series))
        graph.add((series_node, RDF.type, BF.Hub))
        # graph.add((series_node, RDF.type, BF.Uncontrolled))
        title_node = URIRef(series_node + "_title")
        graph.add((series_node, BF.title, title_node))
        graph.set((title_node, RDF.type, BF.Title))
        graph.set((title_node, BF.mainTitle, Literal(series_title)))
        if series_volume is not None:
            graph.add((relationship_node, BF.seriesEnumeration, Literal(series_volume)))


def fetch_surrounding_book_info(record):
    # PAGE, split into page_start, page_end using split_pages() function

    try:
        page_string = record.find("PAGE").text
        try:
            page_start, page_end, extent, article_number = split_pages(page_string)
        except:
            page_start = None
            page_end = None
            extent = None
            article_number = None
    except:
        page_string = None
    # SSDFK, if it exists (then link to book without writing all the editors etc in here)
    try:
        book_dfk = record.find("SSDFK").text
    except:
        book_dfk = None
    # if no SSDFK:
    # if book_dfk is None: nope, we'll always export the title, even if we link to a real instancebundle via dfk (because it might not be in our current dataset package)
    try:
        book_title = record.find("BIP").text
    except:
        book_title = None
    # - BIP as book_title
    # - SSSE (series title and volume)
    # - SSNE (edition)
    # - EDRPs (no affil in this field), EDRKs -> contributors with role editor, either Person or Org
    # - SSPU (wie PU)
    # - MT, MT2
    return (
        book_dfk,
        book_title,
        page_start,
        page_end,
        extent,
        article_number,
    )


def build_book_relationship(
    resource_node,
    graph,
    book_dfk,
    book_title,
    page_start,
    page_end,
    extent,
    article_number,
):

    relationship_node = URIRef(resource_node + "#bookrel")
    graph.add((resource_node, BFLC.relationship, relationship_node))
    graph.set((relationship_node, RDF.type, BFLC.Relationship))
    # the book itself:
    book_node = URIRef(relationship_node + "_book")
    graph.add((relationship_node, BF.relatedTo, book_node))
    graph.add((book_node, RDF.type, PXC.InstanceBundle))
    if book_dfk is not None:
        # add the book_dfk_node as an owl:sameAs to the book_node
        book_dfk_node = URIRef(INSTANCEBUNDLES[book_dfk])
        graph.add((book_node, OWL.sameAs, book_dfk_node))
        # add class pxc:InstanceBundle to the book_dfk_node
        graph.add((book_dfk_node, RDF.type, PXC.InstanceBundle))
    else:
        graph.add((book_node, RDF.type, BFLC.Uncontrolled))

    # if no book_dfk, add the book title to the instancebundle
    if book_title is not None:
        title_node = URIRef(book_node + "_title")
        # give bf:Title class to the title node
        graph.add((title_node, RDF.type, BF.Title))
        graph.add((title_node, BF.mainTitle, Literal(book_title)))
        graph.add((book_node, BF.title, title_node))
    # add page_start, page_end, extent, article_number
    if page_start is not None:
        graph.add((relationship_node, PXP.pageStart, Literal(page_start)))
    if page_end is not None:
        graph.add((relationship_node, PXP.pageEnd, Literal(page_end)))
    if extent is not None:
        graph.add((resource_node, PXP.extent, Literal(extent)))
    if article_number is not None:
        identifiers.build_articleno_identifier_node(
            relationship_node, article_number, graph
        )


# print(split_pages("i-iii"))
# print(split_pages("E14-E23"))
# print(split_pages("B97-B109"))
# print(split_pages("I/117-I/129"))
# print(split_pages("Insgesamt 162"))
# print(split_pages("122"))
# print(split_pages("e12655"))
# print(split_pages("zgaa050"))
# print(split_pages("Art. 1"))
# print(split_pages("No. 000010151520210111"))
# print(split_pages("No. e12656"))
# print(split_pages("No e12657"))


# print(split_series_title_volume("Heidelberger Jahrbücher Online, Band 3"))
# print(split_series_title_volume("UTB, Band 5591"))
# print(split_series_title_volume("utb, 5344"))
# print(split_series_title_volume("Schriften der KatHO NRW, Band 18"))
# print(split_series_title_volume("essentials"))
# print(split_series_title_volume("BALANCE ratgeber"))
# print(split_series_title_volume("SpringerTests"))
# print(
#     split_series_title_volume(
#         "Psychodynamische Psychotherapie mit Kindern, Jugendlichen und jungen Erwachsenen"
#     )
# )
# print(
#     split_series_title_volume(
#         "MPI-Series in human cognitive and brain sciences, Vol. 67"
#     )
# )
