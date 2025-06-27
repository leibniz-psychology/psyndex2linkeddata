from ast import main
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
import modules.mappings as mappings
import modules.helpers as helpers
# import modules.research_info as research_info
#mport html

# import modules.abstract as abstract

# import modules.instance_source_ids as instance_source_ids
# import modules.instance_sources as instance_sources
# import modules.local_api_lookups as localapi
# import modules.mappings as mappings
# import modules.namespace as ns
# import modules.publication_types as publication_types
# import modules.terms as terms

testgs = ["CRA |l Compound Remote Associate-Worträtsel |c 6895 |n 11334", 
          "AUT |l Alternative Uses Test |n 13659", "SKID-II |l Strukturiertes Klinisches Interview für DSM-IV Achse II (Persönlichkeitsstörungen) |z x|n 15671",
          "NCCN-DT |l National Comprehensive Cancer Network Distress Thermometer - deutsche Fassung |c 5637 |n 3830",
          "AF-BP |l Aggressionsfragebogen von Buss und Perry |c 5065 |n 5060",
          "FKK |l FRAGEBOGEN ZU KOMPETENZ- UND KONTROLLÜBERZEUGUNGEN |c 2361 |n 2249",
          "SF-36 |l Fragebogen zum Gesundheitszustand |c 3482 |u SF-12 |f Kurzform |n 3413",
          "PHQ-D |l Gesundheitsfragebogen für Patienten |c 4556 |u PHQ-9 |f Depression Module |n 4539", # |f und |u vorhanden (u: verwendete Unterform; f: verwendetes Modul), muss in remark?          
          "", # mit |d x = "deutschsprchiger Test trotz englischen Titels" -> remark
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

]

# TODO: run the longNames through the captializion fix mapping I made earlier, so we don't have stupid allcaps names in the output. There is a python script "validate_corrected_lnams.py" that does this in the other_conversions/testdatabase/simple-json folder.
# TODO: check if any of the tests that were added as uncontrolled (have only n, no c) are controlled and in the DB by now, so do have a code? But how? Compare longName with the DB?
# or make a list of all unique uncontrolled tests in any record, compare with db just once and put this somewehere to check the shortname? Or the |n ... and then?
# what is |x???

# template for the related test dict
relatedTestOrMeasure = {
    "shortName": None, # from main field; bf:relatedTo > pxc:Test >> bf:title >> bf:AbbreviatedTitle > bf:mainTitle
    "longName": None, # from |l; bf:relatedTo > pxc:Test >> bf:title >> bf:Title > bf:mainTitle
    "relationType": None, # from |z x -> "zentral" = analyzes, sonst (|z nicht vorhanden oder leer, also ohne x) "uses"
    "test_id": None, # from |c; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:PsytkomTestId >> rdf:value "6300" (no identifiedBy if Test uncontrolled)
    "itemsComplete": None, # from |v x; Relationship > pxp:allItemsInWork true/false
    "remark": None, # Relationship > bf:note > bf:Note >> rdfs:label
    "uncontrolled": None, # true/false?
    "uncontrolled_id": None, # from |n; bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:UncontrolledTestId >> rdf:value "1234"
}

def build_related_test(testg_field):
    relatedTestOrMeasure = {
    "shortName": None, # from main field; bf:relatedTo > pxc:Test >> bf:title >> bf:AbbreviatedTitle > bf:mainTitle
    "longName": None, # from |l; bf:relatedTo > pxc:Test >> bf:title >> bf:Title > bf:mainTitle
    "relationType": "uses", # from |z x -> "zentral" = analyzes, sonst (|z nicht vorhanden oder leer, also ohne x) "uses"
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
        # if starts with two consecutive capital letters, assume it is a n allcaps name and change case to all lowercase:
        if relatedTestOrMeasure["longName"] and relatedTestOrMeasure["longName"][0:2].isupper():
            relatedTestOrMeasure["longName"] = relatedTestOrMeasure["longName"].lower() # replace with a better case correction function later, using the mapping I made in validate_corrected_lnams.py/lnam_allcaps.csv
    # get |z to define relationType:
    try:
        z_field = helpers.get_subfield(testg_field, "z")
        if z_field is not None:
            if z_field.strip() == "x":
                relatedTestOrMeasure["relationType"] = "analyzes"

    except Exception as e:
        print(f"Error getting relationType from {testg_field}: {e}")
    # get test_id:
    try:
        c_field = helpers.get_subfield(testg_field, "c")
        if c_field is not None:
            relatedTestOrMeasure["test_id"] = c_field.strip()
            relatedTestOrMeasure["uncontrolled"] = False
        else:
            relatedTestOrMeasure["uncontrolled"] = True
    except Exception as e:
        print(f"Error getting test_id from {testg_field}: {e}")
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
    # get uncontrolled_id:
    n_field = helpers.get_subfield(testg_field, "n")
    if n_field is not None and n_field.strip().isdigit():
        relatedTestOrMeasure["uncontrolled_id"] = n_field.strip()

    # bonus: if no c, but n: check "all tests.json" to see if the test is in the database by now and add the id. Probably by checking the longName ans/or shortName, and using a fuzzy match that allows for small differences like "Sibling Relationship Questionnaire - deutsche Fassung" vs "Sibling Relationship Questionnaire"

    return relatedTestOrMeasure

def build_related_test_nodes():
    pass

for index, testg in enumerate(testgs):
    print(f"{index}", build_related_test(testg), "\n")
    # build the related test nodes for each TESTG field
    #build_related_test_nodes(testg)
