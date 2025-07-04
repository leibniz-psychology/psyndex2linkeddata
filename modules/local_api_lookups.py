import logging
from datetime import timedelta
import re

import urllib

from modules import mappings
import requests_cache
from decouple import config

ANNIF_API_URL = f"{config('ANNIF_API_URL')}/v1/projects/"

# project names for different languages:
# psyndex-methods-en + /suggest
# psyndex-methods-de + /suggest

# skosmos api url for looking up concepts in CT, SH, and other controlled vocabs:
SKOSMOS_URL = config("SKOSMOS_URL")
SKOSMOS_API_URL = SKOSMOS_URL + "/rest/v1/"
SKOSMOS_USER = config("SKOSMOS_USER")
SKOSMOS_PASSWORD = config("SKOSMOS_PASSWORD")

ROR_API_URL = config("ROR_API_URL")

# annif api caching:
## Caching requests:
urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}
session_annif = requests_cache.CachedSession(
    cache_name="requests_annif",
    backend="redis",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

# cache for skosmos requests:
session_skosmos = requests_cache.CachedSession(
    cache_name="requests_skosmos",
    backend="redis",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

# a cache for ror requests
session_ror = requests_cache.CachedSession(
    cache_name="requests_ror",
    backend="redis",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)

session_skosmos.auth = (SKOSMOS_USER, SKOSMOS_PASSWORD)


def get_annif_method_suggestion(text, language):
    """
    Get a method suggestion from the Annif API.
    Reads the title from the instancebundle, abstract from the work (must already exist as nodes!)
    and the UTE/UTG field from the record.
    Passes them to annif, baesd on language to different backends,
    and returns the first and only suggestion.
    """
    try:
        backend = "psyndex-methods-" + language
    except:
        backend = "psyndex-methods-en"

    payload = {
        "limit": 1,
        # "threshold": 0.2,
        "text": text,
    }
    # get the suggestion from the Annif API
    # print(
    #     f"Getting a method suggestion from Annif via {ANNIF_API_URL + backend + '/suggest'}."
    # )
    try:
        response = session_annif.post(ANNIF_API_URL + backend + "/suggest", payload)
    except:
        logging.warning(f"Warning: No response from annif!")
        return None
    # return the suggestion
    try:
        return response.json()["results"][0]["notation"]
    except:
        logging.warning(
            f"Could not get a method suggestion from Annif - empty result list."
        )
        return None


def get_concept_uri_from_skosmos(concept_label, vocid):
    """Generic function to get the uri of a concept from skosmos by its label. Works with any skosmos vocabulary, if you know the vocid.

    Args:
        concept_label (String): The label of the concept we want to find in the vocabulary
        vocid (String): The short id of the vocabulary in skosmos, e.g. "terms" for the CT vocabulary, "class" for SH, "addterms" for IT, "agegroups" for AGE.

    Returns:
        uri: The skos:Concept uri of the concept.
    """
    # get the uri of a concept from skosmos by its label
    # works with any skosmos vocabulary, if you know the vocid

    skosmos_request = session_skosmos.get(
        SKOSMOS_API_URL + vocid + "/lookup?label=" + concept_label + "&lang=en",
        timeout=20,
    )

    if skosmos_request.status_code == 200:
        skosmos_response = skosmos_request.json()
        if len(skosmos_response["result"]) > 0:
            # print(skosmos_response["result"][0]["uri"])
            return skosmos_response["result"][0]["uri"]
        else:
            logging.warning("no uri found for " + concept_label)
            return None
    else:
        logging.warning("1. skosmos request failed for " + concept_label)
        return None


def get_preflabel_from_skosmos(uri, vocid, lang="de"):
    """Get the preferred label of a concept from skosmos by its uri. Needs a vocid and the language you want the label in. Works with any skosmos vocabulary, if you know the vocid.

    Args:
        uri (String): The uri of the concept we want to find in the vocabulary
        vocid (String): The short id of the vocabulary in skosmos, e.g. "terms" for the CT vocabulary, "class" for SH, "addterms" for IT, "agegroups" for AGE.
        lang (String, optional): The language of the label we want to get. Defaults to "de".


    Returns:
        String: The preferred label of the concept.
    """

    skosmos_request = session_skosmos.get(
        SKOSMOS_API_URL + "label?uri=" + uri + "&lang=" + lang, timeout=20
    )

    if skosmos_request.status_code == 200:
        skosmos_response = skosmos_request.json()
        if len(skosmos_response) > 0:
            # print(skosmos_response["labels"][0]["label"])
            return skosmos_response["prefLabel"]
        else:
            logging.info("no label found for " + uri)
            return None
    else:
        logging.warning("2. skosmos request failed for " + str(uri))
        return None


def search_in_skosmos(search_term, vocid):
    """Search for a term in a skosmos vocabulary and return the first hit as a skos:Concept uri (localname)."""
    query = SKOSMOS_API_URL + vocid + "/search?query=" + search_term + "&maxhits=1"
    # print("searching " + query)
    skosmos_request = session_skosmos.get(
        query,
        timeout=20,
    )
    # print(skosmos_request.status_code)
    if skosmos_request.status_code == 200:
        skosmos_response = skosmos_request.json()
        if len(skosmos_response["results"]) > 0:
            return skosmos_response["results"][0]["localname"]
        else:
            # print("no concept found for " + search_term)
            return None
    else:
        logging.warning("3. skosmos request failed for " + search_term)
        return None


def get_broader_transitive(vocid, concept_uri):
    """Get the broader transitive relations from skosmos for the CT vocabulary."""
    query = SKOSMOS_API_URL + "/" + vocid + "/" + "broaderTransitive?uri=" + concept_uri
    skosmos_request = session_skosmos.get(
        query,
        timeout=20,
    )
    if skosmos_request.status_code == 200:
        skosmos_response = skosmos_request.json()
        return skosmos_response
    else:
        logging.warning("4. skosmos request failed for broaderTransitive")
        return None

def get_ror_id_from_api(orgname_string):
    # this function takes a string with an organization name (e.g. from affiliations) and returns the ror id for that org from the ror api

    # but first, find some common substrings from names that ror can't find with those it will find:
    for affiliation in mappings.affilation_org_substr_replacelist:
        if re.search(r"\b" + re.escape(affiliation[0]) + r"\b", orgname_string, re.IGNORECASE):
            orgname_string = affiliation[1]
            # print("replacing " + funder[0] + " with " + funder[1])
            # do not return here; continue to query the ROR API with the modified orgname_string
    # make a request to the ror api:
    encoded_orgname = urllib.parse.quote_plus(orgname_string)
    ror_api_url = f"{ROR_API_URL}/v1/organizations?affiliation={encoded_orgname}"
    # ror_api_request = requests.get(ror_api_url)
    # make request to api with caching:
    ror_api_request = session_ror.get(ror_api_url, timeout=20)
    # if the request was successful, get the json response:
    if ror_api_request.status_code == 200:
        ror_api_response = ror_api_request.json()
        if "items" in ror_api_response and len(ror_api_response["items"]) > 0:
            for item in ror_api_response["items"]:
                # check if the item has a "chosen" key and if it is True, or if not, but score is 1.0:
                if item.get("chosen") == True or (item.get("score") == 1.0):
                    found_chosen = True
                    try:
                        return item["organization"]["id"]
                    except KeyError:
                        logging.warning(f"Missing 'organization' or 'id' key in ROR API response item: {item}")
                        return None
            return None
        else:
            logging.info(f"ROR API returned status code {ror_api_request.status_code} for URL: {ror_api_url}")
            return None
        
def get_ror_org_country(affiliation_ror_id):
    """
    Given a ROR ID, retrieve the country of the organization from the ROR API.

    Args:
        affiliation_ror_id (str): The ROR ID of the organization.

    Returns:
        str or None: The country name of the organization, or None if not found.
    """
    # given a ror id, get the country of the organization from the ror api:
    # first, use only the last part of the ror id, which is the id itself:
    if not isinstance(affiliation_ror_id, str):
        raise TypeError("affiliation_ror_id must be a string")
    if not affiliation_ror_id:
        logging.warning("Empty affiliation_ror_id provided.")
        return None
    try:
        affiliation_ror_id = affiliation_ror_id.rstrip("/").split("/")[-1]
    except ValueError as e:
        logging.warning("affiliation_ror_id does not contain a valid ID segment.")
        return None
    # the country name is in country.name in the json response

    ror_request = session_ror.get(
        f"{ROR_API_URL}/v1/organizations/" + affiliation_ror_id,
        timeout=20,
    )
    if ror_request.status_code == 200:
        ror_response = ror_request.json()
        # The country name is typically at ror_response["country"]["country_name"]
        if "country" in ror_response and "country_name" in ror_response["country"]:
            return ror_response["country"]["country_name"]
        else:
            logging.info("no country or country_name found for " + affiliation_ror_id)
            return None
    else:
        logging.warning(f"ROR API returned status code {ror_request.status_code} for ID: {affiliation_ror_id}")
        return None