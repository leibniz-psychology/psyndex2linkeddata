import html
import logging
import re
from tkinter import N

import requests
from modules import local_api_lookups
from modules import contributions
import requests_cache
from datetime import timedelta
from rapidfuzz import fuzz
import dateparser

CROSSREF_FRIENDLY_MAIL = "&mailto=ttr@leibniz-psychology.org"
# for getting a list of funders from api ():
CROSSREF_API_URL = "https://api.crossref.org/works?query="



from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

import modules.helpers as helpers
import modules.identifiers as identifiers
import modules.mappings as mappings
import modules.namespace as ns

relation_types = {
    "rd_open_access": {
        "relation": "hasResearchData",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Dataset",
        "content_type": "cod",
        "relationship_type": "ResearchData",
        "genre": "ResearchData",
        "access_policy_label": "open access",
        "access_policy_value": "http://purl.org/coar/access_right/c_abf2",
        "access_policy_concept": "https://w3id.org/zpid/vocabs/access/open",
    },
    "rd_restricted_access": {
        "relation": "hasResearchData",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Dataset",
        "content_type": "cod",
        "relationship_type": "ResearchData",
        "genre": "ResearchData",
        "access_policy_label": "restricted access",
        "access_policy_value": "http://purl.org/coar/access_right/c_16ec",
        "access_policy_concept": "https://w3id.org/zpid/vocabs/access/open",
    },
    "preregistration": {
        "relation": "hasPreregistration",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "Preregistration",
        "genre": "Preregistration",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
    "replication": {
        "relation": "isReplicationOf",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "Replication",
        "genre": "ScholarlyPaper",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "reanalysis": {
        "relation": "isReanalysisOf",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "Reanalysis",
        "genre": "ScholarlyPaper",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "isRelatedTo": {
        "relation": "isRelatedTo",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "Comment",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "hasComment": {
        "relation": "hasComment",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "Comment",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "isCommentOn": {
        "relation": "isCommentOn",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "ScholarlyPaper",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "isReplyToComment": {
        "relation": "isReplyToComment",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "Comment",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "hasReplyToComment": {
        "relation": "hasReplyToComment",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "CommentReply",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "hasReplyToCommentsOnItself": {
        "relation": "hasReplyToCommentsOnItself",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "CommentReply",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
    "hasOlderEdition": {
        "relation": "hasOlderEdition",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": None,
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
        "hasArticlePartOfCompilationThesis": {
        "relation": "hasArticlePartOfCompilationThesis",
        "relatedTo_subprop": "relatedTo",
        "work_subclass": "Text",
        "content_type": "txt",
        "relationship_type": "RelatedWork",
        "genre": "ScholarlyPaper",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
}

## urls for unknown preregistrations, replicated works, reanalyzed works
# that we find from CMs (but where no applicable PRREG or RPLIC field exists):
UNKNOWN_PREREG_URL = "https://w3id.org/zpid/dummyworks/unknown_preregistration" # or "https://unknown-preregistration.example.org"
UNKNOWN_REPLICATION_URL = "https://w3id.org/zpid/dummyworks/unknown_replicated_study" # or 
# "https://unknown-replicated-study.example.org"
UNKNOWN_REANALYSIS_URL = "https://w3id.org/zpid/dummyworks/unknown_reanalyzed_study" # or
# "https://unknown-reanalyzed-study.example.org"


# ### Building generic bf:Note nodes
#
# Will probably also need this later for other kinds of notes, such as the ones in field BN.

def build_note_node(resource_uri, note, graph):
    if note is not None and note != "":
        # make a fragment uri node for the note:
        note_node = URIRef(
            resource_uri + "_note"
        )  # TODO: how can swe decide whether to add it with _note or #note - based on whether it is a node for a main work or a subnode? Probably check for existing "#" in the resource_uri!
        graph.set((note_node, RDF.type, ns.BF.Note))
        graph.set((note_node, RDFS.label, Literal(note)))
        graph.set((resource_uri, ns.BF.note, note_node))


# ## Function: Build a Relationship Node for different types of related works
#
# Should take parameters - a dict per type (research data closed access, rd open access, ...) that has values for all the needed fields


def build_work_relationship_node(work_uri, graph, relation_type, count=None):
    # check the relation_type against the relation_types dict:
    if relation_type in relation_types:
        # if it is, get the values for the relation_type:
        relation = relation_types[relation_type]["relation"]
        relatedTo_subprop = relation_types[relation_type]["relatedTo_subprop"]
        work_subclass = relation_types[relation_type]["work_subclass"]
        # TODO: add content type and genre to the relationship node later, when we actually export the data for psychporta:
        content_type = relation_types[relation_type]["content_type"]
        genre = relation_types[relation_type]["genre"]
        relationship_type = relation_types[relation_type]["relationship_type"]
        access_policy_label = relation_types[relation_type]["access_policy_label"]
        access_policy_value = relation_types[relation_type]["access_policy_value"]
        access_policy_concept = relation_types[relation_type]["access_policy_concept"]
    # make a node for this relationship:
    
    # make it class bflc:Relationship:
    # relationship_subclass = genre[0].upper() + genre[1:] + "Relationship"
    relationship_subclass = relationship_type[0].upper() + relationship_type[1:] + "Relationship"
    # or "PreregistrationRelationship"
    relationship_bnode = URIRef(
    # use count to attach a numbering to the node so two different Relationships have unique names:
        work_uri + "#" + str(relationship_subclass) + str(count)
    )
    # or other. We can use the content of "genre" in Camelcase for this:
    # records_bf.add((relationship_bnode, RDF.type, ns.BFLC.Relationship))
    graph.add((relationship_bnode, RDF.type, ns.PXC[relationship_subclass]))

    # add a bflc:Relation (with a label and value) via bflc:relation to the relationship bnode
    # (label and value could be given as a parameter):
    # print("\tbflc:relation [a bflc:Relation ; rdfs:label 'has research data', rdf:value 'relation:hasResearchData'^^xsd:anyURI] ;")
    # relation_bnode = BNode()
    # records_bf.set((relation_bnode, RDF.type, ns.BFLC.Relation))
    # records_bf.add((relation_bnode, RDFS.label, Literal("has research data", lang="en")))
    # records_bf.add((relation_bnode, RDF.value, Literal(RELATIONS.hasResearchData)))
    graph.set((relationship_bnode, ns.BFLC.relation, URIRef(ns.RELATIONS[relation])))
    # make a bnode for the work:
    # related_work_bnode = BNode()
    related_work_bnode = URIRef(relationship_bnode + "_work")
    graph.add((related_work_bnode, RDF.type, ns.BF.Work))
    graph.add((related_work_bnode, RDF.type, URIRef(ns.BF[work_subclass])))
    # give work a content type: no need for initial migration, but later
    # records_bf.add((related_work_bnode, ns.BF.content, URIRef(CONTENTTYPES[content_type])))
    # make the content type a bf:Content:
    # records_bf.add((URIRef(CONTENTTYPES[content_type]), RDF.type, ns.BF.Content))
    # and a genre: not needed for migration, but later
    # records_bf.add((related_work_bnode, ns.BF.genreForm, URIRef(GENRES[genre])))
    # make the genreform a bf:GenreForm:
    # records_bf.add((URIRef(GENRES[genre]), RDF.type, ns.BF.GenreForm))
    # attach the work bnode to the relationship bnode with bf:relatedTo
    # (or a subproperty as given as a parameter)):
    # print("\tbf:relatedTo [a bf:Work ;")
    graph.add((relationship_bnode, ns.BF[relatedTo_subprop], related_work_bnode))
    # make a node for the instance:
    related_instance_bnode = URIRef(related_work_bnode + "_instance")
    graph.set((related_instance_bnode, RDF.type, ns.BF.Instance))
    # add subclass for electronic - not needed for initial migration, but later
    # records_bf.add((related_instance_bnode, RDF.type, ns.BF.Electronic))
    graph.add((related_work_bnode, ns.BF.hasInstance, related_instance_bnode))
    # add accesspolicy to instance:
    if access_policy_label is not None and access_policy_value is not None:
        access_policy_node = URIRef(access_policy_concept)
        graph.add((access_policy_node, RDF.type, ns.BF.AccessPolicy))
        graph.add((access_policy_node, RDFS.label, Literal(access_policy_label)))
        # add preflabels "freier Zugang" and open access - since it will always be open, we don't need to fetch from skosmos, but just use preset labels:
        graph.add(
            (
                access_policy_node,
                SKOS.prefLabel,
                Literal(access_policy_label, lang="en"),
            )
        )
        graph.add(
            (access_policy_node, SKOS.prefLabel, Literal("freier Zugang", lang="de"))
        )
        # not adding the url to coar for now, we don't need it for migration:
        # records_bf.set(
        #     (
        #         access_policy_node,
        #         RDF.value,
        #         Literal(access_policy_value, datatype=XSD.anyURI),
        #     )
        # )
        # add concept from our own vocabulary:
        # records_bf.set((access_policy_node, OWL.sameAs, URIRef(access_policy_concept)))
        graph.add(
            (related_instance_bnode, ns.BF.usageAndAccessPolicy, access_policy_node)
        )
    # in the end, return the relationship bnode so it can be attached to the work
    # records_bf.add((work_uri, ns.BFLC.relationship, relationship_bnode))
    return relationship_bnode, related_instance_bnode


# ## Functions: Add Research Data Link from DATAC and URLAI
#
# Field URLAI should only hold a doi for a psychdata dataset (these are usually, or rather, always, restricted access). This field always has a full doi link, in various prefix formats. We remove the prefix and only keep the pure doi.
#
# Field DATAC has either a subfield |u with a regular url link or a subfield |d with a doi (or both).
# The doi in DATAC is usually a pure doi, without any prefixes. But sometimes it's not!
#
# Since the data is so dirty, we make our own classficiation: we run all subfields, no matter declared Doi or URL (so from |u or |d) through our own recognition tree:
# - anything that is a pure doi (starts with "10.") will be saved as a DOI (bf:identifiedBy > bf:Doi)
# - so will anything with a pseudo url that is in reality just a DOI with a prefix (like "https://doi.org/10.1234/5678")
# - anything that seems a regular URL (with a DOI inside) will be declared a URL (bf:electronicLocator)
# - anything that is neither of the above will be ignored (or copied into a note)
#
# So we just check all subfields, see if they contain a DOI in any form, and keep that. And then check for other urls and keep those as electroniclocators (but only if they don't contain the DOI again?)
#
# In Bibframe, Research Data is modeled as a bnode bf:Work with a bf:Instance that has a bf:electronicLocator for a URL and a bf:identifiedBy for the Doi. This Work is in a bflc:Relationship to the study'S work, and the general relatedTo-subproperty should be bf:supplement. We also define a skos bflc:Relation "hasResearchData" to use as the bflc:Relationship's bflc:relation.
#
# Research Data can be (or rather, contain) either Code or a DataSet, or both. We can use the bf:genreForm to distinguish between the two, and also the Work subclass (bf:Dataset, bf:Multimedia).
#
# We also want to add the information whether the data is restricted or open access. We can do this in Bibframe with [bf_usageAndAccessPolicy](http://id.loc.gov/ontologies/bibframe/usageAndAccessPolicy) and [bf:AccessPolicy](http://id.loc.gov/ontologies/bibframe/AccessPolicy) on the Data's Instance (it is what the LoC instance-bf2marc excel table does. This info is based on MARC21 field 506).
#
# According to the github repo of the conversion script, it should look like this:
#
# ```turtle
# <Instance> bf:usageAndAccessPolicy access:open . # or access:restricted
# access:open a bf:AccessPolicy;
#     rdfs:label "open access"@en, "offener Zugang"@de;
#     # or:
#     # rdfs:label "restricted access"@en, "eingeschränkter Zugang"@de;
#     rdf:value "http://purl.org/coar/access_right/c_abf2"^^xsd:anyURI; # a link to the license or uri of the skos term: here: open access
#     # or:
#     # rdf:value "http://purl.org/coar/access_right/c_16ec"^^xsd:anyURI; # restricted
# .
# ```


def get_urlai(work_uri, record, graph):
    """Gets research data from field URLAI. This is always in PsychData, so it will be restricted access by default.
    We will also assume it to always be just research data, not code.
    """
    researchdatalink_counter = len(record.findall("DATAC"))

    for data in record.findall("URLAI"):
        urlai_field = mappings.replace_encodings(data.text.strip())
        unknown_field_content = None
        researchdatalink_counter += 1
        # build the relationship node:
        # add ~~secondary~~ only class pxc:ResearchDataRelationship to the relationship node for research data
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            graph,
            relation_type="rd_restricted_access",
            count=researchdatalink_counter,
        )
        # there are no subfields in urlai, so let's just grab the whole thing and pass it on to the url or doi checker:
        # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
        # as a doi or url:
        url_set = set()
        doi_set = set()
        # if it is a doi, run a function to generate a doi identifier node
        if helpers.check_for_url_or_doi(urlai_field)[1] == "doi":
            # build_doi_identifier_node(instance,check_for_url_or_doi(urlai_field)[0])
            doi_set.add(helpers.check_for_url_or_doi(urlai_field)[0])
        elif helpers.check_for_url_or_doi(urlai_field)[1] == "url":
            # build_electronic_locator_node(instance, check_for_url_or_doi(urlai_field)[0])
            url_set.add(helpers.check_for_url_or_doi(urlai_field)[0])
        # if the returned typ is something else "unknown", do nothing with it:
        else:
            # print("bf:note > bf:Note > rdfs:label: " + urlai_field)
            if (
                urlai_field is not None
                and helpers.check_for_url_or_doi(urlai_field)[0] is not None
                and helpers.check_for_url_or_doi(urlai_field)[0] != ""
            ):
                # add a variable
                unknown_field_content = helpers.check_for_url_or_doi(urlai_field)[
                    0
                ].strip()
                logging.info(
                    f"unknown type: {unknown_field_content}. Adding as a note."
                )
                helpers.build_note_node(
                    instance, helpers.check_for_url_or_doi(urlai_field)[0], graph
                )

        # compare all the dois in the doi_set to each item in the url set. If the url contains the doi, remove it from the url set:
        for doi in doi_set:
            for url in url_set.copy():
                if doi in url:
                    url_set.remove(url)
                    # special case: if url is osf and contains the same short code as the osf doi, also remove the url. Example: https://osf.io/kcb4d/ and 10.17605/OSF.IO/KCB4D
                elif (
                    "osf.io" in url
                    and "OSF.IO/" in doi
                    and doi.split("/")[2].lower() in url
                ):
                    logging.info(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)

        # loop through the set to build doi nodes, so we won't have duplicates:
        for doi in doi_set:
            identifiers.build_doi_identifier_node(instance, doi, graph)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, graph)

        # now attach the finished node for the relationship to the work:
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))


def get_datac(work_uri, record, graph):
    """Gets research data from field DATAC, adds a Relationship node to the work.
    Note: We define all data from this field as type "research data only, no code", and "open/unrestricted access"
    Newer data from PSYNDEXER may be something else, but for first migration, we assume all data is research data only.
    """
    # go through the list of datac fields and get the doi, if there is one:
    for index, data in enumerate(record.findall("DATAC")):
        datac_field = mappings.replace_encodings(data.text.strip())
        # build the relationship node:
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            graph,
            relation_type="rd_open_access",
            count=index + 1,
        )
        # we want to drop any duplicate dois that can occur if datac has a doi and doi url (same doi, but protocol etc prefixed)
        # for the same data that,
        # after conversion, ends up being identical. So we make a set of dois,
        # which we will add dois to, and then later loop through the set (sets are by defintion list with only unique items!):
        doi_set = set()
        url_set = set()
        # grab subfields u and d as strings and check if they are a url or a doi:
        for subfield_name in ("u", "d"):
            try:
                subfield = helpers.get_subfield(datac_field, subfield_name)
            except:
                subfield = None
            else:
                # print(subfield)
                # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
                # as a doi or url:
                # if it is a doi, run a function to generate a doi identifier node
                if (
                    subfield is not None
                    and helpers.check_for_url_or_doi(subfield)[1] == "doi"
                ):
                    # add the doi to a list:
                    doi_set.add(helpers.check_for_url_or_doi(subfield)[0])
                    # build_doi_identifier_node(instance, check_for_url_or_doi(subfield)[0])
                elif (
                    subfield is not None
                    and helpers.check_for_url_or_doi(subfield)[1] == "url"
                ):
                    # add the url to a list:
                    url_set.add(helpers.check_for_url_or_doi(subfield)[0])
                    # build_electronic_locator_node(instance, check_for_url_or_doi(subfield)[0])
                    # if the returned typ is something else "unknown", do nothing with it:
                else:
                    # print("bf:note > bf:Note > rdfs:label: " + subfield)
                    if (
                        subfield is not None
                        and helpers.check_for_url_or_doi(subfield)[0] is not None
                        and helpers.check_for_url_or_doi(subfield)[0] != ""
                    ):
                        # add a variable
                        unknown_field_content = helpers.check_for_url_or_doi(subfield)[
                            0
                        ].strip()
                        logging.info(
                            f"unknown type: {unknown_field_content}. Adding as a note."
                        )
                        build_note_node(
                            instance, helpers.check_for_url_or_doi(subfield)[0], graph
                        )
        # first, compare all the dois in the doi_set to each item in the url set. If the url contains the doi, remove it from the url set:
        for doi in doi_set:
            for url in url_set.copy():
                if doi in url:
                    url_set.remove(url)
                    # special case: if url is osf and contains the same short code as the osf doi, also remove the url. Example: https://osf.io/kcb4d/ and 10.17605/OSF.IO/KCB4D
                elif (
                    "osf.io" in url
                    and "OSF.IO/" in doi
                    and doi.split("/")[2].lower() in url
                ):
                    logging.info(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)
        for doi in doi_set:
            identifiers.build_doi_identifier_node(instance, doi, graph)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, graph)
        # now attach the finished node for the relationship to the work:
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))



# ## Function: Create nodes for PRREG (linked Preregistration Works)
#
# Field PRREG can occur multiple times per record (0..n).
# It contains a link and/or DOI to a preregistration document.
#
# Possible subfields:
# - |u URL linking to the document
# - |d DOI for the document
# - |i additional Info text
#
# There are many errors we could catch here.
# - [x] Most importantly, we can replace any " " with "_" in the |u.
# - [x] Also, |d should contain pure DOIs with prefixes, so they should start with "10." If they don't, remove any prefixes to make a "pure" DOI.
# - [x] remove or ignore any empty subfields that may exist (|u, |d, |i)
#
# Example:
#
# ```turtle
# <https://w3id.org/zpid/pub/work/0003> a bf:Work;
#     bflc:relationship
#     [
#         a bflc:Relationship;
#         bflc:relation relations:hasPreregistration;
#         bf:note [a bf:Note; rdfs:label "Australian Sample"];
#         bf:supplement # may change, not sure?
#         [
#             a bf:Work, bf:Text;
#             bf:genreForm genres:preregistration;
#             bf:content content:text;

#             bf:hasInstance
#             [
#                 a bf:Instance;
#                 bf:electronicLocator <https://osf.io/prereg1>;
#                 bf:identifiedBy [a bf:Identifier, bf:Doi; rdf:value "10.123code003"];
#                 bf:identifiedBy [a bf:TrialNumber;
# rdf:value "DRCT-123";
# bf:assigner <https://w3id.org/zpid/vocabs/trialregs/clinical-trials-gov> ;
# ];
#                 # add bf:media "computer" from rda media types
#                 bf:media <http://rdvocab.info/termList/RDAMediaType/1003>;
#                 # bf:carrier "online resource" from rda vocabulary
#                 bf:carrier <http://rdvocab.info/termList/RDACarrierType/1018>;
#             ]
#         ]
#     ]
# .
# ```

# function to build the nodes for preregistration links
def get_bf_preregistrations(work_uri, record, graph):
    # get the preregistration link from the field PREREG:
    preregistration_note = None
    unknown_field_content = None
    for index, prreg in enumerate(record.findall("PRREG")):
        # get the full content of the field, sanitize it:
        prregfield = html.unescape(mappings.replace_encodings(prreg.text.strip()))
        # use our node-building function to build the node:
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            graph,
            relation_type="preregistration",
            count=index + 1,
        )
        doi_set = set()
        url_set = set()
        for subfield_name in ("u", "d"):
            try:
                subfield = helpers.get_subfield(prregfield, subfield_name)
            except:
                subfield = None
            else:
                # print(subfield)
                # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
                # as a doi or url:
                # if it is a doi, run a function to generate a doi identifier node
                if (
                    subfield is not None
                    and helpers.check_for_url_or_doi(subfield)[1] == "doi"
                ):
                    # add the doi to a list:
                    doi_set.add(helpers.check_for_url_or_doi(subfield)[0])
                    # build_doi_identifier_node(instance, check_for_url_or_doi(subfield)[0])
                elif (
                    subfield is not None
                    and helpers.check_for_url_or_doi(subfield)[1] == "url"
                ):
                    url_set.add(helpers.check_for_url_or_doi(subfield)[0])
                    # build_electronic_locator_node(instance, check_for_url_or_doi(subfield)[0])
                    # if the returned typ is something else - "unknown", do nothing with it:
                else:
                    # print("bf:note > bf:Note > rdfs:label: " + subfield)
                    # build_note_node(instance, check_for_url_or_doi(subfield)[0])
                    if (
                        subfield is not None
                        and helpers.check_for_url_or_doi(subfield)[0] is not None
                        and helpers.check_for_url_or_doi(subfield)[0] != ""
                    ):
                        # add a variable
                        unknown_field_content = helpers.check_for_url_or_doi(subfield)[
                            0
                        ].strip()
                        logging.info(
                            f"unknown type: {unknown_field_content}. Adding as a note."
                        )
                        # add the string as a note to the instance:
                        # build_note_node(instance, check_for_url_or_doi(subfield)[0])

        # compare all the dois in the doi_set to each item in the url set. If the url contains the doi, remove it from the url set:
        for doi in doi_set:
            for url in url_set.copy():
                if doi in url:
                    url_set.remove(url)
                    # special case: if url is osf and contains the same short code as the osf doi, also remove the url. Example: https://osf.io/kcb4d/ and 10.17605/OSF.IO/KCB4D
                elif (
                    "osf.io" in url
                    and "OSF.IO/" in doi
                    and doi.split("/")[2].lower() in url
                ):
                    logging.info(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)
        # now build the doi identifier nodes for any DOIs in the set we collected:
        for doi in doi_set:
            identifiers.build_doi_identifier_node(instance, doi, graph)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, graph)
        # for the text in the |i subfield, build a note without further processing:
        try:
            preregistration_note = helpers.get_subfield(prregfield, "i")
        except:
            preregistration_note = None

        # add anything in the |i subfield as a note to the instance:
        # but if we found something unrecognizable in |u or |i, also add it to the note:
        if unknown_field_content is not None:
            build_note_node(
                relationship_node, preregistration_note + ". " + unknown_field_content
            )
        else:
            build_note_node(relationship_node, preregistration_note, graph)
        # now attach the finished node for the relationship to the work:
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))

        # add preregistration_node to work:
        # graph.add((work_uri, ns.BFLC.relationship, relationship_node))


