""" any functions that define the 'is-ness' of a resource: content type (text, audio?),
    genreForm (Reseach Paper, Thesis, Handbook),
    media and carrier type, both our own combined one and the LC ones,
    issuanceType - our own (Journal Article, Chapter, Edited Book, etc.)
    and the RDA ones (single unit etc.)
"""

import xml.etree.ElementTree as ET
from rdflib import OWL, Literal, URIRef, Namespace, Graph, RDF, RDFS
import modules.helpers as helpers
import modules.local_api_lookups as localapi

BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
WORKS = Namespace("https://w3id.org/zpid/resources/works/")
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
graph.bind("pxc", PXC)
graph.bind("pxp", PXP)
graph.bind("works", WORKS)
graph.bind("contenttypes", CONTENTTYPES)
graph.bind("genres", GENRES)
graph.bind("pmt", PMT)
graph.bind("methods", METHODS)


def generate_content_type(record, dfk, work_node, graph):
    """
    Generate a bf:content type based on the record's different fields.
    """
    content_type_string = work_subclass = ""
    try:
        DT = record.find("DT").text
    except AttributeError:
        DT = None
    try:
        DT2 = record.find("DT2").text
    except AttributeError:
        DT2 = None
    try:
        DT2 = record.find("DT2").text
    except AttributeError:
        DT2 = None
    try:
        MT = record.find("MT").text
    except AttributeError:
        MT = None
    try:
        MT2 = record.find("MT2").text
    except AttributeError:
        MT2 = None
    try:
        MT2 = record.find("MT2").text
    except AttributeError:
        MT2 = None
    try:
        MT2 = record.find("MT2").text
    except AttributeError:
        MT2 = None
    if DT != "40" and DT is not None:
        content_type_string = bf_work_subclass = "Text"  # alle textbasierten DTs
    elif DT is not None and DT != "":  # DT == 40 -> also alle AVs
        # Folien:
        if (DT2 is None or DT2 == "") and (
            MT == "Photographic Slides" or MT2 == "Photographic Slides"
        ):
            content_type_string = bf_work_subclass = "StillImage"
        # Audio (Spoken):
        elif DT2 == 41 or DT2 == "" or DT2 == None:  # 40 & 41 (sound)/leer
            content_type_string = "SpokenWord"
            bf_work_subclass = "NonMusicAudio"
        # Video:
        elif DT2 == 42 or DT2 == "" or DT2 == None:  # 40 & 42 (image)/leer
            content_type_string = bf_work_subclass = "MovingImage"
    # if no DT is given (rare, but bound to happen as an error): just assume text
    elif DT is None and DT2 is None:
        print(f"No DT given in {dfk}, assuming text.")
        content_type_string = bf_work_subclass = "Text"
    # print(content_type_string, bf_work_subclass)
    # create a node for the content type:
    content_type_node = URIRef(CONTENTTYPES[content_type_string.lower()])
    # make it a bf:Content class
    graph.add(
        (
            content_type_node,
            RDF.type,
            BF.Content,
        )
    )
    graph.add(
        (
            work_node,
            BF.content,
            content_type_node,
        )
    )
    # add a secondary class to work, if applicable:
    if bf_work_subclass != "":
        work_subclass_node = URIRef(BF[bf_work_subclass])
        graph.add(
            (
                work_node,
                RDF.type,
                work_subclass_node,
            )
        )


