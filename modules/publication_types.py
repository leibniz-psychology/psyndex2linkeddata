""" any functions that define the 'is-ness' of a resource: content type (text, audio?),
    genreForm (Reseach Paper, Thesis, Handbook),
    media and carrier type, both our own combined one and the LC ones,
    issuanceType - our own (Journal Article, Chapter, Edited Book, etc.)
    and the RDA ones (single unit etc.)
"""

import logging

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, URIRef

import modules.helpers as helpers
import modules.local_api_lookups as localapi
import modules.mappings as mappings
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


def generate_content_type(record, dfk, work_node, graph):
    """
    Generate a bf:content type based on the record's different fields.
    """
    content_type_string = bf_work_subclass = ""
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
        logging.info(f"No DT given in {dfk}, assuming text.")
        content_type_string = bf_work_subclass = "Text"
    # print(content_type_string, bf_work_subclass)
    # create a node for the content type:
    content_type_node = URIRef(ns.CONTENTTYPES[content_type_string.lower()])
    # make it a bf:Content class
    graph.add(
        (
            content_type_node,
            RDF.type,
            ns.BF.Content,
        )
    )
    graph.add(
        (
            work_node,
            ns.BF.content,
            content_type_node,
        )
    )
    # add a secondary class to work, if applicable:
    if bf_work_subclass != "":
        work_subclass_node = URIRef(ns.BF[bf_work_subclass])
        graph.add(
            (
                work_node,
                RDF.type,
                work_subclass_node,
            )
        )