def add_trials_as_preregs(work_uri, record, graph):
    """Checks the PRREG field for trial numbers and adds them as separate preregistrations per number, adding the recognzed registry, too.
    Also checks any existing Preregistration nodes to see if a trial is already listed via its url, and adding the trialnumber and registry to that node, otherwise creating a new Preregistration node.
    """
    trial_number_regexes = [
        (r"DRKS\d+", "drks"),
        (r"CRD\d+", "prospero"),
        (r"ISRCTN\d+", "srctn"),
        (r"NCT\d+", "clinical-trials-gov"),
        (r"actrn\d+", "anzctr"),
        (r"(?i)chictr[-a-z]*\d+", "chictr"),
        (r"kct\d+", "cris"),
        (r"ctri[\d/]+", "clinical-trial-registry-india"),
        # r("\d{4}-\d+-\d+", "euctr"),
        (r"irct[0-9a-z]+", "irct"),
        (r"isrctn\d+", "isrctn"),
        # r("", "jma"),
        # r("", "jprn"),
        (r"(?i)(nl|ntr)[-0-9]+", "dutch-trial-register"),
        (r"rbr\d+", "rebec"),
        (r"rpcec\d+", "rpec"),
        (r"slctr[\d/]+", "slctr"),
        (r"tctr\d+", "tctr"),
        (r"umin\d+", "umin-japan"),
        # r("u[\d-]+", "utn"),
    ]

    preregistrationlink_counter = len(record.findall("PRREG"))
    # for each PRREG field:
    for prreg in record.findall("PRREG"):
        # a string may contain several trial numbers from different registries.
        # match all of them!
        prereg_string = html.unescape(mappings.replace_encodings(prreg.text.strip()))
        trialnumber_matches = []
        for trial_number_regex, trialreg in trial_number_regexes:
            # match = trial_number_regex.search(prereg_string)
            # change to use a string for the regex, adding re.compile() here only once:
            # and make sure to ignore the case:
            match = re.compile(trial_number_regex, re.IGNORECASE).search(prereg_string)
            if match:
                trialnumber_matches.append(
                    [trialreg, match.group(), False]
                )  # this adds a list with the registry and the trial number to the trialnumber_matches list, and sets a boolean to False to indicate that it has not been added to a node yet.

                # print(match.group() + " matches registry: " + trialreg)
        # print(trialnumber_matches)

        # create a new Preregistration node for each match:
        for trialnumber in trialnumber_matches:
            # if it has two parts, the first is the registry, the second the trial number, the third a boolean to indicate if it has been added to a node yet.:
            if trialnumber is not None and len(trialnumber) == 3:
                # if the locator contains the trial number, add the trial number and registry to the node:
                # break this loop if we find a match
                for relationship in graph.objects(
                    subject=work_uri, predicate=ns.BFLC.relationship
                ):
                    # print(
                    #     "checking relationship node: "
                    #     + str(relationship)
                    #     + " of class "
                    #     + records_bf.value(relationship, RDF.type)
                    #     + " against trial number: "
                    #     + trialnumber[1]
                    # )

                    # if the rdf:type of the relationship node is pxc:PreregistrationRelationship:
                    if (
                        graph.value(relationship, RDF.type)
                        == ns.PXC.PreregistrationRelationship
                    ):
                        # first get the work that is attached via bf:supplement:
                        # print(
                        #     "found a PreregistrationRelationship node! "
                        #     + str(relationship)
                        # )
                        preregistration_work = graph.value(
                            subject=relationship, predicate=ns.BF.supplement, any=False
                        )
                        # then the instance of this preregistration work:
                        prereg_instance = graph.value(
                            subject=preregistration_work,
                            predicate=ns.BF.hasInstance,
                            any=False,
                        )
                        # then the electronicLocator of this instance:
                        prereg_url = graph.value(
                            subject=prereg_instance,
                            predicate=ns.BF.electronicLocator,
                            any=False,
                        )
                        # print(prereg_url)
                        # if the url contains the trial number, add the trial number and registry to the node:
                        if prereg_url is not None and trialnumber[1] in prereg_url:
                            # print("found match for trialnumber in prereg url!")
                            # get the instance node, so we can attach the trial number and registry to it:
                            # add the trial number to the node:
                            # make a node for the number:
                            trialnumber_node = URIRef(
                                str(prereg_instance) + "_trialnumber"
                            )
                            graph.add((trialnumber_node, RDF.type, ns.PXC.TrialNumber))
                            graph.add(
                                (prereg_instance, ns.BF.identifiedBy, trialnumber_node)
                            )
                            graph.add(
                                (trialnumber_node, RDF.value, Literal(trialnumber[1]))
                            )
                            # add the registry as an bf:assigner with class pxc:TrialRegistry:
                            registry_node = URIRef(
                                "https://w3id.org/zpid/vocabs/trialregs/"
                                + trialnumber[0]
                            )
                            graph.set((registry_node, RDF.type, ns.PXC.TrialRegistry))
                            graph.add((trialnumber_node, ns.BF.assigner, registry_node))
                            # after adding the trial number and registry to the instance, we can stop looking for a match and move on to the next trial number.
                            # i should remove the trial number from its array after adding it to the node, so that we don't add it twice.
                            # trialnumber_matches.remove(trialnumber)
                            # set the trialnumber as added = True
                            # maybe by adding another key to the trialnumber dict, "added" = True
                            # and then checking for that key in the next loop.
                            # ok, let's do it:
                            trialnumber[2] = True  # is that enough?
                            break  #  break the loop for the relationship node, so we can move on to the next trial number.
                # for any trialnumbers that found no match in the previous loop, we need to create a new Preregistration node:
                # however, the current code does both - it adds the number to the existing matching node, but it also creates a new node.
                # we only want to create a new node if there was no match in the previous loop.
                # so we need to add a check here to see if the trial number was added to a node in the previous loop, and only if it wasn't, create a new node.
                # if the trial number was added to a node in the previous loop, we can skip this part and move on to the next trial number.
                # how can we do this? we need to add a check to see if the trial number was added to a node in the previous loop.
                # we could add a boolean variable that is set to False at the beginning of the loop, and set to True if the trial number was added to a node.

                if trialnumber[2] is not True:
                    # first, count up the counter:
                    preregistrationlink_counter += 1
                    # make a new Preregistration node:
                    relationship_node, instance = build_work_relationship_node(
                        work_uri,
                        graph,
                        relation_type="preregistration",
                        count=preregistrationlink_counter,
                    )
                    logging.info(
                        "adding new Preregistration node for trial number: "
                        + trialnumber[1]
                    )
                    # add the trial number to the node:
                    # make a node for the number:
                    trialnumber_node = URIRef(str(instance) + "_trialnumber")
                    graph.add((trialnumber_node, RDF.type, ns.PXC.TrialNumber))
                    graph.add((instance, ns.BF.identifiedBy, trialnumber_node))
                    graph.add((trialnumber_node, RDF.value, Literal(trialnumber[1])))
                    # add the registry as an bf:assigner with class pxc:TrialRegistry:
                    registry_node = URIRef(
                        "https://w3id.org/zpid/vocabs/trialregs/" + trialnumber[0]
                    )
                    graph.set((registry_node, RDF.type, ns.PXC.TrialRegistry))
                    graph.add((trialnumber_node, ns.BF.assigner, registry_node))
                    # add the finished node for the relationship to the work:
                    graph.add((work_uri, ns.BFLC.relationship, relationship_node))
                    # add preregistration_node to work:
                    # graph.add((work_uri, ns.BFLC.relationship, relationship_node))

