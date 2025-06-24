from calendar import c
import datetime
import logging
import dateparser
import html

import re
import sys
import os

# go up from testing/REL to the root of the project and then import modules- 
# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
# import modules
import modules.mappings as mappings
import modules.helpers as helpers
import modules.research_info as research_info
import modules.local_api_lookups as local_api_lookups

# logging.basicConfig(
#     filename=datetime.now().strftime("logs/thesis-%Y_%m_%d_%H%M%S.log"),
#     level=logging.INFO,
# )

theses = [
    { "BE": "SM", "DT":"61", "DT2": "01", "AUP":"Naumer, Marcus Johannes |f AU", "GRAD": "Dr. phil.", "PD": "19.12.2006", "PROMY": "2006", "INST": "University, Faculty of Psychology and Neuroscience",
      "ORT": "Maastricht", "HRF": "Goebel, R. W." }, # BE nicht SH, sondern nur aus DT/DT2 erkennbar; kein KRF, keine Affil in AUP
    {"BE":"SH", "DT":"61", "AUP": "Hansmann, Ralf |f AU |c SWITZERLAND |i Natural and Social Science Interface (NSSI), Department of Environmental Sciences, ETH Zurich","GRAD": "Dr. habil.", "PD":"14.12.99","PROMY": "2009", "INST": "ETH Zurich; Department of Environmental Systems Science", "ORT": "Zurich"}, # BE ist SH, AUP mit Affil, weder KRF noch HRF
    {"BE":"SH", "DT":"61", "AUP": "Olteteanu, Ana-Maria", "GRAD": "Dr. rer. nat.", "PD": "N. N.", 
     "PROMY": "2016","INST":"Universität, Fachbereich Mathematik/Informatik", "ORT":"Bremen",
    "HRF": "Freksa, C.", "KRF": ["Plaza, Enric", "Sloman, Aaron"]}# PD ist kein Datum, keine Affil in AUP
]



