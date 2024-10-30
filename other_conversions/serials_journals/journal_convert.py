import re
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, Namespace
from rdflib import URIRef
import xml.etree.ElementTree as ET
import csv
from datetime import timedelta
import requests_cache

# import helpers module - it contains the guess_language function and can be found one level up in the directory structure
import sys

# add the path to the sys.path list so i can import the helpers module
sys.path.append("../../")
import modules.helpers as helpers
import modules.contributions as contributions

# broken hex codes for special characters in the XML file, use in fixing subtitles and variant titles:
broken_hex_codes = {
    "#e22": "é",
    "#e25": "ë",
    "^DDS": "-",
    "^D%s": "š",
    "^D$e": "€",
    "^Dls": "ș",
}

# lookup for broken issns:
broken_issn_replacements = {
    "2091073-3": None,
    "1873-425": "1873-4251",
    "1479-575": "1479-5752",
    "17511917": "1751-1917",
    "17511925": "1751-1925",
    "1178-166": "1178-1661",
    "90649301": "0269-9702",  # adding pISSN as Lissn field
    "2313-1047/17": "2313-1047",
    "17413176": "1741-3176",
    "19382715": "1938-2715",
    "1338-5283W": "1338-5283",
    "0012^DDS0731": None,
    "2183^DDS2803": "2183-2803",
    "2247^DDS1537": "2247-1537",
    "2247^DDS1537": "2247-1537",  # (eigentlich falsch, da dann die pISSN und eISSN identisch sind)
    "1751-243": "1751-2433",
    "1065-305": "1065-3058",
}

OPENALEX_API_URL = "https://api.openalex.org/"

urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}

