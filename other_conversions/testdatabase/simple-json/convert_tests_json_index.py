# ingests the two xml files psytkom and ptshort and converts them to json arrays that contain
# basic fields that can help search for and identify a test for linking it in a work.


import xml.etree.ElementTree as ET
import json
import csv

# read the xml file
root = ET.parse("../Tests_231128/231128/ALLTESTS.xml")

record_count = 0
records_without_classifications = 0
records_without_longName = 0
records_without_shortName = 0
records_without_synonyms = 0
records_without_englishName = 0
records_without_authors = 0
records_without_publicationYear = 0
records_without_vars = 0

# Load the lnam_allcaps mappings from the csv file
lnam_allcaps = {}
with open("lnam_allcaps.csv", "r") as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        # the first column is the id, the second column is the longName with all caps, the third column is the longName with correct casing:
        lnam_allcaps[row[0]] = [row[1], row[2]]
        # an example entry looks like this:
        # '0001': ['AACHENER APHASIE TEST', 'Aachener Aphasie Test']
        # we can access the caseCorrectedLNAM like this:
        # lnam_allcaps['0001'][1]

# create an empty array to store the records:
test_list = []

for record in root.findall("Record"):
    # but only the first 500 records:
    # if len(test_list) >= 2500:
    #     break
    # get the four-digit test id:
    id = record.find("ND").text
    # add the id to the current test record in the test_list array:
    test_list.append({"psytkomId": id})
    record_count += 1

    # get the shortName from SNAM, if it exists:
    try:
        shortName = record.find("SNAM")
        try:
            # if record.find("SNAM") != None and record.find("SNAM").text != None:
            shortName = record.find("SNAM").text
        except:
            print("SNAM field (short name) empty in record: " + id)
            shortName = None
            records_without_shortName += 1
    except:
        print("SNAM field (short name) not present in record: " + id)
        shortName = None
        records_without_shortName += 1
        # and add this key-value pair to the current test record in the test_list array:
    else:
        test_list[-1]["shortName"] = shortName

    # and the longName from LNAM, if it exists:
    try:
        longName = record.find("LNAM")
        try:
            longName = record.find("LNAM").text
        except:
            print("LNAM field (long name) empty in record: " + id)
            longName = None
            records_without_longName += 1
    except:
        print("LNAM field (long name) not present in record: " + id)
        longName = None
        records_without_longName += 1

    # later: Check if the id is contained in the name replacement list csv: "lnam_allcaps.csv" that we loaded above.
    # If it is, replace the longName with the one in the csv's column "caseCorrectedLNAM":
    if id in lnam_allcaps:
        longName = lnam_allcaps[id][1]

    # add the longName to the current test object:
    test_list[-1]["longName"] = longName

    otherNames = []
    # get ENAM:
    try:
        enam = record.find("ENAM")
        try:
            # ENAM ends in a "/" followed by a short string. Remove this part - it can be either: /zpid, /author, /autor or /journal:
            # enam_origin = enam.text.split("/")[1]
            enam = enam.text.split("/")[0]
        except:
            print("ENAM has no origin part (after /) in record: " + id)
            # use the whole string as the enam instead:
            enam = enam.text
    except:
        enam = None
        records_without_englishName += 1
        print("ENAM field (other names) not present in record: " + id)
    # whatever the case may be, add the enam to the otherNames array:
    else:
        otherNames.append(enam)

    # get SYN:
    try:
        syn = record.find("SYN")
        try:
            # split the string along the "; " delimiter:
            for element in syn.text.split("; "):
                # add each element to the otherNames array:
                otherNames.append(element)
        except:
            # print("SYN field has only one synonym in record: " + id)
            syn = syn.text
            # add the whole string to the otherNames array:
            otherNames.append(syn)
    except:
        syn = None
        records_without_synonyms += 1
        # print("SYN field (synonyms) not present in record: " + id)
    else:
        # add the otherNames object to the test object:
        test_list[-1]["otherNames"] = otherNames

    # check if there is a field VAR:
    try:
        var = record.find(
            "VAR"
        ).text  # if this fails (because there is no text in the field or there is no VAR field), the except block will be executed
    except:
        # print("VAR field (included test variants) not present in record: " + id)
        records_without_vars += 1
    else:
        # start a list of includedTestVariants that shall contain objects with the keys "shortName" and "longName":
        includedTestVariants = []
        # print("VAR field (included test variants) found in record: " + id)
        # print("VAR", var + " in record: " + id)
        try:
            # split the string along the "; " delimiter and then go through all the items:
            for element in var.split("; "):
                # add an empty object that will hold the shortName and/or longName string for each variant later:
                variant = {}
                # if both short and long name are present and in the correct order (starting with k, followed by l. like "|k ABC |l Adventure Book Calendar"):
                if element.startswith("|k") and "|l" in element:
                    # use the part directly after the "|k " as the shortName of the new dict, and what follows after the "|l " as the longName:
                    variant["shortName"] = element.split("|k ")[1].split(" |l ")[0]
                    variant["longName"] = element.split("|k ")[1].split(" |l ")[1]

                # if k and l are present, but in the wrong order (starting with l, followed by k):
                elif element.startswith("|l") and "|k" in element:
                    # use the part directly after the "|l " as the longName of the new dict, and what follows after the "|k " as the shortName:
                    variant["longName"] = element.split("|l ")[1].split(" |k ")[0]
                    variant["shortName"] = element.split("|l ")[1].split(" |k ")[1]
                # if there is only a "|k ", use what comes after it as the shortName:
                elif element.startswith("|k") and "|l" not in element:
                    variant["shortName"] = element.split("|k ")[1]
                # if there is only one (or more) "|l ", but no "|k " at all:
                elif element.startswith("|l") and "|k" not in element:
                    # special case: if |l exists twice (somebody used l twice, the first one for the shortName), use the first one as the shortName and the second one as the longName:
                    if element.count("|l") == 2:
                        variant["shortName"] = element.split("|l ")[0]
                        variant["longName"] = element.split("|l ")[1]
                    else:
                        # only one |l and no |k, use what comes after it as the longName:
                        variant["longName"] = element.split("|l ")[1]
                    # what if somebody forgot to spearate all or some fields with a semicolon and we have run-on sequences like:
                    # |k CTQ-SF |l Childhood Trauma Questionnaire (Short-Form) |k CTS |l Childhood Trauma Screener?
                    # then we fix this at the SOURCE! Let _me_ handle this (and i will manually fix it _temporarily_ in my local xml file)!
                    # if there is no |k and no |l, use the whole string as the shortName:
                # now that we have the shortName and longName, we can add the variant object as a new element to the includedTestVariants array:
                includedTestVariants.append(variant)
                # print("includedTestVariants", includedTestVariants)
        except:
            print("VAR has no subfields in record: " + id, ": ", var)
            # var = var.text
            # add the whole string to the includedTestVariants array:
            # includedTestVariants.append(var)
        else:
            # add the includedTestVariants object to the test object:
            test_list[-1]["includedTestVariants"] = includedTestVariants

    # add the includedTestVariants to the test object - if it is not empty:
    # if includedTestVariants != None:
    #     test_list[-1]["includedTestVariants"] = includedTestVariants

    # get the authors from repeatable field AUP:
    authors = []
    roles = [" (Au.).", " (Ed.).", " (Org.)."]
    try:
        # check if fields ends with anything other than the roles above:
        for element in record.findall("AUP"):
            # if it does, add it to the authors array as a whole (not removing any role)):
            if not element.text.endswith(tuple(roles)):
                authors.append(element.text)
                print(
                    "AUP field (authors) in record "
                    + id
                    + " has no role, using full field: "
                    + element.text
                )
            # if it does not, remove the role and add it to the authors array:
            else:
                authors.append(element.text[:-7])
    except:
        print("AUP field (authors): none present in record " + id)
        # count up the number of records that have no authors:
        records_without_authors += 1
    else:
        # add the authors to the test object:
        test_list[-1]["authors"] = authors

    try:
        # get the publicationYear from PY:
        year = int(record.find("PY").text)
        # make sure it is a four-digit number, then try to convert it to an integer:
        # try:
        #     true_year = (
        #         year.isdigit() and len(year) == 4
        #     )  # should evaluate to true if year is a four-digit number
        # if the publicationYear is not a number (contains letters), print it and don't add it to the test object:
    except:
        # if the publicationYear is not a year in YYYY (contains letters), print it and don't add it to the test object:
        year = record.find("PY").text
        # count up the number of records that have no publicationYear:
        records_without_publicationYear += 1
        print(
            "PY (publicationYear) in record " + id + " is a string: " + year,
            "- omitting",
        )
    else:
        # check if the integer is a four-digit number - a true year in the YYYY sense:
        if year > 999 and year < 10000:
            # if it is, convert it to an integer and add it to the test object:
            test_list[-1]["publicationYear"] = year
        else:
            # count up the number of records that have no publicationYear:
            records_without_publicationYear += 1
            print(
                "PY (year) in record " + id + " is not in format YYYY: " + year,
                "- omitting",
            )

    # get the classifications found in the repeatable field PTSH1, adding them to the classifications array as strings, or if there are no PTSH1 fields at all, make the classifications array None:
    classifications = [element.text for element in record.findall("PTSH1")] or None
    try:
        len(
            classifications
        ) > 0  # should evaluate to true if classifications is not empty and false if it is empty/None -> on false the except block will be executed, on true the else block
    except:
        # print("PTSH1 field (classifications) not present in record: " + id)
        # count up the number of records that have no classifications:
        records_without_classifications += 1

    else:
        # add the classifications to the test object:
        test_list[-1]["classifications"] = classifications

    # get the type of record from BT ("Short" - only found in PTSHORT)
    # the levels are (by "complete"-ness): "Review" > "Abstract" > "Info" > "Short".
    # This indicates the level of detail or depth of analysis of this record.
    # in Bibframe, this would be the description level:
    # <TestWork> bf:adminMetadata [a bf:AdminMetadata; bf:descriptionLevel [a bf:DescriptionLevel; rdfs:label "Short", rdf:value 1]]]
    recordType = record.find("BT").text

    # add the recordType to the test object:
    test_list[-1]["bibliographicDescriptionDepth"] = recordType

    # dump the array to a json file:
    with open("tests.json", "w") as outfile:
        # make sure to encode any umlauts correctly:
        json.dump(test_list, outfile, ensure_ascii=False)

print("\n================= Stats ======================")
print("Total records exported: " + str(record_count))

# print the number of records that have no classifications:
print(
    "Number of records without classifications: " + str(records_without_classifications)
)
# print the number of records that have no publicationYear:
print(
    "Number of records without publicationYear: " + str(records_without_publicationYear)
)
# print the number of records that have no authors:
print("Number of records without author(s): " + str(records_without_authors))
# print the number of records that have no longName:
print("Number of records without longName: " + str(records_without_longName))
# print the number of records that have no shortName:
print("Number of records without shortName: " + str(records_without_shortName))
# print the number of records that have no englishName:
print("Records without englishName: " + str(records_without_englishName))
# print the number of records that have no synonyms:
print("Records without synonyms: " + str(records_without_synonyms))
print("Records with includedTestVariants: " + str(record_count - records_without_vars))
