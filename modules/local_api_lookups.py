import modules.mappings as mappings
import modules.publication_types as publication_types
import modules.helpers as helpers

import requests
import requests_cache
from datetime import timedelta

ANNIF_API_URL = "https://annif.dev.zpid.org/v1/projects/"

# project names for different languages:
# psyndex-methods-en + /suggest
# psyndex-methods-de + /suggest

SKOSMOS_API_URL = "https://skosmos.dev.zpid.org/rest/v1/"

# annif api caching:
## Caching requests:
urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}
session_annif = requests_cache.CachedSession(
    ".cache/requests_annif",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)
session_skosmos = requests_cache.CachedSession(
    ".cache/requests_skosmos",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)


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
        print(f"Warning: No response from annif!")
        return None
    # return the suggestion
    try:
        return response.json()["results"][0]["notation"]
    except:
        print(f"Could not get a method suggestion from Annif - empty result list.")
        return None
