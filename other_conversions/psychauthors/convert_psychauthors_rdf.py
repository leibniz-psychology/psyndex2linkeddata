from datetime import timedelta
from tqdm.auto import tqdm
import dateparser
import requests_cache
import modules.dicts as dicts
from dateparser.search import search_dates
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, Namespace

# from rdflib import BNode
from rdflib import URIRef

# import xml.etree.ElementTree as ET
import re
import csv

ROR_API_URL = "https://api.ror.org/organizations?affiliation="

# a cache for ror requests

urls_expire_after = {
    # Custom cache duration per url, 0 means "don't cache"
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/09183&lang=de': 0,
    # f'{SKOSMOS_URL}/rest/v1/label?uri=https%3A//w3id.org/zpid/vocabs/terms/': 0,
}
session_ror = requests_cache.CachedSession(
    ".cache/requests_ror",
    allowable_codes=[200, 404],
    expire_after=timedelta(days=30),
    urls_expire_after=urls_expire_after,
)


def get_ror_id_from_api(orgname_string):
    # this function takes a string with an organization name (e.g. from affiliations) and returns the ror id for that org from the ror api
    ror_api_url = ROR_API_URL + orgname_string
    # make a request to the ror api:
    # ror_api_request = requests.get(ror_api_url)
    # make request to api with caching:
    ror_api_request = session_ror.get(ror_api_url, timeout=20)
    # if the request was successful, get the json response:
    if ror_api_request.status_code == 200:
        # print("we have a response: " + str(ror_api_request.status_code))
        ror_api_response = ror_api_request.json()
        # check if the response has any hits:
        if len(ror_api_response["items"]) > 0:
            # print("there are some hits")
            # if so, get the item with a key value pair of "chosen" and "true" and return its id:
            for item in ror_api_response["items"]:
                if item["chosen"] == True:
                    # print("it's chosen")
                    return item["organization"]["id"], item["organization"]["name"]
        else:
            print("no hits")
            return None
    else:
        print("no 200 response")
        return None


# Namespaces
PERSONS = Namespace("https://w3id.org/zpid/resources/authorities/persons/")
LOCID = Namespace("http://id.loc.gov/vocabulary/identifiers/")
QUAL = Namespace("https://w3id.org/zpid/vocabs/qualifications/")
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
SCHEMA = Namespace("https://schema.org/")
GNDO = Namespace("https://d-nb.info/standards/elementset/gnd#")
PXC = Namespace("https://w3id.org/zpid/ontology/classes/")
PXP = Namespace("https://w3id.org/zpid/ontology/properties/")
GENDER = Namespace("https://w3id.org/zpid/vocabs/gender/")

# load data from source_tables/psychauthors-dump-2022-02/psychauthors.kerndaten.csv


# create a graph of psychauthor persons:

psychauthors = Graph()

# bind namespaces:
psychauthors.bind("locid", LOCID)
psychauthors.bind("persons", PERSONS)
psychauthors.bind("bf", BF)
psychauthors.bind("schema", SCHEMA)
psychauthors.bind("gndo", GNDO)
psychauthors.bind("pxc", PXC)
psychauthors.bind("pxp", PXP)
psychauthors.bind("gender", GENDER)
psychauthors.bind("qualifications", QUAL)


# create a dictionary of all persons with their ID as key
persons = {}
with open(
    "/home/tina/Developement/py-star2bf/other_conversions/psychauthors/source_tables/psychauthors-dump-2022-02/psychauthors.kerndaten.csv",
    newline="",
    encoding="utf-8",
) as csvfile:
    reader = csv.DictReader(csvfile, delimiter=",")
    for row in reader:
        # add the row to the dictionary:
        persons[row["id"]] = row


# walk through all persons and create a person node for each person

