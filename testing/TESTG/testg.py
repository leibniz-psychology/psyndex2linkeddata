import logging
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
import modules.helpers as helpers
import modules.namespace as ns
import json
from rapidfuzz import fuzz

from rdflib import Literal, URIRef, Graph
from rdflib.namespace import RDF, RDFS, SKOS

# create a new graph
graph = Graph()
graph = Graph(identifier=URIRef("https://w3id.org/zpid/testgraph/"))
# set the namespace for the graph

# Bind the namespaces to the prefixes we want to see in the output:
graph.bind("bf", ns.BF)
graph.bind("bflc", ns.BFLC)
graph.bind("works", ns.WORKS)
# records_schema.bind("works", WORKS)
graph.bind("instances", ns.INSTANCES)
graph.bind("pxc", ns.PXC)
graph.bind("pxp", ns.PXP)
graph.bind("lang", ns.LANG)
graph.bind("schema", ns.SCHEMA)
graph.bind("locid", ns.LOCID)
graph.bind("mads", ns.MADS)
graph.bind("roles", ns.ROLES)
graph.bind("relations", ns.RELATIONS)
graph.bind("genres", ns.GENRES)
graph.bind("contenttypes", ns.CONTENTTYPES)
graph.bind("issuances", ns.ISSUANCES)  # issuance types
graph.bind("pmt", ns.PMT)  # mediacarriers
graph.bind("licenses", ns.LICENSES)  # licenses

testgs = ["CRA |l Compound Remote Associate-Worträtsel |c 6895 |n 11334", 
          "AUT |l Alternative Uses Test |n 13659", 
          "SKID-II |l Strukturiertes Klinisches Interview für DSM-IV Achse II (Persönlichkeitsstörungen) |z x|n 15671",
          "NCCN-DT |l National Comprehensive Cancer Network Distress Thermometer - deutsche Fassung |c 5637 |n 3830",
          "AF-BP |l Aggressionsfragebogen von Buss und Perry |c 5065 |n 5060",
          "FKK |l FRAGEBOGEN ZU KOMPETENZ- UND KONTROLLÜBERZEUGUNGEN |c 2361 |n 2249",
          "SF-36 |l Fragebogen zum Gesundheitszustand |c 3482 |u SF-12 |f Kurzform |n 3413",
          "PHQ-D |l Gesundheitsfragebogen für Patienten |c 4556 |u PHQ-9 |f Depression Module |n 4539", # |f und |u vorhanden (u: verwendete Unterform; f: verwendetes Modul), muss in remark?          
          #"", # mit |d x = "deutschsprchiger Test trotz englischen Titels" -> remark
          "|l Self-Report Psychopathy Scale III |n 0000 |d x", # no short name
        #  "", # no long name
        #  "", # no testid (uncontrolled test)
            "TESTG |l Test Name long German |c 1234 |n 5678 |v x |z x |k This is a test remark", # example with all fields
            "CAPS |l Clinician-Administered PTSD Scale |c  |n 7930  |d  |z  |v  |k ", # alles mögliche ist komisch leer
            "|l 5C Scale |z x |v x |k Betsch C, Schmid P, Heinemeier D, Korn L, Holtmann C, Bo¨hm R (2018) Beyond confidence: Development of a measure assessing the 5C psychological antecedents of vaccination. PLoS ONE 13(12): e0208601. https://doi.org/ 10.1371/journal.pone.0208601|n 20170", # viel Kommentar, inkl. Zitation mit kaputten Zeichen und fehlenden Kommata nach den Nachnamen, WTH?, und (kaputter!) DOI, zentral UND itemsComplete, aber kein c, also uncontrolled test
            "|l Bells Test |n 14300 |d x", # öhm, sehr _reduziert, aber mit |d x
            "|d x |n Vollerfassung$|e Eating Disorders |d Essstörungen |g x$$X", # WTH? gibt es noch mehrmals mit |v x |n Vollerfassung und "|k ...". Alle ohne short- und longname ganz skippen, weil eigentlich immer Fehler?
            "|n 6556", "|n 0000" #aha? skippen?
            "|x 8866", #???
            "DAS |l Skala Dysfunktionaler Einstellungen |c 1534 |u DAS-C |f Skala dysfunktionaler Einstellungen für Kinder |n 1486",
            "MWT-B |l MEHRFACHWAHL-WORTSCHATZ-INTELLIGENZTEST |c 0342 |n 335 |d  |z  |v  |k",
            "HAMD |l HAMILTON-DEPRESSIONS-SKALA - DEUTSCHE FASSUNG |c 1102  |n 1073  |d  |z  |v  |k ",
            "NEO-FFI |l NEO-FÜNF-FAKTOREN INVENTAR NACH COSTA UND MCCRAE - DEUTSCHE FASSUNG |c 2328 |n 2216 |d  |z  |v  |k ",
            "SIDAM |l STRUKTURIERTES INTERVIEW FÜR DIE DIAGNOSE EINER DEMENZ VOM ALZHEIMER TYP, DER MULTIINFARKT-DEMENZ UND DEMENZEN ANDERER ÄTIOLOGIE NACH DSM-III-R, DSM-IV UND ICD-10 |c 2552 |n 2442 |d  |z  |v  |k ",
            "KFT 4-13+ |l KOGNITIVER FÄHIGKEITS-TEST FÜR 4. BIS 13. KLASSEN |c 0263 |n 257",
            "K-ABC |l KAUFMAN-ASSESSMENT BATTERY FOR CHILDREN - DEUTSCHSPRACHIGE FASSUNG |c 2417 |n 2305",
            "ST-AST 6-11 |l SPORTTEST: ALLGEMEINER SPORTMOTORISCHER TEST ZUR DIAGNOSE DER KONDITIONELLEN UND KOORDINATIVEN LEISTUNGSFÄHIGKEIT (PSYNDEX Tests Review) |c 1300 |n 1264 |d x |k ",
            "WCST |l Wisconsin Card Sorting Test |c 1848 |u M-WCST |f Modified Wisconsin Card Sorting Test |n 1788",
            "HEXACO-PI-R |l HEXACO Persönlichkeitsinventar |c 6671 |n 11128",
            "SCL-K-9 |l Symptom-Checkliste - Kurzform |c  |n 9964 |d  |z  |v  |k "]