def add_work_studytypes(record, dfk, work_node, instance_bundle_node, graph):
    """
    Reads any CM fields in the record and maps them to a new method, a new genre, or both. In a few cases, also adds new subjects and classifications. Then generates bf:classification and other nodes for the Work based on it. Includes a link to the vocabs/methods/ vocabulary in our Skosmos.

    Args:
        record: the record to read the CM fields from
        dfk: the DFK of the record
        work_node: the work node to add the classification nodes to
        instance_bundle_node: the instance bundle node (which we need to look up the title for works that dont have a cm yet, for sending it to annif and get a cm suggestion)
        graph: the graph to add the nodes to

    """
    try:
        methods = []
        for method in record.findall("CM"):
            method_code = helpers.get_subfield(method.text, "c")
            methods.append(method_code)
    except:
        logging.info(f"No controlled methods found in {dfk}.")
        methods = []
    if methods == []:
        logging.info(
            f"No controlled methods found in {dfk}. Getting a suggestion from Annif!"
        )
        # get a method suggestion from the Annif API:
        # get the title from instance bundle's bf:title > rdfs:label
        # get all titles, then use the one with class bf:Title, not the one with pxc:Translated Title:
        title_node = graph.value(instance_bundle_node, ns.BF.title, None)
        #  make sure it is not RDF.type pxc:TranslatedTitle:
        if (
            title_node is not None
            and graph.value(title_node, RDF.type, None) != ns.PXC.Title
        ):
            try:
                title = graph.value(title_node, RDFS.label, None)
                logging.info(f"Title found")
            except:
                logging.info("exception: No title found.")
                title = ""
        else:
            title = ""
        # get the abstract from the work:
        abstract_node = graph.value(work_node, ns.BF.summary, None)
        if (
            abstract_node is not None
            and graph.value(abstract_node, RDF.type, None) != ns.PXC.SecondaryAbstract
        ):
            abstract = graph.value(abstract_node, RDFS.label, None)
            logging.info(f"Abstract found!")
        else:
            abstract = ""
            logging.info("No abstract found.")
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
            logging.info(f"Method suggestion from Annif: {method_suggestion}")
        except:
            logging.info(f"Could not get a method suggestion from Annif for {dfk}.")
            method_suggestion = None
        # add the method suggestion to the methods list:
        if method_suggestion is not None:
            methods.append(method_suggestion)

    # go through the list of methods and add them to the work (but only if they arent a genre, too):
    method_count = 0
    for method_code in methods:
        # first, look up the code in the mappings.cm_lookup data structure. If it is in there under "old_cm", add any new_cm, new_genre, ct, it to the lists.
        # later, go through the lists and add the new methods and genres to the graph.
        new_methods = []  # # array of methods with keys "cm" and "label"
        new_genres = []
        try:
            # print("checking for " + method_code + " in mappings")
            # check if the method_code is the value of any key "old_cm" in the mappings.cm_lookup list of dicts:
            for cm in mappings.cm_mapping_lookup:
                # print("checking for " + method_code + " in mappings")
                if method_code in cm["old_cm"]:
                    # print("found " + method_code + " in mappings")
                    # if it is, add the new_cm, new_genre, ct, it to the lists:
                    if cm["new_cm"] is not None and cm["new_cm"] != "":
                        # new_methods.append(cm["new_cm"])
                        if cm["new_cm_label"] is not None and cm["new_cm_label"] != "":
                            # make a new dict in the array, and add the new_cm value under the key "cm":
                            # construct a dict:
                            cm_dict = dict(code=cm["new_cm"], label=cm["new_cm_label"])
                        else:
                            cm_dict = dict(code=cm["new_cm"])
                        new_methods.append(cm_dict)
                    if cm["new_genre"] is not None and cm["new_genre"] != "":
                        new_genres.append(cm["new_genre"])
        except:
            logging.info(
                "no new methods or genres found in mappings for " + method_code
            )
        # TODO: clean up the list of methods: only keep the lowest!
        # - if a work already has something starting with "101" (a subtype of experimental), remove "10000"
        # - if it already has something starting with 200[1-9] (subtypes of nonempirical), remove "20000"
        # ALSO: if it already has a 100[0-9] code (empirical and subtypes), remove any "20000" (nonempirical)
        # for method in new_methods:
        #     if method["code"] == "10000" and any(
        #         m["code"].startswith("101") for m in new_methods if m != method
        #     ):
        #         print("removed 10000 from " + work_node)
        #         new_methods.remove(method)
        # elif method["code"] == "20000" and any in new_methods["code"].startswith("")
        # now go through the lists and add the new methods and genres to the graph:
        for method in new_methods:
            method_count += 1
            # method_node = URIRef(METHODS[method_code])
            # make a hashed uri from work:
            method_node = URIRef(work_node + "#controlledmethod" + str(method_count))
            # give it class pxc:ControlledMethod:
            graph.add(
                (
                    method_node,
                    RDF.type,
                    ns.PXC.ControlledMethod,
                )
            )
            # add the method_code as an owl:sameAs to the node:
            graph.add(
                (
                    method_node,
                    OWL.sameAs,
                    URIRef(ns.METHODS[method["code"]]),
                )
            )
            # if there is a label, add that:
            if method["label"] is not None:
                graph.add(
                    (
                        method_node,
                        RDFS.label,
                        Literal(method["label"]),
                    )
                )

            # if this is the first method in the list, add a class pxc:ControlledMethodWeighted to the work:
            if method_count == 1:
                graph.add(
                    (
                        method_node,
                        RDF.type,
                        ns.PXC.ControlledMethodWeighted,
                    )
                )

            graph.add(
                (
                    work_node,
                    ns.BF.classification,
                    method_node,
                )
            )

        ## if both ScholarlyWork AND ResearchPaper are added due to this conversion, only keep the ResearchPaper (the subconcept), since ResearchPaper is a more specific subconcept of ScholarlyWork.
        # So: check if the new_genres List contains both ScholarlyWork and ResearchPaper, and if so, remove ScholarlyWork.

        if "ScholarlyWork" in new_genres and "ResearchPaper" in new_genres:
            logging.info(
                "removed ScholarlyWork genre from ResearchPaper work " + work_node
            )
            new_genres.remove("ScholarlyWork")
        for genre in new_genres:
            genre_node = URIRef(ns.GENRES[genre])
            graph.add(
                (
                    genre_node,
                    RDF.type,
                    ns.BF.GenreForm,
                )
            )
            graph.add(
                (
                    work_node,
                    ns.BF.genreForm,
                    genre_node,
                )
            )
            try:
                german_label = localapi.get_preflabel_from_skosmos(
                    genre_node, "genres", "de"
                ).strip()
                english_label = localapi.get_preflabel_from_skosmos(
                    genre_node, "genres", "en"
                ).strip()
                # add as prefLabel:
                graph.add((genre_node, SKOS.prefLabel, Literal(german_label, "de")))
                graph.add((genre_node, SKOS.prefLabel, Literal(english_label, "en")))
                graph.add((genre_node, RDFS.label, Literal(english_label)))
            except:
                logging.info("no label found for genre " + genre)
                # keeping the genre without label for now


