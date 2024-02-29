# read the csv file lnam_all.csv and for each row, compare columns LNAM and caseCorrectedLNAM (casefolded) to see if they are the same string.
# If not, print the two strings side by side for comparison.
# The goal is to check if the semi-automated ML-based case correction process has worked correctly - as done by Github Co-Pilot.

import csv

with open("lnam_allcaps.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        lnam = row["LNAM"].casefold()
        caseCorrectedLNAM = row["caseCorrectedLNAM"].casefold()
        if lnam != caseCorrectedLNAM:
            # print both and indicate the actual differences after that:
            print(lnam + " | " + caseCorrectedLNAM)
            # print the differences:
            for i in range(len(lnam)):
                if lnam[i] != caseCorrectedLNAM[i]:
                    print(" " * i + "^")
                    break