## Function to go through the subfields of a RPLIC field and generate a Replication. The actual node is
# created from that data elsewhere, but we need to extract the data from the subfields.
# input: a RPLIC string, which is a field from the PSYNDEXER record with subfields |u (URL), |d (DOI), |f (DFK)
# output: DFK, or DOI, or URL, or a citation string.
def generate_replication_from_rplic(rplic_string):
    """Generates a replication from a RPLIC string, which is a field from the PSYNDEXER record with subfields |u (URL), |d (DOI), |f (DFK).
    Returns a dictionary with the keys 'doi', 'url', 'dfk', and 'citation'.
    """
    skip_list = [
    "Testeintrag, wieder loeschen",
    "dittrich, K.",
    "no URL", "no URL |f  |u  |d "
    ]
    replication = {
        "doi": None,
        "url": None,
        "dfk": None,
        "citation": None,
    }
    # first, clean the whole string up from DD codes and html entities:
    rplic_string = mappings.replace_encodings(html.unescape(rplic_string.strip()))

    # then filter out anything from the skip_list, so we don't process those:
    if rplic_string in skip_list:
        #print(f"Skipping RPLIC field: {rplic_string}")
        return replication  # return early if we skip this field
    # get the subfield and main fields and fill them into variables: 
    # subfield_url, subfield_doi, subfield_dfk, mainfield_citation
    subfield_dfk = helpers.get_subfield(rplic_string, "f") if "f" in rplic_string else None
    subfield_doi = helpers.get_subfield(rplic_string, "d") if "d" in rplic_string else None
    subfield_url = helpers.get_subfield(rplic_string, "u") if "u" in rplic_string else None
    mainfield_citation = helpers.get_mainfield(rplic_string) if rplic_string != "" else None
    # if we have a valid DFK in the subfield_dfk, add it to the replication dict and stop (valid: 7 digits):
    if subfield_dfk is not None and re.match(r"^\d{7}$", subfield_dfk):
        replication["dfk"] = subfield_dfk
        #print(f"✅ Found DFK: {subfield_dfk} in RPLIC field. Stopping search.")
        return replication
    # else, if no DFK, we continue to check for a DOI or URL:
    else:
        #print("No DFK, checking for others:\n'" + str(rplic_string) + "'")
        try:
            # generate a List of tuples using the check_for_url_or_doi() function for each of the three fields, but only if they are not None - otherwise do not add them to the list:
            url_doi_list = []
            if subfield_doi is not None:
                url_doi_list.append(
                    helpers.check_for_url_or_doi(subfield_doi)
                ) 
            if subfield_url is not None:
                url_doi_list.append(
                    helpers.check_for_url_or_doi(subfield_url)
                )
            if mainfield_citation is not None:
                url_doi_list.append(
                    helpers.check_for_url_or_doi(mainfield_citation)
                )

            # remove duplicates by converting the list to a set:
            url_doi_set = set(url_doi_list)
            # print(
            #     f"Found {len([x for x in url_doi_set if x[1] in ['doi', 'url']])} valid url/doi tuples in RPLIC field: {url_doi_set}"
            # )
            # First, try to find a valid DOI
            for url_doi_tuple in url_doi_set:
                if url_doi_tuple[1] == "doi":
                    if validate_doi_against_crossref(url_doi_tuple[0], mainfield_citation):
                        replication["doi"] = url_doi_tuple[0]
                        return replication  # return early if we found a valid doi

            # If no valid DOI, try to find a URL
            for url_doi_tuple in url_doi_set:
                if url_doi_tuple[1] == "url":
                    replication["url"] = url_doi_tuple[0]
                    #print(f"✅ Found URL: {url_doi_tuple[0]} in RPLIC field, stopping.")
                    return replication

            # If neither, check for unknown/citation
            for url_doi_tuple in url_doi_set:
                if url_doi_tuple[1] == "unknown":
                    # if check_crossref_for_citation_doi(url_doi_tuple[0]) returns a doi (is not None or ""), we can use that as a doi:
                    try:
                        crossref_doi = check_crossref_for_citation_doi(url_doi_tuple[0])
                        if crossref_doi is not None and crossref_doi != "":
                            replication["doi"] = crossref_doi
                            logging.info(f"Found DOI from Crossref: {crossref_doi}"
                            )
                        else: # it returns None, so we use the url_doi_tuple[0] as a citation:
                            replication["citation"] = url_doi_tuple[0]
                    except Exception as e:
                        logging.error(f"Error checking Crossref for citation: {e}")
                        replication["citation"] = url_doi_tuple[0]
            # if we reach this point, we have no doi or url, but maybe a citation:
            if mainfield_citation is not None and mainfield_citation not in skip_list:
                replication["citation"] = mainfield_citation
        except Exception as e:
            logging.error(f"Error processing RPLIC field: {e}")
            replication["citation"] = rplic_string
    return replication  # return the replication dict with the found values
        
    

