# a place for helper functions that extract stuff from subfields etc.

"""extract here:
- [x] def check_for_url_or_doi(string)
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
     

# Chatty suggested the following version of the above, which it says is more robust
# against inconsistent spacing (since it uses some regexes) and is also a bit 
# shorter and thus easier to understand. (But it has no comments, so i added some).
# Haven't tested it yet!

# def get_subfield(text, code):
#     # Fast subfield extractor using string split.
#     ## If passed string is empty or does not contain the given subfield code, 
#     ## return None.
#     ## Otherwise, clean up the string and split it into parts:
#     if not text or f"|{code}" not in text:
#         return None
#     ## string cleaning - remove leading/trailing spaces and 
#     ## replace multiple spaces with a single space:
#     text = re.sub(r'\s{2,}', ' ', text.strip())
#     ## Only now, split the string into parts using the 
#     # subfield code as a delimiter:
#     parts = text.split(f"|{code}", 1)
#     ## If the split does not yield at least two parts, return None,
#     # because the subfield was either empty or not found:
#     if len(parts) < 2:
#         return None
#     ## Otherwise, take the second part, split it again 
#     # at the first pipe character, and strip any leading/trailing spaces:
#     value = parts[1].split("|", 1)[0].strip()
#     ## Finally, return the cleaned-up value, using html.unescape
#     ## and mappings.replace_encodings to decode any HTML entities.
#     ## If the value is empty, return None:
#     ## Otherwise, return the cleaned-up value:
#     return html.unescape(mappings.replace_encodings(value)) if value else None



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
def check_for_url_or_doi(original_string):
    """checks if the content of the string is a doi or url or something else.
    Returns the a string and a string_type (doi, url, unknown). The given string
    is sanitized, eg. missing http protocol is added for urls; dois are stripped
    of web protocols and domain/subdomains like dx, doi.org).
    Pass any string where you suspect it might contain a url or doi,
    returns the cleaned up string (for urls and dois; because STAR messes then up and indexers make mistakes and are inconsistent) and a string type (doi, url, or unknown).
    """
    
    string = original_string.strip()  # first, strip any spaces from the string
    

    # use a regex: if string contains "DOI " or "DOI:" or "DOI: " (also case insensitive, so ".doi: " as well), remove that and anything before that and strip again:
    # examples:
    # 'Rütsche, B., Hauser, T. U., Jäncke, L., and Grabner, R. H. (2015). Whenproblem size matters: differential effects of brain stimulation on arithmeticproblem  solving  and  neural  oscillations. PLoS ONE10:e0120665.doi: 10.1371/journal.pone.0120665'
    # note, to do that, we must catch anything that comes before that pattern in a capture group, so we can remove it:
    # doi_error_pattern = re.compile(
    #     r"^(.*)(DOI: |DOI |DOI:)(.*)$", re.IGNORECASE
    # ) 
    # # now drop the first group and the second group, and only keeps the third, the actual doi
    # string = doi_error_pattern.sub(r"\3", string).strip()
    # # string = doi_error_pattern.sub("", string).strip()  # this will remove the doi error pattern, but also anything that came before it

    # examples I want caught, with their results:
    # - 'Rütsche, B., Hauser, T. U., Jäncke, L., and Grabner, R. H. (2015). Whenproblem size matters: differential effects of brain stimulation on arithmeticproblem  solving  and  neural  oscillations. PLoS ONE10:e0120665.doi: 10.1371/journal.pone.0120665' -> 10.1371/journal.pone.0120665
    # - "Daw ND, O^D&gt;'Doherty JP, Dayan P, Seymour B, Dolan RJ. 2006. Cortical substrates for exploratory decisions inhumans.Nature441:876^DDS879.DOI: https://doi.org/10.1038/nature04766,PMID: 16778890" -> 10.1038/nature04766
    doi_error_pattern = re.compile(
        r"^(.*)(DOI: |DOI |DOI:|doi:|doi |doi:)(.*)$", re.IGNORECASE
    )
    # now drop the first group and the second group, and only keeps the third, the actual doi
    string = doi_error_pattern.sub(r"\3", string).strip()
    

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
    # so this will fix urls like "osf. io" to "osf.io", "domain. org" to "domain.org", etc.

    # replace spaces after slashes (when followed by a letter or a digit a question mark, eg "osf.io/ abc"):
    # use this regex: (.*/) ([a-z]) and replace with group1, group2:
    # example: "osf.io/ abc" -> "osf.io/abc", "https:// osf.io/ abc" -> "https://osf.io/abc"
    url_error_pattern3 = re.compile(r"(.*/) ([a-z]|[0-9]|\?)")
    string = url_error_pattern3.sub(r"\1\2", string)
    # this will fix urls like "osf.io/ abc" to "osf.io/abc", "https:// osf.io/ abc" to "https://osf.io/abc", etc.


    # and now spaces before slashes:
    # use this regex: (.*) (/) and replace with group1, group2:
    # example: "https: //", "http://domain.org/blabla /"
    url_error_pattern4 = re.compile(r"(.*) (/)")
    string = url_error_pattern4.sub(r"\1\2", string)
    # this will fix urls like "https: //", "http://domain.org/blabla /" to "https://", "http://domain.org/blabla/"

    # replace single space with underscore,
    # fixing a known STAR bug that replaces underscores with spaces,
    # which is especially bad for urls.  (In other text,
    # we can't really fix it, since usually a space was intended):

    string = re.sub(" ", "_", string)
    # this will fix urls like "osf.io/ab c" to "osf.io/ab_c", right?
    

    # now check for doi or url:
    # this will catch the following doi types:
    # - "10.1371/journal.pone.0120665"
    # - "https://doi.org/10.1371/journal.pone.0120665"
    # - "https://dx.doi.org/10.1371/journal.pone.0120665"
    # - "https://doi.org/10.3758/BF03193932"
    # - "https://link.springer.com/article/10.3758/BF03193932"
    # - "https://onlinelibrary.wiley.com/doi/10.1111/j.1469-8986.2010.01081.x" - modify such that it will also catch the final two:
    doi_pattern = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
    match = doi_pattern.search(string)

    if match: # that is, this looks like a doi
        # keep the matching part (only the canonical doi, not the whole url):
        # example: "https://doi.org/10.1371/journal.pone.0120665" -> "10.1371/journal.pone.0120665"
        # which is the 4th capture group in the regex:
        # string = doi_pattern.search(string).group(4)
        string = match.group()
        # remove any trailing characters, such as a "." or a space or an underscore:
        # example: "10.1371/journal.pone.0120665." -> "10.1371/journal.pone.0120665"
        string = re.sub(r"[. _]*$", "", string)
        string_type = "doi"
        # print("DOI: " + doi)
    # elif string.startswith("10."):
    #     # if the string starts with "10." the whole thing is a DOI:
    #     string_type = "doi"
        # print("DOI: " + doi)
    else: # if it doesn't match the doi pattern, check for a url:
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
            string = original_string.strip()
            # as the value, return the original string:

            # print("Das ist weder eine DOI noch eine URL: " + string)
    return string, string_type
## result: a tuple with the cleaned-up string and the type (doi, url, or unknown), e.g.
# ("10.1234/5678", "doi") or ("http://example.com", "url") or ("some random text", "unknown")


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

def split_family_and_given_name(name):
    """Splits a name into family name and given name.
    Returns a tuple with the family name and given name.
    If the name cannot be split, returns the name as family name and None as given name
    """
    # first, strip any spaces from the name:
    name = name.strip()
    # then, split the name at the first comma:
    parts = name.split(",")
    if len(parts) == 2:  # if there are two parts, the first is the family name, the second is the given name
        family_name = parts[0].strip()
        given_name = parts[1].strip()
        return family_name, given_name
    else:  # if there is no comma or only one part, return the whole name as family name and None as given name
        return name, None