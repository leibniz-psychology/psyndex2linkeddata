# Purpose: Convert STAR XML to Bibframe RDF
# Import libraries:


import datetime
import dateparser
from numpy import rec
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, OWL, Namespace
from rdflib import BNode
from rdflib import URIRef
import xml.etree.ElementTree as ET
import re
import html
from tqdm.auto import tqdm


import modules.mappings as mappings
import modules.publication_types as publication_types
import modules.helpers as helpers
import modules.local_api_lookups as localapi
import modules.terms as terms
import modules.identifiers as identifiers
import modules.instance_source_ids as instance_source_ids

# import modules.contributions as contributions
# import modules.open_science as open_science

import requests
import requests_cache
from datetime import timedelta

# old fuzzy compare for reconciliations: using fuzzywuzzy
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# TODO: new fuzzy compare: using the faster rapidfuzz as a drop-in replacement for fuzzywuzzy:
# from rapidfuzz import fuzz
# from rapidfuzz import process

import csv  # for looking up institutes from our csv of luxembourg authority institutes

from modules.mappings import funder_names_replacelist

# ror lookup api url for looking up organization contributors and the affiliations of persons:
ROR_API_URL = "https://api.ror.org/organizations?affiliation="


## crossref api stuff for looking up funders:
# set up friendly session by adding mail in request:
CROSSREF_FRIENDLY_MAIL = "&mailto=ttr@leibniz-psychology.org"
# for getting a list of funders from api ():
CROSSREF_API_URL = "https://api.crossref.org/funders?query="

## Caching requests:
urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}

# a cache for ror requests
session_ror = requests_cache.CachedSession(
    ".cache/requests_ror",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)
# and a cache for the crossref api:
session_fundref = requests_cache.CachedSession(
    ".cache/requests_fundref",
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


# Create an "element tree" from the records in my selected xml file so we can loop through them and do things with them:
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


# We first set a few namespace objects for bibframe, schema.org and for our resources (the works and instances) themselves.
#
# Then, we create two graphs from the xml source file, one to generate triples for our bibframe profile output, and the other for the simplified schema.org profile.
#
# Finally, we bind the prefixes with their appropriate namespaces to the graphs.

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
LICENSES = Namespace("https://w3id.org/zpid/vocabs/licenses/")


# graph for bibframe profile:
records_bf = Graph()
# make the graph named for the records: just for clarity in the output:
records_bf = Graph(identifier=URIRef("https://w3id.org/zpid/bibframe/records/"))

# import the graph for kerndaten.ttl from PsychAuthors - we'll need it for
# matching person names to ids when the names in the records are unmatchable
# - we'll try to match alternate names from kerndaten:
kerndaten = Graph()
kerndaten.parse("ttl-data/kerndaten.ttl", format="turtle")

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
records_bf.bind("issuances", ISSUANCES)  # issuance types
records_bf.bind("pmt", PMT)  # mediacarriers
records_bf.bind("licenses", LICENSES)  # licenses


# # Functions to do all the things
#
# We need functions for the different things we will do - to avoid one long monolith of a loop.
#
# This is where they will go. Examples: Create nodes for Idebtifiers, create nested contribution objects from disparate person entries in AUP, AUK, CS and COU fields, merge PAUP (psychauthor person names and ids) with the person's name in AUP...
#
# These functions will later be called at the bottom of the program, in a loop over all the xml records.


# Define a function to convert a string to camel case
def camel_case(s):
    # Use regular expression substitution to replace underscores and hyphens with spaces,
    # then title case the string (capitalize the first letter of each word), and remove spaces
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")

    # Join the string, ensuring the first letter is lowercase
    return "".join([s[0].lower(), s[1:]])


def get_abstract_release(record):
    """ "Checks if the record's abstract can be exported or must be suppressed for copyright reasons. Based on Publisher as determined from DOI stem 10.1016 && COPR = PUBL"""
    if record.find("DOI") is not None and record.find("COPR") is not None:
        record_doi = record.find("DOI").text
        record_copyright = record.find("COPR").text
        if "10.1016" in record_doi and "PUBL" in record_copyright:
            return False
        else:
            return True
    else:
        return True


def get_ror_org_country(affiliation_ror_id):
    # given a ror id, get the country of the organization from the ror api:
    # first, use only the last part of the ror id, which is the id itself:
    affiliation_ror_id = affiliation_ror_id.split("/")[-1]
    # the country name is in country.name in the json response
    ror_request = session_ror.get(
        "https://api.ror.org/organizations/" + affiliation_ror_id, timeout=20
    )
    if ror_request.status_code == 200:
        ror_response = ror_request.json()
        if "country" in ror_response:
            return ror_response["country"]["name"]
        else:
            print("no country found for " + affiliation_ror_id)
            return None


def add_instance_license(resource_uri, record):
    """Reads field COPR and generates a bf:usageAndAccessPolicy node for the resource_uri based on it. Includes a link to the vocabs/licenses/ vocabulary in our Skosmos. We'll probably only use the last subfield (|c PUBL) and directly build a skosmos-uri from it (and pull the label from there?). There are more specific notes in the migration aection of each license concept in Skosmos. Note: the license always applies to an instance (or an instancebundle), not to a work, since the license is about the publication, not the content of the publication - the work content might be published elsewhere with a different license. Manuel mentioned something like that already about being confused about different licenses for different versions at Crossref.

    Args:
        resource_uri (_type_): The node to which the usageAndAccessPolicy node will be added.
        record (_type_): The PSYNDEX record from which the COPR field will be read.
    """
    if record.find("COPR") is not None:
        # get the last subfield of COPR:
        license_code = helpers.get_subfield(record.find("COPR").text, "c")
        # get the german_label from |d:
        license_german_label = helpers.get_subfield(record.find("COPR").text, "d")
        # create a skosmos uri for the license:
        SKOSMOS_LICENSES_PREFIX = "https://w3id.org/zpid/vocabs/licenses/"
        # license_uri = URIRef(LICENSES + license_code)
        # several cases and the different uris for the licenses:
        if license_code == "CC":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "C00_1.0")
        elif license_code == "PDM":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "PDM_1.0")
        # CC BY 4.0
        elif license_code == "CC BY 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY_4.0")
        # CC BY-SA 4.0
        elif license_code == "CC BY-SA 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-SA_4.0")
        # CC BY-NC-ND 3.0
        elif license_code == "CC BY-NC-ND 3.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-ND_3.0")
        # CC BY-NC-ND 4.0
        elif license_code == "CC BY-NC-ND 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-ND_4.0")
        elif license_code == "CC BY-NC 1.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC_1.0")
        elif license_code == "CC BY-NC 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC_4.0")
            # CC BY-NC-ND 2.5
        elif license_code == "CC BY-NC-ND 2.5":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-ND_2.5")
            # CC BY-NC-SA 4.0
        elif license_code == "CC BY-NC-SA 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-SA_4.0")
            # CC BY-ND 4.0
        elif license_code == "CC BY-ND 4.0":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-ND_4.0")
            # CC BY-ND 2.5
        elif license_code == "CC BY-ND 2.5":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-ND_2.5")
            # CC BY (unknown version)
        elif license_code == "CC BY":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY")
            # CC BY-NC (unknown version)
        elif license_code == "CC BY-NC":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC")
            # CC BY-NC-SA (unknown version)
        elif license_code == "CC BY-NC-SA":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-SA")
            # CC BY-SA (unknown version)
        elif license_code == "CC BY-SA":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-SA")
            # CC BY-NC-ND (unknown version)
        elif license_code == "CC BY-NC-ND":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-NC-ND")
            # CC BY-ND (unknown version)
        elif license_code == "CC BY-ND":
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "CC_BY-ND")
            # starts with "AUTH":
        elif license_code.startswith("AUTH"):
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "AUTH")
            # starts with "PUBL" or license_german_label starts with "Volles Urheberrecht des Verlags" > PUBL:
        elif license_code.startswith("PUBL") or license_german_label.startswith(
            "Volles Urheberrecht des Verlags"
        ):
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "PUBL")
            # starts with starts with "Hogrefe OpenMind" -> HogrefeOpenMind
        elif license_code.startswith("Hogrefe OpenMind"):
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "HogrefeOpenMind")
            # contains contains "Springer"-> ExclusiveSpringer:
        elif "Springer" in license_code:
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "ExclusiveSpringer")
        # starts with "OTHER" -> UnspecifiedOpenLicense
        elif license_code.startswith("OTHER"):
            license_uri = URIRef(SKOSMOS_LICENSES_PREFIX + "UnspecifiedOpenLicense")
        else:
            print(
                f"no license uri found for {license_code} in record {record.find('DFK').text}"
            )
            license_uri = None
        if license_uri is not None:
            # add the license uri from skosmos directly:
            license_node = license_uri
            records_bf.set((license_node, RDF.type, BF.UsePolicy))
            records_bf.add((resource_uri, BF.usageAndAccessPolicy, license_node))

            # Get the label from skosmos:
            try:
                german_preflabel = localapi.get_preflabel_from_skosmos(
                    license_uri, "licenses", "de"
                )
            except:
                print(f"failed getting prefLabels for license {license_uri}")
                german_preflabel = None
            try:
                english_preflabel = localapi.get_preflabel_from_skosmos(
                    license_uri, "licenses", "en"
                )
            except:
                print(f"failed getting prefLabels for license {license_uri}")
                english_preflabel = None
            # add the prefLabels to the license node:
            if german_preflabel is not None:
                records_bf.add(
                    (license_node, SKOS.prefLabel, Literal(german_preflabel, lang="de"))
                )
            else:
                print(f"no german prefLabel found for {license_uri}")
            if english_preflabel is not None:
                records_bf.add(
                    (
                        license_node,
                        SKOS.prefLabel,
                        Literal(english_preflabel, lang="en"),
                    )
                )
                records_bf.set((license_node, RDFS.label, Literal(english_preflabel)))
            else:
                print(f"no english prefLabel found for {license_uri}")

            # english_preflabel = localapi.get_preflabel_from_skosmos(license_uri, "licenses", "en")
            # TODO: get url for license itself from skosmos (e.g. creative commons deed url)
    else:
        print(f"warning: record {record.find('DFK').text} has no valid license!")