# for all of them:
for person_id in tqdm(persons):
    # get the psychauthors ID of the person from field 'code':
    psychauthorsId = persons[person_id]["code"]

    # create a URI for the person:
    person_uri = URIRef(PERSONS[psychauthorsId])
    # add the person to the graph as a schema:Person:
    psychauthors.add((person_uri, RDF.type, SCHEMA.Person))

    # if the person has a family name, save it as a variable - using try:
    try:
        familyName = persons[person_id]["nachname"]
    except:
        pass
    # try to find initial and save into a variable, if it exists:
    try:
        initial = persons[person_id]["initial"]
    except:
        print("no initial")
        initial = None
    # if the person has a given name, save it as a variable - using try:
    try:
        givenName = persons[person_id]["vorname"]
    except:
        pass

    # add any initial to the given name:
    try:
        if initial is not None and initial != "":
            givenName = givenName + " " + initial
    except:
        pass

    # create a combined name from family name and given name - using try:
    try:
        name = familyName + ", " + givenName
    except:
        pass
    # add the name to the graph as a schema:name:
    try:
        psychauthors.add((person_uri, SCHEMA.name, Literal(name)))
        # hashed node for the name:
        preferred_name_node = URIRef(person_uri + "#prefname")
        # print(preferred_name_node)
        psychauthors.set((preferred_name_node, RDF.type, GNDO.NameOfThePerson))
        psychauthors.add((preferred_name_node, SCHEMA.givenName, Literal(givenName)))
        psychauthors.add((preferred_name_node, SCHEMA.familyName, Literal(familyName)))
        psychauthors.add(
            (person_uri, GNDO.preferredNameEntityForThePerson, preferred_name_node)
        )
    except:
        print("couldn't add prefname")

    # try to find geb_name and save into a variable, if it exists:
    try:
        geb_name = persons[person_id]["geb_name"]
    except:
        geb_name = None
    try:
        if geb_name is not None and geb_name != "":
            full_geb_name = geb_name + ", " + givenName
            try:
                psychauthors.add(
                    (person_uri, SCHEMA.alternateName, Literal(full_geb_name))
                )
                # hashed node for the name:
                variant_name_node = URIRef(person_uri + "#altname")
                # print(preferred_name_node)
                psychauthors.set((variant_name_node, RDF.type, GNDO.NameOfThePerson))
                psychauthors.add(
                    (variant_name_node, SCHEMA.givenName, Literal(givenName))
                )
                psychauthors.add(
                    (variant_name_node, SCHEMA.familyName, Literal(geb_name))
                )
                psychauthors.add(
                    (person_uri, GNDO.variantNameEntityForThePerson, variant_name_node)
                )
            except:
                pass
    except:
        pass

    # get gender:
    try:
        gender_original = persons[person_id]["geschlecht"]
    except:
        gender_original = None
    try:
        if gender_original is not None and gender_original != "":
            if gender_original == "Herr":
                gender = "male"
            elif gender_original == "Frau":
                gender = "female"
        else:
            gender = "unknown"
    except:
        pass
    try:
        # make the node for the uri:
        psychauthors.add((person_uri, SCHEMA.gender, URIRef(GENDER[gender])))
    except:
        pass

    ## get birthdate
    try:
        birthDate = persons[person_id]["geb_tag"]
    except:
        birthDate = None
    try:
        if birthDate is not None and birthDate != "" and birthDate != "1000-01-01":
            psychauthors.add(
                (person_uri, SCHEMA.birthDate, Literal(birthDate, datatype=XSD.date))
            )
    except:
        pass

    ## get email
    try:
        eMail = persons[person_id]["email"]
    except:
        eMail = None
    try:
        if eMail is not None and eMail != "" and eMail != "zpid@zpid.de":
            psychauthors.add((person_uri, SCHEMA.email, URIRef("mailto:" + eMail)))
    except:
        pass

    ## get websites
    # make array from url1 and url2:
    websites = []
    try:
        url1 = persons[person_id]["url1"]
        if url1 is not None and url1 != "":
            websites.append(url1)
        url2 = persons[person_id]["url2"]
        if url2 is not None and url2 != "":
            websites.append(url2)
    except:
        pass
    # go through array and add to graph:
    try:
        for website in websites:
            psychauthors.add((person_uri, SCHEMA.url, URIRef(website)))
    except:
        pass

    ## add orcid (using bf:identifiedBy)
    try:
        orcid = persons[person_id]["orcid"]
    except:
        orcid = None
    try:
        if orcid is not None and orcid != "":
            orcid_uri = URIRef("https://orcid.org/" + orcid)
            psychauthors.set((orcid_uri, RDF.type, LOCID.orcid))
            psychauthors.set((orcid_uri, RDF.value, Literal(orcid)))
            psychauthors.add((person_uri, BF.identifiedBy, orcid_uri))
    except:
        pass

    ## ad psychauthorsId as identifier:
    try:
        if psychauthorsId is not None and psychauthorsId != "":
            psychauthorsId_uri = URIRef(person_uri + "#psychauthorsID")
            psychauthors.set((psychauthorsId_uri, RDF.type, PXC.PsychAuthorsID))
            psychauthors.set((psychauthorsId_uri, RDF.value, Literal(psychauthorsId)))
            psychauthors.add((person_uri, BF.identifiedBy, psychauthorsId_uri))
    except:
        pass

    ## Auszeichnungen: auszeichnung, int_auszeichnung as schema:award:
    try:
        auszeichnung_liststring = persons[person_id]["auszeichnung"]
        int_auszeichnung_liststring = persons[person_id]["int_auszeichnung"]
    except:
        auszeichnung_liststring = None
        int_auszeichnung_liststring = None
    # split strings into one combined list "auszeichnungen" (separator is "\r")
    auszeichnungen = auszeichnung_liststring.split("\r")
    auszeichnungen.extend(int_auszeichnung_liststring.split("\r"))
    award_count = 0
    try:
        for auszeichnung in auszeichnungen:
            if auszeichnung is not None and auszeichnung != "":
                award_count += 1
                # strip any preceding "-":
                auszeichnung = re.sub(r"^-", "", auszeichnung.strip())
                # strip whitespace around the string:
                auszeichnung = auszeichnung.strip()
                # get startdate, if possible, using dateparser:
                try:
                    startdate = search_dates(
                        auszeichnung,
                        languages=["de", "en"],
                        settings={
                            "PREFER_MONTH_OF_YEAR": "first",
                            "PREFER_DAY_OF_MONTH": "first",
                            "PREFER_DATES_FROM": "past",
                            "REQUIRE_PARTS": ["year"],
                        },
                    )[0][1].strftime("%Y")
                    # print(startdate)
                except:
                    startdate = None
                # use schema:Role reification:
                award_node = URIRef(person_uri + "#award" + str(award_count))
                psychauthors.set((award_node, RDF.type, SCHEMA.Role))
                psychauthors.add((award_node, SCHEMA.award, Literal(auszeichnung)))
                if startdate is not None:
                    psychauthors.add(
                        (
                            award_node,
                            SCHEMA.startDate,
                            Literal(startdate, datatype=XSD.gYear),
                        )
                    )
                psychauthors.add((person_uri, SCHEMA.award, award_node))
    except:
        pass

    ## add academic qualifications:
    try:
        qualifications_liststring = persons[person_id]["qualifikation"]
    except:
        qualifications_liststring = None
    # split strings into one combined list "qualifications" (separator is "\r")
    qualifications = qualifications_liststring.split("\r")
    # attach as a schema:aluminiOf construct where the text becomes schema:description of the schema:CollegeOrUniversity
    qualification_count = 0
    try:
        for qualification in qualifications:
            college = None
            if qualification is not None and qualification != "":
                qualification_count += 1
                qualification = qualification.strip()
                # get startdate, if possible, using dateparser:
                try:
                    startdate = search_dates(
                        qualification,
                        languages=["de", "en"],
                        settings={
                            "PREFER_MONTH_OF_YEAR": "first",
                            "PREFER_DAY_OF_MONTH": "first",
                            "PREFER_DATES_FROM": "past",
                            "REQUIRE_PARTS": ["year"],
                        },
                    )[0][1].strftime("%Y")
                    # print(enddate)
                except:
                    startdate = None

                # using the degree_lookup dict in modules/dicts.py:
                degree = "other"
                try:
                    for degree_dict in dicts.degree_lookup:
                        for synonym in degree_dict["synonyms"]:
                            if synonym in qualification:
                                # print(synonym + " - " + qualification)
                                degree = degree_dict["name"]
                                # print("degree is: " + degree)
                except:
                    degree = "other"

                # try to recognize some institutions:
                # use data from dicts.py to get a string and ror uri for the college:
                college = None
                college_ror = None
                try:
                    for college_dict in dicts.college_lookup:
                        for synonym in college_dict["synonyms"]:
                            if synonym in qualification:
                                college = college_dict["name"]
                                if college_dict["ror"] is not None:
                                    college_ror = college_dict["ror"]
                except:
                    pass
                ## for any that were not matched (college still None), use the ror api:
                if college is None:
                    try:
                        print("no ror found for " + qualification)
                        college_ror, college = get_ror_id_from_api(qualification)
                    except:
                        college = None
                        college_ror = None

                qualification_node = URIRef(
                    person_uri + "#qualification" + str(qualification_count)
                )
                psychauthors.set(
                    (qualification_node, RDF.type, SCHEMA.OrganizationRole)
                )
                # add a college node:
                college_node = URIRef(qualification_node + "#org")
                psychauthors.set((qualification_node, SCHEMA.alumniOf, college_node))
                psychauthors.set((college_node, RDF.type, SCHEMA.CollegeOrUniversity))
                psychauthors.add(
                    (qualification_node, SCHEMA.description, Literal(qualification))
                )
                if startdate is not None:
                    psychauthors.add(
                        (
                            qualification_node,
                            SCHEMA.startDate,
                            Literal(startdate, datatype=XSD.gYear),
                        )
                    )
                if degree is not None:
                    psychauthors.add(
                        (qualification_node, SCHEMA.hasCredential, URIRef(QUAL[degree]))
                    )
                if college is not None:
                    psychauthors.add((college_node, SCHEMA.name, Literal(college)))
                if college_ror is not None:
                    psychauthors.add((college_node, SCHEMA.sameAs, URIRef(college_ror)))

                psychauthors.add((person_uri, SCHEMA.alumniOf, qualification_node))
    except:
        pass

    # get degree/titles string in field "titel" and attach via gnd:academicDegree:
    try:
        titles_int = persons[person_id]["titel"]
        # look up this int in the academic_titles array of dicts in modules/dicts.py to get a string - use the int as the value for the "number" key, get the value in dict in the key "name":
        titles_string = dicts.academic_titles[int(titles_int)]["name"]
        # print(titles_int)
        # if it exists, add it to the graph as a schema:academicDegree

    except:
        titles_int = None
        titles_string = None
    try:
        if titles_string is not None and titles_string != "":
            psychauthors.add((person_uri, GNDO.academicDegree, Literal(titles_string)))
    except:
        pass