def validate_doi_against_crossref(our_doi, mainfield_citation):
    """Validates a citation against Crossref using the DOI.
    Returns True if the citation matches, False otherwise.
    imput: a doi and the citation that came with it.
    output: True if the doi can be found on crossref AND
    if the title crossref has for the doi matches our citation (using fuzzywuzzy/rapidfuzz).
    """
    similarity_threshold = 30  # set a threshold for fuzzy matching
    # Collects Crossref rejections for review
    crossref_rejections = []
    #crossref_api_url = CROSSREF_API_URL + mainfield_citation + CROSSREF_FRIENDLY_MAIL
    urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
    }

    session_crossref_doi_checker = requests_cache.CachedSession(
        ".cache/requests",
        allowable_codes=[200, 404],
        expire_after=timedelta(days=30),
        urls_expire_after=urls_expire_after,
    )
    
    #print(f"- Validating DOI: {our_doi} against citation: '{mainfield_citation}'")
    if our_doi is None or our_doi == "":
        logging.warning("No DOI provided for validation.")
        return False
    elif mainfield_citation is None or mainfield_citation == "" or mainfield_citation.startswith("http") or mainfield_citation.startswith("10."):
        # if the citation is empty or just a url or doi, we cannot validate it against crossref, so we return True, we assume it is valid, because that is all we have
        logging.warning("No valid citation provided for validation.")
        #print(f"✅ Crossref can't compare empty titles, so we assume the DOI {our_doi} is valid.")
        return True
    try: #send doi we have on file to crossref and check if it matches the citation
        response = session_crossref_doi_checker.get(
            "https://api.crossref.org/works/" + our_doi,
            timeout=20
        )
        # print the api url we are creating:
        # print(f"Crossref API URL: {response.url}")
        if response.ok:
            item = response.json().get('message')
            if item is not None:
                title = item.get('title', [''])[0]
                authors = ', '.join([a.get('family', '') for a in item.get('author', []) if 'family' in a])

                crossref_str = f"{title} {authors}".lower()
                citation_str = mainfield_citation.lower()

                similarity = fuzz.token_sort_ratio(crossref_str, citation_str)

                if similarity >= similarity_threshold:  # threshold for fuzzy matching
                    #print(f"✅ Crossref says this DOI has the same title (similarity={similarity}): {title}")
                    return True  # Accept match
                else:
                    crossref_rejections.append({
                        'doi': our_doi,
                        'crossref_title': title,
                        'crossref_authors': authors,
                        'similarity': similarity
                    })
                    #print(f"⚠️ Crossref says this DOI {our_doi} has a different title (similarity={similarity}): {title}")
                    return False  # Reject match
    except requests.exceptions.RequestException as e:
        logging.error(f"Error validating DOI against Crossref for {our_doi}: {e}")
        return False
    

    

