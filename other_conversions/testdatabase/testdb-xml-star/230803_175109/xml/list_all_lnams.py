import os
import csv
import xml.etree.ElementTree as ET

# Define the path of the XML file
xml_file_path = "/home/tina/Developement/py-star2bf/testdatabase/testdb-xml-star/230803_175109/records.xml"

# Parse the XML file
tree = ET.parse(xml_file_path)
root = tree.getroot()

# Open a CSV file in write mode
with open("records.csv", "w", newline="") as file:
    writer = csv.writer(file)

    # Write the headers to the CSV file
    writer.writerow(["ND", "LNAM"])

    # Iterate over each 'Record' in the XML file
    for record in root.findall("Record"):
        # For each 'Record', find 'ND' and 'LNAM' elements and get their text
        nd = record.find("ND").text
        lnam = record.find("LNAM").text

        # Write the 'ND' and 'LNAM' values to the CSV file
        writer.writerow([nd, lnam])
