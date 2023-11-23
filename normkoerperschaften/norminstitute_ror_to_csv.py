# %%
# import modules

# import the module "mappings" from the directory above:
import sys

sys.path.append("../modules")  # Add the "modules" directory to the sys.path

import mappings
import requests_cache
from datetime import timedelta

import csv


# ror lookup
ROR_API_URL = "https://api.ror.org/organizations?affiliation="

urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}
# using cache for ror requests
session = requests_cache.CachedSession(
    ".cache/requests",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)


def get_ror_data_from_api(affiliation_string):
    # this function takes a string with an affiliation name and returns the ror data for that affiliation from the ror api (including the ror id and the name of the organization)

    ror_api_url = ROR_API_URL + affiliation_string
    # make request to api with caching:
    ror_api_request = session.get(ror_api_url, timeout=20)
    # if the request was successful, get the json response:
    if ror_api_request.status_code == 200:
        ror_api_response = ror_api_request.json()
        # check if the response has any hits:
        if len(ror_api_response["items"]) > 0:
            # if so, get the item with a key value pair of "chosen" and "true" and return its id:
            for item in ror_api_response["items"]:
                if item["chosen"] == True:
                    # print(item["organization"]["name"],":",item["organization"]["id"])
                    # return both id and name:
                    return item["organization"]["id"], item["organization"]["name"]
        # if there were no hits, return None:
        else:
            return None
    # if the request was not successful, return None:
    else:
        return None


# open csv file, read column "Cluster" and look up ror the ror entry for each entry, then make a new csv file "lux_with_ror.csv" that is a copy of the old one, but with added column "ror_id":

filename = sys.argv[1]  # Get the filename from command-line argument

with open(filename, newline="") as csvfile:
    lux_reader = csv.DictReader(csvfile, delimiter=",")
    output_filename = filename.split(".")[0] + "_with_ror.csv"
    with open(output_filename, "w", newline="") as csvfile:
        fieldnames = [
            "UUID",
            "Cluster",
            "Vorkommende Namen",
            "Land",
            "ror_id",
            "ror_name",
        ]
        lux_writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=",")
        lux_writer.writeheader()
        for row in lux_reader:
            # run mappings.replace_encodings on row Cluster and Vorkommende Namen:
            row["Cluster"] = mappings.replace_encodings(row["Cluster"])
            row["Vorkommende Namen"] = mappings.replace_encodings(
                row["Vorkommende Namen"]
            )
            # get ror_id and ror_name for each row (include the country name to be sure we won't find things in the wrong country):
            ror_data = get_ror_data_from_api(row["Cluster"] + " " + row["Land"])
            # if there is no ror_id, try again with all the names in the "Vorkommende Namen" column, until there is a hit:
            if ror_data == None:
                print(
                    "No ror_id found for Cluster name",
                    row["Cluster"],
                    ", trying other names... ",
                )
                # split 'Vorkommende Namen' into list of names along separator ##:
                other_names = row["Vorkommende Namen"].split("##")
                # and trim surrounding whitespace for each item in the list:
                # other_names = [name.strip() for name in other_names]
                # print(other_names)
                for name in other_names:
                    name = name.strip()
                    ror_data = get_ror_data_from_api(name + " " + row["Land"])
                    if ror_data != None:
                        print("Success! ror_id found for:", name)
                        break
                    else:
                        print("Sorry, no success for other name ", name)

            #

            print(ror_data)
            # read "Land" and fix capitalization:
            land = row["Land"].capitalize()
            # get data from ror_data:
            if ror_data != None:
                ror_id, ror_name = ror_data
            else:
                ror_id = None
                ror_name = None
            # write row with ror id to new csv file:
            # lux_writer.writerow({'UUID':row['UUID'],'Cluster': row['Cluster'],'Vorkommende Namen': row['Vorkommende Namen'],'Land': land, 'ror_id': ror_id, 'ror_name': ror_name})
            lux_writer.writerow(
                {
                    "UUID": row["UUID"],
                    "Cluster": row["Cluster"],
                    "Vorkommende Namen": row["Vorkommende Namen"],
                    "Land": land,
                    "ror_id": ror_id,
                    "ror_name": ror_name,
                }
            )

# %%
