# a place for helper functions that extract stuff from subfields etc.

"""extract here:
- def check_for_url_or_doi(string)
- build_doi_identifier_node(instance, doi) - uses a doi returned from check_for_url_or_doi, eg., to build a node
- def build_electronic_locator_node(instance, url) - uses a url returned from check_for_url_or_doi, eg., to build a node 
 that is attached to a resource via bf:electronicLocator
- def build_note_node(instance, note)
- get_langtag_from_field(langfield)
"""
import html
import re
import modules.mappings as mappings


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


# ## Function: Guess language of a given string
# Used for missing language fields or if there are discrepancies between the language field and the language of the title etc.

import langid

langid.set_languages(["de", "en"])


def guess_language(string_in_language):
    return langid.classify(string_in_language)[0]