def check_crossref_for_citation_doi(citation_string, similarity_threshold=30):
    """Checks Crossref for a DOI for a given citation string.
    Also checks if the title of the citation matches the title of the work as archived in Crossref (using fuzzywuzzy/rapidfuzz). If they are too different (>30%), we return None.
    Returns the DOI if found, None otherwise.
    Note: only check against the citation_string if it is not None or empty aside from a url or doi,
    which is the case for these examples:
    - 'https://doi.org/10.1016/j.tate.2021.103346'
    - '10.1037/pspp0000263'
    - ''

    """
   
    crossref_rejections = []
    #crossref_api_url = CROSSREF_API_URL + mainfield_citation + CROSSREF_FRIENDLY_MAIL
    urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
    }

    session_crossref_doi_finder = requests_cache.CachedSession(
        ".cache/requests",
        allowable_codes=[200, 404],
        expire_after=timedelta(days=30),
        urls_expire_after=urls_expire_after,
    )
    #similarity_threshold = 30  # set a threshold for fuzzy matching
    try:
        response = session_crossref_doi_finder.get(
            CROSSREF_API_URL,
            params={'query.bibliographic': citation_string, 'rows': 1, 'mailto': CROSSREF_FRIENDLY_MAIL},
            timeout=20
        )
        if response.ok:
            items = response.json().get('message', {}).get('items', [])
            if items:
                item = items[0]
                doi = item.get('DOI')
                title = item.get('title', [''])[0]
                authors = ', '.join([a.get('family', '') for a in item.get('author', []) if 'family' in a])

                crossref_str = f"{title} {authors}".lower()
                citation_str = citation_string.lower()

                similarity = fuzz.token_sort_ratio(crossref_str, citation_str)

                if similarity >= similarity_threshold:
                    print(f"✅ Crossref match accepted (similarity={similarity}): {title}")
                    return doi  # Accept match
                else:
                    crossref_rejections.append({
                        'original': citation_string,
                        'doi': doi,
                        'crossref_title': title,
                        'crossref_authors': authors,
                        'similarity': similarity
                    })
                    print(f"⚠️ Crossref match rejected (similarity={similarity}): {title}, saving as plain citation.")
                    return None  # Reject match
    except requests.exceptions.RequestException as e:
        logging.error(f"Error checking Crossref for DOI for {citation_string}: {e}")
        return None  # Return None if there was an error
    
## function to go through all RPLIC fields in a record and build nodes for each replication.
def get_rplic_replications(work_uri, graph, rplic_field):
    """Gets replication objects from the RPLIC fields in a record.
    Each Replication object is a dictionary with the keys 'doi', 'url', 'dfk', and 'citation'.
    It expects a list of RPLIC fields, at least one. To get these out of a record, 
    use the record.findall("RPLIC") method and then we need the text content, so .text.
    It will then build a node for each replication object, and attach it to the work_uri.
    There will only ever be one rplic field per record, right?
    """

    rplic_string = html.unescape(mappings.replace_encodings(rplic_field.strip()))
    # get object from the rplic_string:
    replication = generate_replication_from_rplic(rplic_string)
    # already build a node for the replicated work, to which we can then attach identifiers/other properties for dfk, doi, url, or citation: (but only if the replication object has at least one of those properties set)
    if replication["doi"] is None and replication["url"] is None and replication["dfk"] is None and replication["citation"] is None:
        logging.warning(f"No valid identifier found in RPLIC field: {rplic_string}")
    else: # we have at least one valid identifier, so we can build a node for the replication:
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            graph,
            relation_type="replication",
            count=1,  # we can use a count of 1 here, since we only expect one replication per work.
        ) # the function returns a relationship node and an instance node for the replication. But we may need an instancebundle, too, so we can attach the dfk (studyId) to it. Maybe it is ok to use the work to attach the dfk to it?

        # if the replication object has a DFK, we can build an identifier node for the instancebundle with the DFK:
        if replication["dfk"] is not None:
            # build a DFK identifier node for the instance:
            # NOTE: for now, we will attach the DFK to the instance, even though it really belongs to the instancebundle.
            # It is not time efficient to rewrite the node creation function to handle instancebundles, so we will just attach it to the instance for now - since it is only
            # for initial data migration. In the future, links to existing works will be handled differently (by linking
            # the work uri directly to the replicating work, not by attaching the DFK to the instancebundle).
            identifiers.build_dfk_identifier_node(instance, replication["dfk"], graph)
        # if the replication object has a DOI, we can build a DOI identifier node for the instance:
        elif replication["doi"] is not None:
            identifiers.build_doi_identifier_node(instance, replication["doi"], graph)
        # if the replication object has a URL, we can build an electronic locator node for the instance:
        elif replication["url"] is not None:
            identifiers.build_electronic_locator_node(instance, replication["url"], graph)
        # if the replication object has a citation, we can build a preferredCitation node for the instance:
        elif replication["citation"] is not None:
            # build a preferredCitation node for the instance:
            # identifiers.build_preferred_citation_node(work_uri, replication["citation"], graph)
            # let's do it right here, since it is dead simple and just a literal property:
            graph.add(
                (instance, ns.BF.preferredCitation, Literal(replication["citation"]))
            )
        else:
            logging.warning(f"No valid identifier found in RPLIC field: {rplic_string}")

        # now attach the finished relationship node, including instance and identifiers to the work:
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))


def build_empty_replication_reanalyis_node(work_uri, graph, relation_type):
    """Builds an empty replication reanalysis node for a work.
    This is used to indicate that the work is a replication or reanalysis, but no specific replication data is available.
    For cases where the cm says something is a replication or a reanalysis, but no specific replication data is available (because no RPLIC field was found).
    """
    # create a new node for the replication reanalysis:
    relationship_node, instance = build_work_relationship_node(
        work_uri,
        graph,
        relation_type, # expects either "reanalysis" or "replication"
    )
    # add a generic url to the instance, so it can be found in the graph:
    if relation_type == "replication":
        # add a generic url to the instance, so it can be found in the graph:
        identifiers.build_electronic_locator_node(
            instance, UNKNOWN_REPLICATION_URL, graph
        )
    elif relation_type == "reanalysis":
        # add a generic url to the instance, so it can be found in the graph:
        identifiers.build_electronic_locator_node(
            instance, UNKNOWN_REANALYSIS_URL, graph
        )       
    else:
        logging.error(
            f"Unknown relation type for replication reanalysis node: {relation_type}. Expected 'replication' or 'reanalysis'."
        )
        # dont add any electroniclocator
    
    # add the relationship node to the work:
    graph.add((work_uri, ns.BFLC.relationship, relationship_node))


