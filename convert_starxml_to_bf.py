# Purpose: Convert STAR XML to Bibframe RDF

import csv  # for looking up institutes from our csv of luxembourg authority institutes

# import datetime
import html
import logging
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import dateparser
import requests
import requests_cache
from decouple import config

# old fuzzy compare for reconciliations: using fuzzywuzzy
from fuzzywuzzy import fuzz, process
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD
from tqdm.auto import tqdm

import modules.contributions as contributions
import modules.abstract as abstract
import modules.helpers as helpers
import modules.instance_source_ids as instance_source_ids
import modules.instance_sources as instance_sources
import modules.local_api_lookups as local_api_lookups
import modules.mappings as mappings
import modules.identifiers as  identifiers
import modules.namespace as ns
import modules.publication_types as publication_types
import modules.research_info as research_info
import modules.terms as terms

# import modules.open_science as open_science

logging.basicConfig(
    filename=datetime.now().strftime("logs/convert-starxml-to-bf-%Y_%m_%d_%H%M%S.log"),
    level=logging.INFO,
)

RECORDS_FILE = config("RECORDS_FILE")
RECORDS_START = int(config("RECORDS_START"))
RECORDS_END = int(config("RECORDS_END"))
MAX_WORKERS = int(config("MAX_WORKERS"))

# TODO: new fuzzy compare: using the faster rapidfuzz as a drop-in replacement for fuzzywuzzy:
# from rapidfuzz import fuzz
# from rapidfuzz import process

# ror lookup api url for looking up organization contributors and the affiliations of persons:
# ROR_API_URL = f"{config('ROR_API_URL')}/organizations?affiliation="
ROR_API_URL = config("ROR_API_URL")

## crossref api stuff for looking up funders:
# set up friendly session by adding mail in request:
CROSSREF_FRIENDLY_MAIL = f"&mailto={config('CROSSREF_FRIENDLY_MAIL')}"
# for getting a list of funders from api ():
CROSSREF_API_URL = f"{config('CROSSREF_API_URL')}/funders?query="

## Caching requests:
urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}

# a cache for ror requests
session_ror = requests_cache.CachedSession(
    cache_name="requests_ror",
    backend="redis",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)
# and a cache for the crossref api:
session_fundref = requests_cache.CachedSession(
    cache_name="requests_fundref",
    backend="redis",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)


# import csv of LUX authority institutes:
# with open("institute_lux.csv", newline="") as csvfile:
#     reader = csv.DictReader(csvfile)
#     # save it in a list:
#     lux_institutes = list(reader)
#     # split string "known_names" into a list of strings on "##":
#     for institute in lux_institutes:
#         institute["known_names"] = institute["known_names"].split(" ## ")
# print("Und die ganze Tabelle:")
# print(dachlux_institutes)


# Create an "element tree" from the records in my selected xml file so we can loop through them and do things with them:
root = ET.parse(RECORDS_FILE)

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

# graph for bibframe profile:
records_bf = Graph()
# make the graph named for the records: just for clarity in the output:
records_bf = Graph(identifier=URIRef("https://w3id.org/zpid/bibframe/records/"))


# Bind the namespaces to the prefixes we want to see in the output:
records_bf.bind("bf", ns.BF)
records_bf.bind("bflc", ns.BFLC)
records_bf.bind("works", ns.WORKS)
# records_schema.bind("works", WORKS)
records_bf.bind("instances", ns.INSTANCES)
records_bf.bind("pxc", ns.PXC)
records_bf.bind("pxp", ns.PXP)
records_bf.bind("lang", ns.LANG)
records_bf.bind("schema", ns.SCHEMA)
records_bf.bind("locid", ns.LOCID)
records_bf.bind("mads", ns.MADS)
records_bf.bind("roles", ns.ROLES)
records_bf.bind("relations", ns.RELATIONS)
records_bf.bind("genres", ns.GENRES)
records_bf.bind("contenttypes", ns.CONTENTTYPES)
records_bf.bind("issuances", ns.ISSUANCES)  # issuance types
records_bf.bind("pmt", ns.PMT)  # mediacarriers
records_bf.bind("licenses", ns.LICENSES)  # licenses


# # Functions to do all the things
#
# We need functions for the different things we will do - to avoid one long monolith of a loop.
#
# This is where they will go. Examples: Create nodes for Idebtifiers, create nested contribution objects from disparate person entries in AUP, AUK, CS and COU fields, merge PAUP (psychauthor person names and ids) with the person's name in AUP...
#
# These functions will later be called at the bottom of the program, in a loop over all the xml records.


