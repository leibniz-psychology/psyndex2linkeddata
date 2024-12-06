# ## Function: Create Topics, Weighted Topics from CT
#
# CTs - controlled terms from our own thesaurus - are added like this. Some are always weighted (=more important) and have an added class pxc:WeightedTopic (a subclass of bf:Topic), some are not.
#
# We use the label that is supplied in the CT field to look up the URI of the controlled term in our SKOSMOS API. We also add the preflabels from skosmos here directly.
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


import logging
import re

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


def add_controlled_terms(work_uri, record, records_bf, termtype, vocid, counter):
    # get the controlled terms from the field CT and IT:
    for topic in record.findall(termtype):
        # get the content of the CT field:
        controlled_term_string = mappings.replace_encodings(topic.text.strip())
        # we need to split the string into these possible parts:
        # "|e English Label" for the English label,
        # "|d Deutsches Label" for the German label, and
        # "|g x", which, if it exists, indicates that this Topic is also weighted and should get an additional class (beside bf:Topic) of either "PXC.WeightedTopic"
        # we will use the get_Subfield function, which takes the subfield name as the parameter and returns the content of that subfield if it exists, or None if it doesn't.
        # initialize variables for the controlled term string parts:
        controlled_term_string_english = helpers.get_subfield(
            controlled_term_string, "e"
        )
        controlled_term_string_german = helpers.get_subfield(
            controlled_term_string, "d"
        )
        term_weighting = helpers.get_subfield(controlled_term_string, "g")
        if term_weighting is not None and term_weighting == "x":
            controlled_term_weighted = True
        else:
            controlled_term_weighted = False
        # increment the counter for the controlled terms:
        counter += 1
        # create a blank node for the controlled term and make it a class bf:Topic:
        controlled_term_node = URIRef(str(work_uri) + "#topic" + str(counter))
        # a ct node is a bf:Topic (and a skos:Concept - albeit without a uri identifier, because the CT "code" is not exported, only the labels); sometimes it is also a pxc:WeightedTopic:
        records_bf.add((controlled_term_node, RDF.type, ns.BF.Topic))
        # records_bf.add((controlled_term_node, RDF.type, SKOS.Concept))
        # uncomment for export to real graph (not needed for migration to pxr):
        # add source to the controlled term node (bf:source <https://w3id.org/zpid/vocabs/terms>):
        # records_bf.add(
        #     (
        #         controlled_term_node,
        #         BF.source,
        #         URIRef("https://w3id.org/zpid/vocabs/" + vocid),
        #     )
        # )
        # get uri from lookup in skosmos api:
        try:
            controlled_term_uri = localapi.get_concept_uri_from_skosmos(
                controlled_term_string_english, vocid
            )
        except:
            controlled_term_uri = None
            logging.warning(
                "no uri found in skosmos for Controlled term: "
                + controlled_term_string_english
            )
        if controlled_term_weighted:
            records_bf.add((controlled_term_node, RDF.type, ns.PXC.WeightedTopic))
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
        if controlled_term_uri is not None:
            records_bf.add(
                (controlled_term_node, OWL.sameAs, URIRef(controlled_term_uri))
            )

        # attach the controlled term node to the work node:
        records_bf.add((work_uri, ns.BF.subject, controlled_term_node))
    return counter