def add_work_classification(work_uri, record):
    pass


def add_additional_descriptor(work_uri, record):
    """Reads any fields `IT` and adds the descriptor as a bf_subject > bf:Topic. Looks up the URI of that concept using the Skomos API. Note that the IT will be added like any other PSYNDEX (APA) Term. We may add the IT vocab as a different "source" to tell them apart. In the furture, these two vocabs will be integrated, and there is already only one input field in PSYNDEXER for it.
    TODO: May merge this functionality into the subject function, so that it can be used for both IT and CT fields.

    Args:
        work_uri (_type_): The work to which the subject/topics will be added.
        record (_type_): The record from which the IT fields will be read.
    """


def get_publication_date(record):
    """Get the publication date from the record's PHIST or PY field and return it as a Literal.

    Args:
        record (_type_): The record from which the publication date will be read.

    Returns:
        _type_: The publication date as a Literal, either YYYY or, if from PHIST, YYYY-MM-DD.
    """
    # from field PHIST or PY, get pub date and return this as a Literal
    # get date from PHIST field, it exists, otherwise from P> field:
    if record.find("PHIST") is not None and record.find("PHIST").text != "":
        date = helpers.get_subfield(record.find("PHIST").text, "o")
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
        # print("no date found in PHIST, using PY")
        try:
            date = record.find("PY").text
        except:
            print("record has no valid publication date!")
            date = None
    return date


def add_isbns(record, instancebundle_uri):
    """Reads the record's PU field and adds any ISBNs found in it as bf:identifiedBy nodes to the instancebundle_uri.

    Args:
        record (_type_): _description_
        instancebundle_uri (_type_): _description_
    """
    # if there is a PU, find subfield |i and e
    try:
        pu = record.find("PU")
    except:
        pu = None
    if pu is not None and pu.text != "":
        try:
            isbn_print = helpers.get_subfield(pu.text, "i")
        except:
            isbn_print = None
        try:
            isbn_ebook = helpers.get_subfield(pu.text, "e")
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

        # Adding isbns by type to their repsective instance - by mediaCarrier. TODO: Make this actually work!
        # Check all the instances of this work whether they are print or online mediacarrier. If so, add appropriate isbn to them:
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


def match_paups_to_contribution_nodes(work_uri, record):
    # go through all PAUP fields and get the id:
    for paup in record.findall("PAUP"):
        paup_id = helpers.get_subfield(paup.text, "n")
        paup_name = helpers.get_mainfield(paup.text)
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
                # use partial_ratio for a more lenient comparison - so we can check if one of the them is a substring of the other - for double names, etc.:
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
            # loop through the contribtors again, and check if any of the alternate names from psychauthors kerndaten match a person's name from AUP:
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # get the agent of the contribution:
                agent = records_bf.value(contribution, BF.agent)
                # if the agent is a person, get the given and family names:
                if records_bf.value(agent, RDF.type) == BF.Person:
                    # get the given and family names of the agent:
                    givenname = records_bf.value(agent, SCHEMA.givenName)
                    familyname = records_bf.value(agent, SCHEMA.familyName)
                    aupname_normalized = normalize_names(familyname, givenname)
                    # try to match the paup_id to a uri in kerndaten.ttl and check if any of the alternate names match the agent's name:
                    person_uri = URIRef("https://w3id.org/zpid/person/" + paup_id)
                    for alternatename in kerndaten.objects(
                        person_uri, SCHEMA.alternateName
                    ):
                        # split the alternatename into family and given name:
                        alternatename_split = alternatename.split(",")
                        alternatename_familyname = alternatename_split[0].strip()
                        alternatename_givenname = alternatename_split[1].strip()
                        # normalize the name:
                        alternatename_normalized = normalize_names(
                            alternatename_familyname, alternatename_givenname
                        )
                        # if the alternatename matches the agent's name, add the paup_id as an identifier to the agent: again using fuzzywuzzy'S partial ratio to also match substrings of the name inside each other:
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
        orcid_id = helpers.get_subfield(orcid.text, "u")
        orcid_name = helpers.get_mainfield(orcid.text)
        # is the orcid well formed?
        # clean up the orcid_id by removing spaces that sometimes sneak in when entering them in the database:
        if orcid_id is not None and " " in orcid_id:
            print("warning: orcid_id contains spaces, cleaning it up: " + orcid_id)
        orcid_id = orcid_id.replace(" ", "")
        # by the way, here is a regex pattern for valid orcids:
        orcid_pattern = re.compile(
            r"^(https?:\/\/(orcid\.)?org\/)?(orcid\.org\/)?(\/)?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])$"
        )
        if orcid_pattern.match(orcid_id):
            # remove the prefixes and slashes from the orcid id:
            orcid_id = orcid_pattern.match(orcid_id).group(5)
        else:
            # warn if it doesn't match the pattern for well-formed orcids:
            print(f"warning: invalid orcid: {orcid_id}")
        # get the given and family part of the orcid name:
        # make sure we give an error message when we can't split:
        try:
            orcid_split = orcid_name.split(",")
            orcid_familyname = orcid_split[0].strip()
            orcid_givenname = orcid_split[1].strip()
            orcidname_normalized = normalize_names(orcid_familyname, orcid_givenname)
        except:
            print(
                "couldn't split orcid name into given and family name: "
                + orcid_name
                + " in record "
                + record.find("DFK").text
                + ". Using the full name as a fallback."
            )
            orcidname_normalized = (
                orcid_name  # if we can't split, just try the full name
            )
        # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person - and match names to those in the orcid field:
        for contribution in records_bf.objects(work_uri, BF.contribution):
            # get the agent of the contribution:
            agent = records_bf.value(contribution, BF.agent)
            # if the agent is a person, get the given and family names:
            if records_bf.value(agent, RDF.type) == BF.Person:
                # get the given and family names of the agent:
                givenname = records_bf.value(agent, SCHEMA.givenName)
                familyname = records_bf.value(agent, SCHEMA.familyName)
                aupname_normalized = normalize_names(familyname, givenname)

                # if the orcidname_normalized matches the agent's name, add the orcid_id as an identifier to the agent:

                # check using fuzzywuzzy - use partial_ratio to check if one of the them is a substring of the other:
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