def add_work_genres(work_uri, record, dfk, records_bf):
    """Reads several fields from the record to calculate a genreForm for the work_uri and adds it as a bf:genreForm node. Includes a link to the vocabs/genres/ vocabulary in our Skosmos. Fields considered are: BE, DT, DT2, CM.

    Args:
        work_uri (_type_): The work node to which the genreForm node will be added.
        record (_type_): The record from which the fields will be read.
    """
    # set up a list of genres to add to the work:
    genres = []
    # get the bibliographic level from BE:
    try:
        bibliographic_level = record.find("BE").text.strip()
    except:
        bibliographic_level = ""
    # get the document type from DT:
    try:
        document_type = record.find("DT").text.strip()
    except:
        document_type = ""
    # get the document type 2 from DT2:
    try:
        document_type_2 = record.find("DT2").text.strip()
    except:
        document_type_2 = ""
    try:
        didh = record.find("DIDH").text.strip()
    except:
        didh = ""
    try:
        bibliographic_note = record.find("BN").text.strip()
    except:
        bibliographic_note = ""
    # get an array of all the methods from CM, but only subfield c:
    try:
        methods = record.findall("CM")
        # print("methods: " + str(methods))
        # for each method, get the text, then the c subfield:
        methods = [helpers.get_subfield(method.text, "c") for method in methods]
        # print("methods for record " + record.find("DFK").text + ": " + str(methods))
    except:
        methods = []
        logging.info("no methods found in record " + dfk)

    ## Doctoral Thesis:
    if (
        bibliographic_level == "SH"
        or document_type == "61"
        or document_type_2 == "61"
        or "Diss".casefold() in didh.casefold()
        or "Dissertation".casefold() in bibliographic_note.casefold()
    ):
        if "kumulative".casefold() in bibliographic_note.casefold():
            genres.append("CompilationThesisDoctoral")
        else:
            genres.append("ThesisDoctoral")
    ## Habilitation Thesis:
    elif (
        "habil".casefold() in didh.casefold()
        or "habilitationsschrift".casefold() in bibliographic_note.casefold()
    ):
        if "kumulative".casefold() in bibliographic_note.casefold():
            genres.append("CompilationThesisHabilitation")
        else:
            genres.append("ThesisHabilitation")
    # if any method _starts with_  "|c 10" add "ResearchPaper" to genres
    # remeber it has to start with "|c 10" and not just contain it:
    # or if it is exactly one of the following: 11100 (method. study),12100 (theor. study), 13100 (literature review),13110 (systematic review)
    # if any(notation.startswith("101") for notation in methods) or any(
    #     notation in ["10200", "10300", "13100", "13110"] for notation in methods
    # ):
    #     # but only if it isn't already a thesis:
    #     if "ThesisDoctoral" not in genres and "ThesisHabilitation" not in genres:
    #         genres.append("ResearchPaper")

    # if any are 11200 or 11300 and also bibliographic level is "UZ", also add ResearchPaper:
    # if (
    #     any(notation in ["11200", "11300"] for notation in methods)
    #     and bibliographic_level == "UZ"
    # ):
    #     genres.append("ResearchPaper")

    # for any that are 18650 (workshop) and also have specific DFKs, treat them before, then go through the rest to make them ~~either MeetingReport or~~ CourseMaterial:
    if any(notation in ["18650"] for notation in methods):
        ## Special cases wrongly tagged as "workshop":
        # DFK = 0369284 -> "ConferenceProceedings"
        if "0369284" in dfk:
            genres.append("ConferenceProceedings")
        # DFKs 0262075, 0266517, 0266519, 0273412, 0291044 -> "Talk"
        elif any(dfk in ["0262075", "0266517", "0266519", "0273412", "0291044"]):
            genres.append("Talk")
        elif any(
            # 0307206 "Textbesprechung" - einfach eine Sammlung von Aufsätzen dieser verstorbenen Person -> "PaperCollection"
            "0307206"
            in record.find("DFK").text
        ):
            genres.append("PaperCollection")
        # for any that are 18650 (workshop) and also BE=UZ, UR, US, add "MeetingReport"
        # elif bibliographic_level in [
        #     "UZ",
        #     "UR",
        #     "US",
        # ]:
        #     genres.append("MeetingReport")
        # for any that are 18650 (workshop) and BE=AV, add "CourseMaterial"
        elif bibliographic_level == "AV":
            genres.append("CourseMaterial")

    # for any that are 18650 (workshop) add "CourseMaterial"
    # if any(notation in ["18650"] for notation in methods):
    #     genres.append("CourseMaterial")

    # if this record has a DFK from the following list, add "Bibliography": 0308189, 0179058, 0406548 (Manfred's testverzeichnisse)
    if dfk in ["0308189", "0179058", "0406548"]:
        genres.append("Bibliography")

    # if any method can be found via a search in skosmos, add it to genres as the skosmos concept you found:
    # for notation in methods:
    #     try:
    #         # print("searching for " + notation + " in skosmos")
    #         genre_cm = localapi.search_in_skosmos(notation, "genres")
    #     except:
    #         genre_cm = None
    #         print("failed searching for " + notation + " in skosmos")
    #     if genre_cm is not None:
    #         genres.append(genre_cm)

    # # create node for each genre:
    for genre in genres:
        genre_node = URIRef(ns.GENRES[genre])
        # class bf:GenreForm
        records_bf.set((genre_node, RDF.type, ns.BF.GenreForm))
        # get the label from skosmos:
        try:
            german_label = localapi.get_preflabel_from_skosmos(
                genre_node, "genres", "de"
            ).strip()
            english_label = localapi.get_preflabel_from_skosmos(
                genre_node, "genres", "en"
            ).strip()
            # add as prefLabel:
            records_bf.add((genre_node, SKOS.prefLabel, Literal(german_label, "de")))
            records_bf.add((genre_node, SKOS.prefLabel, Literal(english_label, "en")))
            records_bf.add((genre_node, RDFS.label, Literal(english_label)))
        except:
            logging.info("no label found for genre " + genre)
            # keeping the genre without label for now
        finally:
            # add it to the work:
            records_bf.add((work_uri, ns.BF.genreForm, genre_node))
            # add a label: no need for first migration! Get from skosmos api later.
            # records_bf.set((genre_node, RDFS.label, Literal(genre)))