def get_thesis_info(index,thesis):
    """
    Extracts thesis information from the given thesis dictionary.
    
    Args:
        thesis (dict): A record with fields relevant for generating thesis information.
        
    Returns:
        dict: A dictionary with extracted thesis information.
    """
    thesis_infos = {
    "degree_granted": None,
    "institute": None, # including place, should be written in Affiliation of first author, if not already there
    # we need to get the ror id and from there, especially if not in Affiliation:
    "institute_ror_id": None, # ror id of the institute, if available
    "institute_country": None, # country of the institute, if available
    "thesisAdvisor": None, # first supervisor, optional, but at most one should be present
    "thesisReviewers": [], # second supervisor, optional, but can also be several
    "dateDegreeGranted": None, # date of the PhD thesis, optional?
    }
    if thesis.get("BE") == "SH" or thesis.get("DT") == "61" or thesis.get("DT2") == "61":
        print(f"\nyes, {index} is a  thesis. Processing it...")

        # get degree granted:
        if "GRAD" in thesis:
            thesis_infos["degree_granted"] = thesis["GRAD"].strip()
            print("Degree granted: {}".format(thesis_infos["degree_granted"]))
        else:
            print("No degree found.")

        # check AUP affiliation for institute and place, otherwise concatenate INST and ORT:
        if "AUP" in thesis:
        # it contains a pipe |i, which is the subfield for institute:
            if "|i" in thesis["AUP"]:
            # get subfield i:
                try:
                    # use helpers.get_subfield(field, i):
                    thesis_infos["institute"] = helpers.get_subfield(thesis["AUP"], "i").strip()
                    print("Institute from AUP: {}".format(thesis_infos["institute"]))
                except KeyError:
                    print("No institute found in AUP.")
            else:
                print("No institute found in AUP, trying INST + ORT instead.")
                # if no institute found in AUP, try INST + ORT:
                if "INST" in thesis and "ORT" in thesis:
                    # try to concatenate sensibly: first check INST if it has a comma, than insert ORT before the comma:
                    if "," in thesis["INST"]:
                        # split INST at the comma, take the first part and add ORT and then the rest of INST:
                        thesis_infos["institute"] = thesis["INST"].split(",")[0].strip() + " " + thesis["ORT"].strip() + ", " + thesis["INST"].split(",")[1].strip()
                    else:
                        # just concatenate INST and ORT:
                        thesis_infos["institute"] = thesis["INST"].strip() + " " + thesis["ORT"].strip()
                    print("Institute from INST + ORT: {}".format(thesis_infos["institute"]))
                else:
                    print("No institute found in AUP, INST or ORT.")
            # if we have an institute, get the ror-id from the api, as well as the country:
            if thesis_infos["institute"]:
                # get the ror-id and country from the api;
                # use get_ror_id_from_api in main program:
                try:
                    ror_id = local_api_lookups.get_ror_id_from_api(thesis_infos["institute"])
                    thesis_infos["institute_ror_id"] = ror_id
                    print("ROR ID: {}".format(thesis_infos["institute_ror_id"]))
                    # if we have a ror id, get the country from the api:
                    try:
                        institute_country = local_api_lookups.get_ror_org_country(ror_id)
                        thesis_infos["institute_country"] = institute_country
                        print("Institute country: {}".format(thesis_infos["institute_country"]))
                    except Exception as e:
                        print(f"Error getting institute country: {e}")
                except Exception as e:
                    print(f"Error getting ROR ID: {e}")
        
            else:
                print("No institute found, cannot get ROR ID or country.")


        # get HRF:
        if "HRF" in thesis:
            # split into given and family name, if possible
            thesis_infos["thesisAdvisor"] = helpers.split_family_and_given_name(thesis["HRF"].strip())
            print("Hauptreferent: {}".format(thesis_infos["thesisAdvisor"]))
        else:
            print("No HRF found.")
        
        # get KRFs:
        if "KRF" in thesis:
            for count,krf in enumerate(thesis["KRF"]):
                thesis_infos["thesisReviewers"].append(helpers.split_family_and_given_name(krf.strip()))
                print("Nebenreferent {}: {}".format(count+1,thesis_infos["thesisReviewers"][-1]))
        else:
            print("No KRFs found.")
        # getting a date of the thesis:
        try:
            dateDegreeGranted =  thesis.get("PD").strip()  # PD is the date of the thesis, if it exists
            # check if this really contains any digits, otherwise, this won't be a date (e.g. "N. N."):
            if not re.match(r"^\d", dateDegreeGranted):
                raise ValueError(f"Invalid date format: {dateDegreeGranted}")
                # and move on to the exception handling below
                
            # parse the date: it can be either "8 June 2021" or "08.06.2021"
            # parse and convert this to the yyyy-mm-dd format:
            dateDegreeGranted = dateparser.parse(dateDegreeGranted, settings={'PREFER_DATES_FROM': 'past','PREFER_DAY_OF_MONTH': 'first','PREFER_MONTH_OF_YEAR': 'first'}).strftime("%Y-%m-%d")
            print(f"Parsed date: {dateDegreeGranted}")
            # write into thesis_infos:
            thesis_infos["dateDegreeGranted"] = dateDegreeGranted
        except:
            print(
                f"parsedate: couldn't parse {str(dateDegreeGranted)} for {index}! Trying to use PROMY instead!"
            )
            # print(
            #     "Data in PD looks like an unsalvagable mess, using PY insead!"
            # )
            try:
                dateDegreeGranted =  thesis.get("PROMY")  # PROMY is the year of the thesis, if it exists
                print(f"Using PROMY for {index}: {dateDegreeGranted}")
                # write into thesis_infos:
                thesis_infos["dateDegreeGranted"] = dateDegreeGranted
            except:
                print(
                    f"no PROMY found for {index}! Using None instead!"
                )
                dateDegreeGranted = None
    print(thesis_infos)

# run through all theses and extract info
for index,thesis in enumerate(theses):
    get_thesis_info(index,thesis)