def match_CS_COU_affiliations_to_first_contribution(work_uri, record):
    # get the content of CS:
    try:
        affiliation = record.find("CS").text
    except:
        affiliation = ""
    # get the country from COU:
    try:
        country = record.find("COU").text
    except:
        country = ""
    #
    # if there is a CS field, add the affiliation to the first contribution node:
    if affiliation is not None and country is not None:
        # get the first contribution node:
        for contribution in records_bf.objects(work_uri, BF.contribution):
            agent_node = records_bf.value(
                contribution, BF.agent
            )  # get the agent of the contribution
            # dont get the agent at all, but just the position of the contribution:
            position = records_bf.value(contribution, PXP.contributionPosition)
            if (
                int(position) == 1
                and records_bf.value(agent_node, RDF.type) == BF.Person
            ):
                # add the affiliation to the contribution node using the function we already have for it:
                records_bf.add(
                    (
                        contribution,
                        MADS.hasAffiliation,
                        build_affiliation_nodes(agent_node, affiliation, country),
                    )
                )
                break


def match_email_to_contribution_nodes(work_uri, record):
    # there is only ever one email field in a record, so we can just get it.
    # unless there is also a field emid, the email will be added to the first contribution node.
    # if there is an emid, the email will be added to the person with a name matching the name in emid.
    # fortunately, the name in EMID should always be exactly the same as the one in an AUP field
    # (unlike for PAUP and ORCID, :eyeroll:) so matching the names is pretty easy.
    # First get the email:
    if record.find("EMAIL") is not None:
        # cleaning up the horrible mess that star makes of any urls and email addresses (it replaces _ with space, but there is no way to differentiate between an underscore-based space and a real one...):
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
            # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # get the agent of the contribution:
                agent = records_bf.value(contribution, BF.agent)
                # if the agent is a person, get the given and family names:
                if records_bf.value(agent, RDF.type) == BF.Person:
                    # get the given and family names of the agent:
                    name = records_bf.value(agent, RDFS.label)
                    emid_name = mappings.replace_encodings(emid_name).strip()
                    # if the emid_name matches the agent's name, add the email as a mads:email to the agent:
                    if fuzz.partial_ratio(emid_name, name) > 80:
                        # add to contribution node:
                        records_bf.add((contribution, MADS.email, URIRef(email)))
                        # and break the loop, since we only need to add the email to one person:
                        break
        # if after all loops, no match was found for EMID in the AUP-based name,
        # add the email to the first contribution node:
        else:
            # finding the contribution node from those the work_uri has that has pxp:contributionPosition 1:
            for contribution in records_bf.objects(work_uri, BF.contribution):
                # dont get the agent at all, but just the position of the contribution:
                position = records_bf.value(contribution, PXP.contributionPosition)
                if int(position) == 1:
                    # add to contribution node:
                    records_bf.add((contribution, MADS.email, URIRef(email)))
                    # break after position 1 - since we only need the first contribution node:
                    break


def extract_contribution_role(contributiontext):
    role = helpers.get_subfield(contributiontext, "f")
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
    # if we are in the first loop, set contribution's bf:qualifier" to "first":
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
        org_name = mappings.replace_encodings(helpers.get_mainfield(org.text))
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
        # else:
        #     print("ror-api: no ror id found for " + org_name)

        # get any affiliation in |i and add it to the name:
        try:
            org_affiliation_name = helpers.get_subfield(org.text, "i")
            # print("org affiliation:" + org_affiliation_name)
        except:
            org_affiliation_name = None
            # print("AUK subfield i: no affiliation for org " + org_name)
        if org_affiliation_name is not None:
            org_name = org_name + "; " + org_affiliation_name
        # # get country name in |c, if it exists:
        try:
            org_country = helpers.get_subfield(org.text, "c")
            # print("AUK subfield c: org country:" + org_country)
        except:
            org_country = None
            # print("AUK subfield c: no country for org " + org_name)
        if org_country is not None:
            # generate a node for the country, clean up the label, look up the geonames id and then add both label and geonamesid node to the org node!
            affiliation_node = build_affiliation_nodes(org_node, "", org_country)
            # add the affiliation node to the contribution node:
            records_bf.add((contribution_node, MADS.hasAffiliation, affiliation_node))

        # TODO: we should probably check for affiliations and countries in fields CS and COU for records that have only AUKS or AUK as first contribution? we already did the same for persons.

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
    ror_api_request = session_ror.get(ror_api_url, timeout=20)
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
    #### unused: matching luxembourg Affiliation names to local authority table in our csv:
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
    if agent_affiliation_country is None or agent_affiliation_country == "":
        # try to check if we have a ror id for the affiliation and get the country from the ror api:
        try:
            agent_affiliation_country = get_ror_org_country(affiliation_ror_id)
        except:
            agent_affiliation_country = None

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
        personname = mappings.replace_encodings(
            helpers.get_mainfield(person.text)
        ).strip()

        records_bf.add((person_node, RDFS.label, Literal(personname)))

        # initialize variables for later use:
        personname_normalized = None
        orcidId = None

        # split personname into first and last name:
        personname_split = personname.split(",")
        try:
            familyname = personname_split[0].strip()
            givenname = personname_split[1].strip()
        except:
            familyname = personname
            givenname = ""
            print(
                "no comma in personname: "
                + personname
                + " in record "
                + record.find("DFK").text
                + " - name content added as familyname + empty string for givenname."
            )

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
        # if contribution_counter == 1:
        #     if record.find("CS") is not None:
        #         print("CS field found in record " + record.find("DFK").text)
        #         # get the content of the CS field:
        #         affiliation_string = html.unescape(
        #             mappings.replace_encodings(record.find("CS").text.strip())
        #         )

        #     if record.find("COU") is not None:
        #         # get the country from the COU field:
        #         affiliation_country = mappings.replace_encodings(
        #             sanitize_country_names(record.find("COU").text.strip())
        #         )

        ## Get affiliation from AUP |i, country from |c:
        # no looping necessary here, just check if a string |i exists in AUP and if so, add it to the person node as the affiliation string:
        affiliation_string = helpers.get_subfield(person.text, "i")

        affiliation_country = sanitize_country_names(
            helpers.get_subfield(person.text, "c")
        )

        # pass this to function build_affiliation_nodes to get a finished affiliation node:
        if affiliation_string != "" and affiliation_string is not None:
            affiliation_node = build_affiliation_nodes(
                person_node, affiliation_string, affiliation_country
            )
            # add the affiliation node to the contribution node:
            records_bf.add((contribution_node, MADS.hasAffiliation, affiliation_node))

        # add the role from AUP subfield |f to the contribution node:
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
        publisher_name = helpers.get_subfield(pufield, "v")
        # get place from subfield o:
        publication_place = helpers.get_subfield(pufield, "o")
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


# ## Semi-generic helper functions


# %% [markdown]
# ### Building generic bf:Note nodes
#
# Will probably also need this later for other kinds of notes, such as the ones in field BN.


# %%
def build_note_node(resource_uri, note):
    if note is not None and note != "":
        # make a fragment uri node for the note:
        note_node = URIRef(
            resource_uri + "_note"
        )  # TODO: how can swe decide whether to add it with _note or #note - based on whether it is a node for a main work or a subnode? Probably check for existing "#" in the resource_uri!
        records_bf.set((note_node, RDF.type, BF.Note))
        records_bf.set((note_node, RDFS.label, Literal(note)))
        records_bf.set((resource_uri, BF.note, note_node))


# ## Function: Adding DFK as an Identifier

# ### DFK as id for Bibframe
#
# We want to add the DFK as a local bf:Identifier to the work (or instance?).
# We also want to say where the Identifier originates (to say it is from PSYNDEX/ZPID).
#
# The format for that is:
# ```turtle
# instancebundles:123456 bf:identifiedBy instancebundles:123456#dfk .
# instancebundles:123456#dfk a bf:Identifier ;
#     a pxc:DFK;
#     rdf:value "1234456";
# .
# ```
#
# So, we need a node for the Identifier. This is a function that will return such an identifier bnode to add to the work_uri. We are calling it way down below in the loop:


