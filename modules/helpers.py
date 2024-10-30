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

# langid.set_languages(["de", "en", "fr", "it", "pl"])


def guess_language(string_in_language):
    return langid.classify(string_in_language)[0]


# ### Getting URLs and DOIs from a field
# Converting http-DOIs to pure ones, checking if what looks like url really is one.
def check_for_url_or_doi(string):
    """checks if the content of the string is a doi or url or something else.
    Returns the a string and a string_type (doi, url, unknown). The given string
    is sanitized, eg. missing http protocol is added for urls; dois are stripped
    of web protocols and domain/subdomains like dx, doi.org).
    Pass any string where you suspect it might be a url or doi,
    returns the cleaned up string (for urls and dois; because STAR messes then up and indexers make mistakes and are inconsistent) and a string type (doi, url, or unknown).
    """
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


def check_issn_format(issn):
    """Checks if the ISSN is in the correct format, returns True or False."""
    # first, strip any spaces from the string and convert to uppercase so the X will be recognized:
    issn = issn.strip().upper()
    # then check for any DD-Codes using the appropriate function:
    issn = html.unescape(mappings.replace_encodings(issn))
    # also remove ^DDS and replace with -
    issn = re.sub(r"\^DDS", "-", issn)
    # check if the ISSN is in the correct format:
    issn_pattern = re.compile(r"^\d{4}-\d{3}[\dxX]$")
    if issn_pattern.match(issn):
        return True, issn
    else:
        # we might fix some more obvious errors here, like missing hyphen (we can add it):
        return False, issn
