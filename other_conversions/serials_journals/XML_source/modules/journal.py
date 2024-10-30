from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, Namespace
from rdflib import URIRef
import xml.etree.ElementTree as ET

## Namespaces
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = Namespace("http://id.loc.gov/ontologies/bflc/")

# # bind the namespaces to the graph
# journals_graph.bind("bf", BF)
# journals_graph.bind("bflc", BFLC)


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
        self.__journalcode = 0000
        self.uuid = ""
        self.title = ""

    @property
    def journalcode(self):
        return self.__journalcode

    @journalcode.setter
    def journalcode(self, jtc):
        self.__journalcode = jtc

    def fetch_journalcode(self, record):
        self.journalcode = record.find("JTC").text

    @property
    def uuid(self):
        return self.__uuid

    @uuid.setter
    def uuid(self, uuid):
        self.__uuid = uuid

    def fetch_uuid(self, record, jtc_uuid_lookup):
        # use the journalcode to look up the uuid in the csv file jtc_uui_lookup.csv
        journalcode = self.journalcode(record)
        self.uuid = jtc_uuid_lookup[journalcode]

    def build_journalhub(self, record, journals_graph, jtc_uuid_lookup):
        # build the journalhub rdf
        # make a new node for the journalhub, its uri should be the seriescluster_namespace_prefix + uuid
        # first, fetch the journalcode
        self.fetch_uuid(record, self.journalcode, jtc_uuid_lookup)
        journalhub = URIRef(self.seriescluster_namespace_prefix + self.uuid)
        # add the type of the journalhub
        journals_graph.add((journalhub, RDF.type, BF.Hub))
        # add the type of the journalhub
        journals_graph.add((journalhub, RDF.type, BF.Serial))
        # add the type of the journalhub
        # journals_graph.add((journalhub, RDF.type, BF.Text))

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, title):
        self.__title = title

    def fetch_title(self, title):
        pass  # in field JTTI, guess the langauge