#  a function to be called in a for-loop while going through all records of the source xml,
# which returns a new triple to add to the graph that has a hashed uri node for the dfk identifier.
# The predicate is "bf:identifiedBy" and the object is a node of rdf:Type "pxc:DFK":
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


# ## Generic Function: Replace languages with their language tag
#
# Can be used for different fields that are converted to langstrings or language uris. Use within other functions that work with the languages in different fields.
#
# Returns an array with two values: a two-letter langstring tag at [0] and a three-letter uri code for the library of congress language vocab at [1].


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


def get_work_language(record):
    work_language = get_langtag_from_field(record.find("LA").text.strip())[1]
    work_lang_uri = LANG[work_language]
    return work_lang_uri


# ## Function: Build a Relationship Node for different types of related works
#
# Should take parameters - a dict per type (research data closed access, rd open access, ...) that has values for all the needed fields


def build_work_relationship_node(work_uri, relation_type, count=None):
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
        access_policy_concept = relation_types[relation_type]["access_policy_concept"]
    # make a node for this relationship:
    # use a random number to make node unique:
    # TODO: use count to attach a numbering to the node so two different Relationships have unique names and aren't collapsed anymore!
    # make it class bflc:Relationship:
    relationship_subclass = genre[0].upper() + genre[1:] + "Relationship"
    # or "PreregistrationRelationship"
    relationship_bnode = URIRef(
        work_uri + "#" + str(relationship_subclass) + str(count)
    )
    # or other. We can use the content of "genre" in Camelcase for this:
    # records_bf.add((relationship_bnode, RDF.type, BFLC.Relationship))
    records_bf.add((relationship_bnode, RDF.type, PXC[relationship_subclass]))

    # add a bflc:Relation (with a label and value) via bflc:relation to the relationship bnode
    # (label and value could be given as a parameter):
    # print("\tbflc:relation [a bflc:Relation ; rdfs:label 'has research data', rdf:value 'relation:hasResearchData'^^xsd:anyURI] ;")
    # relation_bnode = BNode()
    # records_bf.set((relation_bnode, RDF.type, BFLC.Relation))
    # records_bf.add((relation_bnode, RDFS.label, Literal("has research data", lang="en")))
    # records_bf.add((relation_bnode, RDF.value, Literal(RELATIONS.hasResearchData)))
    records_bf.set((relationship_bnode, BFLC.relation, URIRef(RELATIONS[relation])))
    # make a bnode for the work:
    # related_work_bnode = BNode()
    related_work_bnode = URIRef(relationship_bnode + "_work")
    records_bf.add((related_work_bnode, RDF.type, BF.Work))
    records_bf.add((related_work_bnode, RDF.type, URIRef(BF[work_subclass])))
    # give work a content type: no need for initial migration, but later
    # records_bf.add((related_work_bnode, BF.content, URIRef(CONTENTTYPES[content_type])))
    # make the content type a bf:Content:
    # records_bf.add((URIRef(CONTENTTYPES[content_type]), RDF.type, BF.Content))
    # and a genre: not needed for migration, but later
    # records_bf.add((related_work_bnode, BF.genreForm, URIRef(GENRES[genre])))
    # make the genreform a bf:GenreForm:
    # records_bf.add((URIRef(GENRES[genre]), RDF.type, BF.GenreForm))
    # attach the work bnode to the relationship bnode with bf:relatedTo
    # (or a subproperty as given as a parameter)):
    # print("\tbf:relatedTo [a bf:Work ;")
    records_bf.add((relationship_bnode, BF[relatedTo_subprop], related_work_bnode))
    # make a node for the instance:
    related_instance_bnode = URIRef(related_work_bnode + "_instance")
    records_bf.set((related_instance_bnode, RDF.type, BF.Instance))
    # add subclass for electronic - not needed for initial migration, but later
    # records_bf.add((related_instance_bnode, RDF.type, BF.Electronic))
    records_bf.add((related_work_bnode, BF.hasInstance, related_instance_bnode))
    # add accesspolicy to instance:
    if access_policy_label is not None and access_policy_value is not None:
        access_policy_node = URIRef(access_policy_concept)
        records_bf.add((access_policy_node, RDF.type, BF.AccessPolicy))
        records_bf.add((access_policy_node, RDFS.label, Literal(access_policy_label)))
        # add preflabels "freier Zugang" and open access - since it will always be open, we don't need to fetch from skosmos, but just use preset labels:
        records_bf.add(
            (
                access_policy_node,
                SKOS.prefLabel,
                Literal(access_policy_label, lang="en"),
            )
        )
        records_bf.add(
            (access_policy_node, SKOS.prefLabel, Literal("freier Zugang", lang="de"))
        )
        # not addind the url to coar for now, we don't need it for migration:
        # records_bf.set(
        #     (
        #         access_policy_node,
        #         RDF.value,
        #         Literal(access_policy_value, datatype=XSD.anyURI),
        #     )
        # )
        # add concept from our own vocabulary:
        # records_bf.set((access_policy_node, OWL.sameAs, URIRef(access_policy_concept)))
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
        "genre": "Preregistration",
        "access_policy_label": None,
        "access_policy_value": None,
        "access_policy_concept": None,
    },
}


# ## Function: Create Instance Title nodes from fields TI, TIU, TIL, TIUE...
#
# Titles and Translated titles are attached to Instances. Translated titles also have a source, which can be DeepL, ZPID, or Original.
#
# Example:
#
# ```turtle
# instancebundles:123456 bf:title instancebundles:123456#title .
# instancebundles:123456#title a bf:Title ;
#    rdfs:label "Disentangling the process of epistemic change" ;
#    bf:mainTitle "Disentangling the process of epistemic change"@en;
#    bf:subtitle "The role of epistemic volition"@en;
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
            maintitle_language = helpers.guess_language(maintitle)
    else:  # if there is no TIL field, guess the language from the string itself!
        maintitle_language = helpers.guess_language(maintitle)

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
                subtitle_language = helpers.guess_language(subtitle)
        else:  # if there is no TIUL field, guess the language from the string itself!
            subtitle_language = helpers.guess_language(subtitle)

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
        fulltitle_language = helpers.guess_language(fulltitle)

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


def add_abstract_licensing_note(abstract, abstracttext):
    # use this on the abstract _after_ first removing the ToC!
    # we will extract any text at the end of an abstract that is not actually part of the abstract, but a licensing note or a note about what software was used to translate it.
    """Adds a licensing note to the abstract if it contains a copyright string and/or a "translated by DeepL" notice."""
    abstract_copyright_string = None
    # 1. first check if there is a "(translated by DeepL)" at the end of the abstract, remove it and add it to the licensing note.
    # 2 then check for a copyright string at the (new) end of the abstract. Remove it and copy it into the licensinf note -
    # but only if there isn't already something in there (the translated by deepl note) - because if there is, the translation note takes precedence
    # and the copyright note will not be retained.
    deepl_match = re.search(
        r"^(.*)\s\((translated by DeepL)\)$", abstracttext, re.IGNORECASE
    )
    if deepl_match:
        # replace the abstract with the content before the "(translated by DeepL)":
        abstracttext = deepl_match.group(1)
        # add it to the licensing note, but only if empty:
        abstract_copyright_string = deepl_match.group(2)
    else:
        abstract_copyright_string = None

    # also, after that, check the new abstract for a copyright string:
    license_match = re.search(r"(.*)(\(c\).*)$", abstracttext, re.IGNORECASE)
    # if that match is not None, check if it is in the last 100 characters of the abstract:
    if license_match and len(license_match.group(2)) < 100:
        # if so, check if there is a "(b)" anywhere in the abstract before the match (this is an exclusion criterion,
        # because if there is a "(b)" before the "(c)", it's just a lettered list item, not the copyright string):
        if re.search(r"(.*)(\(b\).*)", license_match.group(1), re.IGNORECASE):
            pass
            # if there is _no_ "(b)" before the "(c)", we have a copyright string; add it to the licensing note.
            # unless it already contains something - which will always be the translation note:
        else:
            if abstract_copyright_string is None or abstract_copyright_string == "":
                abstract_copyright_string = license_match.group(2)
                abstracttext = license_match.group(1)
            else:
                # don't write it into the note if there is already something in it, but do remove it from the abstract!
                abstracttext = license_match.group(1)
            # otherwise ignore the string, we have no copyright string

    if abstract_copyright_string is not None and abstract_copyright_string != "":
        # make a node for the abstract licensing note:
        # give it a fragment uri:
        abstract_license_node = URIRef(abstract + "_license")
        # give it a class:
        records_bf.add((abstract_license_node, RDF.type, BF.UsageAndAccessPolicy))
        # add the license type to the node with rdf:value and anyURI:
        if (
            abstract_blocked
        ):  # if it's an elsevier abstract with publisher copyright (blocked from release/sharing), use this specific string to indicate we can't release it, otherwise the string we find at the end:
            records_bf.add(
                (
                    abstract_license_node,
                    RDFS.label,
                    Literal("Abstract not released by publisher."),
                )
            )
        else:
            records_bf.add(
                (abstract_license_node, RDFS.label, Literal(abstract_copyright_string))
            )
        # attach it to the abstract node with bf:usageAndAccessPolicy:
        records_bf.add((abstract, BF.usageAndAccessPolicy, abstract_license_node))
    # also, return the new abstracttext with any copyright string removed:
    return abstracttext.strip()


