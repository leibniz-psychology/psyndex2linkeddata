# go through the xml file XML_source/journals-241008_101417.xml and generate a lookup table.
# one line per record.
# first column: content of field JTTI of the record
# second column: content of the field JTRV of the record
# serialize as a csv file.

import xml.etree.ElementTree as ET

tree = ET.parse("XML_source/journals-241008_101417.xml")
root = tree.getroot()

# example output:
# JTC, UUID
# 0001, 0b3b3b3b-0b3b-4b3b-8b3b-0b3b3b3b3b3b

# save the output to a csv file
with open("title_reviewnote.csv", "w") as f:
    f.write("JTC;JTTI;JTRV\n")
    for record in root.findall("Record"):
        if record.find("JTRV") is not None:
            if record.find("JTTI") is not None:
                JTC = record.find("JTC").text
                JTRV = record.find("JTRV").text
                JTTI = record.find("JTTI").text
                f.write(f"{JTC};{JTTI};{JTRV}\n")