def build_empty_preregistration_node(work_uri, graph):
    """Builds an empty preregistration node for a work.
    This is used to indicate that the work is a preregistration, but no specific preregistration data is available.
    For cases where the cm says something has a preregistration, but no specific preregistration data is available (because no PRREG field was found).
    """
    # create a new node for the preregistration:
    relationship_node, instance = build_work_relationship_node(
        work_uri,
        graph,
        relation_type="preregistration",
    )
    # add a generic url to the instance, so it can be found in the graph:
    identifiers.build_electronic_locator_node(
        instance, UNKNOWN_PREREG_URL, graph
    )
    
    # add the relationship node to the work:
    graph.add((work_uri, ns.BFLC.relationship, relationship_node))

def handle_other_relations(relationship_type):
    # in case of books, compilation theses and "else" (any other cms), we
    # want to handle all of them the same way, but i don't want to repeat 
    # the same else condition 3 times, so we can just make a function
    # takes: the relationship type, returns: the desired new relationship type
    # if the reltype is "Comment", we replace it with "hasComment":
    if relationship_type == "Comment":
        relationship_type = "hasComment"
        # and if it is "Reply", we replace it with "hasReplyToCommentsOnItself:
    elif relationship_type == "Reply":
        relationship_type = "hasReplyToCommentsOnItself"
    # if it is Original or empty, we replace it with "isRelatedTo":
    elif relationship_type == "Original" or relationship_type == None:
        relationship_type = "isRelatedTo"
    # for any other case, we set the type to "isRelatedTo", which is the default:
    else:
        relationship_type = "isRelatedTo"
    return relationship_type

def build_rels(record, work_uri, graph):
    ## access BE, BN and CM fields to inform or override the relation type found in REL |b
    # do we want to make a function that makes all rels for this work? Yes!
    # so we go through all relas in the record.
    # get the BE, BN and the three relevant CM fields from the record:
    # set book to true if we find BE with text SM or SS:
    book = False
    compilation_thesis = False
    has_cm_comment = False
    has_cm_comment_reply = False
    has_cm_comment_appended = False
    if record.find("BE") is not None and record.find("BE").text == "SS" or record.find("BE").text == "SM":
        book = True
    if record.find("BN") is not None:
        if record.find("BN").text is not None and record.find("BN").text.startswith("Kumu"):
            compilation_thesis = True
            print("Found BN field with Kumu, setting compilation_thesis to True.")
    # go through all the CM fields and set the flags accordingly:
    for cm_field in record.findall("CM"):
        if cm_field.text is not None:
            if cm_field.text.startswith("|c 14100"): # comment
                has_cm_comment = True
            elif cm_field.text.startswith("|c 14110"): # comment reply
                has_cm_comment_reply = True
            elif cm_field.text.startswith("|c 14120"):  # comment appended
                has_cm_comment_appended = True
    # now we have all the info, go through the REL field and build the relations:
    for index,rel_field in enumerate(record.findall("REL")):
         
        # if the REL field is empty, we can skip it:
        if rel_field is None or rel_field.text is None:
            print("Skipping REL field because it is empty.")
            continue
        # if the REL field is not empty, we can process it:
        rel_string = rel_field.text.strip()
        ## first, make empty REL object:
        related_work = {
            "dfk": None,  # DFK of the related work
            "doi": None,  # DOI of the related work, if available
            "url": None,  # URL of the related work, if available
            "citation": None,  # citation of the related work, if available
            "relationship_type": None,  # type of relationship, e.g. "Original", "Reply", "Comment" etc.
        }
        # strip and clean it up first:
        rel_string = html.unescape(mappings.replace_encodings(rel_string.strip()))
        # if it starts with |b and there is no other subfield (# count of "|"" symbols is just 1), we can ignore it.
        if rel_string.startswith("|b") and rel_string.count("|") == 1 or rel_string == "":
            print(f"Skipping REL because empty: {rel_string}")
            return None # stop and return early, since there is nothing to extract here.
        # if it instead starts with a DFK (7-digit number), we can just return that and the relationship type.:
        elif rel_string[:7].isdigit():
            related_work["dfk"] = rel_string[:7]
            print(f"Found DFK: {related_work['dfk']}")
        else:
            # these are the special cases where there is no DFK, but we still want to extract the relationship type and other information.
            # first, check for a hidden doi anywhere in the string.
            # we have a neat function for that: check_for_url_or_doi(string)
            # we can expect just one doi or url in the whole string, so we can just use the first one.
            doi_or_url = helpers.check_for_url_or_doi(rel_string)
            if doi_or_url:
                # if the type is doi, we can just set it as the doi for our object:
                if doi_or_url[1] == "doi":
                    related_work["doi"] = doi_or_url[0]
                    print(f"Found DOI: {related_work['doi']}")
                # if the type is url, we can just set it as the url for our object:
                elif doi_or_url[1] == "url":
                    related_work["url"] = doi_or_url[0]
                    print(f"Found URL: {related_work['url']}")
                else: # if no doi or url, we need to send the title in |t to crossref to get the doi. Use the research_info.validate_doi_against_crossref function.
                    try:
                        title = helpers.get_subfield(rel_string, "t") 
                    except ValueError:
                        title = None
                    try:
                        author = helpers.get_subfield(rel_string, "a")
                    except ValueError:
                        author = None
                    try:
                        year = helpers.get_subfield(rel_string, "j")
                    except ValueError:
                        year = None
                    try:
                        source = helpers.get_subfield(rel_string, "q")
                    except ValueError:
                        source = None
                    # concatenate into the semblance of a citation:
                    if title and author and year and source:
                        citation = f"{author}: {title}; {year}; {source}"
                    elif title and author and year:
                        citation = f"{author}: {title}; {year}"
                    elif title and author:
                        citation = f"{author}: {title}"
                    elif title and year and source:
                        citation = f"{title}; {year}; {source}"
                    elif title and year:
                        citation = f"{title}; {year}"
                    elif title:
                        citation = title
                    else:
                        citation = None
                    try:
                        related_work["doi"] = check_crossref_for_citation_doi(
                            citation, similarity_threshold=60  # low similarity threshold to get most of the RELs
                        )
                        if related_work["doi"] is not None:
                            print(f"Found DOI via Crossref: {related_work['doi']}")
                        else:
                            print(f"No DOI found via Crossref for citation: {citation}")
                            related_work["citation"] = citation
                            print(f"Using citation as fallback: {related_work['citation']}")
                    # if there is an error, we can just use the citation as fallback:
                    except:
                        print(f"Error checking Crossref for DOI: {citation}")
                        related_work["citation"] = citation
                        print(f"Using citation as fallback: {related_work['citation']}")
        # Now we need to extract the relation type from subfield |b. If there is no |b, we assume "Original", probably?
        # get subfield |b, if it exists:
        try:
            related_work["relationship_type"] = helpers.get_subfield(rel_string, "b")
        # if there is no |b, we assume "Original" (or just empty, if we don't know):
        except ValueError:
            # if there is no |b, we assume "Original"
            related_work["relationship_type"] = "Original" 

        ## This is where some more magic needs to happen based on our flags from the beginning of the function:
        if book: ## any books (BE=SM or SS) can have reltypes "Original", which should by replaced by our new relationship "hasOlderEdition"
            if related_work["relationship_type"] == "Original":
                # if the work is a book, we can replace the relationship type with "hasOlderEdition"
                related_work["relationship_type"] = "hasOlderEdition"
            # TODO: what about other relationship types, e.g. when the book is a comment or a reply? Currently, we don't even check for that.
            else:
                related_work["relationship_type"] = handle_other_relations(related_work["relationship_type"])
        elif compilation_thesis:
            if related_work["relationship_type"] == "Original":
            # if the work is a compilation thesis, we can replace the relationship type with "hasArticlePartOfCompilationThesis"
                related_work["relationship_type"] = "hasArticlePartOfCompilationThesis"
            else:
                related_work["relationship_type"] = handle_other_relations(related_work["relationship_type"])
        elif has_cm_comment:  # if the work is a comment, and the relationship type is "Comment" or "Original" we replace it with "isCommentOn":
            if related_work["relationship_type"] == "Comment" or related_work["relationship_type"] == "Original":
                related_work["relationship_type"] = "isCommentOn"
            # if it is empy or "Reply", we replace it with "hasReplyToComment":
            elif related_work["relationship_type"] == None or related_work["relationship_type"] == "Reply":
                related_work["relationship_type"] = "hasReplyToComment"
        elif has_cm_comment_reply:  # if the work is a comment reply, and the reltype is "Comment" OR "Reply" or empty-> `isReplyToComment`
            if related_work["relationship_type"] == "Comment" or related_work["relationship_type"] == "Reply" or related_work["relationship_type"] == None:
                related_work["relationship_type"] = "isReplyToComment"
            # and if it is "Original" we replace it with the new, weird relationship type "hasReplyToCommentsOnItself":
            elif related_work["relationship_type"] == "Original":
                related_work["relationship_type"] = "hasReplyToCommentsOnItself"
        elif has_cm_comment_appended:  # if the work is a comment appended, with any reltype, we replace it with "isCommentOn":
            related_work["relationship_type"] = "isCommentOn"
        # for any other cm, we have some cases, depending on reltype, as well:
        else:
            related_work["relationship_type"] = handle_other_relations(related_work["relationship_type"])
        print(f"Found relationship type: {related_work['relationship_type']} in REL field: {rel_string}")
        # we now have a related_work dictionary with the extracted information, which we can use to generate a relationship node set. 
        
        # let's build the relationship node for the related work:
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            graph,
            relation_type=related_work["relationship_type"],
            count = index+1 # we'll use the index of the loop to count the relationships
        )
        # now we can add the identifiers to the instance node:
        if related_work["dfk"] is not None:
            # if we have a DFK, we can build a DFK identifier node for the instance:
            identifiers.build_dfk_identifier_node(instance, related_work["dfk"], graph)
        elif related_work["doi"] is not None:
            # if we have a DOI, we can build a DOI identifier node for the instance:
            identifiers.build_doi_identifier_node(instance, related_work["doi"], graph)
        elif related_work["url"] is not None:
            # if we have a URL, we can build an electronic locator node for the instance:
            identifiers.build_electronic_locator_node(instance, related_work["url"], graph)
        elif related_work["citation"] is not None:
            # if we have a citation, we can build a preferredCitation node for the instance:
            graph.add(
                (instance, ns.BF.preferredCitation, Literal(related_work["citation"]))
            )
        else:
            logging.warning(
                f"No valid identifier found in REL field: {rel_string}"
            )
        # now we can add the relationship node to the work:
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))

