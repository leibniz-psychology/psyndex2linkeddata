import dateparser
from dateparser.search import search_dates
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, XSD, SKOS, Namespace

# from rdflib import BNode
from rdflib import URIRef

# import xml.etree.ElementTree as ET
import re
import csv


# Namespaces
PERSONS = Namespace("https://w3id.org/zpid/resources/authorities/persons/")
LOCID = Namespace("http://id.loc.gov/vocabulary/identifiers/")
BF = Namespace("http://id.loc.gov/ontologies/bibframe/")
SCHEMA = Namespace("https://schema.org/")
GNDO = Namespace("https://d-nb.info/standards/elementset/gnd")
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
        # print the id:
# create a dictionary of all institutions with their ID as key
# institutions = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.institut.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         institutions[row['id']] = row


# create a dictionary of all titles with their ID as key
# titles = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.titel.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         titles[row['id']] = row

# create a dictionary of all cities in stadt.csv with their ID as key
# cities = {}
# with open('source_tables/psychauthors-dump-2022-02/psychauthors.stadt.csv', newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     for row in reader:
#         cities[row['id']] = row

# walk through all persons and create a person node for each person

# for all of them:
for person_id in persons:
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
