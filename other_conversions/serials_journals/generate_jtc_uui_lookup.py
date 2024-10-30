# go through the xml file XML_source/journals-241008_101417.xml and generate a lookup table.
# one line per record.
# first column: content of field JTC of the record
# second column: generate a UUID for each record
# serialize as a csv file.

import xml.etree.ElementTree as ET
import uuid

tree = ET.parse("XML_source/journals-241008_101417.xml")
root = tree.getroot()

# example output:
# JTC, UUID
# 0001, 0b3b3b3b-0b3b-4b3b-8b3b-0b3b3b3b3b3b

# save the output to a csv file
with open("jtc_uui_lookup.csv", "w") as f:
    f.write("JTC, UUID\n")
    for record in root.findall("Record"):
        JTC = record.find("JTC").text
        f.write(f"{JTC}, {uuid.uuid4()}\n")