# # template for the related test dict
# relatedTestOrMeasure = {
#     "shortName": None, # from main field; bf:relatedTo > pxc:Test >> bf:title >> bf:AbbreviatedTitle > bf:mainTitle
#     "longName": None, # from |l; bf:relatedTo > pxc:Test >> bf:title >> bf:Title > bf:mainTitle
#     "relationType": None, # from |z x -> "zentral" = analyzes, sonst (|z nicht vorhanden oder leer, also ohne x) "uses"
#     "test_id": None, # from |c; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:PsytkomTestId >> rdf:value "6300" (no identifiedBy if Test uncontrolled)
#     "itemsComplete": None, # from |v x; Relationship > pxp:allItemsInWork true/false
#     "remark": None, # Relationship > bf:note > bf:Note >> rdfs:label
#     "uncontrolled": None, # true/false?
#     "uncontrolled_id": None, # from |n; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:UncontrolledTestId >> rdf:value "1234"
# }

def lookup_test_id_from_name(long_name):
    """
    Looks up the test id from the long name and optional short name in the all_tests.json file using fuzzy matching.
    Returns the test id if a sufficiently similar name is found (using RapidFuzz token_sort_ratio >= 70), 
    and skips matches involving significant DSM/ICD number mismatches (e.g., DSM-III vs DSM-IV).
    """
    # load the all_tests.json file
    all_tests_file = os.path.join(project_root, "other_conversions", "testdatabase","simple-json", "all_tests.json")
    with open(all_tests_file, "r", encoding="utf-8") as f:
        all_tests = json.load(f)
    # look for the test in the all_tests.json file
    for test in all_tests:
        similarity = fuzz.token_sort_ratio(test["longName"], long_name)
        if similarity >= 70:
            if ("DSM-III" in test["longName"] and "DSM-IV" in long_name) or ("DSM-III" in long_name and "DSM-IV" in test["longName"]) or ("DSM-IV" in test["longName"] and "DSM-5" in long_name) or ("ICD-10" in test["longName"] and "ICD-11" in long_name) or ("ICD-11" in test["longName"] and "ICD-10" in long_name):
                continue  # Skip this pair if you detect that it involves a significant mismatch in numbers
            logging.info(f"Found test with longName: {long_name} and test_id: {test['id']}")
            return test["id"]
    return None