def add_instance_license(resource_uri, record):
    """Reads field COPR and generates a bf:usageAndAccessPolicy node for the resource_uri based on it. Includes a link to the vocabs/licenses/ vocabulary in our Skosmos. We'll probably only use the last subfield (|c PUBL) and directly build a skosmos-uri from it (and pull the label from there?). There are more specific notes in the migration aection of each license concept in Skosmos. Note: the license always applies to an instance (or an instancebundle), not to a work, since the license is about the publication, not the content of the publication - the work content might be published elsewhere with a different license. Manuel mentioned something like that already about being confused about different licenses for different versions at Crossref.

    Args:
        resource_uri (_type_): The node to which the usageAndAccessPolicy node will be added.
        record (_type_): The PSYNDEX record from which the COPR field will be read.
    """
    if record.find("COPR") is not None:
        # get the last subfield of COPR:
        try:
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
                logging.info(
                    f"no license uri found for {license_code} in record {record.find('DFK').text}"
                )
                license_uri = None
            if license_uri is not None:
                # add the license uri from skosmos directly:
                license_node = license_uri
                records_bf.set((license_node, RDF.type, ns.BF.UsePolicy))
                records_bf.add((resource_uri, ns.BF.usageAndAccessPolicy, license_node))

                # Get the label from skosmos:
                try:
                    german_preflabel = local_api_lookups.get_preflabel_from_skosmos(
                        license_uri, "licenses", "de"
                    )
                except:
                    logging.warning(
                        f"failed getting prefLabels for license {license_uri}"
                    )
                    german_preflabel = None
                try:
                    english_preflabel = local_api_lookups.get_preflabel_from_skosmos(
                        license_uri, "licenses", "en"
                    )
                except:
                    logging.warning(
                        f"failed getting prefLabels for license {license_uri}"
                    )
                    english_preflabel = None
                # add the prefLabels to the license node:
                if german_preflabel is not None:
                    records_bf.add(
                        (
                            license_node,
                            SKOS.prefLabel,
                            Literal(german_preflabel, lang="de"),
                        )
                    )
                else:
                    logging.warning(f"no german prefLabel found for {license_uri}")
                if english_preflabel is not None:
                    records_bf.add(
                        (
                            license_node,
                            SKOS.prefLabel,
                            Literal(english_preflabel, lang="en"),
                        )
                    )
                    records_bf.set(
                        (license_node, RDFS.label, Literal(english_preflabel))
                    )
                else:
                    logging.warning(f"no english prefLabel found for {license_uri}")

                # english_preflabel = localapi.get_preflabel_from_skosmos(license_uri, "licenses", "en")
                # TODO: get url for license itself from skosmos (e.g. creative commons deed url)
        except:
            logging.warning(
                f"no valid license found for record {record.find('DFK').text}: {record.find('COPR').text}"
            )
    else:
        logging.warning(f"record {record.find('DFK').text} has no license!")


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
        try:
            date = helpers.get_subfield(record.find("PHIST").text, "o")
            # clean up anything that's not a digit at the  start, such as ":" - make sure with a regex that date starts with a digit:
            date.strip()
            # parse the date: it can be either "8 June 2021" or "08.06.2021"
            # parse and convert this to the yyyy-mm-dd format:
            date = dateparser.parse(date).strftime("%Y-%m-%d")
        except:
            logging.warning(
                f"parsedate: couldn't parse ${str(date)} for record ${record.find('DFK').text}"
            )
            logging.warning(
                "Data in PHIST looks like an unsalvagable mess, using PY insead!"
            )
            try:
                date = record.find("PY").text
            except:
                logging.warning(
                    f"record ${record.find('DFK').text} has no valid publication date!"
                )
                date = None

    else:
        # print("no date found in PHIST, using PY")
        try:
            date = record.find("PY").text
        except:
            logging.warning(
                f"record ${record.find('DFK').text} has no valid publication date!"
            )
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
            records_bf.set((isbn_print_node, RDF.type, ns.BF.Isbn))
            records_bf.set((isbn_print_node, RDF.value, Literal(isbn_print)))
            records_bf.add((instancebundle_uri, ns.BF.identifiedBy, isbn_print_node))

        if isbn_ebook is not None:
            isbn_ebook_node = URIRef(str(instancebundle_uri) + "#isbn_ebook")
            records_bf.set((isbn_ebook_node, RDF.type, ns.BF.Isbn))
            records_bf.set((isbn_ebook_node, RDF.value, Literal(isbn_ebook)))
            records_bf.add((instancebundle_uri, ns.BF.identifiedBy, isbn_ebook_node))

        # Adding isbns by type to their repsective instance - by mediaCarrier. TODO: Make this actually work!
        # Check all the instances of this work whether they are print or online mediacarrier. If so, add appropriate isbn to them:
        # for instance in records_bf.objects(work_uri, ns.BF.hasInstance):
        #     if isbn_print is not None:
        #         if records_bf.value(instance, RDF.type) == ns.BF.Print:
        #             isbn_print_node = URIRef(str(instance) + "_isbn")
        #             records_bf.set((isbn_print_node, RDF.type, ns.BF.Isbn))
        #             records_bf.set((isbn_print_node, RDF.value, Literal(isbn_print)))
        #             records_bf.add((instance, ns.BF.identifiedBy, isbn_print_node))
        #         else:
        #             print("found no place for print isbn: " + isbn_print)
        #             # try:
        #             #     instance_bundle = records_bf.value(work_uri, PXP.hasInstanceBundle)
        #             #     isbn_print_node = URIRef(str(instance_bundle) + "_isbn")
        #             #     records_bf.set((isbn_print_node, RDF.type, ns.BF.Isbn))
        #             #     records_bf.set(
        #             #         (isbn_print_node, RDF.value, Literal(isbn_print))
        #             #     )
        #             #     records_bf.add((instance_bundle, ns.BF.identifiedBy, isbn_print_node))
        #             # except:
        #             #     print("failed adding print isbn")

        #             # why are they not being added? maybe we should try to add singletons to singleton Instances, at least?

        #     if isbn_ebook is not None:
        #         if records_bf.value(instance, RDF.type) == ns.BF.Electronic:
        #             isbn_ebook_node = URIRef(str(instance) + "_isbn")
        #             records_bf.set((isbn_ebook_node, RDF.type, ns.BF.Isbn))
        #             records_bf.set((isbn_ebook_node, RDF.value, Literal(isbn_ebook)))
        #             records_bf.add((instance, ns.BF.identifiedBy, isbn_ebook_node))
        #         else:
        #             print("found no place for e-issn: " + isbn_ebook)