def clean_up_genres(work_uri, graph):
    # remove any genres:ResearchPaper node when the work already has a variation of genre:Thesis:
    if (
        (
            work_uri,
            ns.BF.genreForm,
            URIRef(ns.GENRES["ThesisDoctoral"]),
        )
        in graph
        or (
            work_uri,
            ns.BF.genreForm,
            URIRef(ns.GENRES["CompilationThesisDoctoral"]),
        )
        in graph
        or (
            work_uri,
            ns.BF.genreForm,
            URIRef(ns.GENRES["ThesisHabilitation"]),
        )
        in graph
        or (
            work_uri,
            ns.BF.genreForm,
            URIRef(ns.GENRES["CompilationThesisHabilitation"]),
        )
        in graph
    ):
        logging.info("we have a thesis!")
        if ((work_uri, ns.BF.genreForm, URIRef(ns.GENRES["ResearchPaper"]))) in graph:
            # print("removed ResearchPaper genre from Thesis work " + work_uri)
            graph.remove(
                (
                    work_uri,
                    ns.BF.genreForm,
                    URIRef(ns.GENRES["ResearchPaper"]),
                )
            )
        if ((work_uri, ns.BF.genreForm, URIRef(ns.GENRES["ScholarlyWork"]))) in graph:
            # print("removed ScholarlyWork genre from Thesis work " + work_uri)
            graph.remove(
                (
                    work_uri,
                    ns.BF.genreForm,
                    URIRef(ns.GENRES["ScholarlyWork"]),
                )
            )
    # also, if both ScholarlyWork AND ResearchPaper exist, only keep the ResearchPaper (the subconcept), since ResearchPaper is a more specific subconcept of ScholarlyWork.
    # if (
    #     work_uri,
    #     BF.genreForm,
    #     URIRef(GENRES["ResearchPaper"]),
    # ) in graph and (
    #     work_uri,
    #     BF.genreForm,
    #     URIRef(GENRES["ScholarlyWork"]),
    # ) in graph:
    #     graph.remove(
    #         (
    #             work_uri,
    #             BF.genreForm,
    #             URIRef(GENRES["ScholarlyWork"]),
    #         )
    #     )
    # generally: if there is already a genre that is a subconcept of another genre, remove the more general one.
    # check this using the skosmos api
    # first, get all genres of the work:
    genres = graph.objects(work_uri, ns.BF.genreForm)
    genre_count = len(list(genres))

    if genre_count > 1:
        logging.info(
            str(work_uri)
            + " has several genres, checking for hierarchy sanity: "
            + str(genre_count)
        )
        # print the genres, iterating through the generator again:
        # print(type(genres))
        # iterate the generator genres:
        genres = graph.objects(work_uri, ns.BF.genreForm)
        # then, for each genre, check if it is a subconcept of another genre:
        for genre in list(genres):
            logging.info(str(genre))
            # get the broaderTransitive of the genre from skosmos:
            try:
                broader = localapi.get_broader_transitive("genres", genre)
                # print("got broaderTransitive for " + str(genre))
            except:
                logging.info("could not get broaderTransitive for " + str(genre))
                broader = None
            if broader is not None:
                # turn the whole thing into a list, but only the content of the "broaderTransitive" key:
                broader_list = list(broader["broaderTransitive"].keys())
                # print(
                #     str(work_uri)
                #     + " genre: "
                #     + str(genre)
                #     + " - broader_list: "
                #     + str(broader_list)
                # )
                # go through this list of broader concepts, but first remove the one that is the same as the genre itself:
                try:
                    # print("removing " + str(genre) + " itself from broader list.")
                    broader_list.remove(str(genre))
                except:
                    pass
                # also remove any top-level concepts from the list (https://w3id.org/zpid/vocabs/genres/InformationalWork, https://w3id.org/zpid/vocabs/genres/InstructionalOrEducationalWork, https://w3id.org/zpid/vocabs/genres/DiscursiveWork, https://w3id.org/zpid/vocabs/genres/WorkCollection, https://w3id.org/zpid/vocabs/genres/WorkCollectionStatic, https://w3id.org/zpid/vocabs/genres/PaperCollection), if they exist:
                top_level_genres = [
                    str(URIRef(ns.GENRES["InformationalWork"])),
                    str(URIRef(ns.GENRES["InstructionalOrEducationalWork"])),
                    str(URIRef(ns.GENRES["DiscursiveWork"])),
                    str(URIRef(ns.GENRES["WorkCollection"])),
                    str(URIRef(ns.GENRES["WorkCollectionStatic"])),
                    str(URIRef(ns.GENRES["PaperCollection"])),
                ]
                try:
                    for top_level_genre in top_level_genres:
                        if top_level_genre in broader_list:
                            # print(
                            #     "removing " + str(top_level_genre) + " from broader list."
                            # )
                            broader_list.remove(top_level_genre)
                    # print("broader_list: " + str(broader_list))
                except:
                    logging.info("could not remove top-level genres from broader list.")

                # then, for each broader concept, check if the work already has any of these broader concepts as a genre:
                for broader_genre in broader_list:
                    # remember that "genres" is a list of uris and broader_genre is just a string, so we need to recast it:
                    broader_genre = URIRef(broader_genre)
                    if broader_genre in graph.objects(work_uri, ns.BF.genreForm):
                        logging.info(
                            str(work_uri)
                            + " has a broader ("
                            + str(broader_genre)
                            + ") that is also in the list of the work's genres."
                        )
                        # if it does, remove the genre from the work:
                        try:
                            graph.remove(
                                (
                                    work_uri,
                                    ns.BF.genreForm,
                                    broader_genre,
                                )
                            )
                            # print("removed " + str(broader_genre) + " from work.")
                        except:
                            logging.info(
                                "could not remove " + str(broader_genre) + " from work."
                            )


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
        issuance_node = URIRef(ns.ISSUANCES + issuance_uri_fragment)
        # class bf:Issuance
        graph.set((issuance_node, RDF.type, ns.PXC.IssuanceType))
        # add it to the instance
        graph.add((instance_bundle_uri, ns.PXP.issuanceType, issuance_node))
        # add a label:
        graph.set((issuance_node, RDFS.label, Literal(issuance_type)))
    except:
        logging.warning("record has no valid bibliographic level!")


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
            logging.info("no match for " + mediatype)
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
                    ns.PXP.mediaCarrier,
                    URIRef(ns.PMT[media_carrier_type]),
                )
            )
            add_media_and_carrier_rda(instance_node, graph, media_carrier_type)
        if instance_subclass is not None:
            graph.add(
                (
                    instance_node,
                    RDF.type,
                    URIRef(ns.BF[instance_subclass]),
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
            work_node = graph.value(instance_node, ns.BF.instanceOf, None)
            # get the content type of the work:
            content_type_node = graph.value(work_node, ns.BF.content, None)
            if content_type_node is not None:
                if content_type_node == URIRef(ns.PMT["MovingImage"]):
                    media_type = "v"  # video
                    carrier_type = "vd"  # videodisc
                elif content_type_node == URIRef(ns.PMT["Text"]):
                    media_type = "c"  # computer
                    carrier_type = "cd"  # computer disc
        case "TapeCassette":
            if content_type_node == URIRef(ns.PMT["SpokenWord"]):
                media_type = "s"  # audio
                carrier_type = "ss"  # audiocassette
            elif content_type_node == URIRef(ns.PMT["MovingImage"]):
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
                ns.BF.media,
                URIRef(ns.MEDIA[media_type]),
            )
        )

    if carrier_type is not None:
        graph.add(
            (
                instance_node,
                ns.BF.carrier,
                URIRef(ns.CARRIER[carrier_type]),
            )
        )