## Thesis information and node generation:

def get_thesis_info(record):
    """
    Extracts thesis information from the given record.

    Args:
        record: A record with fields relevant for generating thesis information.

    Returns:
        dict: A dictionary with extracted thesis information. If the record does not represent a thesis, all values in the dictionary will be None.
    """
    # TODO: rewrite so this takes not straight fields from a dict, but the fields from the XML, using find for GRAD, HRF, and findall for KRF.
    thesis_infos = {
    "degreeGranted": None,
    "institute": None, # including place, should be written in Affiliation of first author, if not already there
    # we need to get the ror id and from there, especially if not in Affiliation:
    "institute_ror_id": None, # ror id of the institute, if available
    "institute_country": None, # country of the institute, if available
    "institute_country_geonames": None, # country of the institute, if available, as geonames id
    "thesisAdvisor": None, # first supervisor, optional, but at most one should be present
    "thesisReviewers": [], # second supervisor, optional, but can also be several
    "dateDegreeGranted": None, # date of the PhD thesis, optional?
    }

    # get BE field from the thesis record:
    try:
        be_field = record.find("BE").text.strip()
    except AttributeError:
        be_field = None  # if BE field is not present, set to None
    # get DT and DT2:
    try:
        dt_field = record.find("DT").text.strip()
    except AttributeError:
        dt_field = None
    try:
        dt2_field = record.find("DT2").text.strip()
    except AttributeError:
        dt2_field = None
    # check if this is a thesis, based on BE, DT and DT2:#

    if be_field == "SH" or dt_field == "61" or dt2_field == "61":

        # get dfk for logging purposes:
        try:
            dfk = record.find("DFK").text.strip()
        except AttributeError:
            dfk = None
        
        print(f"\n{dfk} is a thesis; processing it...")

        # get GRAD field:
        try:
            grad_field = record.find("GRAD").text.strip()
        except AttributeError:
            grad_field = None  # if GRAD field is not present, set to None
        # get PD field:
        try:
            pd_field = record.find("PD").text.strip()
        except AttributeError:
            pd_field = None  # if PD field is not present, set to None
        # get first AUP field:
        try:
            aup_field = record.find("AUP").text.strip() # gets the first AUP field, which is the first author.
        except AttributeError:
            aup_field = None
        # get INST field:
        try:
            inst_field = record.find("INST").text.strip()
        except AttributeError:
            inst_field = None  # if INST field is not present, set to None
        # get ORT field:
        try:
            ort_field = record.find("ORT").text.strip()
        except AttributeError:
            ort_field = None
        # get HRF field:
        try:
            hrf_field = record.find("HRF").text.strip()
        except AttributeError:
            hrf_field = None
        # get KRFs as a list:
        try:
            krf_fields = [krf.text.strip() for krf in record.findall("KRF")]
        except AttributeError:
            krf_fields = []

        # get degree granted:
        if grad_field is not None:
            thesis_infos["degreeGranted"] = grad_field
            print("Degree granted: {}".format(thesis_infos["degreeGranted"]))
        else:
            print("No degree found.")

        # check AUP affiliation for institute and place, otherwise concatenate INST and ORT:
        if aup_field is not None: # we can only add the institute as an affiliation if there is a first author (first AUP), so no need to check for AUPs with no first author.
        # it contains a pipe |i, which is the subfield for institute:
            if "|i" in aup_field:
            # get subfield i:
                try:
                    # use helpers.get_subfield(field, i):
                    thesis_infos["institute"] = helpers.get_subfield(aup_field, "i").strip()
                    print("Institute from AUP: {}".format(thesis_infos["institute"]))
                except KeyError:
                    print("No institute found in AUP.")
            else:
                print(f"No institute found in AUP, trying INST + ORT instead: {aup_field}, INST: {inst_field}, ORT: {ort_field}")
                # if no institute found in AUP, try INST + ORT:
                if inst_field is not None and ort_field is not None: 
                    print(f"Found INST and ORT fields, trying to concatenate them: {inst_field} + {ort_field}")
                    # try to concatenate sensibly: first check INST if it has a comma, than insert ORT before the comma:
                    if "," in inst_field:
                        # split INST at the comma, take the first part and add ORT and then the rest of INST:
                        print("Found comma in INST field, concatenating with ORT.")
                        # split INST at the comma:
                        # we assume that the first part is the institute name and the second part is the city:
                        # e.g. "University of Example, Example City"
                        # so we take the first part and add ORT to it:
                        thesis_infos["institute"] = inst_field.split(",")[0].strip() + " " + ort_field.strip() + ", " + inst_field.split(",")[1].strip()
                    else:
                        # just concatenate INST and ORT:
                        thesis_infos["institute"] = inst_field.strip() + " " + ort_field.strip()
                    print("Institute from INST + ORT: {}".format(thesis_infos["institute"]))
                elif inst_field is not None and ort_field is None:
                    # if only INST is present, use that:
                    thesis_infos["institute"] = inst_field.strip()
                elif inst_field is None and ort_field is not None:
                    # if only ORT is present, use that:
                    thesis_infos["institute"] = ort_field.strip()
                else:
                    print("No institute found in AUP, INST or ORT.")
            # if we have an institute, get the ror-id from the api, as well as the country:
            if thesis_infos["institute"]:
                # get the ror-id and country from the api;
                # use get_ror_id_from_api in main program:
                try:
                    ror_id = local_api_lookups.get_ror_id_from_api(thesis_infos["institute"])
                    thesis_infos["institute_ror_id"] = ror_id
                    print("ROR ID: {}".format(thesis_infos["institute_ror_id"]))
                    # if we have a ror id, get the country from the api:
                    try:
                        institute_country = local_api_lookups.get_ror_org_country(ror_id)
                        thesis_infos["institute_country"] = institute_country
                        print("Institute country: {}".format(thesis_infos["institute_country"]))
                        # look up geonames id for the country in mappings.geonames_countries -
                        # format is for each country in that table: ("Germany", "2921044", "DE")
                        # if thesis_infos["institute_country"]:
                        #     try:
                        #         # use funtion helpers.country_geonames_lookup
                        #         geonames_id = helpers.country_geonames_lookup(thesis_infos["institute_country"])
                        #         thesis_infos["institute_country_geonames"] = geonames_id[1]
                        #         print("Institute country geonames id: {}".format(thesis_infos["institute_country_geonames"]))
                        #     except Exception as e:
                        #         print(f"Error getting geonames id for country {thesis_infos['institute_country']}: {e}")
                    except Exception as e:
                        print(f"Error getting institute country: {e}")
                except Exception as e:
                    print(f"Error getting ROR ID: {e}")
            else:
                print("No institute found, cannot get ROR ID or country.")

        # get HRF:
        if hrf_field is not None:
            # split into given and family name, if possible
            thesis_infos["thesisAdvisor"] = helpers.split_family_and_given_name(hrf_field)
            print("Hauptreferent: {}".format(thesis_infos["thesisAdvisor"]))
        else:
            print("No HRF found.")
        
        # get KRFs:
        if krf_fields is not None and len(krf_fields) > 0:
            for count,krf in enumerate(krf_fields):
                thesis_infos["thesisReviewers"].append(helpers.split_family_and_given_name(krf.strip()))
                print("Nebenreferent {}: {}".format(count+1,thesis_infos["thesisReviewers"][-1]))
        else:
            print("No KRFs found.")
        # getting a date of the thesis:
        try:
            dateDegreeGranted =  pd_field  # PD is the date of the thesis, if it exists
            # check if this really contains any digits, otherwise, this won't be a date (e.g. "N. N."):
            if not re.match(r"^\d", dateDegreeGranted):
                raise ValueError(f"Invalid date format: {dateDegreeGranted}")
                # and move on to the exception handling below
                
            # parse the date: it is usally formatted like "08.06.2021", but sometimes we have just the year "1999" or an abbreviated year "11.12.99"
            # parse and convert this to the yyyy-mm-dd format:
            dateDegreeGranted = dateparser.parse(dateDegreeGranted, settings={'PREFER_DATES_FROM': 'past','PREFER_DAY_OF_MONTH': 'first','PREFER_MONTH_OF_YEAR': 'first'}).strftime("%Y-%m-%d")
            print(f"Parsed date: {dateDegreeGranted}")
            # write into thesis_infos:
            thesis_infos["dateDegreeGranted"] = dateDegreeGranted
        except:
            print(
                f"parsedate: couldn't parse {str(dateDegreeGranted)} for {dfk}! Trying to use PROMY instead!"
            )
            try:
                # get PROMY field
                try:
                    promy_field = record.find("PROMY").text.strip()
                except AttributeError:
                    promy_field = None  # if PROMY field is not present, set to None
                dateDegreeGranted =  promy_field  # PROMY is the year of the thesis, if it exists
                print(f"Using PROMY for {dfk}: {dateDegreeGranted}")
                # write into thesis_infos:
                thesis_infos["dateDegreeGranted"] = dateDegreeGranted
            except:
                print(
                    f"no PROMY found for {dfk}! Using PY instead!"
                )
                try:
                    # get PY field
                    py_field = record.find("PY").text.strip()
                    dateDegreeGranted = py_field  # PY is the year of the thesis, if it exists
                    print(f"Using PY for {dfk}: {dateDegreeGranted}")
                    # write into thesis_infos:
                    thesis_infos["dateDegreeGranted"] = dateDegreeGranted
                except AttributeError:
                    print(f"No PY field found for {dfk}, setting dateDegreeGranted to None.")
                    dateDegreeGranted = None
    return thesis_infos