# function to get the original abstract:
def get_bf_abstract(work_uri, record, abstract_blocked):
    """Extracts the abstract from field ABH and adds a bf:Summary bnode with the abstract and its metadata. Also extracts the Table of Content from the same field."""
    ## first check if this is even an abstract at all, or just some text saying "no abstract":
    # if the text is very short (under 50 characters) and contains "no abstract" or "kein Abstract", it's not an abstract:
    if len(record.find("ABH").text) < 500 and re.search(
        r"(no abstract|kein Abstract)", record.find("ABH").text, re.IGNORECASE
    ):
        return None  # don't make a node at all!
    # if it's not a "no abstract" text, make a node for the abstract:

    abstract = URIRef(work_uri + "#abstract")
    # abstract = URIRef(work_uri + "/abstract")
    records_bf.add((abstract, RDF.type, PXC.Abstract))
    # get abstract text from ABH
    abstracttext = html.unescape(
        mappings.replace_encodings(record.find("ABH").text).strip()
    )

    ## == Extracting the table of contents from the abstract: == ##
    # check via regex if there is a " - Inhalt: " or " - Contents: " in it.
    # if so, split out what comes after. Drop the contents/inhalt part itself.
    match2 = re.search(r"^(.*)[-–]\s*(?:Contents|Inhalt)\s*:\s*(.*)$", abstracttext)
    if match2:
        abstracttext = match2.group(1).strip()
        contents = match2.group(2).strip()
        # make a node for bf:TableOfContents:
        toc = URIRef(work_uri + "#toc")
        records_bf.add((toc, RDF.type, BF.TableOfContents))
        # add the bnode to the work via bf:tableOfContents:
        records_bf.add((work_uri, BF.tableOfContents, toc))
        # add the contents to the abstract node as a bf:tableOfContents:
        # if the contents start with http, extract as url into rdf:value:
        if contents.startswith("http"):
            records_bf.add((toc, RDF.value, Literal(contents, datatype=XSD.anyURI)))
            # otherwise it's a text toc and needs to go into the label
        else:
            # but we need to determine the language of the toc:
            try:
                toc_language = helpers.guess_language(contents)
            except:
                toc_language = "und"
            records_bf.add((toc, RDFS.label, Literal(contents, lang=toc_language)))

    # Check for end of abstract that says something about the license "translated by DeepL"
    # and remove them, but add them to the node as a bf:usageAndAccessPolicy:
    # note: I won't remove the useless string saying "no abstract" that is in place of the abstract. It's not worth the effort. Somebody else
    # can do it if they want to - it can be filtered by looking for the "no abstract" concept added to the abstract node.
    # check the abstract for any copyright strings (and "translated by DeepL") and remove them, but add them to the node as a bf:usageAndAccessPolicy:
    abstracttext = add_abstract_licensing_note(abstract, abstracttext)

    # get abstract language from ABLH ("German" or "English")
    abstract_language = "en"  # set default
    # TODO: that's a bad idea, actually. Better: if field is missing, use a language recog function!
    if record.find("ABLH") is not None:
        abstract_language = get_langtag_from_field(record.find("ABLH").text.strip())[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = helpers.guess_language(abstracttext)
    else:  # if the ABLH field is missing, try to recognize the language of the abstract from its text:
        abstract_language = helpers.guess_language(abstracttext)

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
    # add a boolean qualifier whether the abstract is "open" - cleared by the publisher to be shared
    records_bf.add(
        (
            abstract_source_node,
            PXP.blockedAbstract,
            Literal(abstract_blocked, datatype=XSD.boolean),
        )
    )


def get_bf_secondary_abstract(work_uri, record, abstract_blocked):
    ## first check if this is even an abstract at all, or just some text saying "no abstract":
    # if the text is very short (under 100 characters) and contains "no abstract" or "kein Abstract", it's not an abstract:
    if len(record.find("ABN").text) < 50 and re.search(
        r"(no abstract|kein Abstract)", record.find("ABH").text, re.IGNORECASE
    ):
        return None  # don't make a node at all!
    abstract = URIRef(work_uri + "#secondaryabstract")
    # abstract = URIRef(work_uri + "/abstract/secondary")
    records_bf.add((abstract, RDF.type, PXC.Abstract))
    records_bf.add((abstract, RDF.type, PXC.SecondaryAbstract))
    abstracttext = html.unescape(
        mappings.replace_encodings(record.find("ABN").text).strip()
    )
    # check if the abstracttext ends with " (translated by DeepL)" or a licensing note,
    # and if so, remove those from the abstract and place them into a UsageandAccessPolicy node.
    abstracttext = add_abstract_licensing_note(abstract, abstracttext)

    abstract_language = "de"  # fallback default

    if record.find("ABLN") is not None and record.find("ABLN").text != "":
        abstract_language = get_langtag_from_field(record.find("ABLN").text.strip())[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = helpers.guess_language(abstracttext)
    else:  # if no language field, guess language from the text:
        abstract_language = helpers.guess_language(abstracttext)

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
    # return abstract
    # or better, attach it right away:
    records_bf.add((work_uri, BF.summary, abstract))
    # add a boolean qualifier whether the abstract is "open" - cleared by the publisher to be shared
    records_bf.add(
        (
            abstract_source_node,
            PXP.blockedAbstract,
            Literal(abstract_blocked, datatype=XSD.boolean),
        )
    )


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
# def get_bf_toc(work_uri, record):
#     # read the abstract in ABH
#     contents = ""
#     if record.find("ABH") is not None:
#         abstracttext = html.unescape(
#             mappings.replace_encodings(record.find("ABH").text).strip()
#         )
#         # check via regex if there is a " - Inhalt: " or " - Contents: " in it.
#         # if so, split out what comes after. Drop the contents/inhalt part itself.
#         match = re.search(r"^(.*)[-–]\s*(?:Contents|Inhalt)\s*:\s*(.*)$", abstracttext)
#         if match:
#             abstracttext = match.group(1).strip()
#             contents = match.group(2).strip()

#     # also check if what comes is either a string or a uri following the  given pattern
#     # and export one as a rdfs_label and the other as rdf:value "..."^^xsd:anyURI (remember to add XSD namespace!)
#     # also remember that we should only create a node and attach it to the work
#     # if a) ABH exists at all and
#     # b) the regex is satisfied.
#     # So I guess we must do the whole checking and adding procedure in this function!

#     # only return an added triple if the toc exisits, otherwise return nothing:
#     if contents:
#         return records_bf.add((work_uri, BF.tableOfContents, Literal(contents)))
#     else:
#         return None
#     # return records_bf.add((work_uri, BF.tableOfContents, Literal("test")))


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

# %%
# function to build the nodes for preregistration links


def get_bf_preregistrations(work_uri, record):
    # get the preregistration link from the field PREREG:
    preregistration_note = None
    unknown_field_content = None
    for prreg in record.findall("PRREG"):
        global preregistrationlink_counter
        preregistrationlink_counter += 1
        # get the full content of the field, sanitize it:
        prregfield = html.unescape(mappings.replace_encodings(prreg.text.strip()))
        # use our node-building function to build the node:
        relationship_node, instance = build_work_relationship_node(
            work_uri, relation_type="preregistration", count=preregistrationlink_counter
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
            identifiers.build_doi_identifier_node(instance, doi, records_bf)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, records_bf)
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
            build_note_node(relationship_node, preregistration_note)
        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))

        # add preregistration_node to work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