def build_related_test(testg_field):
    """
    Builds a dictionary containing information about a related test or measure from a TESTG field.

    This function processes a single TESTG field from a record and extracts relevant information to construct
    a dictionary with details about the related test or measure. The resulting dictionary can be used to build
    related test nodes for further processing.

    Args:
        testg_field (dict or object): The TESTG field data from which to extract related test information.

    Returns:
        dict: A dictionary with the following keys:
            - shortName (str or None): Abbreviated title of the test, extracted from the main field.
            - longName (str or None): Full title of the test, cleaned and case-corrected if necessary.
            - relationType (str): Type of relation, either "usesTest" or "analyzesTest", based on subfield |z.
            - test_id (str or None): Identifier for the test, from subfield |c or looked up by longName.
            - itemsComplete (bool or None): Whether all items are included, based on subfield |v.
            - remark (str or None): Additional notes, possibly augmented with subfields |u, |f, |d.
            - uncontrolled (bool or None): Indicates if the test is uncontrolled (i.e., lacks a test_id).
            - uncontrolled_id (str or None): Identifier for uncontrolled tests, from subfield |n.

    Notes:
        - The function uses several helper functions (e.g., get_mainfield, get_subfield, title_except, lookup_test_id_from_name)
          to extract and process subfields.
        - If the test_id is not found, the function attempts to look it up by longName.
        - Remarks may be augmented with information from subfields |u (used submodule), |f (used form), and |d (German language flag).
        - The function handles missing or malformed fields gracefully and logs warnings as needed.
    """
    relatedTestOrMeasure = {
    "shortName": None, # from main field; bf:relatedTo > pxc:Test >> bf:title >> bf:AbbreviatedTitle > bf:mainTitle
    "longName": None, # from |l; bf:relatedTo > pxc:Test >> bf:title >> bf:Title > bf:mainTitle
    "relationType": "usesTest", # from |z x -> "zentral" = analyzes, sonst (|z nicht vorhanden oder leer, also ohne x) "uses"
    "test_id": None, # from |c; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:PsytkomTestId >> rdf:value "6300" (no identifiedBy if Test uncontrolled)
    "itemsComplete": None, # from |v x; Relationship > pxp:allItemsInWork true/false
    "remark": None, # Relationship > bf:note > bf:Note >> rdfs:label
    "uncontrolled": None, # true/false?
    "uncontrolled_id": None, # from |n; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:UncontrolledTestId >> rdf:value "1234"
}
    # go through one TESTG field in a record and build a dict with all relevant info which will
    # be used to build the related test nodes using the build_related_test_nodes function
    # this function will be called for each TESTG field in a record
    # get shortName:
    main_field = helpers.get_mainfield(testg_field)
    if main_field is not None and main_field.strip() != "":
        relatedTestOrMeasure["shortName"] = main_field.strip()
    # get longName:
    l_field = helpers.get_subfield(testg_field, "l")
    if l_field is not None and l_field.strip() != "":
        relatedTestOrMeasure["longName"] = l_field.strip()
        # first, remove "(PSYNDEX Tests Review)" and "(PSYNDEX Tests Info)" and "(PSYNDEX Tests Abstract)" from the longName, if present:
        relatedTestOrMeasure["longName"] = relatedTestOrMeasure["longName"].replace("(PSYNDEX Tests Review)", "").replace("(PSYNDEX Tests Info)", "").replace("(PSYNDEX Tests Abstract)", "")
        # if starts with two consecutive capital letters, assume it is a n allcaps name and change case to all lowercase:
        # check if the name is all uppercase
        if relatedTestOrMeasure["longName"] and relatedTestOrMeasure["longName"].isupper(): # won't catch things with special characters like ":", "(", ")"
            # then capitalize the first letter of each word, except for some common articles:
            relatedTestOrMeasure["longName"] = helpers.title_except(relatedTestOrMeasure["longName"]) # replace with a better case correction function later, using the mapping I made in validate_corrected_lnams.py/lnam_allcaps.csv
    # get |z to define relationType:
    try:
        z_field = helpers.get_subfield(testg_field, "z")
        if z_field is not None:
            if z_field.strip() == "x":
                relatedTestOrMeasure["relationType"] = "analyzesTest"

    except Exception as e:
        logging.warning(f"Error getting relationType from {testg_field}: {e}")
    # get test_id:
    try:
        c_field = helpers.get_subfield(testg_field, "c")
        if c_field is not None:
            relatedTestOrMeasure["test_id"] = c_field.strip()
            relatedTestOrMeasure["uncontrolled"] = False
        else:
            relatedTestOrMeasure["uncontrolled"] = True
    except Exception as e:
        logging.warning(f"Error getting test_id from {testg_field}: {e}")
    # get itemsComplete:
    v_field = helpers.get_subfield(testg_field, "v")
    if v_field is not None and v_field.strip() != "":
            if v_field.strip() == "x":
                relatedTestOrMeasure["itemsComplete"] = True
            else:
                relatedTestOrMeasure["itemsComplete"] = False
    else:
        relatedTestOrMeasure["itemsComplete"] = False
    # get remark:
    k_field = helpers.get_subfield(testg_field, "k")
    if k_field is not None and k_field.strip() != "":
        relatedTestOrMeasure["remark"] = k_field.strip()
    # get values of fields |u, |f and |d:
    # |u = used submodule, |f = used form, |d = is German despite English title
    try:
        u_field = helpers.get_subfield(testg_field, "u")
    except Exception as e:
        logging.warning(f"Error getting usedSubmodule from {testg_field}: {e}")
    try:
        f_field = helpers.get_subfield(testg_field, "f")
    except Exception as e:
        logging.warning(f"Error getting usedForm from {testg_field}: {e}")
    try:
        d_field = helpers.get_subfield(testg_field, "d")
    except Exception as e:
        logging.warning(f"Error getting isGerman from {testg_field}: {e}")
    # add u_field, f_field and d_field to remark if they are present:
    if relatedTestOrMeasure["remark"] is not None:
        if u_field is not None and u_field.strip() != "":
            relatedTestOrMeasure["remark"] += f"; Verwendete Variante oder Unterform: {u_field.strip()}"
        if f_field is not None and f_field.strip() != "":
            relatedTestOrMeasure["remark"] += f"; Langname verwendete Variante: {f_field.strip()}"
        if d_field is not None and d_field.strip() == "x":
            relatedTestOrMeasure["remark"] += "; deutschsprachiger Test trotz englischen Titels"
    else:
        relatedTestOrMeasure["remark"] = ""
        if u_field is not None and u_field.strip() != "":
            relatedTestOrMeasure["remark"] += f"; Verwendete Variante oder Unterform: {u_field.strip()}"
        if f_field is not None and f_field.strip() != "":
            relatedTestOrMeasure["remark"] += f"; Langname verwendete Variante: {f_field.strip()}"
        if d_field is not None and d_field.strip() == "x":
            relatedTestOrMeasure["remark"] += "; deutschsprachiger Test trotz englischen Titels"
    # remove any starting semicolon or whitespace from the remark:
    if relatedTestOrMeasure["remark"] and relatedTestOrMeasure["remark"].startswith("; "):
        relatedTestOrMeasure["remark"] = relatedTestOrMeasure["remark"].lstrip("; ").strip()
    # get uncontrolled_id:
    n_field = helpers.get_subfield(testg_field, "n")
    if n_field is not None and n_field.strip().isdigit():
        relatedTestOrMeasure["uncontrolled_id"] = n_field.strip()

    if relatedTestOrMeasure["test_id"] is None: # we have no test_id, then it is an uncontrolled test - that may by now be in the database, so we can look it up by longName
        # look up the test id from the long name in the all_tests.json file - because it may be in the database by now, but not in the TESTG file.
        # if the longName is None, we can't look it up, so we skip this
        if relatedTestOrMeasure["longName"] is not None:
            # check if the longName is in the all_tests.json file and get the test_id
            relatedTestOrMeasure["test_id"] = lookup_test_id_from_name(relatedTestOrMeasure["longName"]) # this returns the test_id if found, otherwise None
            if relatedTestOrMeasure["test_id"] is not None:
                relatedTestOrMeasure["uncontrolled"] = False
            else:
                relatedTestOrMeasure["uncontrolled"] = True
        else:
            relatedTestOrMeasure["uncontrolled"] = True
    return relatedTestOrMeasure