def build_thesis_nodes(work_uri,graph,thesis_info):
    """
    Builds RDF nodes for the thesis information and adds them to the provided graph in place.

    Args:
        thesis_info (dict): A dictionary with extracted thesis information.

    Side Effects:
        Modifies the provided RDF graph in place by adding thesis-related nodes and triples.

    Returns:
        None
    """
    # At least one of 'degreeGranted' or 'dateDegreeGranted' must be present to create thesis nodes;
    # if both are missing, there is not enough information to generate a thesis node, so return early.
    if not (thesis_info["degreeGranted"] or thesis_info["dateDegreeGranted"]):
        return

    # add a dissertation node to the work:
    # create the node with type bf:Dissertation:
    # give it a unique URI:
    dissertation_uri = URIRef(
        str(work_uri) + "#dissertation")
    graph.add((dissertation_uri, RDF.type, ns.BF.Dissertation))
    graph.add((work_uri, ns.BF.dissertation, dissertation_uri))
    # add degreeGranted to the dissertation node:
    if thesis_info["degreeGranted"]:
        graph.add((dissertation_uri, ns.BF.degree, Literal(thesis_info["degreeGranted"])))
    # add dateDegreeGranted to the dissertation node:
    if thesis_info["dateDegreeGranted"]:
        graph.add((dissertation_uri, ns.BF.date, Literal(thesis_info["dateDegreeGranted"])))
    # add thesis advisor to the work:
    if thesis_info["thesisAdvisor"] is not None:
        if (
            thesis_info["thesisAdvisor"] is None
            or not isinstance(thesis_info["thesisAdvisor"], (list, tuple))
            or len(thesis_info["thesisAdvisor"]) != 2
        ):
            logging.warning(f"Thesis advisor {thesis_info['thesisAdvisor']} is not a valid name tuple, skipping.")
        else:
            # create a URI for the thesis advisor:
            contribution_uri = URIRef(
                str(work_uri) + "#thesis_advisor")
            graph.add((contribution_uri, RDF.type, ns.BF.Contribution))
            graph.add((contribution_uri, RDF.type, ns.BF.ThesisAdvisory))
            graph.add((work_uri, ns.BF.contribution, contribution_uri))
            # add a node for the advisor agent, a Person:
            advisor_uri = URIRef(str(contribution_uri) + "_person")
            graph.add((advisor_uri, RDF.type, ns.BF.Person))
            # add the advisor to the contribution:
            graph.add((contribution_uri, ns.BF.agent, advisor_uri))
            # add the family and given name to the advisor:
            graph.add((advisor_uri, ns.SCHEMA.familyName, Literal(thesis_info["thesisAdvisor"][0])))
            graph.add((advisor_uri, ns.SCHEMA.givenName, Literal(thesis_info["thesisAdvisor"][1])))
            # add role to the advisor:
            graph.add((contribution_uri, ns.BF.role, URIRef("https://id.loc.gov/vocabulary/relators/ths")))  # ths = thesis supervisor

        ## add thesis reviewers:
        for reviewer_index,reviewer in enumerate(thesis_info["thesisReviewers"]):
            # create a URI for the thesis reviewer:
            contribution_uri = URIRef(
                str(work_uri) + "#thesis_reviewer_" + str(reviewer_index+1))
            graph.add((contribution_uri, RDF.type, ns.BF.Contribution))
            graph.add((contribution_uri, RDF.type, ns.BF.ThesisReview))
            graph.add((work_uri, ns.BF.contribution, contribution_uri))
            # add a node for the reviewer agent, a Person:
            reviewer_uri = URIRef(str(contribution_uri) + "_person")
            graph.add((reviewer_uri, RDF.type, ns.BF.Person))
            # add the reviewer to the contribution:
            graph.add((contribution_uri, ns.BF.agent, reviewer_uri))
            # add the names of the reviewer:
            # first, make sure the reviewer is a list or tuple with exactly two elements (family and given name):
            if not isinstance(reviewer, (list, tuple)) or len(reviewer) != 2:
                logging.warning(f"Reviewer {reviewer} is not a valid name tuple, skipping.")
                continue
            graph.add((reviewer_uri, ns.SCHEMA.familyName, Literal(reviewer[0])))
            graph.add((reviewer_uri, ns.SCHEMA.givenName, Literal(reviewer[1])))
            # add role to the reviewer:
            graph.add((contribution_uri, ns.BF.role, URIRef("https://id.loc.gov/vocabulary/relators/dgc")))  # dgc = degree committee member

        # finally, add the institute information to the first contribution node (usually the first author):
        add_thesis_info_to_first_contributon(work_uri, graph, thesis_info)


def add_thesis_info_to_first_contributon(work_uri, graph, thesis_info):
    # this will add the institute (usually from ORT and INST) as an affiliation to the first author of the work. 
    # also adds the institute ror id, country and country's geonames id to the affiliation.
    # For this, it needs to go through the subgraph of the work_uri after adding the author nodes, and find the first author node.
    # it will then add the affiliation to the first author node, if it doesn't exist already. (MAybe we can reuse existing functions to add all these at once, I think we have an add_affilition function that does this already.)
    # also adds a second role "dissertant" in addition to AU.
    # the thesis supervisor and reviewers will be added as further contributions to the work, but not here.
    
    # if there is a CS field, add the affiliation to the first contribution node:
    if thesis_info["institute"] is not None:
    # and thesis_info["institute_country"] is not None:
        # get the first contribution node:
        for contribution in graph.objects(work_uri, ns.BF.contribution):
            agent_node = graph.value(
                contribution, ns.BF.agent
            )  
            # get the position of the contribution:
            position = graph.value(contribution, ns.PXP.contributionPosition)
            if (
                int(position) == 1
                and graph.value(agent_node, RDF.type) == ns.BF.Person
            ):
                # add the affiliation to the contribution node using the function we already have for it:
                print(f"Adding dissertant role to first contribution node")
                # add dissertant role to the contribution node:
                graph.add(
                    (contribution, ns.BF.role, URIRef("https://id.loc.gov/vocabulary/relators/dis")))  # dis = dissertant
                # if there is no affiliation node yet, we can build one:
                if not graph.value(
                    contribution, ns.MADS.hasAffiliation
                ):
                    print("Adding thesis institute as affiliation to first contribution node")
                    # build the affiliation node:
                    affiliation = contributions.build_affiliation_nodes(graph, agent_node, thesis_info["institute"], thesis_info["institute_country"])
                    # add the affiliation to the contribution node:
                    graph.add(
                        (contribution, ns.MADS.hasAffiliation, affiliation)
                    )
                else:
                    print("Affiliation already exists for first contribution node, skipping.")

                # graph.add(
                #     (
                #         contribution,
                #         ns.MADS.hasAffiliation,
                #         build_affiliation_nodes(agent_node, affiliation, country),
                #     )
                # )
                break