def add_subject_classification(work_uri, record, records_bf, termtype, vocid):
    # from fields SH, create a bf:Classification node for each subject heading classification:
    # for now, we only add the uri of the classification, the label, and the code
    heading_counter = 0
    for heading in record.findall(termtype):
        heading_counter += 1
        classification_node = URIRef(
            str(work_uri) + "#subjectheading" + str(heading_counter)
        )
        records_bf.add((classification_node, RDF.type, ns.PXC.SubjectHeading))
        # if it is the first heading, also add the class pxc:SubjectHeadingWeighted:
        if heading_counter == 1:
            records_bf.add(
                (classification_node, RDF.type, ns.PXC.SubjectHeadingWeighted)
            )
        # records_bf.add((classification_node, RDF.type, SKOS.Concept))
        # first, get the code and label from the field:
        # |c 3290 |e Physical &amp; Somatic Disorders |g Körperliche und somatoforme Störungen
        # subfield c is the code, e is the English label, g is the German label
        # get the content of the SH field:
        heading_string = mappings.replace_encodings(heading.text.strip())
        # we need to split the string into these possible parts:
        # "|e English Label" for the English label,
        # "|d Deutsches Label" for the German label (there is no indicator for weighted topics in the SH field)
        # we will use the get_Subfield function, which takes the subfield name as the parameter and returns the content of that subfield if it exists, or None if it doesn't.
        # initialize variables for the controlled term string parts:
        heading_string_english = helpers.get_subfield(heading_string, "e")
        heading_string_german = helpers.get_subfield(heading_string, "g")
        heading_code = helpers.get_subfield(heading_string, "c")

        # records_bf.add(
        #     (
        #         classification_node,
        #         RDFS.label,
        #         Literal(heading_string_english)
        #     )
        # )
        records_bf.add(
            (
                classification_node,
                OWL.sameAs,
                URIRef("https://w3id.org/zpid/vocabs/class/" + heading_code),
            )
        )
        # add source to the classification node (bf:source <https://w3id.org/zpid/vocabs/class>):
        # records_bf.add(
        #     (
        #         classification_node,
        #         BF.source,
        #         URIRef("https://w3id.org/zpid/vocabs/" + vocid),
        #     )
        # )
        # records_bf.add(
        #     (
        #         classification_node,
        #         SKOS.prefLabel,
        #         Literal(heading_string_english, lang="en"),
        #     )
        # )
        # records_bf.add(
        #     (
        #         classification_node,
        #         SKOS.prefLabel,
        #         Literal(heading_string_german, lang="de"),
        #     )
        # )
        records_bf.add((work_uri, ns.BF.classification, classification_node))


def add_age_groups(work_uri, record, records_bf, termtype, vocid):
    # get from field AGE the age groups:
    age_counter = 0
    for age in record.findall(termtype):
        age_counter += 1
        age_string = mappings.replace_encodings(age.text.strip())
        # remove whitespace and lowercase the first word, e.g. "Preschool Age" -> "preschoolAge":
        # first make the first word lowercase,
        # then pick the second word and capitalize it, but only if it exists:
        age_string_list = age_string.split(" ")  # results in a list of words
        if (
            len(age_string_list) > 1
        ):  # if that list has more than one word, capitalize the second word:
            age_camelcased = str(age_string_list[0].lower()) + str(
                age_string_list[1].capitalize()
            )
        else:  # it is only one word, so just lowercase it:
            age_camelcased = str(age_string_list[0].lower())
        # remove whitespace:
        age_camelcased = re.sub(r"\s+", "", age_camelcased)
        age_group_node = URIRef(
            "https://w3id.org/zpid/vocabs/age/" + str(age_camelcased)
        )
        records_bf.add((age_group_node, RDF.type, ns.PXC.AgeGroup))
        # add it to the work node:
        records_bf.add((work_uri, ns.BFLC.demographicGroup, URIRef(age_group_node)))
        # records_bf.add((age_group_node, RDF.type, SKOS.Concept))
        # get the content of the AGE field:
        # the field only ever contains the english label of a controlled term, e.g. "Preschool Age"

        # add source to the age group node (bf:source <https://w3id.org/zpid/vocabs/age>):
        # records_bf.add(
        #     (
        #         age_group_node,
        #         BF.source,
        #         URIRef("https://w3id.org/zpid/vocabs/" + vocid),
        #     )
        # )
        # records_bf.add(
        #     (
        #         age_group_node,
        #         RDFS.label,
        #         Literal(age_string_english)
        #     )
        # )
        # records_bf.add(
        #     (
        #         age_group_node,
        #         SKOS.prefLabel,
        #         Literal(age_string_english, lang="en"),
        #     )
        # )
        # records_bf.add(
        #     (
        #         age_group_node,
        #         SKOS.prefLabel,
        #         Literal(age_string_german, lang="de"),
        #     )
        # )


def add_population_location(work_uri, record, records_bf, termtype):
    # get from field PLOC the population location:
    population_location_counter = 0
