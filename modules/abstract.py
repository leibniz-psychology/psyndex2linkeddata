import html
import re

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

import modules.helpers as helpers
import modules.mappings as mappings
import modules.namespace as ns

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


def replace_abstract_origin_string(origin_string):
    # if the passed string is in "abstract_origin_original", thenreplace it with "Original":
    if origin_string in mappings.abstract_origin_original:
        return "Original"
    elif origin_string in mappings.abstract_origin_zpid:
        return "ZPID"
    # elif origin_string in mappings.abstract_origin_iwf:
    #     return "IWF"
    elif origin_string in mappings.abstract_origin_deepl:
        return "DeepL"
    elif origin_string in mappings.abstract_origin_gesis:
        return "GESIS"
    elif origin_string in mappings.abstract_origin_fis_bildung:
        return "FIS Bildung"
    elif origin_string in mappings.abstract_origin_krimz:
        return "KrimZ"
    else:
        return origin_string


def add_abstract_licensing_note(abstract, abstracttext, abstract_blocked, graph):
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
        graph.add((abstract_license_node, RDF.type, ns.BF.UsageAndAccessPolicy))
        # add the license type to the node with rdf:value and anyURI:
        if (
            abstract_blocked
        ):  # if it's an elsevier abstract with publisher copyright (blocked from release/sharing), use this specific string to indicate we can't release it, otherwise the string we find at the end:
            graph.add(
                (
                    abstract_license_node,
                    RDFS.label,
                    Literal("Abstract not released by publisher."),
                )
            )
        else:
            graph.add(
                (abstract_license_node, RDFS.label, Literal(abstract_copyright_string))
            )
        # attach it to the abstract node with bf:usageAndAccessPolicy:
        graph.add((abstract, ns.BF.usageAndAccessPolicy, abstract_license_node))
    # also, return the new abstracttext with any copyright string removed:
    return abstracttext.strip()