def get_controlled_methods(record, dfk, work_node, instance_bundle_node, graph):
    """
    Get controlled methods from the record field CM and add as a controlled vocab concept.
    """
    try:
        methods = []
        for method in record.findall("CM"):
            method_code = helpers.get_subfield(method.text, "c")
            methods.append(method_code)
    except:
        print(f"No controlled methods found in {dfk}.")
        methods = []
    if methods == []:
        print(f"No controlled methods found in {dfk}. Getting a suggestion from Annif!")
        # get a method suggestion from the Annif API:
        # get the title from instance bundle's bf:title > rdfs:label
        # get all titles, then use the one with class bf:Title, not the one with pxc:Translated Title:
        title_node = graph.value(instance_bundle_node, BF.title, None)
        #  make sure it is not RDF.type pxc:TranslatedTitle:
        if (
            title_node is not None
            and graph.value(title_node, RDF.type, None) != PXC.Title
        ):
            try:
                title = graph.value(title_node, RDFS.label, None)
                print(f"Title found")
            except:
                print("exception: No title found.")
                title = ""
        else:
            title = ""
        # get the abstract from the work:
        abstract_node = graph.value(work_node, BF.summary, None)
        if (
            abstract_node is not None
            and graph.value(abstract_node, RDF.type, None) != PXC.SecondaryAbstract
        ):
            abstract = graph.value(abstract_node, RDFS.label, None)
            print(f"Abstract found!")
        else:
            abstract = ""
            print("No abstract found.")
        # get the uncontrolled keywords from UTE or UTG:

        # concatenate title and abstract:
        text = title + " " + abstract
        # guess the language of the text:
        language = helpers.guess_language(text)
        if language is not None:
            if language == "en":
                # get UTE field:
                try:
                    uncontrolled_keywords = record.find("UTE").text
                except:
                    uncontrolled_keywords = None
            elif language == "de":
                # get UTG field:
                try:
                    uncontrolled_keywords = record.find("UTG").text
                except:
                    uncontrolled_keywords = None
            else:
                uncontrolled_keywords = None
        else:
            uncontrolled_keywords = None
        if uncontrolled_keywords is not None:
            text += " " + uncontrolled_keywords
        # print(f"Trying annif suggest with language: {language} and text: \n{text}")
        # pass the text and language to the Annif API:
        try:
            method_suggestion = localapi.get_annif_method_suggestion(text, language)
            print(f"Method suggestion from Annif: {method_suggestion}")
        except:
            print(f"Could not get a method suggestion from Annif for {dfk}.")
            method_suggestion = None
        # add the method suggestion to the methods list:
        if method_suggestion is not None:
            methods.append(method_suggestion)
    # add a node for each method:
    for index, method_code in enumerate(methods, start=1):
        # method_node = URIRef(METHODS[method_code])
        # make a hashed uri from work:
        method_node = URIRef(work_node + "#studytype" + str(index))
        # give it class pxc:ControlledMethod:
        graph.add(
            (
                method_node,
                RDF.type,
                PXC.ControlledMethod,
            )
        )
        # add the method_code as an owl:sameAs to the node:
        graph.add(
            (
                method_node,
                OWL.sameAs,
                URIRef(METHODS[method_code]),
            )
        )

        # if this is the first method in the list, add a class pxc:ControlledMethodWeighted to the work:
        if index == 1:
            graph.add(
                (
                    method_node,
                    RDF.type,
                    PXC.ControlledMethodWeighted,
                )
            )

        graph.add(
            (
                work_node,
                BF.classification,
                method_node,
            )
        )
        # add labels we got from skosmos:
        #

    # print(f"Methods found in {dfk}: {methods}")


def get_issuance_type(instance_bundle_uri, record, graph):
    # // from field BE
    # from modules.mappings import issuancetypes
    bibliographic_level = record.find("BE").text.strip()
    issuance_uri_fragment = None
    #  for different cases, add different issuance types:
    # TODO: add others that are rarely used, such as for audiovisual media, etc.
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

    # remove spaces from the label to make a CamelCase uri fragment
    issuance_uri_fragment = issuance_type.replace(" ", "")
    try:
        # generate a node for the Issuance:
        issuance_node = URIRef(ISSUANCES + issuance_uri_fragment)
        # class bf:Issuance
        graph.set((issuance_node, RDF.type, PXC.IssuanceType))
        # add it to the instance
        graph.add((instance_bundle_uri, PXP.issuanceType, issuance_node))
        # add a label:
        graph.set((issuance_node, RDFS.label, Literal(issuance_type)))
    except:
        print("record has no valid bibliographic level!")