def build_related_test_nodes(work_uri, graph, relatedTestOrMeasure):
    """
    Builds RDF nodes and relationships in the given graph to represent a related test or measure for a work.

    This function creates and links several RDF nodes, including a relationship node, a test node, title nodes (long and short names), note nodes, and identifier nodes, according to the provided `relatedTestOrMeasure` dictionary. The structure follows specific ontology classes and properties, handling both controlled and uncontrolled tests, and attaches all relevant information to the graph.

    Args:
        work_uri (rdflib.term.URIRef): The URI of the work to which the test or measure is related.
        graph (rdflib.Graph): The RDF graph where nodes and relationships will be added.
        relatedTestOrMeasure (dict): A dictionary containing information about the related test or measure. Expected keys include:
            - "shortName" (str or None): Abbreviated name of the test.
            - "longName" (str or None): Full name of the test.
            - "uncontrolled" (bool): Whether the test is uncontrolled.
            - "remark" (str or None): Additional remarks or notes.
            - "test_id" (str or None): Identifier for the test.
            - "uncontrolled_id" (str or None): Identifier for uncontrolled tests.
            - "itemsComplete" (bool or None): Whether all items are included in the work.
            - "relationType" (str or None): Type of the relationship.

    Returns:
        None

    Notes:
        - If both "shortName" and "longName" are missing, the function logs and skips processing.
        - The function does not use the regular relationship creation function due to the unique structure of test relationships.
        - Additional fields such as `pxp:allItemsInWork` and `pxc:uncontrolledTestId` are handled specifically for tests.
    """
    if relatedTestOrMeasure["shortName"] is None and relatedTestOrMeasure["longName"] is None:
        logging.info(f"Skipping building test relation for TESTG with shortName & longName both missing, likely not a test: {relatedTestOrMeasure}")
        return
    #1. make a Relationship node and attach to the work
    relationship_uri = URIRef(str(work_uri) + "#TestRelationship")
    graph.add((relationship_uri, RDF.type, ns.BFLC.Relationship))
    graph.add((relationship_uri, RDF.type, ns.PXC.TestRelationship))
    # attach to work node
    graph.add((work_uri, ns.BFLC.relationship, relationship_uri))
    #2. make a pxc:Test node and attach to the Relationship node, qlso add bflc:Uncontrolled class if the test is uncontrolled
    test_uri = URIRef(str(relationship_uri) + "_test")
    graph.add((test_uri, RDF.type, ns.PXC.Test))
    if relatedTestOrMeasure["uncontrolled"]:
        graph.add((test_uri, RDF.type, ns.BFLC.Uncontrolled))
    graph.add((relationship_uri, ns.BFLC.relatedTo, test_uri))
    #3. make a bf:Title node from "longName" and attach to the pxc:Test node
    if relatedTestOrMeasure["longName"] is not None:
        long_name = Literal(relatedTestOrMeasure["longName"])
        title_uri = URIRef(str(test_uri) + "_longName")
        graph.add((title_uri, RDF.type, ns.BF.Title))
        graph.add((title_uri, ns.BF.mainTitle, long_name))
        graph.add((test_uri, ns.BF.title, title_uri))
    #4. make a bf:AbbreviatedTitle node from shortName and attach to the pxc:Test node
    if relatedTestOrMeasure["shortName"] is not None:
        short_name = Literal(relatedTestOrMeasure["shortName"])
        abbreviated_title_uri = URIRef(str(test_uri) + "_shortName")
        graph.add((abbreviated_title_uri, RDF.type, ns.BF.AbbreviatedTitle))
        graph.add((abbreviated_title_uri, ns.BF.mainTitle, short_name))
        graph.add((test_uri, ns.BF.title, abbreviated_title_uri))
    #5. make a bf:Note node and attach to the Relationship node
    if relatedTestOrMeasure["remark"] is not None and relatedTestOrMeasure["remark"].strip() != "":
        note_uri = URIRef(str(relationship_uri) + "_remark")
        graph.add((note_uri, RDF.type, ns.BF.Note))
        graph.add((note_uri, RDFS.label, Literal(relatedTestOrMeasure["remark"])))
        graph.add((relationship_uri, ns.BF.note, note_uri))
    #6. make a pxc:PsytkomTestId node and attach to the pxc:Test node
    if relatedTestOrMeasure["test_id"] is not None:
        test_id_uri = URIRef(str(test_uri) + "_testId")
        graph.add((test_id_uri, RDF.type, ns.PXC.PsytkomTestId))
        graph.add((test_id_uri, RDF.value, Literal(relatedTestOrMeasure["test_id"])))
        graph.add((test_uri, ns.BF.identifiedBy, test_id_uri))
    #7. add uncontrolled test id if available as literal property pxp:uncontrolledTestId
    if relatedTestOrMeasure["uncontrolled_id"] is not None and relatedTestOrMeasure["uncontrolled_id"].strip() != "0000":
        # use a simple literal field "pxc:uncontrolledTestId":
        graph.add((test_uri, ns.PXP.uncontrolledTestId, Literal(relatedTestOrMeasure["uncontrolled_id"])))
    # add the itemsComplete property to the Relationship node
    if relatedTestOrMeasure["itemsComplete"] is not None:
        graph.add((relationship_uri, ns.PXP.allItemsInWork, Literal(relatedTestOrMeasure["itemsComplete"])))
    # add relation type to the Relationship node
    if relatedTestOrMeasure["relationType"] is not None:
        graph.add((relationship_uri, ns.BFLC.relation, URIRef(ns.RELATIONS + relatedTestOrMeasure["relationType"])))
    # NOTE: we don't use the regular relationship creation function here, because Tests are a little different, with no Work and Instance nodes, but a pxc:Test node instead, and additional fields like pxp:allItemsInWork and pxp:uncontrolledTestId.

for index, testg in enumerate(testgs):
    print(f"{index}", build_related_test(testg), "\n")
    # make a work node where we will attach the information:
    work_uri = URIRef(
        "https://w3id.org/zpid/testgraph/works/" + str(index))
    # add the work uri to the graph:
    graph.add((work_uri, RDF.type, ns.WORKS.Work))
    # build the related test nodes for each TESTG field
    relatedTestOrMeasure = build_related_test(testg)
    # add the related test nodes to the graph
    build_related_test_nodes(work_uri, graph, relatedTestOrMeasure)

# serialize the graph to a file#+
output_file = os.path.join(project_root, "testing", "TESTG", "testg.ttl")
graph.serialize(destination=output_file, format='turtle')
print(f"Graph serialized to {output_file}")

