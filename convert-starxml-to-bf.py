# %% [markdown]
# # Star2BF - Star to Bibframe

# %% [markdown]
# Import libraries:

# %%
import dateparser
from numpy import rec
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, OWL, Namespace
from rdflib import BNode
from rdflib import URIRef
import xml.etree.ElementTree as ET
import re
import html

import regex

import modules.mappings as mappings
import modules.contributions as contributions

# import modules.open_science as open_science
import requests
import requests_cache
from datetime import timedelta

# old fuzzy compare for reconciliations: using fuzzywuzzy
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# new fuzzy compare: using the faster rapidfuzz as a drop-in replacement for fuzzywuzzy:
# from rapidfuzz import fuzz
# from rapidfuzz import process

import csv

# ror lookup
ROR_API_URL = "https://api.ror.org/organizations?affiliation="

from modules.mappings import funder_names_replacelist

# set up friendly session by adding mail in request:
CROSSREF_FRIENDLY_MAIL = "&mailto=ttr@leibniz-psychology.org"
# for getting a list of funders from api ():
CROSSREF_API_URL = "https://api.crossref.org/funders?query="

SKOSMOS_API_URL = "https://skosmos.dev.zpid.org/rest/v1/"

urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}
# using cache for ror requests
session = requests_cache.CachedSession(
    ".cache/requests",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)