def add_trials_as_preregs(work_uri, prereg_string):
    """Checks the PRREG field for trial numbers and adds them as separate preregistrations per number, adding the recognzed registry, too.
    Also checks any existing Preregistration nodes to see if a trial is already listed via its url, and adding the trialnumber and registry to that node, otherwise creating a new Preregistration node.
    """
    trial_number_regexes = [
        ("DRKS\d+", "drks"),
        ("CRD\d+", "prospero"),
        ("ISRCTN\d+", "srctn"),
        ("NCT\d+", "clinical-trials-gov"),
        ("actrn\d+", "anzctr"),
        ("(?i)chictr[-a-z]*\d+", "chictr"),
        ("kct\d+", "cris"),
        ("ctri[\d/]+", "clinical-trial-registry-india"),
        # ("\d{4}-\d+-\d+", "euctr"),
        ("irct[0-9a-z]+", "irct"),
        ("isrctn\d+", "isrctn"),
        # ("", "jma"),
        # ("", "jprn"),
        ("(?i)(nl|ntr)[-0-9]+", "dutch-trial-register"),
        ("rbr\d+", "rebec"),
        ("rpcec\d+", "rpec"),
        ("slctr[\d/]+", "slctr"),
        ("tctr\d+", "tctr"),
        ("umin\d+", "umin-japan"),
        # ("u[\d-]+", "utn"),
    ]
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
                for relationship in records_bf.objects(
                    subject=work_uri, predicate=BFLC.relationship
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
                        records_bf.value(relationship, RDF.type)
                        == PXC.PreregistrationRelationship
                    ):
                        # first get the work that is attached via bf:supplement:
                        # print(
                        #     "found a PreregistrationRelationship node! "
                        #     + str(relationship)
                        # )
                        preregistration_work = records_bf.value(
                            subject=relationship, predicate=BF.supplement, any=False
                        )
                        # then the instance of this preregistration work:
                        prereg_instance = records_bf.value(
                            subject=preregistration_work,
                            predicate=BF.hasInstance,
                            any=False,
                        )
                        # then the electronicLocator of this instance:
                        prereg_url = records_bf.value(
                            subject=prereg_instance,
                            predicate=BF.electronicLocator,
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
                            records_bf.add(
                                (trialnumber_node, RDF.type, PXC.TrialNumber)
                            )
                            records_bf.add(
                                (prereg_instance, BF.identifiedBy, trialnumber_node)
                            )
                            records_bf.add(
                                (trialnumber_node, RDF.value, Literal(trialnumber[1]))
                            )
                            # add the registry as an bf:assigner with class pxc:TrialRegistry:
                            registry_node = URIRef(
                                "https://w3id.org/zpid/vocabs/trialregs/"
                                + trialnumber[0]
                            )
                            records_bf.set((registry_node, RDF.type, PXC.TrialRegistry))
                            records_bf.add(
                                (trialnumber_node, BF.assigner, registry_node)
                            )
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
                    global preregistrationlink_counter
                    preregistrationlink_counter += 1
                    # make a new Preregistration node:
                    relationship_node, instance = build_work_relationship_node(
                        work_uri,
                        relation_type="preregistration",
                        count=preregistrationlink_counter,
                    )
                    print(
                        "adding new Preregistration node for trial number: "
                        + trialnumber[1]
                    )
                    # add the trial number to the node:
                    # make a node for the number:
                    trialnumber_node = URIRef(str(instance) + "_trialnumber")
                    records_bf.add((trialnumber_node, RDF.type, PXC.TrialNumber))
                    records_bf.add((instance, BF.identifiedBy, trialnumber_node))
                    records_bf.add(
                        (trialnumber_node, RDF.value, Literal(trialnumber[1]))
                    )
                    # add the registry as an bf:assigner with class pxc:TrialRegistry:
                    registry_node = URIRef(
                        "https://w3id.org/zpid/vocabs/trialregs/" + trialnumber[0]
                    )
                    records_bf.set((registry_node, RDF.type, PXC.TrialRegistry))
                    records_bf.add((trialnumber_node, BF.assigner, registry_node))
                    # add the finished node for the relationship to the work:
                    records_bf.add((work_uri, BFLC.relationship, relationship_node))
                    # add preregistration_node to work:
                    records_bf.add((work_uri, BFLC.relationship, relationship_node))


# ## Function: Create nodes for Grants (GRANT)
#
# Includes several helper functions that
# - extract grant numbers if several were listed in the |n subfield
# - replace funder names that fundref usually doesn't match correctly or at all
# - look up funder names in crossref's fundref api to get their fundref id (a doi)


def extract_grant_numbers(subfield_n_string):
    # this function takes a string that possibly contains an unstructured set of several award numbers connected with "and" etc. and returns a real array (List) of award numbers
    # first, split the string on "," or ";" or "and": (first replacing all semicolons and "ands" with commas)")
    if subfield_n_string is not None and subfield_n_string != "":
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
    try:
        crossref_api_request = session_fundref.get(crossref_api_url, timeout=20)
    except:
        print("fundref request failed at " + crossref_api_url)
    try:
        crossref_api_response = crossref_api_request.json()
    except:
        print("fundref response not received for " + crossref_api_url)
    # result_count = int(crossref_api_response["message"]["total-results"])
    # if the request was successful, get the json response:

    try:
        if (
            crossref_api_request.status_code == 200
            and crossref_api_response["message"]["total-results"] > 0
        ):
            return "10.13039/" + crossref_api_response["message"]["items"][0]["id"]
        elif (
            crossref_api_request.status_code == 200
            and crossref_api_response["message"]["total-results"] == 0
        ):
            # retry the funder_name, but remove any words after the first comma:
            # print(f"fundref-api: no hits for {funder_name}.")
            if funder_name.find(",") > -1:
                funder_name = funder_name.split(",")[0]
                # print(f"fundref-api: new funder name: {funder_name}")
                return get_crossref_funder_id(funder_name)
            else:
                # print(f"fundref-api: nothing either for {funder_name}. Returning None.")
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

        # first, use anything found in the main GRANT field as the funder name:
        # but because the database is still messy (may have no funder name at all in some GRANTs), use a
        # default funder name in case there is none, because the label is mandatory for an agent node:
        try:
            funder_name = helpers.get_mainfield(
                grantfield
            )  # we already checked wheter the field is empty, so we can use get_mainfield here
        except:
            funder_name = "unknown funder"  # just in case the GRANT field has no content beside the subfields
        # add the funder name to the funder node:
        records_bf.add((funder_node, RDFS.label, Literal(funder_name)))
        # try to look up this funder name in the crossref funder registry:
        # if there is a match, add the crossref funder id as an identifier:
        crossref_funder_id = None
        crossref_funder_id = get_crossref_funder_id(funder_name)
        if crossref_funder_id is not None:
            # add a node for the identifier:
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
            # if "|n " in grantfield, extract it. It can contain one grant numbers, separated by "and" or "or":
            grants = helpers.get_subfield(grantfield, "n")
            # to number the nodes, we need to count the grants:
            grant_counter = 0
        except:
            grants = None
        if grants is not None:
            # make an array of grant numbers by extracting them from the string:
            grants = extract_grant_numbers(grants)
            # add the grant number to the funding contribution node, counting up:
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
            funding_info = helpers.get_subfield(grantfield, "i")
        except:
            funding_info = None

        try:
            # if "|e " in grantfield:
            funding_recipient = helpers.get_subfield(grantfield, "e")
        except:
            funding_recipient = None
        if funding_recipient is not None:
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


# # Function: Add Conference info from field CF


def get_bf_conferences(work_uri, record):
    # only use conferences from actual books (BE=SS or SM)
    # ignore those in other publication types like journal article
    # get the conference info from the field CF:
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
                conference_name = helpers.get_mainfield(conference_field)
            except:
                conference_name = "MISSING CONFERENCE NAME"
                print(
                    "a conference in field CF has no name. DFK: "
                    + record.find("DFK").text
                )
            # then check the field for a date in apotential subfield |d:
            try:
                conference_date = helpers.get_subfield(conference_field, "d")
            except:
                conference_date = None
            if conference_date is not None:
                # if there is a |d, add the full date to conference_note:
                conference_note = "Date(s): " + conference_date
                # extract the year from the date to use it as conference_year:
                # Anything with 4 consecutive digits anywhere in the date string is a year.
                # here is a regex for finding YYYY pattern in any string:
                year_pattern = re.compile(r"\d{4}")
                # if there is a year in the date string, use that as the date:
                try:
                    conference_year = year_pattern.search(conference_date).group()
                except:
                    conference_year = None
            # then check for a note in a potential subfield |b, but
            # remebering to keep what is already in conference_note from the date:
            try:
                conference_note = (
                    conference_note + ". " + helpers.get_subfield(conference_field, "b")
                )
            except:
                conference_note = conference_note
            # then check the field for a place in a potential subfield |o:
            try:
                conference_place = helpers.get_subfield(conference_field, "o")
            except:
                conference_place = None

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
            # records_bf.add((conference_node, RDF.type, PXC.Conference))
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


def get_urlai(work_uri, record):
    """Gets research data from field URLAI. This is always in PsychData, so it will be restricted access by default.
    We will also assume it to always be just research data, not code.
    """
    for data in record.findall("URLAI"):
        urlai_field = mappings.replace_encodings(data.text.strip())
        unknown_field_content = None
        global researchdatalink_counter
        researchdatalink_counter += 1
        # build the relationship node:
        # add ~~secondary~~ only class pxc:ResearchDataRelationship to the relationship node for research data
        relationship_node, instance = build_work_relationship_node(
            work_uri,
            relation_type="rd_restricted_access",
            count=researchdatalink_counter,
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
            identifiers.build_doi_identifier_node(instance, doi, records_bf)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, records_bf)

        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


def get_datac(work_uri, record):
    """Gets research data from field DATAC, adds a Relationship node to the work.
    Note: We define all data from this field as type "research data only, no code", and "open/unrestricted access"
    Newer data from PSYNDEXER may be something else, but for first migration, we assume all data is research data only.
    """
    # go through the list of datac fields and get the doi, if there is one:
    for data in record.findall("DATAC"):
        datac_field = mappings.replace_encodings(data.text.strip())
        # build the relationship node:
        global researchdatalink_counter
        researchdatalink_counter += 1
        relationship_node, instance = build_work_relationship_node(
            work_uri, count=researchdatalink_counter, relation_type="rd_open_access"
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
            identifiers.build_doi_identifier_node(instance, doi, records_bf)
        for url in url_set:
            identifiers.build_electronic_locator_node(instance, url, records_bf)
        # now attach the finished node for the relationship to the work:
        records_bf.add((work_uri, BFLC.relationship, relationship_node))


# ## TODO: Function: Get Series info for Books (field SE)
#
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

#### # ----- The Loop! -------------- # ####
# ## Creating the Work and Instance uris and adding other triples via functions
# ## This is the main loop that goes through all the records and creates the triples for the works and instances
record_count = 0
for record in tqdm(root.findall("Record")):
    # for record in tqdm(root.findall("Record"))[0:200]:
    """comment this out to run the only 200 records instead of all 700:"""
    # count up the processed records for logging purposes:
    record_count += 1

    # Get the DFK identifier from the record - we need it for naming our URIs of works, instances and instancebundles:
    # note: actually adding it as an identifier is done below, to the instancebundle.
    dfk = record.find("DFK").text

    # Create a URI node for the work and  give it the correct bibframe classes:
    # make sure a work_uri will look like this: works:dfk_work, eg works:123456_work
    work_uri = URIRef(WORKS + dfk + "_work")
    records_bf.add((work_uri, RDF.type, BF.Work))
    records_bf.add((work_uri, RDF.type, PXC.MainWork))

    # Add language of work from field LA and add to Work -
    # TODO: second language from <LA2>? no way to distinguish
    # between main/first language and second in bibframe
    records_bf.add((work_uri, BF.language, get_work_language(record)))

    publication_types.generate_content_type(record, dfk, work_uri, records_bf)

    ## Adding Contributions by Persons and Corporate Bodies to the work (only real creators, like editors, authors, translators,
    # not funders or conferences, which are handled below)
    # set up/reset a global counter for contributions to a work (it will count up in the functions that add Person contributions from AUP fields and Org contributions from AUK fields) - we need it to add the contribution position
    contribution_counter = 0
    fundingreference_counter = 0
    conferencereference_counter = 0
    researchdatalink_counter = 0
    preregistrationlink_counter = 0
    add_bf_contributor_person(work_uri, record)
    # are there any PAUPs left that haven't been successfull matched and added to contributors?
    match_CS_COU_affiliations_to_first_contribution(work_uri, record)
    match_paups_to_contribution_nodes(work_uri, record)
    match_orcids_to_contribution_nodes(work_uri, record)
    add_bf_contributor_corporate_body(work_uri, record)
    match_email_to_contribution_nodes(work_uri, record)

    # Add the table of contents to the work, if we can extract it from the abstract field (ABH):
    # get_bf_toc(work_uri, record) # this is now done inside the abstract functions - along with abstract license recognition

    # TODO: calculate a bool true/false value from fields to set whether abstract should be made available or not due to copyright reasons.
    abstract_blocked = not get_abstract_release(record)

    # Adding main/original abstract to the work:
    # note: somehow not all records have one!
    if record.find("ABH") is not None:
        get_bf_abstract(work_uri, record, abstract_blocked)
        # records_bf.add((work_uri, BF.summary, get_bf_abstract(work_uri, record)))
    # d.add((work_uri, BF.summary, get_bf_abstract(work_uri, record), graph_1))

    # Adding secondary abstract to the work - (usually a translation, so also has data about the origin of the abstract):
    # note: somehow not all records have one!
    if record.find("ABN") is not None:
        get_bf_secondary_abstract(work_uri, record, abstract_blocked)

    # Adding CTs to the work, including skosmos lookup for the concept uris:
    # add_controlled_terms(work_uri, record)
    terms.add_controlled_terms(work_uri, record, records_bf)

    ## TODO: add all the other controlled keywords from the record to the work - SH, CM, AGE, SAM, PLOC
    # including skosmos lookups.

    ## TODO: add any uncontrolled keywords we have:
    # from fields KP - and if they exist, UTE and UTG

    # Adding pxc:FundingReferences from fields <GRANT> to the work:
    get_bf_grants(work_uri, record)

    ## Adding Conferences to the work:
    get_bf_conferences(
        work_uri, record
    )  # adds a bf:contribution >> pxc:ConferenceReference node to the work

    ## Add research data links from fields URLAI and DATAC to the work:
    get_datac(work_uri, record)  # adds the generated bflc:Relationship node to the work
    # switched off for performance reasons

    ### Adding Preregistration links to the work (from field <PREREG>):
    # deactivated due to performance issues and
    # needing a rewrite (replace bnodes with hash-uris),
    # finding a way to frame only "real" main works (1 per star record) in the jsonld,
    # instead of these linked Works, too -> fixed by adding a unique class "MainWork" for root works
    get_bf_preregistrations(work_uri, record)

    # make another round through all the PRREG fields of the record, identifying any trial numbers and adding each as separate pxc:PreregistrationRelationship to the work, including the number as an identifier of the instance, and the ifentified registry as the assigner of the identifier:
    add_trials_as_preregs(work_uri, record)

    ## ==== InstanceBundle ==== ##

    # For each work, create one pxc:InstanceBundle node with an uri
    # like this: instancebundles:0123456 (where 0123456 is the dfk of the record):
    # (we migrate each record as an InstanceBundle with 1 or 2 Instances)
    instance_bundle_uri = URIRef(INSTANCEBUNDLES + dfk)
    records_bf.add((instance_bundle_uri, RDF.type, PXC.InstanceBundle))

    ## ==== Instances ==== ##
    # Create the first instance - there will always be at least one:
    instance_uri = URIRef(INSTANCES + dfk + "#1")
    records_bf.add((instance_uri, RDF.type, BF.Instance))

    # connect the instancebundle to the work:
    records_bf.add((work_uri, PXP.hasInstanceBundle, instance_bundle_uri))
    # connect the instance_bundle to the instance:
    records_bf.add((instance_bundle_uri, BF.hasPart, instance_uri))

    # connect work and instance via bf:instanceOf and bf:hasInstance:
    records_bf.add((instance_uri, BF.instanceOf, work_uri))
    records_bf.add((work_uri, BF.hasInstance, instance_uri))

    # Add mediacarrier from field MT to the first instance:
    # Note: MT is the first media type field in a record, it contains
    # a string name of the medium of the first instance (e.g. "Print" or "Online Medium").

    publication_types.add_mediacarrier_to_instance(
        instance_uri, records_bf, record.find("MT")
    )

    ## Add the publication info (date, publisher, place) to the instancebundle:
    # Note 1: we only have one publication date per record, although two instances could have
    # different publication dates. We only add the first one to the instancebundle.
    # Note 2: publisher and publication place are the same for all instances of a record,
    # so we add them to the instancebundle, not the instance (yet). In future, we should copy them over
    # to the instance, so we can have a complete bf:Publication node for each instance, and then add the
    # (possibly) different publication dates to this node, too.
    # So TODO: add a copy of this bf:Publication node to each instance, adding the instance's unique publication date to it.
    add_publication_info(instance_bundle_uri, record)

    # Add a second instance to the work and instancebundle, if there is a second mediatype in the record:
    if record.find("MT2") is not None:
        instance_uri_2 = URIRef(
            INSTANCES + dfk + "#2"
        )  # create a second instance node:
        records_bf.add(
            (instance_uri_2, RDF.type, BF.Instance)
        )  # give it type/class bf:Instance
        records_bf.add(
            (instance_bundle_uri, BF.hasPart, instance_uri_2)
        )  # connect the instancebundle to the instance
        records_bf.add(
            (instance_uri_2, BF.instanceOf, work_uri)
        )  # connect instance back to work
        records_bf.add(
            (work_uri, BF.hasInstance, instance_uri_2)
        )  # connect work to this instance
        # TODO: add publication date, publisher, place:
        # like this, probably: add_publication_info(instance_uri_2, record, record.find("MT2").text)
        ## Add the mediacarrier node to the instance:
        publication_types.add_mediacarrier_to_instance(
            instance_uri_2, records_bf, record.find("MT2")
        )

    # Add the DFK as an identifier node to the instancebundle:
    records_bf.add(
        (
            instance_bundle_uri,
            BF.identifiedBy,
            get_bf_identifier_dfk(instance_bundle_uri, dfk),
        )
    )

    # Add the issuance type (from BE) to the instancebundle (e.g. "Journal Article" or "Edited Book"):
    publication_types.get_issuance_type(instance_bundle_uri, record, records_bf)

    ## add license to bundle:
    add_instance_license(instance_bundle_uri, record)

    ### Add titles (original and translated) to the instancebundle:

    # Add title from field TI (original title) and associated fields:
    title = get_bf_title(instance_bundle_uri, record)
    records_bf.set((instance_bundle_uri, BF.title, title))

    # Add translated title from TIUE field and associated fields
    # but only if the field exists - which is not always the case, sadly!
    # Not using the same function here as for TI, since translated titles have
    # have many more fields, such as origin etc.
    # There is certainly room for refactoring here!
    if record.find("TIUE") is not None and record.find("TIUE").text != "":
        records_bf.add(
            (
                instance_bundle_uri,
                BF.title,
                get_bf_translated_title(instance_bundle_uri, record),
            )
        )
    # add methods (needs title and abstract already in graph, so do it after all the other stuff):
    publication_types.add_work_studytypes(
        record, dfk, work_uri, instance_bundle_uri, records_bf
    )
    # add other genres (not based on study type/method) to the work (such as Thesis):
    publication_types.add_work_genres(work_uri, record, dfk, records_bf)

    # clean up genres; remove any genres:ResearchPaper node when the work already has genre:ThesisDoctoral:
    publication_types.clean_up_genres(work_uri, records_bf)

    ## adding ISBNs:
    # after we've added everything, we can go through the isbns and other stuff and put them into the instances where they belong.
    # that is hard and very slow. MAybe we should do this in a separate sparql query afterwards?
    # For now, we get the isbns from <PU> subfield |i and |e and add them to the instancebundle first:
    add_isbns(record, instance_bundle_uri)

    # if the instancebundle has an instance that is electronic, add the doi, url and urn to it: (note: currently, if there are no electronic instances, but a doi, url, urn, they are dropped!!!)
    if (
        record.find("DOI") is not None
        or record.find("URLI") is not None
        or record.find("URN") is not None
    ):
        # make a list of all instances in the instancebundle:
        instances = list(records_bf.objects(instance_bundle_uri, BF.hasPart))
        # if there is only one instance, add the doi, url and urn to that:
        if len(instances) == 1:
            print(
                "only one instance in bundle, adding doi, url, urn to it, regardless of mediatype"
            )
            # get the instance:
            instance = instances[0]
            # add doi of the record to the instance:
            instance_source_ids.get_instance_doi(instance, record, records_bf)
            # add the url of the record to the instance:
            instance_source_ids.get_instance_url(instance, record, records_bf)
            # add the urn of the record to the instance:
            instance_source_ids.get_instance_urn(instance, record, records_bf)
        # otherwise, if there are two (or more) instances, add the doi, url and urn to the first electronic instance we can find:
        elif len(instances) > 1:
            print(
                "several instances found, checking for mediatype before adding doi etc."
            )
            # check if either the first or the second from the list are pxp:mediaCarrier pmt:Online:
            for instance in records_bf.objects(instance_bundle_uri, BF.hasPart):
                # get the mediatype of the instance:
                mediacarrier_type = records_bf.value(instance, PXP.mediaCarrier)
                if mediacarrier_type == PMT.Online:
                    # add doi of the record to the instance:
                    instance_source_ids.get_instance_doi(instance, record, records_bf)
                    # add the url of the record to the instance:
                    instance_source_ids.get_instance_url(instance, record, records_bf)
                    # add the urn of the record to the instance:
                    instance_source_ids.get_instance_urn(instance, record, records_bf)
            #     # if there are two or more, but we can't find any electronic instance among them? That would be an error, but what can be done to still catch it?


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
records_bf.add(
    (
        records_bf_admin_metadata_root,
        BF.generationProcess,
        Literal("Converted from STAR XML to BIBFRAME 2.3 using Python/RDFLib"),
    )
)
# # add a bf:generationDate to the admin metadata node:
records_bf.add(
    (
        records_bf_admin_metadata_root,
        BF.generationDate,
        Literal(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
)
# # add the count as BF.count:
# records_bf.add((records_bf_admin_metadata_root, PXP.recordCount, Literal(record_count)))


print(record_count, "records")

# Serialize all the resulting triples as a turtle file and a jsonld file:
records_bf.serialize("ttl-data/bibframe_records.ttl", format="turtle")
records_bf.serialize(
    "ttl-data/bibframe_records.jsonld",
    format="json-ld",
    auto_compact=False,
    sort_keys=True,
    index=True,
)
# also serialize as xml
records_bf.serialize("ttl-data/bibframe_records.xml", format="pretty-xml")

# print a count the triples we generated:
print(len(records_bf), "triples")
