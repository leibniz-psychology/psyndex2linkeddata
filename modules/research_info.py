import html
import logging
import re

import requests
import requests_cache
from datetime import timedelta
from rapidfuzz import fuzz

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
}

## urls for unknown preregistrations, replicated works, reanalyzed works
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
        graph.add((work_uri, ns.BFLC.relationship, relationship_node))


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
                    graph.add((work_uri, ns.BFLC.relationship, relationship_node))

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
        print(f"Skipping RPLIC field: {rplic_string}")
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
        print(f"✅ Found DFK: {subfield_dfk} in RPLIC field. Stopping search.")
        return replication
    # else, if no DFK, we continue to check for a DOI or URL:
    else:
        print("No DFK, checking for others:\n'" + str(rplic_string) + "'")
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
            print(
                f"Found {len([x for x in url_doi_set if x[1] in ['doi', 'url']])} valid url/doi tuples in RPLIC field: {url_doi_set}"
            )
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
                    print(f"✅ Found URL: {url_doi_tuple[0]} in RPLIC field, stopping.")
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
    
    print(f"- Validating DOI: {our_doi} against citation: '{mainfield_citation}'")
    if our_doi is None or our_doi == "":
        logging.warning("No DOI provided for validation.")
        return False
    elif mainfield_citation is None or mainfield_citation == "" or mainfield_citation.startswith("http") or mainfield_citation.startswith("10."):
        # if the citation is empty or just a url or doi, we cannot validate it against crossref, so we return True, we assume it is valid, because that is all we have
        logging.warning("No valid citation provided for validation.")
        print(f"✅ Crossref can't compare empty titles, so we assume the DOI {our_doi} is valid.")
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
                    print(f"✅ Crossref says this DOI has the same title (similarity={similarity}): {title}")
                    return True  # Accept match
                else:
                    crossref_rejections.append({
                        'doi': our_doi,
                        'crossref_title': title,
                        'crossref_authors': authors,
                        'similarity': similarity
                    })
                    print(f"⚠️ Crossref says this DOI {our_doi} has a different title (similarity={similarity}): {title}")
                    return False  # Reject match
    except requests.exceptions.RequestException as e:
        logging.error(f"Error validating DOI against Crossref for {our_doi}: {e}")
        return False
    

    

def check_crossref_for_citation_doi(citation_string):
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
    similarity_threshold = 30  # set a threshold for fuzzy matching
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