# and a cache for the crossref api:
session_fundref = requests_cache.CachedSession(
    ".cache/requests",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

session_skosmos = requests_cache.CachedSession(
    ".cache/requests",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

# import csv of LUX authority institutes:
with open("institute_lux.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    # save it in a list:
    lux_institutes = list(reader)
    # split string "known_names" into a list of strings on "##":
    for institute in lux_institutes:
        institute["known_names"] = institute["known_names"].split(" ## ")
# print("Und die ganze Tabelle:")
# print(dachlux_institutes)


# %% [markdown]
# Create an "element tree" from the records in my xml file so we can loop through them and do things with them:

# %%
# root = ET.parse("xml-data/records-440.xml")
# root = ET.parse("xml-data/records-322.xml")
# root = ET.parse("xml-data/records-395.xml")
# root = ET.parse("xml-data/records-214.xml")
root = ET.parse("xml-data/records-556.xml")

# To see the source xml's structure, uncomment this function:
# def print_element(element, depth=0):
#     print("\t"*depth, element.tag, element.attrib, element.text)
#     for child in element:
#         print_element(child, depth+1)

# for child in root.getroot()[:2]:
#     print_element(child)


# %% [markdown]
# We first set a few namespace objects for bibframe, schema.org and for our resources (the works and instances)
# themselves.
#
# Then, we create two graphs from the xml source file, one to generate triples for our bibframe profile output, and the other for the simplified schema.org profile.
#
# Finally, we bind the prefixes with their appropriate namespaces to the graphs.

# %%
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = Namespace("http://id.loc.gov/ontologies/bflc/")
MADS = Namespace("http://www.loc.gov/mads/rdf/v1#")
SCHEMA = Namespace("https://schema.org/")
WORKS = Namespace("https://w3id.org/zpid/resources/works/")
INSTANCES = Namespace("https://w3id.org/zpid/resources/instances/")
INSTANCEBUNDLES = Namespace("https://w3id.org/zpid/resources/instancebundles/")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")
LANG = Namespace("http://id.loc.gov/vocabulary/iso639-2/")
LOCID = Namespace("http://id.loc.gov/vocabulary/identifiers/")
CONTENTTYPES = Namespace("http://id.loc.gov/vocabulary/contentTypes/")
ROLES = Namespace("https://w3id.org/zpid/vocabs/roles/")
ISSUANCES = Namespace("https://w3id.org/zpid/vocabs/issuances/")
RELATIONS = Namespace("https://w3id.org/zpid/vocabs/relations/")
GENRES = Namespace("https://w3id.org/zpid/vocabs/genres/")
PMT = Namespace("https://w3id.org/zpid/vocabs/mediacarriers/")


# graph for bibframe profile:
records_bf = Graph()
# make the graph named:
records_bf = Graph(identifier=URIRef("https://w3id.org/zpid/bibframe/records/"))

kerndaten = Graph()
kerndaten.parse("ttl-data/kerndaten.ttl", format="turtle")

# import graph for crossref funder registry dump:
# crossref_funders = Graph()
# crossref_funders.parse("crossref_fundref_registry.rdf", format="xml")
# we need a new graph for the schema.org profile, so it won't just reuse the old triples from the other profile
# records_schema = Graph()

# Bind the namespaces to the prefixes we want to see in the output:
records_bf.bind("bf", BF)
records_bf.bind("bflc", BFLC)
records_bf.bind("works", WORKS)
# records_schema.bind("works", WORKS)
records_bf.bind("instances", INSTANCES)
records_bf.bind("pxc", PXC)
records_bf.bind("pxp", PXP)
records_bf.bind("lang", LANG)
records_bf.bind("schema", SCHEMA)
records_bf.bind("locid", LOCID)
records_bf.bind("mads", MADS)
records_bf.bind("roles", ROLES)
records_bf.bind("relations", RELATIONS)
records_bf.bind("genres", GENRES)
records_bf.bind("contenttypes", CONTENTTYPES)
records_bf.bind("issuances", ISSUANCES)
records_bf.bind("pmt", PMT)


# %% [markdown]
# # Functions to do all the things
#
# We need functions for the different things we will do - to avoid one long monolith of a loop.
#
# This is where they will go. Examples: Create blank nodes for Idebtifiers, create nested contribution objects from disparate person entries in AUP, AUK, CS and COU fields, merge PAUP (psychauthor person names and ids) with the person's name in AUP...
#
# These functions will later be called at the bottom of this notebook, in a loop over all the xml records.

# %%


def get_issuance_type(instance_bundle_uri, record):
    # // from field BE
    # from modules.mappings import issuancetypes
    bibliographic_level = record.find("BE").text.strip()
    issuance_uri_fragment = None
    #  for different cases, add different issuance types:
    match bibliographic_level:
        case "SS":
            issuance_type = "Edited Book"
        case "SM":
            issuance_type = "Authored Book"
        case "UZ":
            issuance_type = "Journal Article"
        case "SH":
            issuance_type = "Gray Literature"
        case "SR":
            issuance_type = "Gray Literature"
        case "UR":
            issuance_type = "Chapter"
        case "US":
            issuance_type = "Chapter"
        case _:
            issuance_type = "Other"
    issuance_uri_fragment = issuance_type.replace(" ", "")
    try:
        # generate a node for the Issuance:
        issuance_node = URIRef(ISSUANCES + issuance_uri_fragment)
        # add it to the instance
        records_bf.add((instance_bundle_uri, PXP.issuanceType, issuance_node))
        # add a label:
        records_bf.set((issuance_node, RDFS.label, Literal(issuance_type)))
    except:
        print("record has no valid bibliographic level!")


def get_publication_date(record):
    # from field PHIST or PY, get pub date and return this as a Literal
    # get date from PHIST field, it exists, otherwise from P> field:
    if record.find("PHIST") is not None and record.find("PHIST").text != "":
        date = get_subfield(record.find("PHIST").text, "o")
        # clean up anything that's not a digit at the  start, such as ":" - make sure with a regex that date starts with a digit:
        date.strip()
        # parse the date: it can be either "8 June 2021" or "08.06.2021"
        try:
            # parse and convert this to the yyyy-mm-dd format:
            date = dateparser.parse(date).strftime("%Y-%m-%d")
        except:
            print("parsedate: couldn't parse " + str(date))
            print("Data in PHIST looks like an unsalvagable mess, using PY insead!")
            try:
                date = record.find("PY").text
            except:
                print("record has no valid publication date!")
                date = None

    else:
        print("no date found in PHIST, using PY")
        try:
            date = record.find("PY").text
        except:
            print("record has no valid publication date!")
            date = None
    return date


def add_isbns(record, instancebundle_uri):
    # if there is a PU, find subfield |i and e
    try:
        pu = record.find("PU")
    except:
        pu = None
    if pu is not None and pu.text != "":
        try:
            isbn_print = get_subfield(pu.text, "i")
        except:
            isbn_print = None
        try:
            isbn_ebook = get_subfield(pu.text, "e")
        except:
            isbn_ebook = None

        if isbn_print is not None:
            isbn_print_node = URIRef(str(instancebundle_uri) + "#isbn_print")
            records_bf.set((isbn_print_node, RDF.type, BF.Isbn))
            records_bf.set((isbn_print_node, RDF.value, Literal(isbn_print)))
            records_bf.add((instancebundle_uri, BF.identifiedBy, isbn_print_node))

        if isbn_ebook is not None:
            isbn_ebook_node = URIRef(str(instancebundle_uri) + "#isbn_ebook")
            records_bf.set((isbn_ebook_node, RDF.type, BF.Isbn))
            records_bf.set((isbn_ebook_node, RDF.value, Literal(isbn_ebook)))
            records_bf.add((instancebundle_uri, BF.identifiedBy, isbn_ebook_node))

        # check all the instances of this work whether they are print or online mediacarrier. If so, add appropriate isbn to them:
        # for instance in records_bf.objects(work_uri, BF.hasInstance):
        #     if isbn_print is not None:
        #         if records_bf.value(instance, RDF.type) == BF.Print:
        #             isbn_print_node = URIRef(str(instance) + "_isbn")
        #             records_bf.set((isbn_print_node, RDF.type, BF.Isbn))
        #             records_bf.set((isbn_print_node, RDF.value, Literal(isbn_print)))
        #             records_bf.add((instance, BF.identifiedBy, isbn_print_node))
        #         else:
        #             print("found no place for print isbn: " + isbn_print)
        #             # try:
        #             #     instance_bundle = records_bf.value(work_uri, PXP.hasInstanceBundle)
        #             #     isbn_print_node = URIRef(str(instance_bundle) + "_isbn")
        #             #     records_bf.set((isbn_print_node, RDF.type, BF.Isbn))
        #             #     records_bf.set(
        #             #         (isbn_print_node, RDF.value, Literal(isbn_print))
        #             #     )
        #             #     records_bf.add((instance_bundle, BF.identifiedBy, isbn_print_node))
        #             # except:
        #             #     print("failed adding print isbn")

        #             # why are they not being added? maybe we should try to add singletons to singleton Instances, at least?

        #     if isbn_ebook is not None:
        #         if records_bf.value(instance, RDF.type) == BF.Electronic:
        #             isbn_ebook_node = URIRef(str(instance) + "_isbn")
        #             records_bf.set((isbn_ebook_node, RDF.type, BF.Isbn))
        #             records_bf.set((isbn_ebook_node, RDF.value, Literal(isbn_ebook)))
        #             records_bf.add((instance, BF.identifiedBy, isbn_ebook_node))
        #         else:
        #             print("found no place for e-issn: " + isbn_ebook)


def get_concept_uri_from_skosmos(concept_label, vocid):
    # get the uri of a concept from skosmos by its label

    skosmos_request = session_skosmos.get(
        SKOSMOS_API_URL + vocid + "/lookup?label=" + concept_label + "&lang=en",
        timeout=20,
    )

    if skosmos_request.status_code == 200:
        skosmos_response = skosmos_request.json()
        if len(skosmos_response["result"]) > 0:
            # print(skosmos_response["result"][0]["uri"])
            return skosmos_response["result"][0]["uri"]
        else:
            print("no uri found for " + concept_label)
            return None
    else:
        print("skosmos request failed for " + concept_label)
        return None


def match_paups_to_contribution_nodes(work_uri, record):
    # go through all PAUP fields and get the id:
    for paup in record.findall("PAUP"):
        paup_id = get_subfield(paup.text, "n")
        paup_name = get_mainfield(paup.text)
        # print(
        #     "matching paup_id "
        #     + paup_id
        #     + " to existing contribution nodes of this work_uri"
        # )
        # get the given and family part of the paup name:
        paup_split = paup_name.split(",")
        paup_familyname = paup_split[0].strip()
        paup_givenname = paup_split[1].strip()
        paupname_normalized = normalize_names(paup_familyname, paup_givenname)
        # print("paupname_normalized: " + paupname_normalized)
        # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
        for contribution in records_bf.objects(work_uri, BF.contribution):
            # get the agent of the contribution:
            agent = records_bf.value(contribution, BF.agent)
            # if the agent is a person, get the given and family names:
            if records_bf.value(agent, RDF.type) == BF.Person:
                # get the given and family names of the agent:
                givenname = records_bf.value(agent, SCHEMA.givenName)
                familyname = records_bf.value(agent, SCHEMA.familyName)
                aupname_normalized = normalize_names(familyname, givenname)
                # print("aupname_normalized: " + aupname_normalized)
                # if the paupname_normalized matches the agent's name, add the paup_id as an identifier to the agent:
                # if paupname_normalized == aupname_normalized:
                # check using fuzzywuzzy:
                # if fuzz.ratio(paupname_normalized, aupname_normalized) > 90:
                # use partial_ratio for a more lenient comparison - we can check if one of the them is a substring of the other:
                if fuzz.partial_ratio(paupname_normalized, aupname_normalized) > 80:
                    # create a fragment uri node for the identifier:
                    paup_id_node = URIRef(str(agent) + "_psychauthorsid")
                    # make it a locid:psychAuthorsID:
                    records_bf.set((paup_id_node, RDF.type, PXC.PsychAuthorsID))
                    # add the paup id as a literal to the identifier node:
                    records_bf.add((paup_id_node, RDF.value, Literal(paup_id)))
                    # add the identifier node to the agent node:
                    records_bf.add((agent, BF.identifiedBy, paup_id_node))
                    # print("paup_id added to agent: " + paup_id)
                    # and break the loop:
                    break
                    # after all loops, print a message if no match was found:
        else:
            print(
                "no match found for paup_id "
                + paup_id
                + " ("
                + paup_name
                + ")"
                + " in record "
                + record.find("DFK").text
                + ". Checking name variants found in kerndaten for this id..."
            )
            # loop through the contrubtors again, and check if any of the alternate names match the agent's name:
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # get the agent of the contribution:
                agent = records_bf.value(contribution, BF.agent)
                # if the agent is a person, get the given and family names:
                if records_bf.value(agent, RDF.type) == BF.Person:
                    # get the given and family names of the agent:
                    givenname = records_bf.value(agent, SCHEMA.givenName)
                    familyname = records_bf.value(agent, SCHEMA.familyName)
                    aupname_normalized = normalize_names(familyname, givenname)
                    # print("aupname_normalized: " + aupname_normalized)
                    # try to match the paup_id to a uri in kerndaten.ttl and check if any of the alternate names match the agent's name:
                    person_uri = URIRef("https://w3id.org/zpid/person/" + paup_id)
                    for alternatename in kerndaten.objects(
                        person_uri, SCHEMA.alternateName
                    ):
                        # print("alternatename: " + alternatename)
                        # split the alternatename into family and given name:
                        alternatename_split = alternatename.split(",")
                        alternatename_familyname = alternatename_split[0].strip()
                        alternatename_givenname = alternatename_split[1].strip()
                        # normalize the name:
                        alternatename_normalized = normalize_names(
                            alternatename_familyname, alternatename_givenname
                        )
                        # print("alternatename_normalized: " + alternatename_normalized)
                        # print("aupname_normalized: " + aupname_normalized)

                        # if the alternatename matches the agent's name, add the paup_id as an identifier to the agent:
                        if (
                            fuzz.partial_ratio(
                                alternatename_normalized, aupname_normalized
                            )
                            > 80
                        ):
                            # create a fragment uri node for the identifier:
                            paup_id_node = URIRef(str(agent) + "_psychauthorsid")
                            # make it a locid:psychAuthorsID:
                            records_bf.set((paup_id_node, RDF.type, PXC.PsychAuthorsID))
                            # add the paup id as a literal to the identifier node:
                            records_bf.add((paup_id_node, RDF.value, Literal(paup_id)))
                            # add the identifier node to the agent node:
                            records_bf.add((agent, BF.identifiedBy, paup_id_node))
                            print("paup_id added to agent: " + paup_id)


def match_orcids_to_contribution_nodes(work_uri, record):
    # go through all ORCID fields and get the id:
    for orcid in record.findall("ORCID"):
        # print("orcid: " + orcid.text)
        orcid_id = get_subfield(orcid.text, "u")
        orcid_name = get_mainfield(orcid.text)
        # print(
        #     "matching orcid_id "
        #     + orcid_id
        #     + " to existing contribution nodes of this work_uri"
        # )
        # is the orcid well formed?
        # clean up the orcid_id by removing spaces that sometimes sneak in when entering them in the database:
        if orcid_id is not None and " " in orcid_id:
            print("warning: orcid_id contains spaces: " + orcid_id)
        orcid_id = orcid_id.replace(" ", "")
        # by the way, here is a regex pattern for valid orcids:
        orcid_pattern = re.compile(
            r"^(https?:\/\/(orcid\.)?org\/)?(orcid\.org\/)?(\/)?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])$"
        )
        if orcid_pattern.match(orcid_id):
            # remove the prefixes and slashes from the orcid id:
            orcid_id = orcid_pattern.match(orcid_id).group(5)
        else:
            # don't use it if it doesn't match the pattern:
            print(f"warning: invalid orcid: {orcid_id}")
        # get the given and family part of the orcid name:
        orcid_split = orcid_name.split(",")
        orcid_familyname = orcid_split[0].strip()
        orcid_givenname = orcid_split[1].strip()
        orcidname_normalized = normalize_names(orcid_familyname, orcid_givenname)
        # print("orcidname_normalized: " + orcidname_normalized)
        # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
        for contribution in records_bf.objects(work_uri, BF.contribution):
            # get the agent of the contribution:
            agent = records_bf.value(contribution, BF.agent)
            # if the agent is a person, get the given and family names:
            if records_bf.value(agent, RDF.type) == BF.Person:
                # get the given and family names of the agent:
                givenname = records_bf.value(agent, SCHEMA.givenName)
                familyname = records_bf.value(agent, SCHEMA.familyName)
                aupname_normalized = normalize_names(familyname, givenname)
                # print("aupname_normalized: " + aupname_normalized)
                # if the orcidname_normalized matches the agent's name, add the orcid_id as an identifier to the agent:
                # if orcidname_normalized == orcidname_normalized:
                # check using fuzzywuzzy:
                # if fuzz.ratio(orcidname_normalized, orcidname_normalized) > 90:
                # use partial_ratio for a more lenient comparison - we can check if one of the them is a substring of the other:
                if fuzz.partial_ratio(aupname_normalized, orcidname_normalized) > 80:
                    # create a fragment uri node for the identifier:
                    orcid_id_node = URIRef(str(agent) + "_orcid")
                    # make it a locid:orcid:
                    records_bf.set((orcid_id_node, RDF.type, LOCID.orcid))
                    # add the orcid id as a literal to the identifier node:
                    records_bf.add((orcid_id_node, RDF.value, Literal(orcid_id)))
                    # add the identifier node to the agent node:
                    records_bf.add((agent, BF.identifiedBy, orcid_id_node))
                    # print("orcid_id added to agent: " + orcid_id)
                    # and break the loop:
                    break
                    # after all loops, print a message if no match was found:
        else:
            print(
                "no match found for orcid_id "
                + orcid_id
                + " ("
                + orcid_name
                + ") in record "
                + record.find("DFK").text
            )


def match_email_to_contribution_nodes(work_uri, record):
    # there is only ever one email field in a record, so we can just get it.
    # unless there is also a field emid, the email will be added to the first contribution node.
    # if there is an emid, the email will be added to the person with a name matching the name in emid.
    # get the email:
    if record.find("EMAIL") is not None:
        email = html.unescape(
            mappings.replace_encodings(record.find("EMAIL").text.strip())
        )
        # replace spaces with _, but only if it doesnt come directly before a dot:
        email = re.sub(r"\s(?=[^\.]*\.)", "_", email)
        # if a space comes directly before a dot or after a dot, remove it:
        email = re.sub(r"\s\.", ".", email)
        email = re.sub(r"\.\s", ".", email)
        # check if this is a valid email:
        email_pattern = re.compile(
            r"^([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22))*\x40([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d))*$"
        )
        # check if email matches the regex in email_pattern:
        if not email_pattern.match(email):
            print(
                f"warning: invalid email: {email} in record {record.find('DFK').text}"
            )
        email = "mailto:" + email
        # if there is an emid, the email will be added to the person with a name matching the name in emid.

        # get the emid:
        try:
            emid_name = record.find("EMID").text
        except:
            emid_name = None
        if emid_name is not None:
            # emid_name = emid.text
            # print("matching email to person with name " + emid_name)
            # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # get the agent of the contribution:
                agent = records_bf.value(contribution, BF.agent)
                # if the agent is a person, get the given and family names:
                if records_bf.value(agent, RDF.type) == BF.Person:
                    # get the given and family names of the agent:
                    name = records_bf.value(agent, RDFS.label)
                    emid_name = mappings.replace_encodings(emid_name).strip()
                    # print("aupname_normalized: " + aupname_normalized)
                    # if the emid_name matches the agent's name, add the email as a mads:email to the agent:
                    if fuzz.partial_ratio(emid_name, name) > 80:
                        # add to contribution node:
                        records_bf.add((contribution, MADS.email, URIRef(email)))
                        # print("email added to agent: " + email)
                        # and break the loop:
                        print("email: " + email)
                        break
                    # after all loops, print a message if no match was found:
        # if no emid was found, add the email to the first contribution node:
        else:
            # print("email: to first " + email)

            # print(
            #     "no emid found, trying to add email to first contribution node:" + email
            # )
            # finding the contribution node from those the work_uri has that has bf:qualifier "first":
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # dont get the agent at all, but just the position of the contribution:
                position = records_bf.value(contribution, PXP.contributionPosition)
                # print("position of contribution: " + str(position))
                # break after position 1:
                if int(position) == 1:
                    # add to contribution node:
                    records_bf.add((contribution, MADS.email, URIRef(email)))
                    # print("email added to first contribution: " + email)
                    break


def extract_contribution_role(contributiontext):
    role = get_subfield(contributiontext, "f")
    if role is not None:
        # if we find a role, return it:
        return role
    else:
        # if none is found, add the default role AU:
        return "AU"


def generate_bf_contribution_node(work_uri):
    # will be called by functions that add AUPs and AUKS
    # adds a bf:Contribution node, adds the position from a counter, and returns the node.
    contribution_qualifier = None
    # make the node and add class:
    contribution_node = URIRef(work_uri + "#contribution" + str(contribution_counter))
    records_bf.add((contribution_node, RDF.type, BF.Contribution))

    # add author positions:
    records_bf.add(
        (contribution_node, PXP.contributionPosition, Literal(contribution_counter))
    )
    # if we are in the first loop, set "contribution_qualifier" to "first":
    if contribution_counter == 1:
        contribution_qualifier = "first"
        records_bf.add((contribution_node, RDF.type, BFLC.PrimaryContribution))
    # if we are in the last loop, set "contribution_qualifier" to "last":
    elif contribution_counter == len(record.findall("AUP")) + len(
        record.findall("AUK")
    ):
        contribution_qualifier = "last"
    # if we are in any other loop but the first or last, set "contribution_qualifier" to "middle":
    else:
        contribution_qualifier = "middle"
    # add the contribution qualifier to the contribution node:
    records_bf.add((contribution_node, BF.qualifier, Literal(contribution_qualifier)))
    # finally, return the finished contribution node so we can add our agent and affiliation data to it in their own functions:
    return contribution_node


def add_bf_contributor_corporate_body(work_uri, record):
    # adds all corporate body contributors from any of the record's AUK fields as contributions.
    for org in record.findall("AUK"):
        # count up the global contribution_counter:
        global contribution_counter
        contribution_counter += 1
        # generate a contribution node, including positions, and return it:
        contribution_node = generate_bf_contribution_node(work_uri)
        # do something:
        # read the text in AUK and add it as a label:
        # create a fragment uri node for the agent:
        org_node = URIRef(str(contribution_node) + "_orgagent")
        records_bf.add((org_node, RDF.type, BF.Organization))

        ## extracting the role:
        role = extract_contribution_role(org.text)
        # check if there is a role in |f subfield and add as a role, otherwise set role to AU
        records_bf.set((contribution_node, BF.role, add_bf_contribution_role(role)))

        # get the name (but exclude any subfields - like role |f, affiliation |i and country |c )
        org_name = mappings.replace_encodings(org.text.split("|")[0]).strip()
        # org_name = mappings.replace_encodings(org.text).strip()
        # get ror id of org from api:
        org_ror_id = get_ror_id_from_api(org_name)
        # if there is a ror id, add the ror id as an identifier:
        if org_ror_id is not None and org_ror_id != "null":
            # create a fragment uri node fore the identifier:
            org_ror_id_node = URIRef(str(org_node) + "_rorid")
            # make it a locid:ror:
            records_bf.set((org_ror_id_node, RDF.type, LOCID.ror))
            # add the ror id as a literal to the identifier node:
            records_bf.add((org_ror_id_node, RDF.value, Literal(org_ror_id)))
            records_bf.add((org_node, BF.identifiedBy, org_ror_id_node))
        else:
            print("ror-api: no ror id found for " + org_name)

        # get any affiliation in |i and add it to the name:
        org_affiliation_name = get_subfield(org.text, "i")
        try:
            org_name = org_name + "; " + org_affiliation_name
            # print("org affiliation:" + org_affiliation_name)
        except:
            print("AUK subfield i: no affiliation for org " + org_name)

        # # get country name in |c, if it exists:
        org_country = get_subfield(org.text, "c")
        try:
            print("AUK subfield c: org country:" + org_country)
            # generate a node for the country, clean up the label, look up the geonames id and then add both label and geonamesid node to the org node!
            affiliation_node = build_affiliation_nodes(org_node, "", org_country)
            # add the affiliation node to the contribution node:
            records_bf.add((contribution_node, MADS.hasAffiliation, affiliation_node))
        except:
            print("AUK subfield c: no country for org " + org_name)

        # TOD: we should probably check for affiliations and countries in fields CS and COU for records that have only AUKS or AUK as first contribution? we already did the same for persons.

        # add the name as the org node label:
        records_bf.add((org_node, RDFS.label, Literal(org_name)))

        ## --- Add the contribution node to the work node:
        records_bf.add((work_uri, BF.contribution, contribution_node))
        # add the org node to the contribution node as a contributor:
        records_bf.add((contribution_node, BF.agent, org_node))


# %% [markdown]
# ## Function: Create Person Contribution nodes from Fields AUP, EMID, EMAIL, AUK, PAUP, CS and COU
#
# Use this scheme:
#
# ```turtle
# works:0123456_work a bf:Work;
#     bf:contribution works:0123456_work#contribution1
# .
# works:0123456_work#contribution1 a bf:Contribution, bflc:PrimaryContribution;
#         # the Bibframe Contribution includes, as usual, an agent and their role,
#         # but is supplemented with an Affiliation (in the context of that work/while it was written),
#         # and a position in the author sequence.
#         bf:agent
#         [
#             a bf:Person, schema:Person;
#             rdfs:label "Trillitzsch, Tina"; # name when creating work
#             schema:givenName "Tina"; schema:familyName "Trillitzsch";
#             # owl:sameAs <https://w3id.org/zpid/person/tt_0000001>, <https://orcid.org/0000-0001-7239-4844>; # authority uris of person (local, orcid)
#             bf:identifiedBy [a pxc:PsychAuthorsID; rdf:value "p01979TTR"; #legacy authority ID
#             ];
#             bf:identifiedBy [a locid:orcid; rdf:value "0000-0001-7239-4844"; # ORCID
#             ];
#         ]
#         # we use a model inspired by Option C in Osma Suominen'a suggestion for https://github.com/dcmi/dc-srap/issues/3
#         # adding the Affiliation into the Contribution, separate from the agent itself, since the affiliation
#         # is described in the context of this work, not not as a statement about the person's
#         # current affiliation:
#         mads:hasAffiliation [
#             a mads:Affiliation;
#             # Affiliation blank node has info about the affiliation org (including persistent identifiers),
#             # the address (country with geonames identifier),
#             # and the person's email while affiliated there.
#             mads:organization [
#                 a bf:Organization;
#                 rdfs:label "Leibniz Institute of Psychology (ZPID); Digital Research Development Services"; # org name when work was created
#                 # owl:sameAs <https://w3id.org/zpid/org/zpid_0000001>, <https://ror.org/0165gz615>; # authority uris of org (local, ror)
#                 # internal id and ror id as literal identifiers:
#                 bf:identifiedBy [a pxc:ZpidCorporateBodyId; rdf:value "0000001"; ];
#                 bf:identifiedBy [a locid:ror; rdf:value "0165gz615"; ];
#             ];
#             mads:hasAffiliationAddress [a mads:Address;
#                 mads:country [
#                     a mads:Country;
#                     rdfs:label "Germany";
#                     bf:identifiedBy [a locid:geonames; rdf:value "2921044"; ];
#                     # owl:sameAs <https://w3id.org/zpid/place/country/ger>;
#                 ]
#             ];
#             mads:email <mailto:ttr@leibniz-psychology.org>; # correspondence author email
#         ];
#         bf:role <http://id.loc.gov/vocabulary/relators/aut>;
#         pxp:contributionPosition 1; bf:qualifier "first"; # first author in sequence: our own subproperty of bf:qualifier & schema:position (also: middle, last)
#     ].
# ```
#
# Todos:
# - [x] create blank node for contribution and add agent of type bf:Person
# - [x] add author position (first, middle, last plus order number) to the contribution
# - [x] make first author a bflc:PrimaryContribution
# - [x] match AUP with PAUP to get person names and ids (normalize first)
# - [x] extend AUP-PAUP match with lookup in kerndaten table/ttl to compare schema:alternatename of person with name in AUP (but first before normalization)
# - [x] add ORCID to the person's blank node (doesn't add 4 ORCIDs for unknown reason - maybe duplicates?)
# - [x] add EMAIL to person's blank node (either to person in EMID or to first author)
# - [x] add affiliation from CS field and COU field to first author
# - [x] add Affiliation blank node with org name, country to each author that has these subfields in their AUP (|i and |c)
# - [x] add role from AUP subfield |f
# - [x] add country geonames id using lookup table
# - [ ] move mads:email Literal from bf:Contribution to mads:Affiliation
# - [x] later: reconcile affiliations to add org id, org ror id (once we actually have institution authority files)
#

# %%
from modules.mappings import geonames_countries


def country_geonames_lookup(country):
    for case in geonames_countries:
        if case[0].casefold() == str(country).casefold():
            return case[0], case[1]
    return None


# %%
def sanitize_country_names(country_name):
    if country_name == "COSTA":
        country_name = "Costa Rica"
    elif country_name == "CZECH":
        country_name = "Czech Republic"
    elif country_name == "NEW":
        country_name = "New Zealand"
    elif country_name == "SAUDI":
        country_name = "Saudi Arabia"
    elif country_name == "PEOPLES":
        country_name = "People's Republic of China"
    return country_name


# %%


def add_bf_contribution_role(role):
    # # return role_uri,
    # # generate a node of type bf:Role:
    # records_bf.add((role, RDF.type, BF.Role))
    # # construct the uri for the bf:Role object:
    # role_uri = URIRef(ROLES + role)
    # # add the uri to the role node:
    # records_bf.add((role, RDF.value, role_uri))
    # # return the new node:
    # return role
    return URIRef(ROLES + role)


def normalize_names(familyname, givenname):
    # given a string such as "Forkmann, Thomas"
    # return a normalized version of the name by
    # replacing umlauts and ß with their ascii equivalents and making all given names abbreviated:
    familyname_normalized = (
        familyname.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    # generate an abbreviated version of givenname (only the first letter),
    # (drop any middle names or initials, but keep the first name):
    if givenname:
        givenname_abbreviated = givenname[0] + "."
        # generate a normalized version of the name by concatenating the two with a comma as the separator:
        fullname_normalized = familyname_normalized + ", " + givenname_abbreviated
    return fullname_normalized


def get_local_authority_institute(affiliation_string, country):
    """Uses ~~fuzzywuzzy~~ RapidFuzz to look up the affilaition string in a local authority table loaded from a csv file."""
    if country == "LUXEMBOURG":
        best_match = process.extractOne(
            affiliation_string, lux_institutes, scorer=fuzz.token_set_ratio
        )
        return best_match[0].get("uuid")
    else:
        return None


def get_ror_id_from_api(orgname_string):
    # this function takes a string with an organization name (e.g. from affiliations) and returns the ror id for that org from the ror api
    ror_api_url = ROR_API_URL + orgname_string
    # make a request to the ror api:
    # ror_api_request = requests.get(ror_api_url)
    # make request to api with caching:
    ror_api_request = session.get(ror_api_url, timeout=20)
    # if the request was successful, get the json response:
    if ror_api_request.status_code == 200:
        ror_api_response = ror_api_request.json()
        # check if the response has any hits:
        if len(ror_api_response["items"]) > 0:
            # if so, get the item with a key value pair of "chosen" and "true" and return its id:
            for item in ror_api_response["items"]:
                if item["chosen"] == True:
                    return item["organization"]["id"]
        else:
            return None
    else:
        return None


def build_affiliation_nodes(agent_node, agent_affiliation, agent_affiliation_country):
    # person_affiliation = replace_encodings(person_affiliation)
    # is passed two string: the affiliation name and the affiliation country name
    # make a fragement uri node for the affiliation (use agent node as base) and make it class mads:Affiliation:
    agent_affiliation_node = URIRef(str(agent_node) + "_affiliation1")
    records_bf.add((agent_affiliation_node, RDF.type, MADS.Affiliation))
    # make a fragment uri node for the affiliation organization and make it class bf:Organization:
    # but only for person agents. Org agents will not get an additial affiliation org node (we will pass an empty string for orgs that need an affiliation node to hold their address).
    if agent_affiliation is not None and agent_affiliation != "":
        agent_affiliation_org_node = URIRef(
            str(agent_affiliation_node) + "_organization"
        )
        records_bf.set((agent_affiliation_org_node, RDF.type, BF.Organization))
        # add the affiliation organization node to the affiliation node:
        records_bf.add(
            (agent_affiliation_node, MADS.organization, agent_affiliation_org_node)
        )
        # add the affiliation string to the affiliation org node:
        records_bf.add(
            (agent_affiliation_org_node, RDFS.label, Literal(agent_affiliation))
        )

    # do a ror lookup for the affiliation string
    # and if there is a ror id, add the ror id as an identifier:
    # affiliation_ror_id = None
    affiliation_ror_id = get_ror_id_from_api(agent_affiliation)

    if affiliation_ror_id is not None and affiliation_ror_id != "null":
        # create a fragment uri node fore the identifier:
        affiliation_ror_id_node = URIRef(str(agent_affiliation_org_node) + "_rorid")
        # make it a locid:ror:
        records_bf.set((affiliation_ror_id_node, RDF.type, LOCID.ror))
        # add the ror id as a literal to the identifier node:
        records_bf.add(
            (affiliation_ror_id_node, RDF.value, Literal(affiliation_ror_id))
        )
        records_bf.add(
            (agent_affiliation_org_node, BF.identifiedBy, affiliation_ror_id_node)
        )
    # else:
    # print("no ror id found for " + person_affiliation)

    # affiliation_local_id = None
    # affiliation_local_id = get_local_authority_institute(
    #     person_affiliation, person_affiliation_country
    # )
    # if affiliation_local_id is not None:
    #     # add a blank node fore the identifier:
    #     affiliation_local_id_node = BNode()
    #     # make it a pxc:OrgID:
    #     records_bf.add((affiliation_local_id_node, RDF.type, PXC.OrgID))
    #     records_bf.add(
    #         (person_affiliation_org_node, BF.identifiedBy, affiliation_local_id_node)
    #     )
    #     # add the local uuid as a literal to the identifier node:
    #     records_bf.add(
    #         (affiliation_local_id_node, RDF.value, Literal(affiliation_local_id))
    #     )

    # TODO: sometimes people have an affiliation, but no country (no |c subfield).
    # currently we dont handle that at all and a country label "None" is added
    # where we should just not add an AffiliationAdress node with a country node at all.
    # make a fragment uri node for the affiliation address and make it class mads:Address:
    if agent_affiliation_country is not None and agent_affiliation_country != "":
        person_affiliation_address_node = URIRef(
            str(agent_affiliation_node) + "_address"
        )
        records_bf.add((person_affiliation_address_node, RDF.type, MADS.Address))
        # add a country node to the affiliation address node:
        person_affiliation_country_node = URIRef(
            str(person_affiliation_address_node) + "_country"
        )
        records_bf.add((person_affiliation_country_node, RDF.type, MADS.Country))
        # add the country node to the affiliation address node:
        records_bf.add(
            (
                person_affiliation_address_node,
                MADS.country,
                person_affiliation_country_node,
            )
        )
        # add the affiliation address string to the affiliation address node:
        records_bf.add(
            (
                person_affiliation_country_node,
                RDFS.label,
                Literal(agent_affiliation_country),
            )
        )

        # if the country is in the geonames lookup table, add the geonames uri as sameAs and the geonames id as an identifier:
        if country_geonames_lookup(agent_affiliation_country):
            improved_country_name, geonamesId = country_geonames_lookup(
                agent_affiliation_country
            )
            # create a url to click and add it with sameas:
            # geonames_uri = URIRef("http://geonames.org/" + geonamesId + "/")
            # records_bf.add((person_affiliation_country_node, SCHEMA.sameAs, geonames_uri))
            # replace the country name in the affiliation address node with the improved country name:
            records_bf.add(
                (
                    person_affiliation_country_node,
                    RDFS.label,
                    Literal(improved_country_name),
                )
            )
            # and remove the old label:
            records_bf.remove(
                (
                    person_affiliation_country_node,
                    RDFS.label,
                    Literal(agent_affiliation_country),
                )
            )
            # add the geonames identifier:
            person_affiliation_country_identifier_node = URIRef(
                str(person_affiliation_country_node) + "_geonamesid"
            )
            # records_bf.add((person_affiliation_country_identifier_node, RDF.type, BF.Identifier))
            records_bf.add(
                (person_affiliation_country_identifier_node, RDF.type, LOCID.geonames)
            )
            records_bf.add(
                (
                    person_affiliation_country_identifier_node,
                    RDF.value,
                    Literal(geonamesId),
                )
            )
            records_bf.add(
                (
                    person_affiliation_country_node,
                    BF.identifiedBy,
                    person_affiliation_country_identifier_node,
                )
            )
        # add the affiliation address node to the affiliation node:
        records_bf.add(
            (
                agent_affiliation_node,
                MADS.hasAffiliationAddress,
                person_affiliation_address_node,
            )
        )

    # return the finished affiliation node with all its children and attached strings:
    return agent_affiliation_node


# the full function that creates a contribution node for each person in AUP:
# first, get all AUPs in a record and create a node for each of them
def add_bf_contributor_person(work_uri, record):
    # initialize a counter for the contribution position and a variable for the contribution qualifier:
    # contribution_counter = 0
    # contribution_qualifier = None

    for person in record.findall("AUP"):
        # count how often we've gone through the loop to see the author position:

        # count up the global contribution_counter:
        global contribution_counter
        contribution_counter += 1
        # do all the things a contribution needs in another function (counting and adding positions, generating fragment uri)
        contribution_node = generate_bf_contribution_node(work_uri)

        # make a fragment uri node for the person:
        person_node = URIRef(str(contribution_node) + "_personagent")
        records_bf.add((person_node, RDF.type, BF.Person))

        # add the name from AUP to the person node, but only use the text before the first |: (and clean up the encoding):
        personname = mappings.replace_encodings(person.text.split("|")[0]).strip()

        records_bf.add((person_node, RDFS.label, Literal(personname)))

        # initialize variables for later use:
        personname_normalized = None
        orcidId = None

        # split personname into first and last name:
        personname_split = personname.split(",")
        if len(personname_split) > 1:
            familyname = personname_split[0].strip()
            givenname = personname_split[1].strip()
            records_bf.add((person_node, SCHEMA.familyName, Literal(familyname)))
            records_bf.add((person_node, SCHEMA.givenName, Literal(givenname)))
            # generate a normalized version of familyname to compare with PAUP name later:
            # personname_normalized = normalize_names(familyname, givenname)
            # for debugging, print the normalized name:
            # records_bf.add((person_node, PXP.normalizedName, Literal(personname_normalized)))

        # # check if there is a PAUP field in the same record that matches the personname from this AUP:
        # paId = match_paup(record, person_node, personname_normalized)
        # if paId is not None:
        #     # create a fragment uri node for the identifier:
        #     psychauthors_identifier_node = URIRef(str(person_node) + "_psychauthorsid")
        #     records_bf.add((psychauthors_identifier_node, RDF.type, PXC.PsychAuthorsID))
        #     records_bf.add((psychauthors_identifier_node, RDF.value, Literal(paId)))
        #     # add the identifier node to the person node:
        #     records_bf.add((person_node, BF.identifiedBy, psychauthors_identifier_node))

        # call the function get_orcid to match the personname with the ORCIDs in the record - so for every person in an AUP, we check all the ORCID fields in the record for a name match:
        # orcidId = match_orcid(record, person_node, personname_normalized)
        # if orcidId is not None:
        #     # create a fragment node for the identifier:
        #     orcid_identifier_node = URIRef(str(person_node) + "_orcid")
        #     # records_bf.add((orcid_identifier_node, RDF.type, BF.Identifier))
        #     records_bf.add((orcid_identifier_node, RDF.type, LOCID.orcid))
        #     records_bf.add((orcid_identifier_node, RDF.value, Literal(orcidId)))
        #     # add the identifier node to the person node:
        #     records_bf.add((person_node, BF.identifiedBy, orcid_identifier_node))
        #     # add the orcid id as a sameAs link to the person node:
        #     # orcid_uri = "https://orcid.org/" + orcidId
        #     # records_bf.add((person_node, SCHEMA.sameAs, URIRef(orcid_uri)))
        # else:
        #     print(
        #         "no orcid found for "
        #         + personname
        #         + " in DFK "
        #         + record.find("DFK").text
        #     )

        ## -----
        # Getting Affiliations and their countries from first, CS and COU (only for first author), and then from subfields |i and |c in AUP (for newer records)
        ## -----

        # initialize variables we'll need for adding affiliations and country names from AUP |i and CS/COU/ADR:
        affiliation_string = None
        affiliation_country = None

        # match affiliations in CS and COU to first contribution/author:
        # dont add ADR here yet (even if this is the place for it - we may drop that info anyway.
        # look for the field CS:
        # if the contribution_counter is 1 (i.e. if this is the first loop/first author), add the affiliation to the person node:
        if contribution_counter == 1:
            if record.find("CS") is not None:
                # get the content of the CS field:
                affiliation_string = html.unescape(
                    mappings.replace_encodings(record.find("CS").text.strip())
                )

            if record.find("COU") is not None:
                # get the country from the COU field:
                affiliation_country = mappings.replace_encodings(
                    sanitize_country_names(record.find("COU").text.strip())
                )

        ## Get affiliation from AUP |i, country from |c:
        # no looping necessary here, just check if a string |i exists in AUP and if so, add it to the person node as the affiliation string:
        affiliation_string = get_subfield(person.text, "i")

        affiliation_country = sanitize_country_names(get_subfield(person.text, "c"))

        ### TODO: Switched off affiliation node creation, because we don't want the overhead in our opensearch test index for psychporta
        # pass this to function build_affiliation_nodes to get a finished affiliation node:
        if affiliation_string != "" and affiliation_string is not None:
            affiliation_node = build_affiliation_nodes(
                person_node, affiliation_string, affiliation_country
            )
            # add the affiliation node to the contribution node:
            records_bf.add((contribution_node, MADS.hasAffiliation, affiliation_node))

        # look for the field EMAIL:
        # email = None
        # # TODO: the email address actually belongs into the affiliation section, but we'll leave it directly in the contribution node for now:
        # if record.find("EMAIL") is not None:
        #     # get the email address from the EMAIL field, replacing spaces with underscores (common problem in urls in star) and adding a "mailto:" prefix:
        #     email = html.unescape(
        #         mappings.replace_encodings(
        #             record.find("EMAIL").text.strip().replace(" ", "_")
        #         )
        #     )
        #     # check if this is a valid email address:
        #     email_pattern = re.compile(
        #         r"^([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22))*\x40([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d))*$"
        #     )
        #     # check if email matches the regex in email_pattern:
        #     if not email_pattern.match(email):
        #         print("warning: invalid email address: " + email)
        #         # email = None
        #     email = "mailto:" + email
        #     # email = "mailto:" + record.find("EMAIL").text.strip()
        #     # if there is no EMID and the contribution_counter is 1 (i.e. if this is the first loop), add the email to the person node:
        #     if record.find("EMID") is None and contribution_counter == 1:
        #         records_bf.add((contribution_node, MADS.email, URIRef(email)))
        #     # else match the existing EMID field to the personname:
        #     elif (
        #         record.find("EMID") is not None
        #         and mappings.replace_encodings(record.find("EMID").text.strip())
        #         == personname
        #     ):
        #         records_bf.add((contribution_node, MADS.email, URIRef(email)))

        # extracting the role:
        # check if there is a role in |f subfield and add as a role, otherwise set role to AU
        role = extract_contribution_role(person.text)
        records_bf.set((contribution_node, BF.role, add_bf_contribution_role(role)))

        ## --- Add the contribution node to the work node:
        records_bf.add((work_uri, BF.contribution, contribution_node))
        # add the person node to the contribution node as a contributor:
        records_bf.add((contribution_node, BF.agent, person_node))


# %% [markdown]
# ## TODO: Splitting Instances from single records with MT and MT2
#
# A record that has two media types (both a MT and a MT2 field) actually contains two instances.
#
# Let's start with books, first: Records with BE=SS or SM. Usually, when there are two media types, MT is "Print" and MT2 is "Online Medium" or vice versa.
#
# So we go through each record with BE=SS (or SM) and check for MT and MT2. If both are present, we create two instances, one for each media type. We will first describe this by giving them additional classes: bf:Electronic for Online Medium and bf:Print for Print.
#
# We will also add a property to the instance that links it to its other format, via bf:otherPsysicalFormat.
#


# %%
# function to set mediaCarrier from mt and mt2:
def get_mediacarrier(mediatype):
    mediatype = mediatype.strip()
    MEDIACARRIER_VOCAB_PREFIX_URI = "https://w3id.org/zpid/vocabs/mediacarrier/"
    # cases = [
    #     # format: MT/MT2 value, bf:Instance subclass, pxp:mediaCarrier value/uri localname"
    #     ("Print", "Print", "Print"),
    #     ("Online Medium", "Electronic", "Online"),
    #     ("eBook", "Electronic", "Online"),
    #     # add more types here
    # ]
    match mediatype:
        case "Print":
            return URIRef(BF["Print"]), URIRef(PMT["Print"])
        case "Online Medium":
            return URIRef(BF["Electronic"]), URIRef(PMT["Online"])
        case "eBook":
            return URIRef(BF["Electronic"]), URIRef(PMT["Online"])
        case "Optical Disc":
            return URIRef(BF["Electronic"]), URIRef(PMT["ElectronicDisc"])
        case _:
            print("no match for " + mediatype)
            return URIRef(BF["Print"]), URIRef(PMT["Print"])


def get_publication_info(instance_uri, record, mediatype):
    # get the publication info:
    pu = None
    pu = record.find("PU")
    pufield = html.unescape(pu.text.strip())
    if pu is not None and pufield != "":
        # split out the content after |e:
        pub_lisher = pufield.split("|v")
        pub_place = pufield.split("|o")
        p_isbn = pufield.split("|i")
        e_isbn = pufield.split("|e")
        # add a bf:provisionActivity to the instance:
        publication_node = BNode()
        records_bf.add((instance_uri, BF.provisionActivity, publication_node))
        # add the bf:place to the bf:provisionActivity:
        if len(pub_place) > 1:
            records_bf.add(
                (publication_node, BFLC.simplePlace, Literal(str(pub_place[1]).strip()))
            )
        # add the pub_lisher to the bf:provisionActivity as bflc:simpleAgent:
        if len(pub_lisher) > 1:
            records_bf.add(
                (
                    publication_node,
                    BFLC.simpleAgent,
                    Literal(str(pub_lisher[1]).strip()),
                )
            )
        # add the p_isbn to the instance:
        isbn_node = BNode()
        records_bf.add((instance_uri, BF.identifiedBy, isbn_node))
        records_bf.add((isbn_node, RDF.type, BF.Isbn))
        if get_mediacarrier(mediatype) == BF.Electronic:
            records_bf.add((instance_uri, BF.identifiedBy, isbn_node))
            records_bf.add((isbn_node, RDF.type, BF.Isbn))
            records_bf.add((isbn_node, RDF.value, Literal(str(e_isbn[1]).strip())))
        else:
            records_bf.add((isbn_node, RDF.value, Literal(str(p_isbn[1]).strip())))


def split_books(instance_uri, record):
    # check the BE field to see if it is "SS" or "SM":
    be = None
    be = record.find("BE")
    befield = be.text.strip()
    if be is not None and befield == "SS" or befield == "SM":
        mt = None
        mt2 = None
        mtfield = html.unescape(record.find("MT").text.strip())
        mt2field = html.unescape(record.find("MT2").text.strip())
        # we should check if there is an "e isbn" somewhere in PU subfield |e:

        if mt is not None and mtfield != "":
            # note the content of the MT field and use get_mediacarrier to get the corresponding bibframe instance class:
            # add the resulting bf class to the instance:
            # print("It's a book! Subclass: " + str(get_mediacarrier(mt.text)))
            records_bf.add((instance_uri, RDF.type, get_mediacarrier(mtfield)))

        if mt2 is not None and mt2field != "":
            # use get_mediacarrier to get the corresponding bibframe instance class:
            # add the resulting bf class to the instance:
            # print("It's also a subclass: " + str(get_mediacarrier(mt2.text)))
            # we add another instance for the second book:
            instance2 = BNode()
            # make it class Instance:
            records_bf.add((instance2, RDF.type, BF.Instance))
            # since it is "second instance", also give it the class bflc:SecondaryInstance:
            records_bf.add((instance2, RDF.type, BFLC.SecondaryInstance))
            # also add instance subclass that describes the media type (Electronic or Print):
            records_bf.add((instance2, RDF.type, get_mediacarrier(mt2field)))
            # make sure to connect the two instances with an explicit bf:otherPsychicalFormat,
            # even though we already say this _implicitly_ with the bflc:SecondaryInstance class:
            records_bf.add((instance_uri, BF.otherPhysicalFormat, instance2))


###


###
## get the publication info from PU field and add to the instance:
def add_publication_info(instance_uri, record):
    # print("media type: " + mediatype)
    # get field PU:
    pu = None
    pu = record.find("PU")
    publisher_name = None
    publication_place = None
    publication_date = None
    # create the node for the publication info:
    publication_node = URIRef(str(instance_uri) + "_publication")
    # add the date to the bf:provisionActivity:
    publication_date = get_publication_date(record)
    # add the publication node to the instance:
    records_bf.add((instance_uri, BF.provisionActivity, publication_node))
    # make it class bf:Publication:
    records_bf.set((publication_node, RDF.type, BF.Publication))
    if publication_date is not None:
        records_bf.add((publication_node, BFLC.simpleDate, Literal(publication_date)))

    if pu is not None and pu.text != "":
        pufield = html.unescape(pu.text.strip())
        # get publisher name from subfield v:
        publisher_name = get_subfield(pufield, "v")
        # get place from subfield o:
        publication_place = get_subfield(pufield, "o")
        # add the place to the bf:provisionActivity, its not none:
        if publication_place is not None:
            records_bf.add(
                (publication_node, BFLC.simplePlace, Literal(publication_place))
            )
        # add the publisher to the bf:provisionActivity as bflc:simpleAgent:
        if publisher_name is not None:
            records_bf.add(
                (publication_node, BFLC.simpleAgent, Literal(publisher_name))
            )


# %% [markdown]
# ## Semi-generic helper functions

# %% [markdown]
# ### Getting subfields from a field


# %%
def get_subfield(subfield_full_string, subfield_name):
    """Given a string that contains star subfields (|name ) and the name of the subfield,
    e.g. i for |i, return the content of only that subfield as a string."""
    # first, make sure that the extracted substring is not None, not empty or completely comprised of spaces:
    if subfield_full_string is not None and subfield_full_string != "":
        # strip out any double spaces and replace with single space, also strip spaces around:
        subfield_full_string = re.sub(" {2,}", " ", subfield_full_string.strip())
        # split out the content of the field - from the first |name to either the next | or the end of subfield_full_string:
        subfield = None
        # check if the subfield is in the string:
        if f"|{subfield_name}" in subfield_full_string:
            # if it is, split the string on the subfield name:
            subfield = subfield_full_string.split(f"|{subfield_name}")[1].strip()
            # end the string at the next | or the end of the string:
            subfield = subfield.split("|")[0].strip()
        # subfield = subfield_full_string.split(f"|{subfield_name}")[1].strip().split("|")[0].strip()
        # print(subfield)
        if subfield != "" and subfield is not None:
            return html.unescape(mappings.replace_encodings(subfield))
        else:
            return None


def get_mainfield(field_fullstring):
    """Given a string extracted from a star field that may have substrings or not, return the content of
    the main field as a string - either to the first |subfield or the end of the field, if no subfields.
    """
    # first, make sure that the extracted substring is not None, not empty or completely comprised of spaces:
    if field_fullstring is not None and field_fullstring != "":
        # strip out any double spaces and replace with single space, also strip spaces around:
        field_fullstring = re.sub(" {2,}", " ", field_fullstring.strip())
        # split out the content of the field - to the first | or the end of subfield_full_string:
        field = None
        # check if a subfield is in the string:
        if f"|" in field_fullstring:
            # if it is, return the part before it:
            field = field_fullstring.split("|")[0].strip()
        else:
            # if not, return the whole string:
            field = field_fullstring.strip()
        if field != "" and field is not None:
            return html.unescape(mappings.replace_encodings(field))
        else:
            return None


# %% [markdown]
# ### Getting URLs and DOIs from a field
# Converting http-DOIs to pure ones, checking if what looks like url really is one.


# %%
def check_for_url_or_doi(string):
    """checks if the content of the string is a doi or url or something else.
    Returns the a string and a string_type (doi, url, unknown). The given string
    is sanitized, eg. missing http protocol is added for urls; dois are stripped
    of web protocols and domain/subdomains like dx, doi.org)."""
    # use a regex: if string starts with "DOI " or "DOI:" or "DOI: " (case insensitive), remove that and strip again:
    doi_error_pattern = re.compile(r"^(DOI:|DOI |DOI: )", re.IGNORECASE)
    string = doi_error_pattern.sub("", string).strip()

    # find any stray characters at the start of the field with spaces around them and remove them:
    # "^ . " - this will catch :, but also |u fields marked with "x" for empty:
    error_pattern2 = re.compile(r"^(. )")
    string = error_pattern2.sub("", string).strip()
    # and also remove the words "PsychOpen GOLD" from the start of the field:
    string = re.sub(r"PsychOpen GOLD", "", string)

    # replace double spaces with single space
    string = re.sub(" {2,}", " ", string)

    # Fix spaces in common urls:
    # use this regex: "(.*\.) ((io)|(org)|(com)|(net)|(de))\b"
    # and replace with: group1, group2:
    url_error_pattern = re.compile(r"(.*\.) ((io)|(org)|(com)|(net)|(de))\b")
    string = url_error_pattern.sub(r"\1\2", string)

    # replace spaces after slashes (when followed by a letter or a digit a question mark, eg "osf.io/ abc"):
    # use this regex: (.*/) ([a-z]) and replace with group1, group2:
    # example: "osf.io/ abc" -> "osf.io/abc", "https:// osf.io/ abc" -> "https://osf.io/abc"
    url_error_pattern3 = re.compile(r"(.*/) ([a-z]|[0-9]|\?)")
    string = url_error_pattern3.sub(r"\1\2", string)

    # and now spaces before slashes:
    # use this regex: (.*) (/) and replace with group1, group2:
    # example: "https: //", "http://domain.org/blabla /"
    url_error_pattern4 = re.compile(r"(.*) (/)")
    string = url_error_pattern4.sub(r"\1\2", string)

    # replace single space with underscore,
    # fixing a known STAR bug that replaces underscores with spaces,
    # which is especially bad for urls.  (In other text,
    # we can't really fix it, since usually a space was intended):
    string = re.sub(" ", "_", string)

    # now check for doi or url:
    doi_pattern = re.compile(r"^(https?:)?(\/\/)?(dx\.)?doi\.org\/?(.*)$")
    if doi_pattern.search(string):
        # remove the matching part:
        string = doi_pattern.search(string).group(4)
        string_type = "doi"
        # print("DOI: " + doi)
    elif string.startswith("10."):
        # if the string starts with "10." the whole thing is a DOI:
        string_type = "doi"
        # print("DOI: " + doi)
        # proceed to generate an identifier node for the doi:
    else:
        # doi = None
        # check for validity of url using a regex:
        url_pattern = re.compile(
            r"[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)",
            re.IGNORECASE,
        )
        if url_pattern.search(string):
            # if it's a nonstandard url starting with "//", add a "http:" protocol to the start:
            if string.startswith("//"):
                string = "http:" + string
                # or if it starts with a letter (like osf.io/), add "http://" to the start:
            elif string[0].isalpha() and not string.startswith("http"):
                string = "http://" + string
            string_type = "url"
            # print("URL: " + datac_url)
        else:
            # url = None
            string_type = "unknown"
            # print("Das ist weder eine DOI noch eine URL: " + string)
    return string, string_type


# %% [markdown]
# ### Building identifier nodes for DOIs
#
# Should probably refactor to be more general, so we can use it for other identifiers as well. Needs a parameter for the identifier type.


# %%
def build_doi_identifier_node(instance, doi):
    # print(f"bf:identifiedBy > bf:Doi > rdf:value: {doi}.")
    # make bnode for the identifier:
    identifier_node = BNode()
    # give it class bf:Doi:
    records_bf.add((identifier_node, RDF.type, BF.Doi))
    # give it the doi as a literal value:
    records_bf.add((identifier_node, RDF.value, Literal(doi)))
    # attach it to the instance with bf:identifiedBy:
    records_bf.add((instance, BF.identifiedBy, identifier_node))


# %% [markdown]
# ### Building "Links" as electronic locator nodes for an instance


# %%
def build_electronic_locator_node(instance, url):
    # locator_node = BNode()
    # make it a uri that we can add directly! example: https://id.loc.gov/ontologies/bibframe.html#p_electronicLocator
    locator_node = URIRef(url)
    # add it to the instance_node of relationship_node via bf:electronicLocator
    # directly as a uri! No intermediary class node with a rdf:value
    # records_bf.set((locator_node, RDF.value, Literal(url, datatype=XSD.anyURI)))
    # attach it to the instance with bf:electronicLocator:
    records_bf.set((instance, BF.electronicLocator, locator_node))


# %% [markdown]
# ### Building generic bf:Note nodes
#
# Will probably also need this later for other kinds of notes, such as the ones in field BN.


# %%
def build_note_node(instance, note):
    note_node = BNode()
    records_bf.set((note_node, RDF.type, BF.Note))
    records_bf.set((note_node, RDFS.label, Literal(note)))
    records_bf.set((instance, BF.note, note_node))


# %% [markdown]
# ## Function: Replace weird characters with unicode
#
#

# %%
# from modules.mappings import dd_codes

# def replace_encodings(text):
#     # text = html.escape(text)
#     for case in dd_codes:
#         text = text.replace(case[0], case[1])
#     return text

# moved to modules.mappings!

# %% [markdown]
# ## Function: Guess language of a given string
# Used for missing language fields or if there are discrepancies between the language field and the language of the title etc.

# %%
import langid

langid.set_languages(["de", "en"])


def guess_language(string_in_language):
    return langid.classify(string_in_language)[0]


# %% [markdown]
# ## Function: Adding DFK as an Identifier

# %% [markdown]
# ### DFK as id for Bibframe
#
# We want to add the DFK as a local bf:Identifier to the work (or instance?).
# We also want to say where the Identifier originates (to say it is from PSYNDEX/ZPID).
#
# The format for that is:
# ```turtle
# <Work/Instance> bf:identifiedBy [
#     a bf:Local, pxc:DFK;
#     rdf:value "1234456";
#     bf:source [
#         a bf:Source; bf:code "ZPID.PSYNDEX.DFK"
#     ]
# ];
# ```
#
# So, we need a blank node for the Identifier and inside, another nested bnode for the bf:Source. This is a function that will return such an identifier bnode to add to the work_uri. We are calling it way up down below in the loop:


# %%
#  a function to be called in a for-loop while going through all records of the source xml,
# which returns a new triple to add to the graph that has a bnode for the dfk identifier.
# The predicate is "bf:identifiedBy" and the object is a blank node of rdf:Type "bf:Identifier" and "bf:Local":
# The actual identifier is a literal with the text from the "DFK" element of the record.
def get_bf_identifier_dfk(resource_uri, dfk):
    # make a node of the Identifier class from the BF namespace:
    identifier = URIRef(resource_uri + "#dfk")
    # records_bf.add ((identifier, RDF.type, BF.Identifier))
    # records_bf.add ((identifier, RDF.type, BF.Local))
    records_bf.add((identifier, RDF.type, PXC.DFK))
    # build the source node:
    # records_bf.add((identifier_source, RDF.type, BF.Source))
    # records_bf.add((identifier_source, BF.code, Literal("ZPID.PSYNDEX.DFK")))
    # hang the id source node into the id node:
    # records_bf.add((identifier, BF.source, identifier_source))
    records_bf.add((identifier, RDF.value, Literal(dfk)))
    return identifier


# %% [markdown]
# ## Generic Function: Replace languages with their language tag
#
# Can be used for different fields that are converted to langstrings or language uris. Use within other functions that work with the languages in different fields.
#
# Returns an array with two values: a two-letter langstring tag at [0] and a three-letter uri code for the library of congress language vocab at [1].


# %%
def get_langtag_from_field(langfield):
    # when passed a string from any language field in star, returns an array with two items.
    # Index 0: two-letter langstring tag, e.g. "de"
    # Index 1: two-letter iso langtag, e.g. "ger"
    # can be used on these fields (it contains the different spellings found in them):
    # "LA", "LA2", "TIL", "TIUL", "ABLH", "ABLN", "TIUE |s"
    match langfield:
        case (
            "german" | "de" | "GERM" | "Deutsch" | "GERMAN" | "GERMaN" | "German" | "Fi"
        ):
            return ["de", "ger"]
        case (
            "en"
            | "ENGL"
            | "ENGLISH"
            | "Englisch"
            | "English"
            | "English; English"
            | "english"
        ):
            return ["en", "eng"]
        case "BULG" | "Bulgarian":
            return ["bg", "bul"]
        case "SPAN" | "Spanish":
            return ["es", "spa"]
        case "Dutch":
            return ["nl", "dut"]
        case "CZEC":
            return ["cs", "ces"]
        case "FREN" | "French":
            return ["fr", "fra"]
        case "ITAL" | "Italian":
            return ["it", "ita"]
        case "PORT" | "Portuguese":
            return ["pt", "por"]
        case "JAPN" | "Japanese":
            return ["jp", "jpn"]
        case "HUNG":
            return ["hu", "hun"]
        case "RUSS" | "Russian":
            return ["ru", "rus"]
        case "NONE" | "Silent":
            return ["zxx", "zxx"]
        case _:
            return ["und", "und"]  # for "undetermined!"


# %% [markdown]
# ## Function: Get work language from LA
#
# Example
#
# ```turtle
# @prefix lang: <http://id.loc.gov/vocabulary/iso639-2/> .
# <W> bf:language lang:ger .
# ```
#
# Calls the generic language code lookup function above, get_langtag_from_field, passing the LA field content, returning a uri from the library of congress language vocabulary (built from namespace + 3-letter iso code).
#
# TODO:
# - But what if field LA is missing? (doesn't occur in test set, but not impossible)
# - or if there is another language in LA2? (in my test set, 2 out of 700 records have LA2)


# %%
# function
def get_work_language(record):
    work_language = get_langtag_from_field(record.find("LA").text.strip())[1]
    work_lang_uri = LANG[work_language]
    return work_lang_uri


# %% [markdown]
# ## Function: Build a Relationship Node for different types of related works
#
# Should take parameters - a dict per type (research data closed access, rd open access, ...) that has values for all the needed fields

# %%


def build_work_relationship_node(work_uri, relation_type):
    # check the relation_type against the relation_types dict:
    if relation_type in relation_types:
        # if it is, get the values for the relation_type:
        relation = relation_types[relation_type]["relation"]
        relatedTo_subprop = relation_types[relation_type]["relatedTo_subprop"]
        work_subclass = relation_types[relation_type]["work_subclass"]
        content_type = relation_types[relation_type]["content_type"]
        genre = relation_types[relation_type]["genre"]
        access_policy_label = relation_types[relation_type]["access_policy_label"]
        access_policy_value = relation_types[relation_type]["access_policy_value"]
    # make a bnode for this relationship:
    relationship_bnode = BNode()
    # make it class bflc:Relationship:
    records_bf.set((relationship_bnode, RDF.type, BFLC.Relationship))
    # add a bflc:Relation (with a label and value) via bflc:relation to the relationship bnode
    # (label and value could be given as a parameter):
    # print("\tbflc:relation [a bflc:Relation ; rdfs:label 'has research data', rdf:value 'relation:hasResearchData'^^xsd:anyURI] ;")
    # relation_bnode = BNode()
    # records_bf.set((relation_bnode, RDF.type, BFLC.Relation))
    # records_bf.add((relation_bnode, RDFS.label, Literal("has research data", lang="en")))
    # records_bf.add((relation_bnode, RDF.value, Literal(RELATIONS.hasResearchData)))
    records_bf.set((relationship_bnode, BFLC.relation, URIRef(RELATIONS[relation])))
    # make a bnode for the work:
    related_work_bnode = BNode()
    records_bf.add((related_work_bnode, RDF.type, BF.Work))
    records_bf.add((related_work_bnode, RDF.type, URIRef(BF[work_subclass])))
    # give work a content type:
    records_bf.add((related_work_bnode, BF.content, URIRef(CONTENTTYPES[content_type])))
    # make the content type a bf:Content:
    records_bf.add((URIRef(CONTENTTYPES[content_type]), RDF.type, BF.Content))
    # and a genre:
    records_bf.add((related_work_bnode, BF.genreForm, URIRef(GENRES[genre])))
    # make the genreform a bf:GenreForm:
    records_bf.add((URIRef(GENRES[genre]), RDF.type, BF.GenreForm))
    # attach the work bnode to the relationship bnode with bf:relatedTo
    # (or a subproperty as given as a parameter)):
    # print("\tbf:relatedTo [a bf:Work ;")
    records_bf.add((relationship_bnode, BF[relatedTo_subprop], related_work_bnode))
    # make a bnode for the instance:
    related_instance_bnode = BNode()
    records_bf.set((related_instance_bnode, RDF.type, BF.Instance))
    records_bf.add((related_instance_bnode, RDF.type, BF.Electronic))
    records_bf.add((related_work_bnode, BF.hasInstance, related_instance_bnode))
    # add accesspolicy to instance:
    if access_policy_label is not None and access_policy_value is not None:
        access_policy_node = BNode()
        records_bf.add((access_policy_node, RDF.type, BF.AccessPolicy))
        records_bf.add(
            (access_policy_node, RDFS.label, Literal(access_policy_label, lang="en"))
        )
        records_bf.add(
            (
                access_policy_node,
                RDF.value,
                Literal(access_policy_value, datatype=XSD.anyURI),
            )
        )
        records_bf.add(
            (related_instance_bnode, BF.usageAndAccessPolicy, access_policy_node)
        )
    # in the end, return the relationship bnode so it can be attached to the work
    # records_bf.add((work_uri, BFLC.relationship, relationship_bnode))
    return relationship_bnode, related_instance_bnode


relation_types = {
    "rd_open_access": {
        "relation": "hasResearchData",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Dataset",
        "content_type": "cod",
        "genre": "researchData",
        "access_policy_label": "open access",
        "access_policy_value": "http://purl.org/coar/access_right/c_abf2",
    },
    "rd_restricted_access": {
        "relation": "hasResearchData",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Dataset",
        "content_type": "cod",
        "genre": "researchData",
        "access_policy_label": "restricted access",
        "access_policy_value": "http://purl.org/coar/access_right/c_16ec",
    },
    "preregistration": {
        "relation": "hasPreregistration",
        "relatedTo_subprop": "supplement",
        "work_subclass": "Text",
        "content_type": "txt",
        "genre": "preregistration",
        "access_policy_label": None,
        "access_policy_value": None,
    },
}

# %% [markdown]
# ## Function: Create Instance Title nodes from fields TI, TIU, TIL, TIUE...
#
# Titles and Translated titles are attached to Instances. Translated titles also have a source, which can be DeepL, ZPID, or Original.
#
# Example:
#
# ```turtle
# <Instance> bf:title
#         [a bf:Title;
#             bf:mainTitle "Disentangling the process of epistemic change"@en;
#             bf:subtitle "The role of epistemic volition"@en;
#         ],
#         [a pxc:TranslatedTitle;
#             rdfs:label "Den Prozess des epistemischen Wandels entwirren: Die Rolle des epistemischen Willens."@de;
#             bf:mainTitle "Den Prozess des epistemischen Wandels entwirren: Die Rolle des epistemischen Willens."@de;
#             bf:adminMetadata  [
#                 a bf:AdminMetadata ;
#                 bflc:metadataLicensor  "DeepL";
#         ]
#         ].
# ```
#
# - [x] add TI as bf:Title via bf:mainTitle
# - [x] add subtitle from TIU
# - [x] create a concatenated rdfs:label from TI and TIU
# - [x] add languages for maintitle and subtitle (from TIL and TIUL)
#
# - [x] add translated title from TIUE as pxc:TranslatedTitle with bf:mainTitle and rdfs:label
# - [x] add languages for translated title (from subfield TIU |s, or if unavailable, guess language from the subtitle string itself (contents of TIU)
# - [x] create a source/origin for the translated title (from "(DeepL)" at the end)


# %%
#  a function to be called in a for-loop while going through all records of the source xml,
# which returns a new triple to add to the graph that has a bnode for the dfk identifier.
# The predicate is "bf:identifiedBy" and the object is a blank node of rdf:Type "bf:Identifier" and "bf:Local":
# The actual identifier is a literal with the text from the "DFK" element of the record.
def get_bf_title(resource_uri, record):
    # make a  BNODE for the title:
    title = URIRef(resource_uri + "#title")
    # make it bf:Title class:
    records_bf.add((title, RDF.type, BF.Title))

    # get the content of th TI field as the main title:
    maintitle = html.unescape(
        mappings.replace_encodings(record.find("TI").text).strip()
    )
    # write a full title for the rdfs:label
    # (update later if subtitle exists to add that)
    fulltitle = maintitle
    # set fallback language for main title:
    maintitle_language = "en"
    subtitle_language = "en"
    # get language of main title - if exists!:
    if record.find("TIL") is not None:
        maintitle_language = get_langtag_from_field(record.find("TIL").text.strip())[0]
        # if maintitle_language that is returned the get_langtag_from_field is "und"
        # (because it was a malformed language name), guess the language from the string itself!
        if maintitle_language == "und":
            maintitle_language = guess_language(maintitle)
    else:  # if there is no TIL field, guess the language from the string itself!
        maintitle_language = guess_language(maintitle)

    # add the content of TI etc via bf:mainTitle:
    records_bf.add((title, BF.mainTitle, Literal(maintitle, lang=maintitle_language)))
    # get content of the TIU field as the subtitle,
    # _if_ it exists and has text in it:
    if record.find("TIU") is not None and record.find("TIU").text != "":
        subtitle = html.unescape(
            mappings.replace_encodings(record.find("TIU").text).strip()
        )  # sanitize encoding and remove extraneous spaces
        # concatenate a full title from main- and subtitle,
        # separated with a : and overwrite fulltitle with that
        fulltitle = fulltitle + ": " + subtitle
        # get language of subtitle - it is in field TIUL, but sometimes that is missing...:
        #  # get language of subtitle:
        if record.find("TIUL") is not None:
            subtitle_language = get_langtag_from_field(
                record.find("TIUL").text.strip()
            )[0]
            if subtitle_language == "und":
                subtitle_language = guess_language(subtitle)
        else:  # if there is no TIUL field, guess the language from the string itself!
            subtitle_language = guess_language(subtitle)

        # add the content of TIU to the bf:Title via bf:subtitle:
        records_bf.add((title, BF.subtitle, Literal(subtitle, lang=subtitle_language)))

    # add the concatenated full title to the bf:Title via rdfs:label:
    # (we don't care if the main title's and subtitle's languages don't match - we just set the language of the main title as the full title's language)
    records_bf.add((title, RDFS.label, Literal(fulltitle)))

    # # hang the id source node into the id node:
    # records_bf.add((identifier, BF.source, identifier_source))
    return title


# function for the translated title:
def get_bf_translated_title(resource_uri, record):
    translated_title = URIRef(resource_uri + "#translatedtitle")
    records_bf.add((translated_title, RDF.type, PXC.TranslatedTitle))
    fulltitle = html.unescape(
        mappings.replace_encodings(record.find("TIUE").text).strip()
    )
    fulltitle_language = "de"
    # read subfield |s to get the actual language (it doesn't always exist, though).
    # if fulltitle string ends with "|s " followed by some text (use a regex):
    match = re.search(r"^(.*)\s\|s\s(.*)", fulltitle)
    if match:
        fulltitle = match.group(1).strip()
        fulltitle_language = get_langtag_from_field(match.group(2).strip())[0]
    else:
        # if the language of the translated title (in |s) is missing, guess the language from the string itself!
        fulltitle_language = guess_language(fulltitle)

    # check if the title contains a "(DeepL)" and cut it into a variable for the source:
    titlesource = "ZPID"  # translation source is "ZPID" by default
    # note: we might be able to add source "Original" by finding out
    # if the source of the secondary abstract is something other than ZPID!
    match_source = re.search(r"^(.*)\((DeepL)\)$", fulltitle)
    if match_source:
        fulltitle = match_source.group(1).strip()
        titlesource = match_source.group(2)

    # build a (fragment) source node for the translation:
    titlesource_node = URIRef(translated_title + "_source")
    records_bf.add((titlesource_node, RDF.type, BF.AdminMetadata))
    records_bf.add((titlesource_node, BFLC.metadataLicensor, Literal(titlesource)))

    # add the title string to the node:
    records_bf.add(
        (translated_title, BF.mainTitle, Literal(fulltitle, lang=fulltitle_language))
    )
    records_bf.add((translated_title, RDFS.label, Literal(fulltitle)))
    records_bf.add((translated_title, BF.adminMetadata, titlesource_node))

    return translated_title


# %% [markdown]
# ## Function: Add Abstracts - original abstract (from fields ABH, ABLH, ABSH1, ABSH2) and translated/secondary abstract (from ABN, ABLN, ASN1, ASN2)
#
# - Main Abstract:
#     - abstract text is in field ABH.
#     - abstract language is in ABLH ("German" or "English") but can be missing in rare cases! In that case, we guess it using the langid module.
#     - abstract original source is in ASH1 ("Original" or "ZPID")
#     - agent who edited the original, if that happened, is in ASH2 ()
# - Secondary Abstract
#     - abstract text is in field ABN.
#     - abstract language is in ABLN ("German" or "English")
#     - abstract original source is in ASN1 ("Original" or "ZPID")
#     - agent who edited the original, if that happened, is in ASN2 ()
#
# Scheme:
#
# ```turtle
# <W> bf:summary
#     [ a pxc:Abstract , bf:Summary ;
#         rdfs:label  "Background: Loneliness is ..."@en ;
#         bf:adminMetadata  [
#             a bf:AdminMetadata ;
#             bflc:metadataLicensor  "Original";
#             bf:descriptionModifier "ZPID"
#         ]
# ] .
# ```

# %%
from modules.mappings import (
    abstract_origin_original,
    abstract_origin_zpid,
    abstract_origin_deepl,
    abstract_origin_gesis,
    abstract_origin_fis_bildung,
    abstract_origin_krimz,
)


def replace_abstract_origin_string(origin_string):
    # if the passed string is in "abstract_origin_original", thenreplace it with "Original":
    if origin_string in abstract_origin_original:
        return "Original"
    elif origin_string in abstract_origin_zpid:
        return "ZPID"
    # elif origin_string in abstract_origin_iwf:
    #     return "IWF"
    elif origin_string in abstract_origin_deepl:
        return "DeepL"
    elif origin_string in abstract_origin_gesis:
        return "GESIS"
    elif origin_string in abstract_origin_fis_bildung:
        return "FIS Bildung"
    elif origin_string in abstract_origin_krimz:
        return "KrimZ"
    else:
        return origin_string


# function to get the original abstract:
def get_bf_abstract(work_uri, record):
    """Extracts the abstract from field ABH and adds a bf:Summary bnode with the abstract and its metadata. Also extracts the Table of Content from the same field."""
    abstract = URIRef(work_uri + "#abstract")
    # abstract = URIRef(work_uri + "/abstract")
    records_bf.add((abstract, RDF.type, PXC.Abstract))
    # get abstract text from ABH
    abstracttext = html.unescape(
        mappings.replace_encodings(record.find("ABH").text).strip()
    )
    # TODO: check if the abstract is not really an abstract but a note that says a variation of "no abstract available":
    # if so, return None and don't add the abstract node at all. Or add a note node instead. Or a vocab term for "no abstract available". There was some discussion about this. probably use bf:status for it.
    # works:10000 bf:summary <0000abstract> . <0000abstract> bf:status status:NoAbstractAvailable. # that is weird! i'm not at all sure this works, or that i want it to work, because it makes no sense. Maybe i must export the abstract label as an empty string instead of not exporting the abstract at all?
    # some variations found:
    # - "Abstract not provided by publisher"
    # - Abstract nicht vom Verlag zur Verfügung gestellt
    # - Abstract not released by publisher.
    # - No abstract available.
    # - Kein Abstract vorhanden.
    # check if the abstracttext ends with " (translated by DeepL)" and if so, remove that part:
    match1 = re.search(r"^(.*)\s\(translated by DeepL\)$", abstracttext)
    if match1:
        abstracttext = match1.group(1).strip()
    # check via regex if there is a " - Inhalt: " or " - Contents: " in it.
    # if so, split out what comes after. Drop the contents/inhalt part itself.
    match2 = re.search(r"^(.*)[-–]\s*(?:Contents|Inhalt)\s*:\s*(.*)$", abstracttext)
    if match2:
        abstracttext = match2.group(1).strip()
        contents = match2.group(2).strip()
        # make a node for bf:TableOfContents:
        toc = BNode()
        records_bf.add((toc, RDF.type, BF.TableOfContents))
        # add the bnode to the work via bf:tableOfContents:
        records_bf.add((work_uri, BF.tableOfContents, toc))
        # add the contents to the abstract node as a bf:tableOfContents:
        # if the contents start with http, extract as url into rdf:value:
        if contents.startswith("http"):
            records_bf.add((toc, RDF.value, Literal(contents, datatype=XSD.anyURI)))
            # otherwise it's a text toc and needs to go into the label
        else:
            records_bf.add((toc, RDFS.label, Literal(contents, lang="und")))
    # get abstract language from ABLH ("German" or "English")
    abstract_language = "en"  # set default
    # TODO: that's a bad idea, actually. Better: if field is missing, use a language recog function!
    if record.find("ABLH") is not None:
        abstract_language = get_langtag_from_field(record.find("ABLH").text.strip())[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = guess_language(abstracttext)
    else:  # if the ABLH field is missing, try to recognize the language of the abstract from its text:
        abstract_language = guess_language(abstracttext)

    # add the text to the node:
    records_bf.add(
        (abstract, RDFS.label, Literal(abstracttext, lang=abstract_language))
    )

    # get abstract original source from ASH1 ("Original" or "ZPID")
    abstract_source = "Original"  # default
    # create a blank node for admin metadata:
    abstract_source_node = URIRef(str(abstract) + "_source")
    records_bf.add((abstract_source_node, RDF.type, BF.AdminMetadata))

    if record.find("ASH1") is not None:
        # overwrite default ("Original") with what we find in ASH1:
        # and while we're at it, replace some known strings with their respective values
        # (e.g. employee tags with "ZPID"):
        abstract_source = replace_abstract_origin_string(
            record.find("ASH1").text.strip()
        )

    # write final source text into source node:
    records_bf.add(
        (abstract_source_node, BFLC.metadataLicensor, Literal(abstract_source))
    )

    # here is a list of known zpid employee tags, we will use them later to replace these with "ZPID" if found in ASH2:

    # and this is a list of things we want to replace with "Original":

    # get optional agent who edited the original abstract from ASH2
    if record.find("ASH2") is not None:
        # note what we find in ABSH2:
        abstract_editor = replace_abstract_origin_string(
            record.find("ASH2").text.strip()
        )

        records_bf.add(
            (abstract_source_node, BF.descriptionModifier, Literal(abstract_editor))
        )

    # add the source node to the abstract node:
    records_bf.add((abstract, BF.adminMetadata, abstract_source_node))
    # and return the completed node:
    # return (abstract)
    # or better, attach it right away:
    records_bf.add((work_uri, BF.summary, abstract))


def get_bf_secondary_abstract(work_uri, record):
    abstract = URIRef(work_uri + "#secondaryabstract")
    # abstract = URIRef(work_uri + "/abstract/secondary")
    records_bf.add((abstract, RDF.type, PXC.Abstract))
    records_bf.add((abstract, RDF.type, PXC.SecondaryAbstract))
    abstracttext = html.unescape(
        mappings.replace_encodings(record.find("ABN").text).strip()
    )
    # check if the abstracttext ends with " (translated by DeepL)" and if so, remove that part:
    match = re.search(r"^(.*)\s\(translated by DeepL\)$", abstracttext)
    if match:
        abstracttext = match.group(1).strip()

    abstract_language = "de"  # fallback default

    if record.find("ABLN") is not None and record.find("ABLN").text != "":
        abstract_language = get_langtag_from_field(record.find("ABLN").text.strip())[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = guess_language(abstracttext)
    else:  # if no language field, guess language from the text:
        abstract_language = guess_language(abstracttext)

    records_bf.add(
        (abstract, RDFS.label, Literal(abstracttext, lang=abstract_language))
    )

    abstract_source_node = URIRef(str(abstract) + "_source")
    records_bf.add((abstract_source_node, RDF.type, BF.AdminMetadata))
    abstract_source = "Original"  # fallback default
    if record.find("ASN1") is not None:
        # overwrite default ("Original") with what we find in ASH1:
        abstract_source = replace_abstract_origin_string(
            record.find("ASN1").text.strip()
        )

    records_bf.add(
        (abstract_source_node, BFLC.metadataLicensor, Literal(abstract_source))
    )

    # get optional agent who edited the original abstract from ASH2
    if record.find("ASN2") is not None:
        # note what we find in ABSN2:
        abstract_editor = replace_abstract_origin_string(
            record.find("ASN2").text.strip()
        )
        # and add it via decription modifier:
        records_bf.add(
            (abstract_source_node, BF.descriptionModifier, Literal(abstract_editor))
        )

    # add the source node to the abstract node:
    records_bf.add((abstract, BF.adminMetadata, abstract_source_node))
    # and return the completed node:
    return abstract


# %% [markdown]
# ## Function to split Table of Content from the Abstract field (ABH)
#
# This usually starts with " - Inhalt: " (for German Abstracts) or " - Contents: " (in English abstracts) and ends at the end of the field.
# It can contain a numbered list of chapters or sections as a long string. It can also contain a uri from dnb namespace instead or in addition!
#
# Examples:
# - " - Contents: (1) ..."
# - " - Inhalt: https://d-nb.info/1256712809/04</ABH>" (URI pattern: "https://d-nb.info/" + "1256712809" 10 digits + "/04")
#
# Example:
#
# ```turtle
# <W> bf:tableOfContents [
#     a bf:TableOfContents;
#     rdfs:label "(1) Wünsche, J., Weidmann, R. &amp; Grob, A. (n. d.). Happy in the same way? The link between domain satisfaction and overall life satisfaction in romantic couples. Manuscript submitted for publication. (2) Wünsche, J., Weidmann,...";
# ] .
# ```
#
# Or
#
# ```turtle
# <W> bf:tableOfContents [
#     a bf:TableOfContents;
#     rdf:value "https://d-nb.info/1002790794/04"^^xsd:anyURI ;
# ] .
# ```


# %%
def get_bf_toc(work_uri, record):
    # read the abstract in ABH
    contents = ""
    if record.find("ABH") is not None:
        abstracttext = html.unescape(
            mappings.replace_encodings(record.find("ABH").text).strip()
        )
        # check via regex if there is a " - Inhalt: " or " - Contents: " in it.
        # if so, split out what comes after. Drop the contents/inhalt part itself.
        match = re.search(r"^(.*)[-–]\s*(?:Contents|Inhalt)\s*:\s*(.*)$", abstracttext)
        if match:
            abstracttext = match.group(1).strip()
            contents = match.group(2).strip()

    # also check if what comes is either a string or a uri following thegiven pattern
    # and export one as a rdfs_label and the other as rdf:value "..."^^xsd:anyUrl (remember to add XSD namespace!)
    # also remember that we should only create a node and attach it to the work
    # if a) ABH exists at all and
    # b) the regex is satisfied.
    # So I guess we must do the whole checking and adding procedure in this function!

    # only return an added triple if the toc exisits, otherwise return nothing:
    if contents:
        return records_bf.add((work_uri, BF.tableOfContents, Literal(contents)))
    else:
        return None
    # return records_bf.add((work_uri, BF.tableOfContents, Literal("test")))


# %% [markdown]
# ## Function: Create Topics, Weighted Topics and Classifications from CT, SH
#
# CTs - controlled terms from our own thesaurus - are added like this. Some are always weighted (=more important) and have an added class pxc:WeightedTopic (a subclass of bf:Topic), some are not.
#
# Currently, we don't export the concept uri, since the export files we use have no code info (which we use to construct concept uris). But at least we have a source uri for the concept scheme (which is the same for all concepts in the file).
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


# %%
def add_controlled_terms(work_uri, record):
    # get the controlled terms from the field CT:
    topiccount = 0
    for data in record.findall("CT"):
        # get the content of the CT field:
        controlled_term_string = mappings.replace_encodings(data.text.strip())
        # we need to split the string into these possible parts:
        # "|e English Label" for the English label,
        # "|d Deutsches Label" for the German label, and
        # "|g x", which, if it exists, indicates that this Topic is also weighted and should get an additional class (beside bf:Topic) of either "PXC.WeightedTopic"
        # we will use the get_Subfield function, which takes the subfield name as the parameter and returns the content of that subfield if it exists, or None if it doesn't.
        # initialize variables for the controlled term string parts:
        controlled_term_string_english = get_subfield(controlled_term_string, "e")
        controlled_term_string_german = get_subfield(controlled_term_string, "d")
        term_weighting = get_subfield(controlled_term_string, "g")
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
        # add source to the controlled term node (bf:source <https://w3id.org/zpid/vocabs/terms>):
        # records_bf.add(
        #     (
        #         controlled_term_node,
        #         BF.source,
        #         URIRef("https://w3id.org/zpid/vocabs/terms"),
        #     )
        # )
        # get uri from lookup in skosmos api:
        controlled_term_uri = get_concept_uri_from_skosmos(
            controlled_term_string_english, "terms"
        )
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
        records_bf.set((controlled_term_node, OWL.sameAs, URIRef(controlled_term_uri)))

        # attach the controlled term node to the work node:
        records_bf.add((work_uri, BF.subject, controlled_term_node))


# %% [markdown]
# ## TODO: Function: Create nodes for Population Age Group (AGE) and Population Location (PLOC)
#
# Use this scheme:
#
# ```turtle
# <Work>
# # age group study is about/sample was from:
#     bflc:demographicGroup [a bflc:DemographicGroup, pxc:AgeGroup, skos:Concept;
#         rdfs:label "Adulthood"@en, "Erwachsenenalter"@de;
#         owl:sameAs <https://w3id.org/zpid/vocabs/age/adulthood>;
#         bf:source <https://w3id.org/zpid/vocabs/age/AgeGroups>;
#     ];
#     # population location:
#     bf:geographicCoverage [a bf:GeographicCoverage, pxc:PopulationLocation, skos:Concept;
#         rdfs:label "Germany"@en;
#         owl:sameAs <countries/ger>;
#     ].
# ```

# %% [markdown]
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
#                 bf:identifier [a bf:Identifier, bf:Doi; rdf:value "10.123code003"];
#                 # add bf:media "computer" from rda media types
#                 bf:media <http://rdvocab.info/termList/RDAMediaType/1003>;
#                 # bf:carrier "online resource" from rda vocabulary
#                 bf:carrier <http://rdvocab.info/termList/RDACarrierType/1018>;
#             ]
#         ]
#     ]
# .
# ```

# %%
# function to build the nodes for preregistration links


def get_bf_preregistrations(work_uri, record):
    # get the preregistration link from the field PREREG:
    preregistration_note = None
    unknown_field_content = None
    for prreg in record.findall("PRREG"):
        # get the full content of the field, sanitize it:
        prregfield = html.unescape(mappings.replace_encodings(prreg.text.strip()))
        # use our node-building function to build the node:
        relationship_node, instance = build_work_relationship_node(
            work_uri, relation_type="preregistration"
        )
        doi_set = set()
        url_set = set()
        for subfield_name in ("u", "d"):
            try:
                subfield = get_subfield(prregfield, subfield_name)
            except:
                subfield = None
            else:
                # print(subfield)
                # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
                # as a doi or url:
                # if it is a doi, run a function to generate a doi identifier node
                if subfield is not None and check_for_url_or_doi(subfield)[1] == "doi":
                    # add the doi to a list:
                    doi_set.add(check_for_url_or_doi(subfield)[0])
                    # build_doi_identifier_node(instance, check_for_url_or_doi(subfield)[0])
                elif (
                    subfield is not None and check_for_url_or_doi(subfield)[1] == "url"
                ):
                    url_set.add(check_for_url_or_doi(subfield)[0])
                    # build_electronic_locator_node(instance, check_for_url_or_doi(subfield)[0])
                    # if the returned typ is something else - "unknown", do nothing with it:
                else:
                    # print("bf:note > bf:Note > rdfs:label: " + subfield)
                    # build_note_node(instance, check_for_url_or_doi(subfield)[0])
                    if (
                        subfield is not None
                        and check_for_url_or_doi(subfield)[0] is not None
                        and check_for_url_or_doi(subfield)[0] != ""
                    ):
                        # add a variable
                        unknown_field_content = check_for_url_or_doi(subfield)[
                            0
                        ].strip()
                        print(
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
                    print(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)
        # now build the doi identifier nodes for any DOIs in the set we collected:
        for doi in doi_set:
            build_doi_identifier_node(instance, doi)
        for url in url_set:
            build_electronic_locator_node(instance, url)
        # for the text in the |i subfield, build a note without further processing:
        try:
            preregistration_note = get_subfield(prregfield, "i")
        except:
            preregistration_note = None
        else:
            # add anything in the |i subfield as a note to the instance:
            # but if we found something unrecognizable in |u or |i, also add it to the note:
            if unknown_field_content is not None:
                build_note_node(
                    instance, preregistration_note + ". " + unknown_field_content
                )
            else:
                build_note_node(instance, preregistration_note)
        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))

        # add preregistration_node to work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


# %% [markdown]
# ## Function: Create nodes for Grants (GRANT)
#
# Includes several helper functions that
# - extract grant numbers if several were listed in the |n subfield
# - replace funder names that fundref usually doesn't match correctly or at all
# - look up funder names in crossref's fundref api to get their fundref id (a doi)


# %%
def extract_grant_numbers(subfield_n_string):
    # this function takes a string that possibly contains an unstructured set of several award numbers connected with "and" etc. and returns a real array (List) of award numbers
    # first, split the string on "," or ";" or "and": (first replacing all semicolons and "ands" with commas)")
    subfield_n_string = subfield_n_string.replace(" and ", ", ")
    subfield_n_string = subfield_n_string.replace(" und ", ", ")
    subfield_n_string = subfield_n_string.replace(" & ", ", ")
    subfield_n_string = subfield_n_string.replace(";", ",")
    subfield_n_string = subfield_n_string.split(", ")
    # in each of the returned list elements, remove any substrings that are shorter
    # than 5 characters (to get rid of things like " for" or "KDL: " YG: " etc.)
    # for element in subfield_n_string:
    #     if len(element) < 5:
    #         subfield_n_string.remove(element)
    # go through all the list elements and replace each with a dict,
    # which has a key "grant_number" and a key "grant_name" (which is None for now):
    # for i, element in enumerate(subfield_n_string):
    #     subfield_n_string[i] = {"grant_number": element, "grant_name": None}
    # # return the list of dicts:
    return subfield_n_string


def replace_common_fundernames(funder_name):
    """This will accept a funder name that the crossref api may not recognize, at least not as the first hit,
    and replace it with a string that will supply the right funder as the first hit"""
    # if the funder_name is in the list of funder names to replace (in index 0), then replace it with what is in index 1:
    for funder in mappings.funder_names_replacelist:
        if funder_name == funder[0]:
            funder_name = funder[1]
            # print("replacing " + funder[0] + " with " + funder[1])
    return funder_name


def get_crossref_funder_id(funder_name):
    # this function takes a funder name and returns the crossref funder id for that funder name
    # to do this, use the crossref api.
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

    try:
        if (
            crossref_api_request.status_code == 200
            and crossref_api_response["message"]["total-results"] > 0
        ):
            # return the number of results:
            # print("Treffer: " + str(crossref_api_response["message"]["total-results"]))
            # return the first hit:
            # print("Erster Treffer: " + crossref_api_response["message"]["items"][0]["name"])
            # print("DOI: " + "10.13039" + crossref_api_response["message"]["items"][0]["id"])
            return "10.13039/" + crossref_api_response["message"]["items"][0]["id"]
        elif (
            crossref_api_request.status_code == 200
            and crossref_api_response["message"]["total-results"] == 0
        ):
            # retry the funder_name, but remove any words after the first comma:
            print(f"fundref-api: no hits for {funder_name}.")
            if funder_name.find(",") > -1:
                funder_name = funder_name.split(",")[0]
                print(f"fundref-api: new funder name: {funder_name}")
                return get_crossref_funder_id(funder_name)
            else:
                print(f"fundref-api: nothing either for {funder_name}. Returning None.")
                return None
    except KeyError:
        print("Error: Missing key in crossref_api_response.")
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed - {e}")
    except Exception as e:
        print(f"Error: {e}")


# function to build the nodes for preregistration links
def get_bf_grants(work_uri, record):
    """this function takes a string and returns a funder (name and fundref doi),
    a list of grant numbers, a note with grant holder and info"""
    for grant in record.findall("GRANT"):
        # point zero: remove html entities from the field:
        grantfield = html.unescape(grant.text)
        # if the field contains these, skip it - don't even create a fundinfregerence node:
        if "projekt deal" in grantfield.lower() or "open access" in grantfield.lower():
            continue
        # point one: pipe all text in the field through the DD-Code replacer function:
        grantfield = mappings.replace_encodings(grantfield)
        # count up the global funding counter for this record:
        global fundingreference_counter
        fundingreference_counter += 1
        # add a node for a new Contribution:
        funding_contribution_node = URIRef(
            str(work_uri) + "#fundingreference" + str(fundingreference_counter)
        )
        # records_bf.add((funding_contribution_node, RDF.type, BF.Contribution))
        records_bf.add((funding_contribution_node, RDF.type, PXC.FundingReference))
        # add a blank node for the funder agent:
        funder_node = URIRef(str(funding_contribution_node) + "_funder")
        records_bf.add((funder_node, RDF.type, BF.Agent))
        records_bf.add((funder_node, RDF.type, PXC.Funder))
        # add the funder agent node to the funding contribution node:
        records_bf.add((funding_contribution_node, BF.agent, funder_node))
        # add a role to the funding contribution node:
        records_bf.add(
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
        records_bf.add((funder_node, RDFS.label, Literal(funder_name)))
        # try to look up this funder name in the crossref funder registry:
        # if there is a match, add the crossref funder id as an identifier:
        crossref_funder_id = None
        crossref_funder_id = get_crossref_funder_id(funder_name)
        if crossref_funder_id is not None:
            # add a blank node for the identifier:
            crossref_funder_id_node = URIRef(str(funder_node) + "_funderid")
            # use our custim identifier class FundRefDoi (subclass of bf:Doi):
            records_bf.add((crossref_funder_id_node, RDF.type, PXC.FundRefDoi))
            records_bf.add((funder_node, BF.identifiedBy, crossref_funder_id_node))
            # add the crossref funder id as a literal to the identifier node:
            records_bf.add(
                (crossref_funder_id_node, RDF.value, Literal(crossref_funder_id))
            )

        # then check the rest for a grant number:

        try:
            # if "|n " in grantfield:
            grants = grantfield.split("|n ")[1].split(" |")[0]
            grant_counter = 0
        except:
            grants = None
        else:
            grants = extract_grant_numbers(grants)
            # add the grant number to the funding contribution node:
            for grant_id in grants:
                grant_counter += 1
                # add a blank node for the grant (class pxc:Grant via pxp:grant)
                grant_node = URIRef(
                    str(funding_contribution_node) + "_grant" + str(grant_counter)
                )
                records_bf.add((grant_node, RDF.type, PXC.Grant))
                # add the grant node to the funding contribution node:
                records_bf.add((funding_contribution_node, PXP.grant, grant_node))

                # add a blank node for the identifier:
                grant_identifier_node = URIRef(str(grant_node) + "_awardnumber")
                # records_bf.add((grant_identifier_node, RDF.type, BF.Identifier))
                records_bf.add((grant_identifier_node, RDF.type, PXC.GrantId))
                records_bf.add(
                    (grant_identifier_node, RDF.value, Literal(grant_id.strip()))
                )
                # add the identifier node to the grant node:
                records_bf.add((grant_node, BF.identifiedBy, grant_identifier_node))
        # then check the rest for a grant name or other info/note:
        try:
            # if "|i " in grantfield:
            funding_info = grantfield.split("|i ")[1].split(" |")[0]
        except:
            funding_info = None

        try:
            # if "|e " in grantfield:
            funding_recipient = grantfield.split("|e ")[1].split(" |")[0]
        except:
            funding_recipient = None
        else:
            # add an explanatory prefix text:
            funding_recipient = "Recipient(s): " + funding_recipient
            # add the funding_recipient to the funding_info (with a ". " separator), if that already contains some text, otherwise just use the funding_recipient as the funding_info:
            if funding_info is not None:
                funding_info = funding_info + ". " + funding_recipient
            else:
                funding_info = funding_recipient
        if funding_info is not None:
            # add the funding_info (with data from |i and |e to the funding contribution node as a bf:note:
            funding_info_node = URIRef(str(funding_contribution_node) + "_note")
            records_bf.add((funding_info_node, RDF.type, BF.Note))
            records_bf.set((funding_info_node, RDFS.label, Literal(funding_info)))
            records_bf.add((funding_contribution_node, BF.note, funding_info_node))
        # add the funding contribution node to the work node:
        records_bf.add((work_uri, BF.contribution, funding_contribution_node))
        # return funding_contribution_node


# %% [markdown]
# # Function: Add Conference info from field CF
#
#


# %%
def get_bf_conferences(work_uri, record):
    # only use conferences from actual books (BE=SS or SM)
    # ignore those in other publication types like journal article
    if record.find("BE").text == "SS" or record.find("BE").text == "SM":
        for conference in record.findall("CF"):
            # get the text content of the CF field,
            # sanitize it by unescaping html entities and
            # replacing STAR's ^DD encodings:
            conference_field = html.unescape(
                mappings.replace_encodings(conference.text.strip())
            )
            # try to get the conference name from the CF field:
            try:
                # get conference_name from main CF field, using the first part before any |:
                conference_name = conference_field.split("|")[0].strip()
            except:
                conference_name = "MISSING CONFERENCE NAME"
            # then check the field for a date in apotential subfield |d:
            try:
                conference_date = conference_field.split("|d ")[1].split(" |")[0]
            except:
                conference_date = None
            else:
                # if there is a |d, add the full date to conference_note:
                conference_note = "Date(s): " + conference_date
                # extract the year from the date to use it as conference_year:
                # Anything with 4 consecutive digits anywhere in the date string is a year.
                # here is a regex for finding YYYY pattern in any string:
                year_pattern = re.compile(r"\d{4}")
                # if there is a year in the date string, use that as the date:
                if year_pattern.search(conference_date):
                    conference_year = year_pattern.search(conference_date).group()
                else:
                    conference_year = None
            # then check the field for a place in a potential subfield |o:
            try:
                conference_place = conference_field.split("|o ")[1].split(" |")[0]
            except:
                conference_place = None
            # then check for a note in a potential subfield |b, but
            # remebering to keep what is already in conference_note:
            try:
                conference_note = (
                    conference_note
                    + ". "
                    + conference_field.split("|b ")[1].split(" |")[0]
                )
            except:
                conference_note = conference_note

            # construct the node for the conference:
            # count up the global conference counter for this record:
            global conferencereference_counter
            conferencereference_counter += 1
            # a bnode for the contribution/conferencereference:
            conference_reference_node = URIRef(
                str(work_uri)
                + "#conferencereference"
                + str(conferencereference_counter)
            )
            records_bf.add(
                (conference_reference_node, RDF.type, PXC.ConferenceReference)
            )
            # a blank node for the conference/meeting/agent:
            conference_node = URIRef(str(conference_reference_node) + "_meeting")
            records_bf.add((conference_node, RDF.type, BF.Meeting))
            records_bf.add((conference_node, RDF.type, PXC.Conference))
            # attach the agent to the contribution/conferencereference:
            records_bf.add((conference_reference_node, BF.agent, conference_node))
            # add the conference name as a label to the agent/meeting node:
            records_bf.add((conference_node, RDFS.label, Literal(conference_name)))
            # add the year as a bflc:simpleDate to the agent/meeting node:
            records_bf.add((conference_node, BFLC.simpleDate, Literal(conference_year)))
            # add the place as a bflc:simplePlace to the agent/meeting node:
            records_bf.add(
                (conference_node, BFLC.simplePlace, Literal(conference_place))
            )
            # add the note as a bf:note to the agent/meeting node, first adding a bnode for the bf:Note:
            conference_note_node = URIRef(str(conference_reference_node) + "_note")
            # make it a bf:Note:
            records_bf.add((conference_note_node, RDF.type, BF.Note))
            # add the note to the note node as a literal via rdfs:label:
            records_bf.add((conference_note_node, RDFS.label, Literal(conference_note)))
            # add a bf:role <http://id.loc.gov/vocabulary/relators/ctb> to the ConferenceReference ("contributor" - which is the default for conferences in DNB and LoC):
            records_bf.add(
                (
                    conference_reference_node,
                    BF.role,
                    URIRef("http://id.loc.gov/vocabulary/relators/ctb"),
                )
            )
            # add the note node to the agent/meeting node via bf:note:
            records_bf.add((conference_reference_node, BF.note, conference_note_node))
            # add the conference node to the work node:
            records_bf.add((work_uri, BF.contribution, conference_reference_node))


# %% [markdown]
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
# <Instance> bf:usageAndAccessPolicy [
#     a bf:AccessPolicy;
#     rdfs:label "open access"@en, "offener Zugang"@de;
#     # or:
#     # rdfs:label "restricted access"@en, "eingeschränkter Zugang"@de;
#     rdf:value "http://purl.org/coar/access_right/c_abf2"^^xsd:anyURI; # a link to the license or uri of the skos term: here: open access
#     # or:
#     # rdf:value "http://purl.org/coar/access_right/c_16ec"^^xsd:anyURI; # restricted
# ].
# ```
#
# To be able to use a controlled vocabulary for this, we will make use of the COAR "access rights" skos vocabulary!
# https://vocabularies.coar-repositories.org/access_rights/ - its four concepts: open access, restriced access, embargoed access, metadata only access.


# %%
def get_urlai(work_uri, record):
    """Gets research data from field URLAI. This is always in PsychData, so it will be restricted access by default.
    We will also assume it to always be just research data, not code.
    """
    for data in record.findall("URLAI"):
        urlai_field = mappings.replace_encodings(data.text.strip())
        unknown_field_content = None
        # build the relationship node:
        relationship_node, instance = build_work_relationship_node(
            work_uri, relation_type="rd_restricted_access"
        )
        # there are no subfields in urlai, so let's just grab the whole thing and pass it on to the url or doi checker:
        # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
        # as a doi or url:
        url_set = set()
        doi_set = set()
        # if it is a doi, run a function to generate a doi identifier node
        if check_for_url_or_doi(urlai_field)[1] == "doi":
            # build_doi_identifier_node(instance,check_for_url_or_doi(urlai_field)[0])
            doi_set.add(check_for_url_or_doi(urlai_field)[0])
        elif check_for_url_or_doi(urlai_field)[1] == "url":
            # build_electronic_locator_node(instance, check_for_url_or_doi(urlai_field)[0])
            url_set.add(check_for_url_or_doi(urlai_field)[0])
        # if the returned typ is something else "unknown", do nothing with it:
        else:
            # print("bf:note > bf:Note > rdfs:label: " + urlai_field)
            if (
                urlai_field is not None
                and check_for_url_or_doi(urlai_field)[0] is not None
                and check_for_url_or_doi(urlai_field)[0] != ""
            ):
                # add a variable
                unknown_field_content = check_for_url_or_doi(urlai_field)[0].strip()
                print(f"unknown type: {unknown_field_content}. Adding as a note.")
                build_note_node(instance, check_for_url_or_doi(urlai_field)[0])

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
                    print(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)

        # loop through the set to build doi nodes, so we won't have duplicates:
        for doi in doi_set:
            build_doi_identifier_node(instance, doi)
        for url in url_set:
            build_electronic_locator_node(instance, url)

        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


# %%
def get_datac(work_uri, record):
    """Gets research data from field DATAC, adds a Relationship node to the work.
    Note: We define all data from this field as type "research data only, no code", and "open/unrestricted access"
    Newer data from PSYNDEXER may be something else, but for first migration, we assume all data is research data only.
    """
    # go through the list of datac fields and get the doi, if there is one:
    for data in record.findall("DATAC"):
        datac_field = mappings.replace_encodings(data.text.strip())
        # print(datac_field)
        # add an item "hello" to the set:
        # build the relationship node:
        relationship_node, instance = build_work_relationship_node(
            work_uri, relation_type="rd_open_access"
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
                subfield = get_subfield(datac_field, subfield_name)
            except:
                subfield = None
            else:
                # print(subfield)
                # if the string_type returned [1] is doi or url, treat them accordingly, using the returned string [0]
                # as a doi or url:
                # if it is a doi, run a function to generate a doi identifier node
                if subfield is not None and check_for_url_or_doi(subfield)[1] == "doi":
                    # add the doi to a list:
                    doi_set.add(check_for_url_or_doi(subfield)[0])
                    # build_doi_identifier_node(instance, check_for_url_or_doi(subfield)[0])
                elif (
                    subfield is not None and check_for_url_or_doi(subfield)[1] == "url"
                ):
                    # add the url to a list:
                    url_set.add(check_for_url_or_doi(subfield)[0])
                    # build_electronic_locator_node(instance, check_for_url_or_doi(subfield)[0])
                    # if the returned typ is something else "unknown", do nothing with it:
                else:
                    # print("bf:note > bf:Note > rdfs:label: " + subfield)
                    if (
                        subfield is not None
                        and check_for_url_or_doi(subfield)[0] is not None
                        and check_for_url_or_doi(subfield)[0] != ""
                    ):
                        # add a variable
                        unknown_field_content = check_for_url_or_doi(subfield)[
                            0
                        ].strip()
                        print(
                            f"unknown type: {unknown_field_content}. Adding as a note."
                        )
                        build_note_node(instance, check_for_url_or_doi(subfield)[0])
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
                    print(
                        f"duplicate doi in url {url}: {doi.split('/')[2]} from {doi}. Removing url in favor of doi."
                    )
                    url_set.remove(url)
        for doi in doi_set:
            build_doi_identifier_node(instance, doi)
        for url in url_set:
            build_electronic_locator_node(instance, url)
        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


# %% [markdown]
# ## Function: Get Series info for Books (field SE)
#
# Books (their Instances) can pe part of a monographic series - or even part of more than one series (usually that is a subseries of a bigger series). We currently store the title of that series, along with the volume number of the current book within that series, in field SE. Numbering is usually separated with a comma (but not always, sigh.)
# Also, there are cases where there is no numbering at all, or a strange one that is actually the issue and volume like from a journal?
#
# What we want is something like this - a regular case where there is a series title and a volume number that follows the title after a comma:
#
# ```r
# Works:0396715_work a bf:Work;
#     # omitted: info about the work of the book itself (title, abstract, topics etc.)
# bf:hasInstance
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

# %% [markdown]
# # The Loop!
# ## Creating the Work and Instance uris and adding other triples via functions

# %% [markdown]
# ### Uris and types for Bibframe profile
#
# We want two URIs, since we split the Records into (at first) one work and one instance, which will be linked together.
# We also say one will be a (rdf:type) bf:Work and the other bf:Instance.
# Then we print all these triples into a file for the bibframe profile.

# %%
# print(len(root.findall("Record")))

record_count = 0
for record in root.findall("Record"):
    # for record in root.findall("Record")[0:200]:
    # get the count of this record:
    record_count += 1

    # create a named graph dataset for each "record":
    # Create an empty Dataset
    # d = Dataset()
    # Add a namespace prefix to it, just like for Graph
    # d.bind("ex", Namespace("http://example.com/"))
    # Declare a Graph URI to be used to identify a Graph
    # graph_1 = URIRef("http://example.com/graph/" + dfk + "/")
    # Add an empty Graph, identified by graph_1, to the Dataset
    # d.graph(identifier=graph_1)

    # get the DFK identifier from the record:
    dfk = record.find("DFK").text

    # create a URI for the work and the instance and give them their correct bf classes:
    # make sure a work_uri will look like this: works:dfk_work, eg works:123456_work
    work_uri = URIRef(WORKS + dfk + "_work")
    records_bf.add((work_uri, RDF.type, BF.Work))
    # d.add((work_uri, RDF.type, BF.Work, graph_1))

    # for each work, create one pxc:InstanceBundle with an uri like this: instancebundles:0123456 (where 0123456 is the dfk of the record):
    instance_bundle_uri = URIRef(INSTANCEBUNDLES + dfk)
    records_bf.add((instance_bundle_uri, RDF.type, PXC.InstanceBundle))
    # create one instance:
    instance_uri = URIRef(INSTANCES + dfk + "#1")
    records_bf.add((instance_uri, RDF.type, BF.Instance))

    # connect the instancebundle to the work:
    records_bf.add((work_uri, PXP.hasInstanceBundle, instance_bundle_uri))
    # connect the instance_bundle to the instance:
    records_bf.add((instance_bundle_uri, BF.hasPart, instance_uri))
    # connect work and instance via bf:instanceOf and bf:hasInstance:
    records_bf.add((instance_uri, BF.instanceOf, work_uri))
    records_bf.add((work_uri, BF.hasInstance, instance_uri))
    # add mediacarrier from MT to the instance:
    if record.find("MT") is not None:
        records_bf.add(
            (
                instance_uri,
                PXP.mediaCarrier,
                get_mediacarrier(record.find("MT").text)[1],
            )
        )
        # also add a second class to instance - Eletronic or Print, based on the mediacarrier:
        # records_bf.add(
        #     (
        #         instance_uri,
        #         RDF.type,
        #         get_mediacarrier(record.find("MT").text)[0],
        #     )
        # )

    ## add the publication info (date, publisher, place) to the instancebundle:
    add_publication_info(instance_bundle_uri, record)
    # TODO: add any additional instance in the record as well - identifiable from the existence of an MT2 field.
    if record.find("MT2") is not None:
        instance_uri_2 = URIRef(
            INSTANCES + dfk + "#2"
        )  # create a second instance node:
        records_bf.add(
            (instance_uri_2, RDF.type, BF.Instance)
        )  # give it the type bf:Instance
        records_bf.add(
            (instance_bundle_uri, BF.hasPart, instance_uri_2)
        )  # connect the instancebundle to the instance
        records_bf.add(
            (instance_uri_2, BF.instanceOf, work_uri)
        )  # connect instance back to work
        records_bf.add(
            (work_uri, BF.hasInstance, instance_uri_2)
        )  # connect work to this instance
        # add publication date, publisher, place:
        # add_publication_info(instance_uri_2, record, record.find("MT2").text)
        # add the mediacarrier node to the instance:
        records_bf.add(
            (
                instance_uri_2,
                PXP.mediaCarrier,
                get_mediacarrier(record.find("MT2").text)[1],
            )
        )

    # for the DFK, add an identifier node to the instancebundle using a function:
    records_bf.add(
        (
            instance_bundle_uri,
            BF.identifiedBy,
            get_bf_identifier_dfk(instance_bundle_uri, dfk),
        )
    )

    # add the issuance type (from BE) to the bundle:
    get_issuance_type(instance_bundle_uri, record)

    # get field TI and add as title node to the instance bundle:
    title = get_bf_title(instance_bundle_uri, record)
    records_bf.set((instance_bundle_uri, BF.title, title))
    # also link the title to the instance:
    # records_bf.set((instance_uri, BF.title, title))

    # get TIUE field and add as translated title node:
    # but only if the field exists!
    if record.find("TIUE") is not None and record.find("TIUE").text != "":
        records_bf.add(
            (
                instance_bundle_uri,
                BF.title,
                get_bf_translated_title(instance_bundle_uri, record),
            )
        )

    # get work language from LA
    records_bf.add((work_uri, BF.language, get_work_language(record)))

    # get and add contributors:
    # set up/reset a global counter for contributions to a work (it will count up in the functions that add Person contributions from AUP fields and Org contributions from AUK fields) - we need it to add the contribution position
    contribution_counter = 0
    fundingreference_counter = 0
    conferencereference_counter = 0
    add_bf_contributor_person(work_uri, record)
    # are there any PAUPs left that haven't been successfull matched and added to contributors?
    match_paups_to_contribution_nodes(work_uri, record)
    match_orcids_to_contribution_nodes(work_uri, record)
    add_bf_contributor_corporate_body(work_uri, record)
    match_email_to_contribution_nodes(work_uri, record)
    # get toc, if it exists:
    get_bf_toc(work_uri, record)

    # get and add main/original abstract:
    # note: somehow not all records have one!
    if record.find("ABH") is not None:
        get_bf_abstract(work_uri, record)
        # records_bf.add((work_uri, BF.summary, get_bf_abstract(work_uri, record)))
    # d.add((work_uri, BF.summary, get_bf_abstract(work_uri, record), graph_1))

    # get and add main/original abstract:
    # note: somehow not all records have one!
    if record.find("ABN") is not None:
        records_bf.add(
            (work_uri, BF.summary, get_bf_secondary_abstract(work_uri, record))
        )

    # get and add any CTs:
    add_controlled_terms(work_uri, record)

    # get and add preregistration links:
    # get_bf_preregistrations(work_uri, record)
    # switched off for performance reasons

    # get and add grants by using the returned set of nodes and adding it to the work:
    get_bf_grants(work_uri, record)

    # get and add conferences:
    get_bf_conferences(
        work_uri, record
    )  # adds the generated bflc:Relationship node to the work

    # get_datac(work_uri, record) # adds the generated bfls:Relationship node to the work
    # switched off for performance reasons

    # after we've added everything, we can go through the isbns and other stuff and put them into the instances where they belong:
    # get the isbns and add them to the instance bundle first:
    # return two nodes, one for the print isbn, another for the ebook_isbn.
    # well add them to the appropriate instance.
    add_isbns(record, instance_bundle_uri)

    # Serialize the Dataset to a file.
    # d.serialize(destination="ttl-data/" + dfk + ".jsonld", format="json-ld", auto_compact=True)


# add a Literal for the count of records:
# records_bf.add((URIRef("https://w3id.org/zpid/bibframe/records/"), BF.count, Literal(record_count)))
# and add it to the graph:
# first, add a bnode of class bf:AdminMetadata to the graph:
records_bf_admin_metadata_root = BNode()
records_bf.add((records_bf_admin_metadata_root, RDF.type, BF.AdminMetadata))
# add this bnode to the graph:
records_bf.add(
    (
        URIRef("https://w3id.org/zpid/bibframe/records/"),
        BF.adminMetadata,
        records_bf_admin_metadata_root,
    )
)
# # add a bf:generationProcess to the admin metadata node:
# records_bf.add((records_bf_admin_metadata_root, BF.generationProcess, Literal("Converted from PsychAuthors XML to BIBFRAME 2.2 using Python scripts")))
# # add a bf:generationDate to the admin metadata node:
# #records_bf.add((records_bf_admin_metadata_root, BF.generationDate, Literal(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
# # add the count as BF.count:
# records_bf.add((records_bf_admin_metadata_root, PXP.recordCount, Literal(record_count)))


print(record_count, "records")

# print all the resulting triples:
records_bf.serialize("ttl-data/bibframe_records.ttl", format="turtle")
records_bf.serialize(
    "ttl-data/bibframe_records.jsonld",
    format="json-ld",
    auto_compact=False,
    sort_keys=True,
    index=True,
)
# serialize as xml
records_bf.serialize("ttl-data/bibframe_records.xml", format="pretty-xml")


# # import a context file as a dict:
# with open("bibframe-context.json", "r") as context_file:
#     context = json.load(context_file)
# # add the context to the graph:
# context_dict = context
# # serialize as json-ld and pass the context dict:
# records_bf.serialize("ttl-data/bibframe_records.jsonld", format="json-ld", auto_compact=True, sort_keys=True, index=True, context=context_dict)

# testwork = "https://w3id.org/resources/works/0401567"
# records_bf[testwork].serialize("ttl-data/bibframe_sample.jsonld", format="json-ld")

print(len(records_bf), "triples")


# %% [markdown]
# ### Uris and types for simplified profile (schema-org)
#
# For the simplified profile, we only need one entity per record (for now) and we give it the class schema:CreativeWork.
# Then we print the resulting triples into a separate file for the simplified profile that mostly uses schema.org properties and classes.

# %%


# print(len(root.findall("Record")))

# for record in root.findall("Record"):
#     # get the DFK identifier from the record:
#     dfk = record.find("DFK").text

#     # create a URI for the work by attaching the dfk to the works namespace and
#     # then give it the correct schema.org class:
#     work_uri = WORKS[dfk]
#     records_schema.add((work_uri, RDF.type, SCHEMA.CreativeWork))

#     # get work language from LA
#     records_schema.add((work_uri, SCHEMA.inLanguage, get_work_language(record)))


# records_schema.serialize("ttl-data/schema_records.jsonld", format="json-ld")
# # records_schema.serialize("ttl-data/schema_records.ttl", format="turtle")
# print(len(records_schema), "triples")