session_openalex = requests_cache.CachedSession(
    ".cache/requests_openalex",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

tree = ET.parse("XML_source/journals-241008_101417.xml")
root = tree.getroot()

# a graph for the journal data
journals_graph = Graph()

## Namespaces
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = Namespace("http://id.loc.gov/ontologies/bflc/")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")

# bind the namespaces to the graph
journals_graph.bind("bf", BF)
journals_graph.bind("bflc", BFLC)
journals_graph.bind("pxc", PXC)
journals_graph.bind("pxp", PXP)


# read the csv file jtc_uuid_lookup.csv and make a dictionary to look up the UUID for a journal with a specific JTC code

jtc_uuid_lookup = {}
review_lookup = {}

with open("jtc_uuid_lookup.csv", "r") as file:
    reader = csv.DictReader(file)
    # the file has two columns: JTC and UUID
    # first two lines of the file as an example:
    # JTC, UUID
    # 0001, 38254f3d-aee7-489d-a0c1-5ac86650438a
    # 4745, 0cbaa6ff-276c-4431-992b-0e6f30b7bf65
    # make a data structure to store the jtc-uuid lookup, so i can access the UUID for a journal with a specific JTC code
    # it should look like this:
    # jtc_uuid_lookup = {
    #     "0001": "38254f3d-aee7-489d-a0c1-5ac86650438a",
    #     "4745": "0cbaa6ff-276c-4431-992b-0e6f30b7bf65",
    #     ...
    # }
    # populate the dictionary with the data from the csv file, so i can look up the UUID for a journal with a specific JTC code
    for row in reader:
        # print(row)
        jtc = row["JTC"]
        uuid = row["UUID"]
        jtc_uuid_lookup[jtc] = uuid

with open("review_lookup.csv", "r") as file:
    reader = csv.DictReader(file)
    # the file has two columns: JTC and RV
    # first two lines of the file as an example:
    # JTC, RV
    # 0001, "unknown"
    # 4745, "peerreviewed"
    # make a data structure to store the jtc-review lookup, so i can access the review status for a journal with a specific JTC code
    # it should look like this:
    # review_lookup = {
    #     "0001": "unknown",
    #     "4745": "peerreviewed",
    #     ...
    # }
    # populate the dictionary with the data from the csv file, so i can look up the review status for a journal with a specific JTC code
    for row in reader:
        # print(row)
        jtc = row["JTC"]
        review = row["RV"]
        review_lookup[jtc] = review


class Journal:
    def __init__(self):
        # Variablen vorbelegen, die immer gleich sind:
        self.seriescluster_namespace_prefix = (
            "https://w3id.org/zpid/resources/seriesclusters/"
        )
        self.serial_pubtype = {
            "label_en": "Journal",
            "label_de": "Zeitschrift",
            "uri": "http://id.loc.gov/vocabulary/mserialpubtype/journal",
            "source": "http://id.loc.gov/vocabulary/mserialpubtype/",
        }
        self.hub_types = ["Hub", "Serial", "Text"]
        self.work_types = ["Work", "Serial", "Text"]
        self.content = "http://id.loc.gov/vocabulary/contentTypes/txt"
        self.print_media = "http://id.loc.gov/vocabulary/mediaTypes/n"  # unmediated
        self.online_media = "http://id.loc.gov/vocabulary/mediaTypes/c"  # computer
        self.print_carrier = "http://id.loc.gov/vocabulary/carriers/nc"  # volume
        self.online_carrier = (
            "http://id.loc.gov/vocabulary/carriers/cr"  # online resource
        )
        self.reviewstatus_prefix = "https://w3id.org/zpid/vocabs/reviewstatus/"
        self.__journalcode = "0000"
        self.__uuid = None
        self.__title = None
        self.__subtitle = None
        self.__variant_title = None
        self.__issnL = None
        self.__print_issn = None
        self.__online_issn = None
        self.__lookup_issn = None  # this is the ISSN that will be used to look up the ISSN-L in the OpenAlex API and the zdb id in lobid. It will be the print ISSN, if it exists, otherwise the online ISSN.
        self.__screening_status = None
        self.__screening_note = (
            None  # Rest after "X" in JTAT, to be appended to the note
        )
        self.__review_policy = None  # vocuri from lookup table, based on JTRVK
        self.__review_note = None  # JTRV, to be appended to the note
        self.__access_status = (
            None  # from different fields. Not sure how to handle yet.
        )
        self.__editor_person_list = None
        self.__issuing_body_list = None
        self.__redaktion_person_list = None
        self.__frequency = None  # JTEW, to be appended to the note
        self.__price = None  # JTPR, to be appended to the note
        self.__quality = None  # JTQU, to be appended to the note
        self.__bibliographic_note = None  # will be based on JTBN, but other variables might be appended. If no JTBN exists, but one of the appendable variables, will be created.
        self.__cataloger = None  # from ASHN, just a name for now, will need to be linked to a user id in the future
        self.__media_type_1 = None  # from MT
        self.__media_type_2 = None  # from MT2
        self.__publisher_name = None
        self.__publisher_place = None
        self.__versions = [
            {
                "issn": None,
                "zdbId": None,
                "publisher_name": None,
                "publisher_place": None,
                "media_type": None,
            }
        ]

    @property
    def cataloger(self):
        return self.__cataloger

    @cataloger.setter
    def cataloger(self, cataloger):
        self.__cataloger = cataloger

    def fetch_cataloger(self, record):
        try:
            self.cataloger = record.find("ASHN").text
        except AttributeError:
            self.cataloger = None

    def build_cataloger_node(self, record, journalhub, journals_graph):
        # make a new node for the cataloger of the journal, its uri should be the journalhub uri + "#cataloger"
        # first fetch the cataloger from the record
        self.fetch_cataloger(record)
        if self.cataloger is not None:
            # bf:adminMetadata > bf:AdminMetadata >> bflc:catalogerId "Anita Chasiotis"`
            admin_node = URIRef(str(journalhub) + "#adminmetadata")
            journals_graph.add((admin_node, RDF.type, BF.AdminMetadata))
            # add the metadata to the graph
            journals_graph.add((admin_node, BFLC.catalogerId, Literal(self.cataloger)))
            journals_graph.add((journalhub, BF.adminMetadata, admin_node))
            return admin_node
        else:
            return None

    @property
    def journalcode(self):
        return str(self.__journalcode)

    @journalcode.setter
    def journalcode(self, jtc):
        self.__journalcode = str(jtc)

    def fetch_journalcode(self, record):
        self.journalcode = record.find(
            "JTC"
        ).text  # this sets the journalcode for the instance using the setter, the value after the " = " is the the parameter "jtc" in the setter

    @property
    def uuid(self):
        return self.__uuid

    @uuid.setter
    def uuid(self, uuid):
        self.__uuid = uuid

    def fetch_uuid(self, record, jtc_uuid_lookup):
        # use the fetch_journalcode method to get the journalcode,
        # then use it to look up the uuid in jtc_uui_lookup dictionary
        self.fetch_journalcode(
            record
        )  # this sets the journalcode for the instance using the setter, after fetching it from the record
        try:
            self.uuid = jtc_uuid_lookup[self.journalcode]
        except KeyError:
            print(
                f"Journal code {self.journalcode} not found in the lookup dictionary."
            )

    def build_journalhub(self, record, journals_graph, jtc_uuid_lookup):
        # build the journalhub rdf
        # make a new node for the journalhub, its uri should be the seriescluster_namespace_prefix + uuid
        # first, fetch the uuid from the csv file. The fetch_uuid method will get the journalcode from the record and look up the uuid in the csv file
        self.fetch_uuid(record, jtc_uuid_lookup)  # this
        journalhub = URIRef(self.seriescluster_namespace_prefix + self.uuid)
        # add the type of the journalhub
        journals_graph.add((journalhub, RDF.type, BF.Hub))
        # add the type of the journalhub
        # journals_graph.add((journalhub, RDF.type, BF.Serial))
        # add the type of the journalhub
        # journals_graph.add((journalhub, RDF.type, BF.Text))
        return journalhub

    def build_local_identifier_node(self, journalhub, journals_graph):
        # make a new node for the local identifier of the journal, its uri should be the journalhub uri + "#uuid"
        # first fetch the local identifier from the record
        local_identifier_node = URIRef(str(journalhub) + "#uuid")
        # add the local identifier to the graph
        journals_graph.add((local_identifier_node, RDF.type, BF.Local))
        journals_graph.add((local_identifier_node, RDF.value, Literal(self.uuid)))
        journals_graph.add((journalhub, BF.identifiedBy, local_identifier_node))
        return local_identifier_node

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, title):
        self.__title = self.string_repair(title)

    def string_repair(self, text):
        # check if there are any broken hex codes in the title and replace them with the correct characters
        if text is not None:
            for hex_code in broken_hex_codes:
                text = text.replace(hex_code, broken_hex_codes[hex_code]).strip()
        return text

    def fetch_title(self, record):
        try:
            self.title = record.find("JTTI").text

        except AttributeError:
            self.title = None
            print(
                "No title found for journal "
                + str(self.journalcode)
                + " with UUID "
                + str(self.uuid)
            )

    @property
    def subtitle(self):
        return self.__subtitle

    @subtitle.setter
    def subtitle(self, subtitle):
        # run the subtitle through the title_repair function to replace any broken hex codes
        self.__subtitle = self.string_repair(subtitle)

    def fetch_subtitle(self, record):
        try:
            self.subtitle = record.find("JTUT").text
        except AttributeError:
            self.subtitle = None

    @property
    def variant_title(self):
        return self.__variant_title

    @variant_title.setter
    def variant_title(self, variant_title):
        self.__variant_title = self.string_repair(variant_title)

    def fetch_variant_title(self, record):
        try:
            self.variant_title = record.find("JTPT").text
        except AttributeError:
            self.variant_title = None

    def build_title_node(self, record, journalhub, journals_graph):
        # make a new node for the title of the journal, its uri should be the journalhub uri + "#title"
        # first fetch the title from the record
        self.fetch_title(record)
        self.fetch_subtitle(record)
        # guess language of the title:
        title_language = None
        # since main titles can be too short to reliably guess the language, i will concatenate the main title and the subtitle, if there is one
        if self.title is not None:
            if self.subtitle:
                title_language = helpers.guess_language(
                    self.title + " " + self.subtitle
                )
            else:
                title_language = helpers.guess_language(self.title)

            title_node = URIRef(str(journalhub) + "#title")
            # add the title to the graph
            journals_graph.add((title_node, RDF.type, BF.Title))
            journals_graph.add(
                (title_node, BF.mainTitle, Literal(self.title, lang=title_language))
            )
            if self.subtitle:
                journals_graph.add(
                    (
                        title_node,
                        BF.subtitle,
                        Literal(self.subtitle, lang=title_language),
                    )
                )
                # add a concatenated title to the graph as rdfs:label
                journals_graph.add(
                    (title_node, RDFS.label, Literal(self.title + ": " + self.subtitle))
                )
            else:
                # add only the main title to the graph as rdfs:label
                journals_graph.add((title_node, RDFS.label, Literal(self.title)))
            journals_graph.add((journalhub, BF.title, title_node))
            return title_node
        else:
            # print("No title found for journal" + str(self.journalcode))
            return None

    def build_variant_title_node(self, record, journalhub, journals_graph):
        # make a new node for the variant title of the journal, its uri should be the journalhub uri + "#variant_title"
        # first fetch the variant title from the record
        self.fetch_variant_title(record)
        if self.variant_title is not None:
            # guess language of the variant title:
            try:
                variant_title_language = helpers.guess_language(self.variant_title)
            except:
                variant_title_language = None
            variant_title_node = URIRef(str(journalhub) + "#variant_title")
            # add the variant title to the graph
            journals_graph.add((variant_title_node, RDF.type, BF.VariantTitle))
            journals_graph.add(
                (
                    variant_title_node,
                    BF.mainTitle,
                    Literal(self.variant_title, lang=variant_title_language),
                )
            )
            # add the variant title to the graph as rdfs:label
            journals_graph.add(
                (variant_title_node, RDFS.label, Literal(self.variant_title))
            )
            journals_graph.add((journalhub, BF.title, variant_title_node))
            return variant_title_node
        else:
            return None

    def build_serialpubtype_node(self, journalhub, journals_graph):
        # make a new node for the serial publication type of the journal, its uri should be the journalhub uri + "#serialpubtype"
        serialpubtype_node = URIRef(self.serial_pubtype["uri"])
        # add the serial publication type to the graph
        journals_graph.add((serialpubtype_node, RDF.type, BFLC.SerialPubType))
        journals_graph.add(
            (
                serialpubtype_node,
                RDFS.label,
                Literal(self.serial_pubtype["label_en"], lang="en"),
            )
        )
        journals_graph.add(
            (
                serialpubtype_node,
                RDFS.label,
                Literal(self.serial_pubtype["label_de"], lang="de"),
            )
        )
        journals_graph.add((journalhub, BFLC.serialPubType, serialpubtype_node))
        return serialpubtype_node

    @property
    def issnL(self):
        return self.__issnL

    @issnL.setter
    def issnL(self, issnL):
        # make a sanity check for the ISSN-L, it should be 9 characters long, have a hyphen in the 5th position, and be all numbers; in the second part, there may be an "X" at the end
        # we'll use helpers.check_issn_format to check the format of the ISSN-L
        if issnL is not None:
            # print("Checking ISSN-L format of " + issnL)
            issnL_format_correct = helpers.check_issn_format(issnL)
            if issnL_format_correct[0] is True:
                self.__issnL = issnL_format_correct[1]
            else:
                # run through the cleaned up issn through the replace broken issns function
                replaced_issn = self.replace_broken_issns(issnL_format_correct[1])
                if replaced_issn is not None:
                    self.__issnL = replaced_issn
                else:
                    self.__issnL = None
                    print(
                        "ISSN-L "
                        + str(issnL)
                        + " for journal "
                        + str(self.journalcode)
                        + " is not in the correct format."
                    )
        else:
            self.__issnL = None

    def fetch_issnL(self, record):
        # if it is in the record, use it, otherwise try OpenAlex API
        try:
            self.issnL = record.find("LISSN").text
        except AttributeError:
            # print("No ISSNL in record, trying OpenAlex API")
            self.issnL = None
            self.fetch_lookup_issn(
                record
            )  # will set the lookup_issn to the print or online issn, if one of them exists (preferably print)
            if self.lookup_issn is not None:
                # print(
                #     "Trying to find ISSNL from print or online issn in OpenAlex API... please wait"
                # )
                response = session_openalex.get(
                    OPENALEX_API_URL
                    + "journals/issn:"
                    + self.lookup_issn
                    + "?select=issn_l"
                )
                if response.status_code == 200:
                    # then we have a response, try to get the ISSN-L from the response
                    try:
                        issnl = response.json()["issn_l"]
                        self.issnL = issnl
                    except:
                        print(
                            "OpenAlex API response did not contain an ISSN-L for any of our ISSNs"
                        )
                else:
                    # if both print and online ISSNs exist, we can just use the print issn as the issnL - if all else fails!
                    if self.print_issn is not None and self.online_issn is not None:
                        self.issnL = self.print_issn
                        print(
                            "since both print and online ISSNs exist, using print ISSN as ISSN-L: "
                            + str(self.journalcode)
                        )
                    else:
                        print(
                            "OpenAlex API request failed for journal and no ISSNL or equivalent found in record: "
                            + str(self.journalcode)
                        )

    def build_issnL_node(self, record, journalhub, journals_graph):
        # make a new node for the ISSN-L of the journal, its uri should be the journalhub uri + "#issnL"
        # first fetch the ISSN-L from the record
        self.fetch_issnL(record)
        if self.issnL is not None:
            issnL_node = URIRef(str(journalhub) + "#issnL")
            # add the ISSN-L to the graph
            journals_graph.add((issnL_node, RDF.type, BF.IssnL))
            journals_graph.add((issnL_node, RDF.value, Literal(self.issnL)))
            journals_graph.add((journalhub, BF.identifiedBy, issnL_node))
            return issnL_node
        else:
            return None

    @property
    def print_issn(self):
        return self.__print_issn

    @print_issn.setter
    def print_issn(self, issn):
        # check the format of the print ISSN
        if issn is not None:
            print("Checking print ISSN format of " + issn)
            print_issn_format_correct = helpers.check_issn_format(
                issn
            )  # will return two values, a boolean and a string (a cleaned up version of the issn).
            # if first return value of the check_issn_format function is True, use the second value (a cleaned up ISSN)
            if print_issn_format_correct[0] is True:
                self.__print_issn = print_issn_format_correct[1]
            # if first return value of the check_issn_format function is True, use the second value (a cleaned up ISSN)
            else:
                # run through the cleaned up issn through the replace broken issns function
                replaced_issn = self.replace_broken_issns(print_issn_format_correct[1])
                if replaced_issn is not None:
                    self.__print_issn = replaced_issn
                else:
                    self.__print_issn = None
                    print(
                        "Print ISSN "
                        + str(issn)
                        + " for journal "
                        + str(self.journalcode)
                        + " is not in the correct format."
                    )
        else:
            self.__print_issn = None

    def fetch_print_issn(self, record):
        try:
            self.print_issn = record.find("ISSN").text
            # print(
            #     "Print ISSN found for journal "
            #     + str(self.journalcode)
            #     + ": "
            #     + str(self.print_issn)
            # )
        except AttributeError:
            self.print_issn = None
            # print("No print ISSN found for journal " + str(self.journalcode))

    @property
    def online_issn(self):
        return self.__online_issn

    @online_issn.setter
    def online_issn(self, issn):
        # check the format of the online ISSN
        if issn is not None:  # if a value was passed...
            print("Checking online ISSN format of " + issn)
            online_issn_format_correct = helpers.check_issn_format(issn)
            if online_issn_format_correct[0] is True:
                self.__online_issn = online_issn_format_correct[1]
            else:
                # run through the cleaned up issn through the replace broken issns function
                replaced_issn = self.replace_broken_issns(online_issn_format_correct[1])
                if replaced_issn is not None:
                    self.__online_issn = replaced_issn
                else:
                    self.__online_issn = None
                    print(
                        "Online ISSN "
                        + str(issn)
                        + " for journal "
                        + str(self.journalcode)
                        + " is not in the correct format."
                    )
        else:
            self.__online_issn = None

    def replace_broken_issns(self, issn):
        # check if the ISSN is in the broken_issn_replacements dictionary, if it is, replace it with the value from the dictionary
        if issn in broken_issn_replacements:
            return broken_issn_replacements[issn]
        else:
            return issn

    def fetch_online_issn(self, record):
        try:
            self.online_issn = record.find("EISSN").text
        except AttributeError:
            self.online_issn = None

    def compare_issns(self):
        # compare the print and online ISSNs, if they are the same, print a message
        # what happens: if both are identical, we (usually) have an online journal with no print version! So we should drop the issn completely.
        if self.print_issn is not None and self.online_issn is not None:
            if self.print_issn == self.online_issn:
                print(
                    "Print and online ISSNs are identical for journal "
                    + str(self.journalcode)
                    + ": "
                    + str(self.print_issn)
                )
                # remove the print issn, since there is no print version of that journal!
                self.print_issn = None

    @property
    def lookup_issn(self):
        return self.__lookup_issn

    @lookup_issn.setter
    def lookup_issn(self, lookup_issn):
        self.__lookup_issn = lookup_issn

    def fetch_lookup_issn(self, record):
        # if it is in the record, use it, otherwise try OpenAlex API
        try:
            self.fetch_print_issn(record)
            self.fetch_online_issn(record)
            # compare the print and online ISSNs, if they are the same, do something
            self.compare_issns()
            if self.print_issn is None or self.print_issn == "":
                self.lookup_issn = self.online_issn
                if self.online_issn is None:
                    print("No ISSNs found in record at all: " + str(self.journalcode))
                    return
            else:
                self.lookup_issn = self.print_issn
        except:
            print("No ISSNs found in record at all: " + str(self.journalcode))

    @property
    def screening_status(self):
        return self.__screening_status

    @screening_status.setter
    def screening_status(self, screening_status):
        # process the screening status:
        if screening_status is not None:
            # if starts with X, set to "X"
            if screening_status.startswith("X"):
                self.__screening_status = "X"
                # if anything comes after the X, save to a variable screeningnote: "Erfassungsstatus vor dem Einstellen der Erfassung: " + screeningnote
                self.screening_note = (
                    "Erfassungsstatus vor dem Einstellen der Erfassung: "
                    + screening_status[1:]
                )
            # if equals A, B, or C, set to "A", "B", or "C"
            elif screening_status in ["A", "B", "C"]:
                self.__screening_status = screening_status
            # if equals D (casefolded), set to "C"
            elif screening_status.casefold() == "d":
                self.__screening_status = "C"

    @property
    def screening_note(self):
        return self.__screening_note

    @screening_note.setter
    def screening_note(self, screening_note):
        self.__screening_note = self.string_repair(screening_note)

    def fetch_screening_status(self, record):
        try:
            self.screening_status = record.find("JTAT").text
        except AttributeError:
            self.screening_status = "C"
            # about 45, probably give a status of C
            print(
                "No screening status found for journal "
                + str(self.journalcode)
                + " Title: "
                + str(self.title)
            )

    def build_screeningstatus_node(self, record, journalhub, journals_graph):
        # make a new node for the screening status of the journal, its uri should be the journalhub uri + "#screeningstatus"
        # first fetch the screening status from the record
        self.fetch_screening_status(record)
        if self.screening_status is not None:
            screeningstatus_node = URIRef(
                "https://w3id.org/zpid/vocabs/seriesscreening/" + self.screening_status
            )
            # add the screening status to the graph
            journals_graph.add((screeningstatus_node, RDF.type, BFLC.SeriesAnalysis))
            journals_graph.add((journalhub, BFLC.seriesTreatment, screeningstatus_node))
            return screeningstatus_node
        else:
            return None

    @property
    def review_policy(self):
        return self.__review_policy

    @review_policy.setter
    def review_policy(self, review_policy):
        self.__review_policy = review_policy

    def fetch_review_policy(self, record):
        # if the JTRVK field exists, set the review policy to "peer review" (it is always "Reviewed") in the field
        try:
            if record.find("JTRVK").text == "Reviewed":
                self.review_policy = self.reviewstatus_prefix + "peerreviewed"
        except AttributeError:
            # if the JTRVK field does not exist, check the lookup table for the review status
            try:
                self.review_policy = (
                    self.reviewstatus_prefix + review_lookup[self.journalcode]
                )
            except KeyError:
                # if the JTRVK field does not exist and the journal code is not in the lookup table, set the review policy to "unknown"
                self.review_policy = self.reviewstatus_prefix + "unknown"
                print("No review policy found for journal " + str(self.journalcode))

    def build_review_policy_node(self, record, journalhub, journals_graph):
        # make a new node for the review policy of the journal, its uri should be the journalhub uri + "#reviewpolicy"
        # first fetch the review policy from the record
        self.fetch_review_policy(record)
        if self.review_policy is not None:
            review_policy_node = URIRef(self.review_policy)
            # add a class of PXC:ReviewPolicy
            journals_graph.add((review_policy_node, RDF.type, PXC.ReviewPolicy))
            # add the review policy to the graph
            journals_graph.add((journalhub, PXP.reviewPolicy, review_policy_node))
            return review_policy_node
        else:
            return None

    @property
    def review_note(self):
        return self.__review_note

    @review_note.setter
    def review_note(self, review_note):
        self.__review_note = review_note

    def fetch_review_note(self, record):
        try:
            # there can be multiple JTRV fields, so we need to iterate over them and concatenate them into one string
            review_notes = record.findall("JTRV")
            temp_note = ""
            for note in review_notes:
                temp_note += note.text + "; "
            if temp_note != "":
                self.review_note = temp_note
        except AttributeError:
            self.review_note = None

    @property
    def access_status(self):
        return self.__access_status

    @access_status.setter
    def access_status(self, access_status):
        self.__access_status = access_status

    def fetch_access_status(self, record):
        self.access_status = "unknown"  # TODO: implement this method by analyzing several fields: JTTYP, JTBN, ...
        # should set a value from the vocab https://w3id.org/zpid/vocabs/access/ (unknown, open, hybrid, gold, restricted, subscription, metadataOnly)

    def build_access_status_node(self, record, journalhub, journals_graph):
        # make a new node for the access status of the journal, its uri should be the https://w3id.org/zpid/vocabs/access/ + self.access_status
        # first fetch the access status from the record
        self.fetch_access_status(record)
        if self.access_status is not None:
            access_status_node = URIRef(
                "https://w3id.org/zpid/vocabs/access/" + self.access_status
            )
            # add a class
            journals_graph.add((access_status_node, RDF.type, BF.AccessPolicy))
            # add the access status to the graph
            journals_graph.add(
                (journalhub, BF.usageAndAccessPolicy, access_status_node)
            )
            return access_status_node
        else:
            return None

    # HS - Herausgebende Person
    @property
    def editor_person_list(self):
        return self.__editor_person_list

    @editor_person_list.setter
    def editor_person_list(self, person_list):
        self.__editor_person_list = person_list

    def fetch_editor_person_list(self, record):
        # pass # get from field HS with findall
        try:
            self.editor_person_list = record.findall("HS")
            # role = "ED"
            # print(self.journalcode + " Editors: " + str(self.editor_person_list))
        except AttributeError:
            self.editor_person_list = None
            print("no editors found")

    # KHS - Herausgebende Körperschaft
    @property
    def issuing_body_list(self):
        return self.__issuing_body_list

    @issuing_body_list.setter
    def issuing_body_list(self, person_list):
        self.__issuing_body_list = person_list

    def fetch_issuing_body_list(self, record):
        # get from field KHS with findall
        try:
            self.issuing_body_list = record.findall("KHS")
            role = "ED"
        except AttributeError:
            self.issuing_body_list = None
        # also, add field JTOR to the list, if it exists
        try:
            jtor = record.find("JTOR")
            self.issuing_body_list.append(jtor)
        except AttributeError:
            # leave list as is
            pass

    # RED - Redaktion
    @property
    def redaktion_person_list(self):
        return self.__redaktion_person_list

    @redaktion_person_list.setter
    def redaktion_person_list(self, person_list):
        self.__redaktion_person_list = person_list

    def fetch_redaktion_person_list(self, record):
        # get from field RED with find and split on ";"
        try:
            self.redaktion_person_list = record.find("RED").text.split(";")
            role = "RED"
        except AttributeError:
            self.redaktion_person_list = None

    def build_editor_person_node(self, record, journalhub, journals_graph):
        self.fetch_editor_person_list(record)
        # for each item in list:
        if self.editor_person_list is not None:
            editor_count = 0
            for person in self.editor_person_list:
                editor_count = editor_count + 1
                full_field = person.text
                family_name = helpers.get_mainfield(full_field)
                given_name = helpers.get_subfield(full_field, "v") or ""
                affiliation = helpers.get_subfield(full_field, "i") or ""
                person_name = f"{family_name}, {given_name}".strip(", ")
                if affiliation:
                    person_name += f"; {affiliation}"
                # print("Editor: " + person_name)
                ## make a new node bf:contribution > bf:Contribution
                # >> bf:agent > rdfs:label "Nachname, Vorname or Body name"
                # >> bf:role > </ED> oder </RED>
                # make Contribution node, named #ED + editor_count
                contribution_node = URIRef(str(journalhub) + "#ED_" + str(editor_count))
                journals_graph.add((contribution_node, RDF.type, BF.Contribution))
                journals_graph.add(
                    (
                        contribution_node,
                        BF.role,
                        URIRef("https://w3id.org/zpid/vocabs/roles/ED"),
                    )
                )
                agent_node = URIRef(str(contribution_node) + "_agent")
                # give agent a type of bf:Person
                journals_graph.add((agent_node, RDF.type, BF.Person))
                journals_graph.add((contribution_node, BF.agent, agent_node))
                journals_graph.add((agent_node, RDFS.label, Literal(person_name)))
                # add contribution to journalhub
                journals_graph.add((journalhub, BF.contribution, contribution_node))

    def build_issuing_body_node(self, record, journalhub, journals_graph):
        self.fetch_issuing_body_list(record)
        # for each item in list:
        if self.issuing_body_list is not None:
            isb_count = 0
            for body in self.issuing_body_list:
                isb_count = isb_count + 1
                try:
                    full_field = body.text
                except:
                    if body is not None:
                        full_field = body
                    else:
                        continue
                try:
                    name = helpers.get_mainfield(full_field)
                except:
                    name = full_field
                try:
                    place = helpers.get_subfield(full_field, "o")
                except:
                    place = None
                try:
                    subfields = [
                        helpers.get_subfield(full_field, sub) for sub in ["2", "3"]
                    ]
                except:
                    subfields = None
                subfields = [sub for sub in subfields if sub]  # Filter out None values
                body_name = name
                if subfields:
                    body_name += ", " + ", ".join(subfields)
                if place:
                    body_name += "; " + place
                # print("Editor: " + person_name)
                ## make a new node bf:contribution > bf:Contribution
                # >> bf:agent > rdfs:label "Nachname, Vorname or Body name"
                # >> bf:role > </ED> oder </RED>
                # make Contribution node, named #ED + editor_count
                contribution_node = URIRef(str(journalhub) + "#ISB_" + str(isb_count))
                journals_graph.add((contribution_node, RDF.type, BF.Contribution))
                journals_graph.add(
                    (
                        contribution_node,
                        BF.role,
                        URIRef("http://id.loc.gov/vocabulary/relators/isb"),
                    )
                )
                agent_node = URIRef(str(contribution_node) + "_agent")
                journals_graph.add((contribution_node, BF.agent, agent_node))
                # give agent a type of bf:Organization, since it is always a body
                journals_graph.add((agent_node, RDF.type, BF.Organization))
                # add the name of the body to the agent node
                journals_graph.add((agent_node, RDFS.label, Literal(body_name)))
                # add contribution to journalhub
                journals_graph.add((journalhub, BF.contribution, contribution_node))

    def build_redaktion_person_node(self, record, journalhub, journals_graph):
        self.fetch_redaktion_person_list(record)
        # for each item in list:
        if self.redaktion_person_list is not None:
            red_count = 0
            for person in self.redaktion_person_list:
                red_count = red_count + 1
                contribution_node = URIRef(str(journalhub) + "#RED_" + str(red_count))
                journals_graph.add((contribution_node, RDF.type, BF.Contribution))
                journals_graph.add(
                    (
                        contribution_node,
                        BF.role,
                        URIRef("https://w3id.org/zpid/vocabs/roles/RED"),
                    )
                )
                agent_node = URIRef(str(contribution_node) + "_agent")
                # give agent a type of bf:Person
                journals_graph.add((agent_node, RDF.type, BF.Person))
                journals_graph.add((contribution_node, BF.agent, agent_node))
                journals_graph.add((agent_node, RDFS.label, Literal(person.strip())))
                # add contribution to journalhub
                journals_graph.add((journalhub, BF.contribution, contribution_node))

    @property
    def frequency(self):
        return self.__frequency

    @frequency.setter
    def frequency(self, frequency):
        self.__frequency = frequency

    def fetch_frequency(self, record):
        try:
            self.frequency = record.find("JTEW").text
        except AttributeError:
            self.frequency = None

    @property
    def price(self):
        return self.__price

    @price.setter
    def price(self, price):
        self.__price = price

    def fetch_price(self, record):
        try:
            self.price = record.find("JTPR").text
        except AttributeError:
            self.price = None

    @property
    def quality(self):
        return self.__quality

    @quality.setter
    def quality(self, quality):
        self.__quality = quality

    def fetch_quality(self, record):
        try:
            self.quality = record.find("JTQU").text
        except AttributeError:
            self.quality = None

    @property
    def bibliographic_note(self):
        return self.__bibliographic_note

    @bibliographic_note.setter
    def bibliographic_note(self, bibliographic_note):
        self.__bibliographic_note = self.string_repair(bibliographic_note)

    def fetch_bibliographic_note(self, record):
        try:
            self.bibliographic_note = record.find("JTBN").text
        except AttributeError:
            self.bibliographic_note = None

    def build_bibliographic_note_node(self, record, journalhub, journals_graph):
        # make a new node for the bibliographic note of the journal, its uri should be the journalhub uri + "#note"
        # criteria: if there is a JTBN, use it and append any content from price, quality, frequency, if they exist
        # if there is no JTBN, but there is content in any of price, quality, or frequency, create a note from that content.
        # first fetch the bibliographic note from the record
        self.fetch_bibliographic_note(record)
        self.fetch_price(record)
        self.fetch_quality(record)
        self.fetch_frequency(record)
        self.fetch_review_note(record)
        combined_note = ""
        if self.bibliographic_note is not None:
            combined_note += self.bibliographic_note
        if self.price is not None:
            combined_note += "\n- Preis (JTPR): " + self.price
        if self.quality is not None:
            combined_note += "\n- Qualitätsqualifikation (JTQU): " + self.quality
        if self.frequency is not None:
            combined_note += "\n- Erscheinungsweise (JTEW): " + self.frequency
        if self.review_note is not None:
            combined_note += "\n- Begutachtungsnotiz (JTRV): " + self.review_note
        if self.screening_note is not None:
            combined_note += "\n- (JTAT) " + self.screening_note
        if combined_note != "":
            # first strip any leading or trailing whitespace and linebreaks
            combined_note = combined_note.strip()
            bibliographic_note_node = URIRef(str(journalhub) + "#note")
            # add the bibliographic note to the graph
            journals_graph.add((bibliographic_note_node, RDF.type, BF.Note))
            # add a notetype "internal":
            journals_graph.add(
                (
                    bibliographic_note_node,
                    RDF.type,
                    URIRef("http://id.loc.gov/vocabulary/mnotetype/internal"),
                )
            )
            journals_graph.add(
                (bibliographic_note_node, RDFS.label, Literal(combined_note))
            )
            journals_graph.add((journalhub, BF.note, bibliographic_note_node))
            return bibliographic_note_node
        else:
            return None

    @property
    def media_type_1(self):
        return self.__media_type_1

    @media_type_1.setter
    def media_type_1(self, media_type_1):
        self.__media_type_1 = media_type_1

    def fetch_media_type_1(self, record):
        try:
            self.media_type_1 = record.find("MT").text
        except AttributeError:
            self.media_type_1 = None

    @property
    def media_type_2(self):
        return self.__media_type_2

    @media_type_2.setter
    def media_type_2(self, media_type_2):
        self.__media_type_2 = media_type_2

    def fetch_media_type_2(self, record):
        try:
            self.media_type_2 = record.find("MT2").text
        except AttributeError:
            self.media_type_2 = None

    @property
    def publisher_name(self):
        return self.__publisher_name

    @publisher_name.setter
    def publisher_name(self, name):
        self.__publisher_name = self.string_repair(name)

    @property
    def publisher_place(self):
        return self.__publisher_place

    @publisher_place.setter
    def publisher_place(self, place):
        self.__publisher_place = self.string_repair(place)

    def fetch_publisher(self, record):
        try:
            publisher = record.find("VERL").text
            if publisher is not None:
                try:
                    publisher_name = helpers.get_mainfield(publisher)
                except:
                    publisher_name = None
                try:
                    publisher_imprint = helpers.get_subfield(publisher, "z")
                except:
                    publisher_imprint = None
                if publisher_imprint is not None:
                    publisher_name += " (" + publisher_imprint + ")"
                try:
                    publisher_place = helpers.get_subfield(publisher, "o")
                except:
                    publisher_place = None
                self.publisher_name = publisher_name
                self.publisher_place = publisher_place

        except AttributeError:
            self.publisher_name = None
            self.publisher_place = None

    @property
    def versions(self):
        return self.__versions

    @versions.setter
    def versions(self, versions):
        self.__versions = versions

    def create_versions(self, record):
        self.fetch_print_issn(record)
        self.fetch_online_issn(record)
        self.fetch_media_type_1(record)
        self.fetch_media_type_2(record)
        self.fetch_publisher(record)

        # print(print_issn, online_issn, media_type_1, media_type_2)
        # print(self.print_issn, self.online_issn)

        # set up two versions that we can then add if they exist.
        # one object for each version of the journal
        version_print = {
            "type": "print",
            "issn": self.print_issn,
            "media_type": "https://w3id.org/zpid/vocabs/mediacarriers/Print",
            "bf_media_type": self.print_media,
            "bf_carrier_type": self.print_carrier,
            "publisher_name": self.publisher_name,
            "publisher_place": self.publisher_place,
        }
        version_online = {
            "type": "online",
            "issn": self.online_issn,
            "media_type": "https://w3id.org/zpid/vocabs/mediacarriers/Online",
            "bf_media_type": self.online_media,
            "bf_carrier_type": self.online_carrier,
            "publisher_name": self.publisher_name,
            "publisher_place": self.publisher_place,
        }
        # one complication: sometimes, a journals has both print and online ISSNs, but they are identical. In that case, we only want to add the online version.
        # except: that is sometimes not quite the case. Sometimes we have identical issns, but two different media types. In that case, we want to add both versions.
        if self.print_issn is not None and self.online_issn is not None:  # both exist
            if self.print_issn == self.online_issn:  # but are identical
                if (
                    self.media_type_1 is not None and self.media_type_2 is not None
                ):  # and we have two different media types
                    self.versions = [
                        version_print,
                        version_online,
                    ]  # add both, but know that there is probably an error in one of the ISSNs!
                    print(
                        "Identical ISSNs, but two different media types: "
                        + str(self.journalcode)
                    )
                elif (
                    self.media_type_1 is not None and self.media_type_2 is None
                ):  # but if they are identical and there is only one media type, add only the online version
                    self.versions = [version_online]
            elif (
                self.print_issn != self.online_issn
            ):  # if the ISSNs are different, add both versions
                self.versions = [version_print, version_online]
            else:
                print("Something went wrong with the ISSNs of " + str(self.journalcode))
        # in general, though, we want to add both versions if two different ISSNs exist
        # if only the print ISSN exists, add only the print version, but check if there are still two media types
        elif self.print_issn is not None and self.online_issn is None:
            # if there are two different media types, add both versions, although we don't have issns for each
            if self.media_type_1 is not None and self.media_type_2 is not None:
                self.versions = [version_print, version_online]
            else:  # there is only one media type, so we add only the print version
                self.versions = [version_print]
        # if only the online ISSN exists, add only the online version
        elif self.online_issn is not None and self.print_issn is None:
            # if there are still two different media types, add both versions, although we don't have issns for each
            if self.media_type_1 is not None and self.media_type_2 is not None:
                self.versions = [version_print, version_online]
            else:
                self.versions = [version_online]
        # another snag: sometimes, we have only one issn, but there are two versions (an MT2 exists!)
        # if neither exists, we have a problem
        else:
            print("No ISSNs found for journal " + str(self.journalcode))
            # then we do need to look at the media types. If there is one that is "Print", we add that version. If there is one that is "Online", we add that version.
            # if there are two different media types, we add both versions.
            if self.media_type_1 == "Print" and self.media_type_2 == "Online Medium":
                self.versions = [version_print, version_online]
            elif (
                self.media_type_1 == "Online Medium"
                or self.media_type_1 == "Open Access"
                and self.media_type_2 == "Print"
            ):
                self.versions = [version_online, version_print]
            elif self.media_type_1 == "Print" and self.media_type_2 is None:
                self.versions = [version_print]
            elif (
                self.media_type_1 == "Online Medium"
                or self.media_type_1 == "Open Access"
                and self.media_type_2 is None
            ):
                self.versions = [version_online]
            else:
                print(
                    "No ISSNs and no media types found for journal "
                    + str(self.journalcode)
                )

    def build_versions_nodes(self, journalhub, journals_graph, record):
        self.create_versions(record)
        if self.versions is not None:
            for index, version in enumerate(self.versions):
                version_node = URIRef(str(journalhub) + "#version_" + version["type"])
                # TODO: rename versions from numbered to _print and _online
                journals_graph.add((version_node, RDF.type, BF.Work))
                journals_graph.add((version_node, RDF.type, BF.Serial))
                if version["issn"] is not None:
                    issn_node = URIRef(str(version_node) + "_issn")
                    journals_graph.add((version_node, BF.identifiedBy, issn_node))
                    journals_graph.add((issn_node, RDF.value, Literal(version["issn"])))
                    journals_graph.add((issn_node, RDF.type, BF.Issn))
                # TODO: this should later both be moved to instance (mediacarrier and provisionactivity)
                # add an instance to the work:
                instance_node = URIRef(str(version_node) + "_instance")
                # make it a bf:Instance
                journals_graph.add((instance_node, RDF.type, BF.Instance))
                journals_graph.add((version_node, BF.hasInstance, instance_node))
                journals_graph.add(
                    (instance_node, PXP.mediaCarrier, URIRef(version["media_type"]))
                )
                # add "proper" bf media and carrier types:
                journals_graph.add(
                    (instance_node, BF.media, URIRef(version["bf_media_type"]))
                )
                journals_graph.add(
                    (instance_node, BF.carrier, URIRef(version["bf_carrier_type"]))
                )
                # add publisher:
                if self.publisher_name is not None:
                    publication_statement = None
                    publisher_node = URIRef(str(instance_node) + "_publisher")
                    journals_graph.add(
                        (instance_node, BF.provisionActivity, publisher_node)
                    )
                    journals_graph.add((publisher_node, RDF.type, BF.Publication))
                    journals_graph.add(
                        (publisher_node, BFLC.simpleAgent, Literal(self.publisher_name))
                    )
                    if self.publisher_place is not None:
                        journals_graph.add(
                            (
                                publisher_node,
                                BFLC.simplePlace,
                                Literal(self.publisher_place),
                            )
                        )
                        # also add a literal "bf:publicationStatement" with the publisher name and place
                        publication_statement = (
                            self.publisher_place + ": " + self.publisher_name
                        )
                    else:
                        publication_statement = self.publisher_name
                    journals_graph.add(
                        (
                            instance_node,
                            BF.publicationStatement,
                            Literal(publication_statement),
                        )
                    )
                # add the version to the graph
                journals_graph.add((journalhub, BF.hasExpression, version_node))

    def fetch_open_access_status(self, record):
        # we'll use the API of DOAJ to check if the journal is in the DOAJ
        pass