def get_local_authority_institute(affiliation_string, country):
    """Uses ~~fuzzywuzzy~~ RapidFuzz to look up the affilaition string in a local authority table loaded from a csv file."""
    if country == "LUXEMBOURG":
        best_match = process.extractOne(
            affiliation_string, lux_institutes, scorer=fuzz.token_set_ratio
        )
        return best_match[0].get("uuid")




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
    records_bf.add((instance_uri, ns.BF.provisionActivity, publication_node))
    # make it class bf:Publication:
    records_bf.set((publication_node, RDF.type, ns.BF.Publication))
    if publication_date is not None:
        # add as bf:date (with xsd:date type)
        if len(publication_date) > 4:
            records_bf.add(
                (
                    publication_node,
                    ns.BF.date,
                    Literal(publication_date, datatype=XSD.date),
                )
            )
            # and also just the first 4 characters as simpleDate year:
            records_bf.add(
                (publication_node, ns.BFLC.simpleDate, Literal(publication_date[0:4]))
            )
        else:
            records_bf.add(
                (
                    publication_node,
                    ns.BF.date,
                    Literal(publication_date, datatype=XSD.gYear),
                )
            )
            # and also just the year as simpledate:
            records_bf.add(
                (publication_node, ns.BFLC.simpleDate, Literal(publication_date))
            )

    if pu is not None and pu.text != "":
        pufield = html.unescape(pu.text.strip())
        # get publisher name from subfield v:
        publisher_name = helpers.get_subfield(pufield, "v")
        # get place from subfield o:
        publication_place = helpers.get_subfield(pufield, "o")
        # add the place to the bf:provisionActivity, its not none:
        if publication_place is not None:
            records_bf.add(
                (publication_node, ns.BFLC.simplePlace, Literal(publication_place))
            )
        # add the publisher to the bf:provisionActivity as bflc:simpleAgent:
        if publisher_name is not None:
            records_bf.add(
                (publication_node, ns.BFLC.simpleAgent, Literal(publisher_name))
            )


# ## Semi-generic helper functions


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
    work_language = helpers.get_langtag_from_field(record.find("LA").text.strip())[1]
    work_lang_uri = ns.LANG[work_language]
    return work_lang_uri


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
    records_bf.add((title, RDF.type, ns.BF.Title))

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
        maintitle_language = helpers.get_langtag_from_field(
            record.find("TIL").text.strip()
        )[0]
        # if maintitle_language that is returned the get_langtag_from_field is "und"
        # (because it was a malformed language name), guess the language from the string itself!
        if maintitle_language == "und":
            maintitle_language = helpers.guess_language(maintitle)
    else:  # if there is no TIL field, guess the language from the string itself!
        maintitle_language = helpers.guess_language(maintitle)

    # add the content of TI etc via bf:mainTitle:
    records_bf.add(
        (title, ns.BF.mainTitle, Literal(maintitle, lang=maintitle_language))
    )
    # get content of the TIU field as the subtitle,
    # _if_ it exists and has text in it:
    if record.find("TIU") is not None and record.find("TIU").text != "":
        subtitle = html.unescape(
            mappings.replace_encodings(record.find("TIU").text).strip()
        )  # sanitize encoding and remove extraneous spaces
        # concatenate a full title from main- and subtitle,
        # separated with a : and overwrite fulltitle with that
        fulltitle = fulltitle + ". " + subtitle
        # get language of subtitle - it is in field TIUL, but sometimes that is missing...:
        #  # get language of subtitle:
        if record.find("TIUL") is not None:
            subtitle_language = helpers.get_langtag_from_field(
                record.find("TIUL").text.strip()
            )[0]
            if subtitle_language == "und":
                subtitle_language = helpers.guess_language(subtitle)
        else:  # if there is no TIUL field, guess the language from the string itself!
            subtitle_language = helpers.guess_language(subtitle)

        # add the content of TIU to the bf:Title via bf:subtitle:
        records_bf.add(
            (title, ns.BF.subtitle, Literal(subtitle, lang=subtitle_language))
        )

    # add the concatenated full title to the bf:Title via rdfs:label:
    # (we don't care if the main title's and subtitle's languages don't match - we just set the language of the main title as the full title's language)
    records_bf.add((title, RDFS.label, Literal(fulltitle)))

    # # hang the id source node into the id node:
    # records_bf.add((identifier, ns.BF.source, identifier_source))
    return title