# add labels to gender concepts:
psychauthors.set((URIRef(GENDER["female"]), RDF.type, SKOS.Concept))
psychauthors.add(
    ((URIRef(GENDER["female"]), SKOS.prefLabel, Literal("Female", lang="en")))
)
psychauthors.add(
    ((URIRef(GENDER["female"]), SKOS.prefLabel, Literal("Weiblich", lang="de")))
)
psychauthors.set((URIRef(GENDER["male"]), RDF.type, SKOS.Concept))
psychauthors.add(((URIRef(GENDER["male"]), SKOS.prefLabel, Literal("Male", lang="en"))))
psychauthors.add(
    ((URIRef(GENDER["male"]), SKOS.prefLabel, Literal("Männlich", lang="de")))
)
psychauthors.set((URIRef(GENDER["unknown"]), RDF.type, SKOS.Concept))
psychauthors.add(
    ((URIRef(GENDER["unknown"]), SKOS.prefLabel, Literal("Unknown Gender", lang="en")))
)
psychauthors.add(
    (
        (
            URIRef(GENDER["unknown"]),
            SKOS.prefLabel,
            Literal("Geschlecht unbekannt", lang="de"),
        )
    )
)

# serialize the graph as turtle:
psychauthors.serialize(destination="psychauthors.ttl", format="turtle")
psychauthors.serialize(
    destination="psychauthors.json",
    format="json-ld",
    auto_compact=False,
    sort_keys=True,
    index=True,
)