# function to set mediaCarrier from a mediatype field (MT or MT2):
def generate_new_mediacarrier(mediatype):
    mediatype = mediatype.strip()
    # cases = [
    #     # format: MT/MT2 value, bf:Instance subclass, pxp:mediaCarrier value/uri localname"
    #     ("Print", "Print", "Print"),
    #     ("Online Medium", "Electronic", "Online"),
    #     ("eBook", "Electronic", "Online"),
    #     # add more types here
    # ]
    match mediatype:
        case "Print":
            return "Print", "Print"
        case "Online Medium":
            return "Electronic", "Online"
        case "eBook":
            return "Electronic", "Online"
        case "Optical Disc":
            return "Electronic", "ElectronicDisc"
        case "MagneticTape":
            return None, "TapeCassette"
        case "Film":
            return None, "FilmReelRoll"
        case "Photographic Slides":
            return None, "OverheadTransparency"
        case "Microfiche":
            return "Microform", "Microfiche"
        # what about nachlass? bf:Archival? brauchen wir da auch einen mediaCarrier? unmediated oder unterform manuscript?
        # what about "Schreibmaschinenfassung" in BN/BNDI? That would really be Manuscript, I suppose.
        case _:
            print("no match for " + mediatype)
            return "Print", "Print"
        # TODO: if MT is Print, but BN or BNDI has "Schreibmaschinenfassung", it is actually a manuscript: https://w3id.org/zpid/vocabs/mediacarriers/Manuscript -> go over the graph again later!
        # and what about "Offsetdruck" in BN/BNDI? That would really be Print, I suppose.


def add_mediacarrier_to_instance(instance_node, graph, mediatype_field_object=None):
    # if there is a mediatype (MT or MT2) field in the record, generate a mediaCarrier and add it to the instance
    if mediatype_field_object is not None:
        try:
            instance_subclass, media_carrier_type = generate_new_mediacarrier(
                mediatype_field_object.text
            )
        except:
            instance_subclass, media_carrier_type = None
        if media_carrier_type is not None:
            graph.add(
                (
                    instance_node,
                    PXP.mediaCarrier,
                    URIRef(PMT[media_carrier_type]),
                )
            )
            add_media_and_carrier_rda(instance_node, graph, media_carrier_type)
        if instance_subclass is not None:
            graph.add(
                (
                    instance_node,
                    RDF.type,
                    URIRef(BF[instance_subclass]),
                )
            )


def add_media_and_carrier_rda(instance_node, graph, media_carrier_type):
    # should read an instance and its work and, based on the work's content type
    # and the instance's mediaCarrier,
    # determine the official rda/loc media types and carrier types
    # and add them to the instance using bf:media and bf:carrier
    # and the rda/loc uris
    media_type = None
    carrier_type = None
    match media_carrier_type:
        case "Print":
            media_type = "n"  # unmediated
            carrier_type = "nc"  # volume
        case "Online":
            media_type = "c"  # computer
            carrier_type = "cr"  # online resource
        case "ElectronicDisc":
            # get the work of the instance:
            work_node = graph.value(instance_node, BF.instanceOf, None)
            # get the content type of the work:
            content_type_node = graph.value(work_node, BF.content, None)
            if content_type_node is not None:
                if content_type_node == URIRef(PMT["MovingImage"]):
                    media_type = "v"  # video
                    carrier_type = "vd"  # videodisc
                elif content_type_node == URIRef(PMT["Text"]):
                    media_type = "c"  # computer
                    carrier_type = "cd"  # computer disc
        case "TapeCassette":
            if content_type_node == URIRef(PMT["SpokenWord"]):
                media_type = "s"  # audio
                carrier_type = "ss"  # audiocassette
            elif content_type_node == URIRef(PMT["MovingImage"]):
                media_type = "v"  # video
                carrier_type = "vf"  # videocassette
        case "FilmReelRoll":
            media_type = "v"  # video
            carrier_type = "mr"  # film reel
        case "OverheadTransparency":
            media_type = "g"  # projected
            carrier_type = "gt"  # overhead transparency
        case "Microfiche":
            media_type = "h"  # microform
            carrier_type = "he"  # microfiche
        case _:
            media_type = "z"  # unspecified
            carrier_type = "nc"  # volume
    if media_type is not None:
        graph.add(
            (
                instance_node,
                BF.media,
                URIRef(MEDIA[media_type]),
            )
        )

    if carrier_type is not None:
        graph.add(
            (
                instance_node,
                BF.carrier,
                URIRef(CARRIER[carrier_type]),
            )
        )