# function for the translated title:
def get_bf_translated_title(resource_uri, record):
    translated_title = URIRef(resource_uri + "#translatedtitle")
    records_bf.add((translated_title, RDF.type, ns.PXC.TranslatedTitle))
    fulltitle = html.unescape(
        mappings.replace_encodings(record.find("TIUE").text).strip()
    )
    fulltitle_language = "de"
    # read subfield |s to get the actual language (it doesn't always exist, though).
    # if fulltitle string ends with "|s " followed by some text (use a regex):
    match = re.search(r"^(.*)\s\|s\s(.*)", fulltitle)
    if match:
        fulltitle = match.group(1).strip()
        fulltitle_language = helpers.get_langtag_from_field(match.group(2).strip())[0]
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
    records_bf.add((titlesource_node, RDF.type, ns.BF.AdminMetadata))
    records_bf.add((titlesource_node, ns.BFLC.metadataLicensor, Literal(titlesource)))

    # add the title string to the node:
    records_bf.add(
        (translated_title, ns.BF.mainTitle, Literal(fulltitle, lang=fulltitle_language))
    )
    records_bf.add((translated_title, RDFS.label, Literal(fulltitle)))
    records_bf.add((translated_title, ns.BF.adminMetadata, titlesource_node))

    return translated_title


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
#         return records_bf.add((work_uri, ns.BF.tableOfContents, Literal(contents)))
#     else:
#         return None
#     # return records_bf.add((work_uri, ns.BF.tableOfContents, Literal("test")))


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


# ## Function: Create nodes for Grants (GRANT)
#
# Includes several helper functions that
# - extract grant numbers if several were listed in the |n subfield
# - replace funder names that fundref usually doesn't match correctly or at all
# - look up funder names in crossref's fundref api to get their fundref id (a doi)

# TODO: refactor the following 5 funding-related functions to a separate module: research_info.py
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
    """This will accept a funder name that the fundref or ror api may not recognize, at least not as the first hit,
    and replace it with a string that will supply the right funder as the first hit"""

    # Remove "program", "programme", or "grant" if they appear at the end of the string
    # funder_name = re.sub(
    #     r"\b(program|programme|grant)\b$", "", funder_name, flags=re.IGNORECASE
    # ).strip()

    # find common substrings (e.g. Horizon 2020) and replace the whole name with
    # a more common name (e.g. European Commission):
    for funder in mappings.funder_names_substr_replacelist:
        if re.search(r"\b" + re.escape(funder[0]) + r"\b", funder_name, re.IGNORECASE):
            funder_name = funder[1]
            # print("replacing " + funder[0] + " with " + funder[1])
            return funder_name

    # find full names and replace the whole name with a more common name:
    for funder in mappings.funder_names_full_replacelist:
        if funder[0].lower() == funder_name.lower():
            funder_name = funder[1]
            # print("replacing " + funder[0] + " with " + funder[1])
            return funder_name
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
        logging.warning("fundref request failed at " + crossref_api_url)
    try:
        crossref_api_response = crossref_api_request.json()
    except:
        logging.warning("fundref response not received for " + crossref_api_url)
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
        logging.error("Error: Missing key in crossref_api_response.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error: Request failed - {e}")
    except Exception as e:
        logging.error(f"Error: {e}")


def get_ror_funder_id(funder_name):
    # gets crossref funder id for a funder name from ROR
    funder_name = replace_common_fundernames(funder_name)
    # funder_name = quote(funder_name)

    # construct the api url:
    # https://api.ror.org/v1/organizations?filter=types:Funder?&affiliation=Deutsche%20Forschungsgemeinschaft%20(DFG)
    ror_api_url = ROR_API_URL + "/v1/organizations?affiliation=" + funder_name

    try:
        ror_api_request = session_ror.get(ror_api_url, timeout=20)
    except:
        logging.warning("ror request failed at " + ror_api_url)
    try:
        ror_api_response = ror_api_request.json()
    except:
        logging.warning("ror response not received for " + ror_api_url)

    funder_id = None

    try:
        if (
            ror_api_request.status_code == 200
            and ror_api_response["number_of_results"] > 0
            and ror_api_response["items"][0]["chosen"] == True
            and ror_api_response["items"][0]["organization"]["external_ids"]["FundRef"]
        ):
            try:
                funder_id = (
                    "10.13039/"
                    + ror_api_response["items"][0]["organization"]["external_ids"][
                        "FundRef"
                    ]["preferred"]
                )

            except:
                logging.warning(f"No preferred FundRef id found for '{funder_name}'")
                try:
                    funder_id = (
                        "10.13039/"
                        + ror_api_response["items"][0]["organization"]["external_ids"][
                            "FundRef"
                        ]["all"][0]
                    )
                except:
                    logging.warning(f"No FundRef id found for '{funder_name}'")
        else:
            logging.warning(f"No funder found for '{funder_name}'")

    except KeyError:
        logging.warning(f"Funder without FundRef info found for '{funder_name}'")
    except Exception as e:
        logging.error(f"Error: {e}")

    return funder_id