# new instance of Journal
journal = Journal()

# Gesamtzahl Records: 4.963 (-2, die hier unten ausgeschlossen werden) = 4.961
for record in root.findall("Record"):
    # for record in root.findall("Record")[:1000]:
    # leave out record with JTC 4884, because it has no title
    if record.find("JTC").text == "4884" or record.find("JTC").text == "5033":
        continue

    # use journal.build_journalhub to build the journalhub node for the record and add it to the journals_graph
    journalhub = journal.build_journalhub(record, journals_graph, jtc_uuid_lookup)
    # add the uuid as a Local identifier to the journalhub
    local_identifier = journal.build_local_identifier_node(journalhub, journals_graph)
    # add main title and subtitle to the graph:
    title = journal.build_title_node(record, journalhub, journals_graph)
    # add variant titles to the graph:
    variant_title = journal.build_variant_title_node(record, journalhub, journals_graph)
    # add serial publication type to the graph:
    serialpubtype = journal.build_serialpubtype_node(journalhub, journals_graph)
    # add ISSN-L to the graph:
    issnL = journal.build_issnL_node(record, journalhub, journals_graph)
    # add screening status to the graph:
    screeningstatus = journal.build_screeningstatus_node(
        record, journalhub, journals_graph
    )
    # add review policy/status to the graph:
    review_policy = journal.build_review_policy_node(record, journalhub, journals_graph)

    # add access status to the graph:
    access_status = journal.build_access_status_node(record, journalhub, journals_graph)

    # add all editor persons from HS fields
    editor_persons = journal.build_editor_person_node(
        record, journalhub, journals_graph
    )

    # add all issuing bodies (Herausgebende Körperschaft/Herausgebendes Organ) from KHS field:
    issuing_bodies = journal.build_issuing_body_node(record, journalhub, journals_graph)

    # add all redaktion persons from RED field:
    redaktion_persons = journal.build_redaktion_person_node(
        record, journalhub, journals_graph
    )

    # add bibliographic note to the graph:
    bibliographic_note = journal.build_bibliographic_note_node(
        record, journalhub, journals_graph
    )

    # add cataloger to the graph:
    cataloger = journal.build_cataloger_node(record, journalhub, journals_graph)

    # add versions to the graph:
    versions = journal.build_versions_nodes(journalhub, journals_graph, record)


# serialize the graph
journals_graph.serialize("journals.ttl", format="turtle")