# function to get the original abstract:
def get_bf_abstract(work_uri, record, abstract_blocked, graph):
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
    graph.add((abstract, RDF.type, ns.PXC.Abstract))
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
        graph.add((toc, RDF.type, ns.BF.TableOfContents))
        # add the bnode to the work via bf:tableOfContents:
        graph.add((work_uri, ns.BF.tableOfContents, toc))
        # add the contents to the abstract node as a bf:tableOfContents:
        # if the contents start with http, extract as url into rdf:value:
        if contents.startswith("http"):
            graph.add((toc, RDF.value, Literal(contents, datatype=XSD.anyURI)))
            # otherwise it's a text toc and needs to go into the label
        else:
            # but we need to determine the language of the toc:
            try:
                toc_language = helpers.guess_language(contents)
            except:
                toc_language = "und"
            graph.add((toc, RDFS.label, Literal(contents, lang=toc_language)))

    # Check for end of abstract that says something about the license "translated by DeepL"
    # and remove them, but add them to the node as a bf:usageAndAccessPolicy:
    # note: I won't remove the useless string saying "no abstract" that is in place of the abstract. It's not worth the effort. Somebody else
    # can do it if they want to - it can be filtered by looking for the "no abstract" concept added to the abstract node.
    # check the abstract for any copyright strings (and "translated by DeepL") and remove them, but add them to the node as a bf:usageAndAccessPolicy:
    abstracttext = add_abstract_licensing_note(
        abstract, abstracttext, abstract_blocked, graph
    )

    # get abstract language from ABLH ("German" or "English")
    abstract_language = "en"  # set default
    # TODO: that's a bad idea, actually. Better: if field is missing, use a language recog function!
    if record.find("ABLH") is not None:
        abstract_language = helpers.get_langtag_from_field(
            record.find("ABLH").text.strip()
        )[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = helpers.guess_language(abstracttext)
    else:  # if the ABLH field is missing, try to recognize the language of the abstract from its text:
        abstract_language = helpers.guess_language(abstracttext)

    # add the text to the node:
    graph.add((abstract, RDFS.label, Literal(abstracttext, lang=abstract_language)))

    # get abstract original source from ASH1 ("Original" or "ZPID")
    abstract_source = "Original"  # default
    # create a blank node for admin metadata:
    abstract_source_node = URIRef(str(abstract) + "_source")
    graph.add((abstract_source_node, RDF.type, ns.BF.AdminMetadata))

    if record.find("ASH1") is not None:
        # overwrite default ("Original") with what we find in ASH1:
        # and while we're at it, replace some known strings with their respective values
        # (e.g. employee tags with "ZPID"):
        abstract_source = replace_abstract_origin_string(
            record.find("ASH1").text.strip()
        )

    # write final source text into source node:
    graph.add(
        (abstract_source_node, ns.BFLC.metadataLicensor, Literal(abstract_source))
    )

    # here is a list of known zpid employee tags, we will use them later to replace these with "ZPID" if found in ASH2:

    # and this is a list of things we want to replace with "Original":

    # get optional agent who edited the original abstract from ASH2
    if record.find("ASH2") is not None:
        # note what we find in ABSH2:
        abstract_editor = replace_abstract_origin_string(
            record.find("ASH2").text.strip()
        )

        graph.add(
            (abstract_source_node, ns.BF.descriptionModifier, Literal(abstract_editor))
        )

    # add the source node to the abstract node:
    graph.add((abstract, ns.BF.adminMetadata, abstract_source_node))
    # and return the completed node:
    # return (abstract)
    # or better, attach it right away:
    graph.add((work_uri, ns.BF.summary, abstract))
    # add a boolean qualifier whether the abstract is "open" - cleared by the publisher to be shared
    graph.add(
        (
            abstract_source_node,
            ns.PXP.blockedAbstract,
            Literal(abstract_blocked, datatype=XSD.boolean),
        )
    )


def get_bf_secondary_abstract(work_uri, record, abstract_blocked, graph):
    ## first check if this is even an abstract at all, or just some text saying "no abstract":
    # if the text is very short (under 100 characters) and contains "no abstract" or "kein Abstract", it's not an abstract:
    if (
        record.find("ABN") is not None
        and len(record.find("ABN").text) < 50
        and re.search(
            r"(no abstract|kein Abstract)", record.find("ABN").text, re.IGNORECASE
        )
    ):
        return None  # don't make a node at all!
    abstract = URIRef(work_uri + "#secondaryabstract")
    # abstract = URIRef(work_uri + "/abstract/secondary")
    graph.add((abstract, RDF.type, ns.PXC.Abstract))
    graph.add((abstract, RDF.type, ns.PXC.SecondaryAbstract))
    abstracttext = html.unescape(
        mappings.replace_encodings(record.find("ABN").text).strip()
    )
    # check if the abstracttext ends with " (translated by DeepL)" or a licensing note,
    # and if so, remove those from the abstract and place them into a UsageandAccessPolicy node.
    abstracttext = add_abstract_licensing_note(
        abstract, abstracttext, abstract_blocked, graph
    )

    abstract_language = "de"  # fallback default

    if record.find("ABLN") is not None and record.find("ABLN").text != "":
        abstract_language = helpers.get_langtag_from_field(
            record.find("ABLN").text.strip()
        )[0]
        if abstract_language == "und":
            # guess language from the text:
            abstract_language = helpers.guess_language(abstracttext)
    else:  # if no language field, guess language from the text:
        abstract_language = helpers.guess_language(abstracttext)

    graph.add((abstract, RDFS.label, Literal(abstracttext, lang=abstract_language)))

    abstract_source_node = URIRef(str(abstract) + "_source")
    graph.add((abstract_source_node, RDF.type, ns.BF.AdminMetadata))
    abstract_source = "Original"  # fallback default
    if record.find("ASN1") is not None:
        # overwrite default ("Original") with what we find in ASH1:
        abstract_source = replace_abstract_origin_string(
            record.find("ASN1").text.strip()
        )

    graph.add(
        (abstract_source_node, ns.BFLC.metadataLicensor, Literal(abstract_source))
    )

    # get optional agent who edited the original abstract from ASH2
    if record.find("ASN2") is not None:
        # note what we find in ABSN2:
        abstract_editor = replace_abstract_origin_string(
            record.find("ASN2").text.strip()
        )
        # and add it via decription modifier:
        graph.add(
            (abstract_source_node, ns.BF.descriptionModifier, Literal(abstract_editor))
        )

    # add the source node to the abstract node:
    graph.add((abstract, ns.BF.adminMetadata, abstract_source_node))
    # and return the completed node:
    # return abstract
    # or better, attach it right away:
    graph.add((work_uri, ns.BF.summary, abstract))
    # add a boolean qualifier whether the abstract is "open" - cleared by the publisher to be shared
    graph.add(
        (
            abstract_source_node,
            ns.PXP.blockedAbstract,
            Literal(abstract_blocked, datatype=XSD.boolean),
        )
    )


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