def get_bf_grants(work_uri, record):
    """this function takes a string and returns a funder (name and fundref doi),
    a list of grant numbers, a note with grant holder and info"""
    for index, grant in enumerate(record.findall("GRANT")):
        # point zero: remove html entities from the field:
        grantfield = html.unescape(grant.text)
        # if the field contains these, skip it - don't even create a fundinfregerence node:
        if "projekt deal" in grantfield.lower() or "open access" in grantfield.lower():
            continue
        # point one: pipe all text in the field through the DD-Code replacer function:
        grantfield = mappings.replace_encodings(grantfield)
        # add a node for a new Contribution:
        funding_contribution_node = URIRef(
            str(work_uri) + "#fundingreference" + str(index + 1)
        )
        # records_bf.add((funding_contribution_node, RDF.type, ns.BF.Contribution))
        records_bf.add((funding_contribution_node, RDF.type, ns.PXC.FundingReference))
        # add a blank node for the funder agent:
        funder_node = URIRef(str(funding_contribution_node) + "_funder")
        records_bf.add((funder_node, RDF.type, ns.BF.Agent))
        records_bf.add((funder_node, RDF.type, ns.PXC.Funder))
        # add the funder agent node to the funding contribution node:
        records_bf.add((funding_contribution_node, ns.BF.agent, funder_node))
        # add a role to the funding contribution node:
        records_bf.add(
            (
                funding_contribution_node,
                ns.BF.role,
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
            if funder_name == None:
                raise ValueError
        except:
            logging.warning(
                "Could not extract funder name from GRANT field {grantfield} in record {record.find('DFK').text}"
            )
            funder_name = "unknown funder"  # just in case the GRANT field has no content beside the subfields
        # add the funder name to the funder node:
        records_bf.add((funder_node, RDFS.label, Literal(funder_name)))
        # try to look up this funder name in the crossref funder registry:
        # if there is a match, add the crossref funder id as an identifier:
        crossref_funder_id = None
        crossref_funder_id = get_ror_funder_id(funder_name)
        if crossref_funder_id is not None:
            # add a node for the identifier:
            crossref_funder_id_node = URIRef(str(funder_node) + "_funderid")
            # use our custim identifier class FundRefDoi (subclass of bf:Doi):
            records_bf.add((crossref_funder_id_node, RDF.type, ns.PXC.FundRefDoi))
            records_bf.add((funder_node, ns.BF.identifiedBy, crossref_funder_id_node))
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
                records_bf.add((grant_node, RDF.type, ns.PXC.Grant))
                # add the grant node to the funding contribution node:
                records_bf.add((funding_contribution_node, ns.PXP.grant, grant_node))

                # add a blank node for the identifier:
                grant_identifier_node = URIRef(str(grant_node) + "_awardnumber")
                # records_bf.add((grant_identifier_node, RDF.type, ns.BF.Identifier))
                records_bf.add((grant_identifier_node, RDF.type, ns.PXC.GrantId))
                records_bf.add(
                    (grant_identifier_node, RDF.value, Literal(grant_id.strip()))
                )
                # add the identifier node to the grant node:
                records_bf.add((grant_node, ns.BF.identifiedBy, grant_identifier_node))
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
            records_bf.add((funding_info_node, RDF.type, ns.BF.Note))
            records_bf.set((funding_info_node, RDFS.label, Literal(funding_info)))
            records_bf.add((funding_contribution_node, ns.BF.note, funding_info_node))
        # add the funding contribution node to the work node:
        records_bf.add((work_uri, ns.BF.contribution, funding_contribution_node))
        # return funding_contribution_node


# # Function: Add Conference info from field CF. TODO: refactor this to module research_info.py


def get_bf_conferences(work_uri, record):
    # only use conferences from actual books (BE=SS or SM)
    # ignore those in other publication types like journal article
    # get the conference info from the field CF:
    if record.find("BE").text == "SS" or record.find("BE").text == "SM":
        for index, conference in enumerate(record.findall("CF")):
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
                logging.warning(
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
            # a bnode for the contribution/conferencereference:
            conference_reference_node = URIRef(
                str(work_uri) + "#conferencereference" + str(index + 1)
            )
            records_bf.add(
                (conference_reference_node, RDF.type, ns.PXC.ConferenceReference)
            )
            # a blank node for the conference/meeting/agent:
            conference_node = URIRef(str(conference_reference_node) + "_meeting")
            records_bf.add((conference_node, RDF.type, ns.BF.Meeting))
            # records_bf.add((conference_node, RDF.type, PXC.Conference))
            # attach the agent to the contribution/conferencereference:
            records_bf.add((conference_reference_node, ns.BF.agent, conference_node))
            # add the conference name as a label to the agent/meeting node:
            records_bf.add((conference_node, RDFS.label, Literal(conference_name)))
            # add the year as a bflc:simpleDate to the agent/meeting node:
            records_bf.add(
                (conference_node, ns.BFLC.simpleDate, Literal(conference_year))
            )
            # add the place as a bflc:simplePlace to the agent/meeting node:
            records_bf.add(
                (conference_node, ns.BFLC.simplePlace, Literal(conference_place))
            )
            # add the note as a bf:note to the agent/meeting node, first adding a bnode for the bf:Note:
            conference_note_node = URIRef(str(conference_reference_node) + "_note")
            # make it a bf:Note:
            records_bf.add((conference_note_node, RDF.type, ns.BF.Note))
            # add the note to the note node as a literal via rdfs:label:
            records_bf.add((conference_note_node, RDFS.label, Literal(conference_note)))
            # add a bf:role <http://id.loc.gov/vocabulary/relators/ctb> to the ConferenceReference ("contributor" - which is the default for conferences in DNB and LoC):
            records_bf.add(
                (
                    conference_reference_node,
                    ns.BF.role,
                    URIRef("http://id.loc.gov/vocabulary/relators/ctb"),
                )
            )
            # add the note node to the agent/meeting node via bf:note:
            records_bf.add(
                (conference_reference_node, ns.BF.note, conference_note_node)
            )
            # add the conference node to the work node:
            records_bf.add((work_uri, ns.BF.contribution, conference_reference_node))


#### # ----- The Loop! -------------- # ####
# ## Creating the Work and Instance uris and adding other triples via functions
# ## This is the main loop that goes through all the records and creates the triples for the works and instances


def process_record(record):
    """comment this out to run the only 200 records instead of all 700:"""
    # count up the processed records for logging purposes:

    # Get the DFK identifier from the record - we need it for naming our URIs of works, instances and instancebundles:
    # note: actually adding it as an identifier is done below, to the instancebundle.
    dfk = record.find("DFK").text

    # open tsv file, check if dfk is in first row, if not, skip the record:
    with open("xml-data/bad_dfks.tsv", "r") as dfk_list:
        reader = csv.reader(dfk_list, delimiter="\t")
        for row in reader:
            if row[0] == dfk:
                print(f"Skipping record {dfk}: {row[1]}")
                return

    # print("Processing record " + dfk)

    # Create a URI node for the work and  give it the correct bibframe classes:
    # make sure a work_uri will look like this: works:dfk_work, eg works:123456_work
    work_uri = URIRef(ns.WORKS + dfk + "_work")
    records_bf.add((work_uri, RDF.type, ns.BF.Work))
    records_bf.add((work_uri, RDF.type, ns.PXC.MainWork))

    # Add language of work from field LA and add to Work -
    # TODO: second language from <LA2>? no way to distinguish
    # between main/first language and second in bibframe
    records_bf.add((work_uri, ns.BF.language, get_work_language(record)))

    publication_types.generate_content_type(record, dfk, work_uri, records_bf)

    ## Adding Contributions by Persons and Corporate Bodies to the work (only real creators, like editors, authors, translators,
    # not funders or conferences, which are handled below)
    contributions.add_bf_contributor_person(records_bf,work_uri, record)
    # are there any PAUPs left that haven't been successfull matched and added to contributors?
    contributions.match_CS_COU_affiliations_to_first_contribution(records_bf,work_uri, record)
    contributions.match_paups_to_contribution_nodes(records_bf,work_uri, record)
    contributions.match_orcids_to_contribution_nodes(records_bf,work_uri, record)
    contributions.add_bf_contributor_corporate_body(records_bf,work_uri, record)
    contributions.match_email_to_contribution_nodes(records_bf,work_uri, record)

    ## Add dissertation info to the work, if it exists:
    # run research_info.get_thesis_info(work_uri, record, records_bf) and feed the resulting dict into research_info.build_thesis_nodes(work_uri, records_bf, thesis_info)
    thesis_info = research_info.get_thesis_info(record)
    if thesis_info:
        research_info.build_thesis_nodes(work_uri, records_bf, thesis_info)

    # Add the table of contents to the work, if we can extract it from the abstract field (ABH) -   # get_bf_toc(work_uri, record) # this is now done inside the abstract functions - along with abstract license recognition

    # TODO: calculate a bool true/false value from fields to set whether abstract should be made available or not due to copyright reasons.
    abstract_blocked = not abstract.get_abstract_release(record)

    # Adding main/original abstract to the work:
    # note: somehow not all records have one!
    if record.find("ABH") is not None:
        abstract.get_bf_abstract(work_uri, record, abstract_blocked, records_bf)
        # records_bf.add((work_uri, ns.BF.summary, get_bf_abstract(work_uri, record)))
    # d.add((work_uri, ns.BF.summary, get_bf_abstract(work_uri, record), graph_1))

    # Adding secondary abstract to the work - (usually a translation, so also has data about the origin of the abstract):
    # note: somehow not all records have one!
    if record.find("ABN") is not None:
        abstract.get_bf_secondary_abstract(
            work_uri, record, abstract_blocked, records_bf
        )

    ### Adding controlled terms and subject classifications to the work: CT, IT, SH, AGE, PLOC
    # Adding CTs to the work, including skosmos lookup for the concept uris:
    # add_controlled_terms(work_uri, record)
    # i need a counter that will count up for both the CT and IT fields, so i can add the position of the term in the list as a property to the term node:
    term_counter = 0
    # then to count the counter up in each function that adds a term:
    term_counter = terms.add_controlled_terms(
        work_uri, record, records_bf, "CT", "terms", counter=term_counter
    )
    term_counter = terms.add_controlled_terms(
        work_uri, record, records_bf, "IT", "addterms", counter=term_counter
    )

    terms.add_subject_classification(work_uri, record, records_bf, "SH", "class")

    terms.add_age_groups(work_uri, record, records_bf, "AGE", "age")
    terms.add_population_location(work_uri, record, records_bf, "PLOC")

    ## TODO: add any uncontrolled keywords we have:
    # from fields KP - and if they exist, UTE and UTG

    # Adding pxc:FundingReferences from fields <GRANT> to the work:
    get_bf_grants(work_uri, record)

    ## Adding Conferences to the work:
    get_bf_conferences(
        work_uri, record
    )  # adds a bf:contribution >> pxc:ConferenceReference node to the work

    ## Add research data links from fields URLAI and DATAC to the work:
    research_info.get_datac(
        work_uri, record, records_bf
    )  # adds the generated bflc:Relationship node to the work
    # switched off for performance reasons

    research_info.get_urlai(
        work_uri, record, records_bf
    )  # adds the generated bflc:Relationship node to the work

    ### Adding Preregistration links to the work (from field <PREREG>):
    # deactivated due to performance issues and
    # needing a rewrite (replace bnodes with hash-uris),
    # finding a way to frame only "real" main works (1 per star record) in the jsonld,
    # instead of these linked Works, too -> fixed by adding a unique class "MainWork" for root works
    research_info.get_bf_preregistrations(work_uri, record, records_bf)

    # make another round through all the PRREG fields of the record, identifying any trial numbers and adding each as separate pxc:PreregistrationRelationship to the work, including the number as an identifier of the instance, and the ifentified registry as the assigner of the identifier:
    research_info.add_trials_as_preregs(work_uri, record, records_bf)

    ### Add replication relationship nodes from RPLIC field - there is only ever one per work.
    # get the content of the RPLIC field, if it exists:
    replication_info = record.find("RPLIC")
    if replication_info is not None and replication_info.text is not None:
        # get the text content:
        replication_info = replication_info.text.strip()
        # call our function that pulls out dfk, doi (double checking existing
        # ones via crossref, getting missing ones from crossref and double check
        # them), url or citation from
        # subfiels and the main field and which also calls itself the 
        # node generation function
        research_info.get_rplic_replications(work_uri=work_uri, graph=records_bf, rplic_field=replication_info)

    ## ==== RELs and TESTs ==== ##
    # Add the RELs and TESTs from the record to the work:
    research_info.build_rels(record=record, work_uri=work_uri, graph=records_bf)

    ## TODO
    # research_info.build_tests(record=record, work_uri=work_uri, graph=records_bf)

    ## ==== InstanceBundle ==== ##

    # For each work, create one pxc:InstanceBundle node with an uri
    # like this: instancebundles:0123456 (where 0123456 is the dfk of the record):
    # (we migrate each record as an InstanceBundle with 1 or 2 Instances)
    instance_bundle_uri = URIRef(ns.INSTANCEBUNDLES + dfk)
    records_bf.add((instance_bundle_uri, RDF.type, ns.PXC.InstanceBundle))

    ## ==== Instances ==== ##
    # Create the first instance - there will always be at least one:
    instance_uri = URIRef(ns.INSTANCES + dfk + "#1")
    records_bf.add((instance_uri, RDF.type, ns.BF.Instance))

    # connect the instancebundle to the work:
    records_bf.add((work_uri, ns.PXP.hasInstanceBundle, instance_bundle_uri))
    # connect the instance_bundle to the instance:
    records_bf.add((instance_bundle_uri, ns.BF.hasPart, instance_uri))

    # connect work and instance via bf:instanceOf and bf:hasInstance:
    records_bf.add((instance_uri, ns.BF.instanceOf, work_uri))
    records_bf.add((work_uri, ns.BF.hasInstance, instance_uri))

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

    # fetch journal info from the record and add it to the instancebundle:
    (
        journal_title,
        journal_volume,
        journal_issue,
        page_start,
        page_end,
        extent,
        article_no,
        issn,
        eissn,
    ) = instance_sources.fetch_journal_info(record)
    instance_sources.build_journal_relationship(
        instance_bundle_uri,
        records_bf,
        journal_title,
        journal_volume,
        journal_issue,
        page_start,
        page_end,
        article_no,
        issn,
        eissn,
    )

    # fetch book series info from the record and add it to the instancebundle:
    (series_title, series_volume) = instance_sources.fetch_book_series_info(record)
    instance_sources.build_series_relationship(
        instance_bundle_uri, records_bf, series_title, series_volume
    )

    # fetch surrounding book info for chapters from the record and add it to the instancebundle:
    # only do this if BE is US or UR!
    if record.find("BE").text in ["US", "UR"]:
        (book_dfk, book_title, page_start, page_end, extent, article_number) = (
            instance_sources.fetch_surrounding_book_info(record)
        )
        instance_sources.build_book_relationship(
            instance_bundle_uri,
            records_bf,
            book_dfk,
            book_title,
            page_start,
            page_end,
            extent,
            article_number,
        )

    # Add a second instance to the work and instancebundle, if there is a second mediatype in the record:
    if record.find("MT2") is not None:
        instance_uri_2 = URIRef(
            ns.INSTANCES + dfk + "#2"
        )  # create a second instance node:
        records_bf.add(
            (instance_uri_2, RDF.type, ns.BF.Instance)
        )  # give it type/class bf:Instance
        records_bf.add(
            (instance_bundle_uri, ns.BF.hasPart, instance_uri_2)
        )  # connect the instancebundle to the instance
        records_bf.add(
            (instance_uri_2, ns.BF.instanceOf, work_uri)
        )  # connect instance back to work
        records_bf.add(
            (work_uri, ns.BF.hasInstance, instance_uri_2)
        )  # connect work to this instance
        # TODO: add publication date, publisher, place:
        # like this, probably: add_publication_info(instance_uri_2, record, record.find("MT2").text)
        ## Add the mediacarrier node to the instance:
        publication_types.add_mediacarrier_to_instance(
            instance_uri_2, records_bf, record.find("MT2")
        )

    # Add the DFK as an identifier node to the instancebundle:
    identifiers.build_dfk_identifier_node(instance_bundle_uri, dfk, records_bf)

    # Add the issuance type (from BE) to the instancebundle (e.g. "Journal Article" or "Edited Book"):
    publication_types.get_issuance_type(instance_bundle_uri, record, records_bf)

    ## add license to bundle:
    add_instance_license(instance_bundle_uri, record)

    ### Add titles (original and translated) to the instancebundle:

    # Add title from field TI (original title) and associated fields:
    title = get_bf_title(instance_bundle_uri, record)
    records_bf.set((instance_bundle_uri, ns.BF.title, title))

    # Add translated title from TIUE field and associated fields
    # but only if the field exists - which is not always the case, sadly!
    # Not using the same function here as for TI, since translated titles have
    # have many more fields, such as origin etc.
    # There is certainly room for refactoring here!
    if record.find("TIUE") is not None and record.find("TIUE").text != "":
        records_bf.add(
            (
                instance_bundle_uri,
                ns.BF.title,
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
        instances = list(records_bf.objects(instance_bundle_uri, ns.BF.hasPart))
        # if there is only one instance, add the doi, url and urn to that:
        if len(instances) == 1:
            logging.info(
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
            logging.info(
                "several instances found, checking for mediatype before adding doi etc."
            )
            # check if either the first or the second from the list are pxp:mediaCarrier pmt:Online:
            for instance in records_bf.objects(instance_bundle_uri, ns.BF.hasPart):
                # get the mediatype of the instance:
                mediacarrier_type = records_bf.value(instance, ns.PXP.mediaCarrier)
                if mediacarrier_type == ns.PMT.Online:
                    # add doi of the record to the instance:
                    instance_source_ids.get_instance_doi(instance, record, records_bf)
                    # add the url of the record to the instance:
                    instance_source_ids.get_instance_url(instance, record, records_bf)
                    # add the urn of the record to the instance:
                    instance_source_ids.get_instance_urn(instance, record, records_bf)
            #     # if there are two or more, but we can't find any electronic instance among them? That would be an error, but what can be done to still catch it?


records = root.findall("Record")[RECORDS_START:RECORDS_END]
with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:  # Adjust max_workers to limit the number of parallel threads
    futures = [
        executor.submit(process_record, record) for index, record in enumerate(records)
    ]

    for future in tqdm(as_completed(futures), total=len(futures)):
        future.result()  # Wait for each future to complete


# add a Literal for the count of records:
# records_bf.add((URIRef("https://w3id.org/zpid/bibframe/records/"), ns.BF.count, Literal(record_count)))
# and add it to the graph:
# first, add a bnode of class bf:AdminMetadata to the graph:
records_bf_admin_metadata_root = BNode()
records_bf.add((records_bf_admin_metadata_root, RDF.type, ns.BF.AdminMetadata))
# add this bnode to the graph:
records_bf.add(
    (
        URIRef("https://w3id.org/zpid/bibframe/records/"),
        ns.BF.adminMetadata,
        records_bf_admin_metadata_root,
    )
)
# # add a bf:generationProcess to the admin metadata node:
records_bf.add(
    (
        records_bf_admin_metadata_root,
        ns.BF.generationProcess,
        Literal("Converted from STAR XML to BIBFRAME 2.3 using Python/RDFLib"),
    )
)
# # add a bf:generationDate to the admin metadata node:
records_bf.add(
    (
        records_bf_admin_metadata_root,
        ns.BF.generationDate,
        Literal(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
)
# # add the count as ns.BF.count:
# records_bf.add((records_bf_admin_metadata_root, PXP.recordCount, Literal(record_count)))


print(len(records), "records")

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
# records_bf.serialize("ttl-data/bibframe_records.xml", format="pretty-xml")

# print a count the triples we generated:
print(len(records_bf), "triples")
