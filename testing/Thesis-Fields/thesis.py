from calendar import c
import datetime
from itertools import count
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
import modules.identifiers as identifiers
import modules.namespace as ns
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
    "degreeGranted": None,
    "institute": None, # including place, should be written in Affiliation of first author, if not already there
    # we need to get the ror id and from there, especially if not in Affiliation:
    "institute_ror_id": None, # ror id of the institute, if available
    "institute_country": None, # country of the institute, if available
    "institute_country_geonames": None, # country of the institute, if available, as geonames id
    "thesisAdvisor": None, # first supervisor, optional, but at most one should be present
    "thesisReviewers": [], # second supervisor, optional, but can also be several
    "dateDegreeGranted": None, # date of the PhD thesis, optional?
    }
    if thesis.get("BE") == "SH" or thesis.get("DT") == "61" or thesis.get("DT2") == "61":
        print(f"\nyes, {index} is a  thesis. Processing it...")

        # get degree granted:
        if "GRAD" in thesis:
            thesis_infos["degreeGranted"] = thesis["GRAD"].strip()
            print("Degree granted: {}".format(thesis_infos["degreeGranted"]))
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
                        # look up geonames id for the country in mappings.geonames_countries -
                        # format is for each country in that table: ("Germany", "2921044", "DE")
                        if thesis_infos["institute_country"]:
                            try:
                                # use funtion helpers.country_geonames_lookup
                                geonames_id = helpers.country_geonames_lookup(thesis_infos["institute_country"])
                                thesis_infos["institute_country_geonames"] = geonames_id[1]
                                print("Institute country geonames id: {}".format(thesis_infos["institute_country_geonames"]))
                            except Exception as e:
                                print(f"Error getting geonames id for country {thesis_infos['institute_country']}: {e}")
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
    # print(thesis_infos)
    return thesis_infos

# generate nodes:
# - bf:Work, pxc:MainWork >> bf:dissertation > bf:Dissertation >> bf:degree "Dr. rer. nat." (from degreeGranted)
# - bf:Work, pxc:MainWork >> bf:dissertation > bf:Dissertation >> bf:date "2017" (from dateDegreeGranted)

def build_thesis_nodes(work_uri,thesis_info):
    """ Builds RDF nodes for the thesis information.
    
    Args:
        thesis_infos (dict): A dictionary with extracted thesis information.
        
    Returns:
        Graph: An RDF graph with the thesis information.
    """
    if thesis_info["degreeGranted"] or thesis_info["dateDegreeGranted"]:
        # add a dissertation node to the work:
        # create the node with type bf:Dissertation:
        # give it a unique URI:
        dissertation_uri = URIRef(
            str(work_uri) + "#dissertation")
        graph.add((dissertation_uri, RDF.type, ns.BF.Dissertation))
        graph.add((work_uri, ns.BF.dissertation, dissertation_uri))
    # add degreeGranted to the work:
    if thesis_info["degreeGranted"]:
        graph.add((dissertation_uri, ns.BF.degree, Literal(thesis_info["degreeGranted"])))
    # add dateDegreeGranted to the work:
    if thesis_info["dateDegreeGranted"]:
        graph.add((dissertation_uri, ns.BF.date, Literal(thesis_info["dateDegreeGranted"])))
    # add thesisAdvisor to the work:
    if thesis_info["thesisAdvisor"]:
        # create a URI for the thesis advisor:
        contribution_uri = URIRef(
            str(work_uri) + "#thesis_advisor")
        graph.add((contribution_uri, RDF.type, ns.BF.Contribution))
        graph.add((contribution_uri, RDF.type, ns.BF.ThesisAdvisory))
        graph.add((work_uri, ns.BF.contribution, contribution_uri))
        # add a node for the advisor agent, a Person:
        advisor_uri = URIRef(str(contribution_uri) + "_person")
        graph.add((advisor_uri, RDF.type, ns.BF.Person))
        # add the advisor to the contribution:
        graph.add((contribution_uri, ns.BF.agent, advisor_uri))
        # add the names of the advisor:
        graph.add((advisor_uri, ns.SCHEMA.familyName, Literal(thesis_info["thesisAdvisor"][0])))
        graph.add((advisor_uri, ns.SCHEMA.givenName, Literal(thesis_info["thesisAdvisor"][1])))
        # add role to the advisor:
        graph.add((contribution_uri, ns.BF.role, URIRef("http://id.loc.gov/vocabulary/relators/ths")))

        ## add thesis reviewers:
        for reviewer_index,reviewer in enumerate(thesis_info["thesisReviewers"]):
            # create a URI for the thesis reviewer:
            contribution_uri = URIRef(
                str(work_uri) + "#thesis_reviewer_" + str(reviewer_index+1))
            graph.add((contribution_uri, RDF.type, ns.BF.Contribution))
            graph.add((contribution_uri, RDF.type, ns.BF.ThesisReview))
            graph.add((work_uri, ns.BF.contribution, contribution_uri))
            # add a node for the reviewer agent, a Person:
            reviewer_uri = URIRef(str(contribution_uri) + "_person")
            graph.add((reviewer_uri, RDF.type, ns.BF.Person))
            # add the reviewer to the contribution:
            graph.add((contribution_uri, ns.BF.agent, reviewer_uri))
            # add the names of the reviewer:
            graph.add((reviewer_uri, ns.SCHEMA.familyName, Literal(reviewer[0])))
            graph.add((reviewer_uri, ns.SCHEMA.givenName, Literal(reviewer[1])))
            # add role to the reviewer:
            graph.add((contribution_uri, ns.BF.role, URIRef("https://id.loc.gov/vocabulary/relators/dgc")))  # dgc = degree committee member

    

# run through all theses and extract info
for index,thesis in enumerate(theses):
    thesis_info = get_thesis_info(index,thesis)
    # make a work node where we will attach the information:
    work_uri = URIRef(
        "https://w3id.org/zpid/testgraph/works/" + str(index))
    # add the work uri to the graph:
    graph.add((work_uri, RDF.type, ns.WORKS.Work))
    # build the thesis nodes:
    build_thesis_nodes(work_uri,thesis_info)
    # now we need a place for the institute and the country - it should be in the affiliation of the first author, if not already there.
    # but first, we need to create a contribution for the first author from AUP:
    if "AUP" in thesis:
        # create a URI for the first author contribution:
        first_author_contribution_uri = URIRef(
            str(work_uri) + "#contribution1")
        graph.add((first_author_contribution_uri, RDF.type, ns.BF.Contribution))
        graph.add((first_author_contribution_uri, RDF.type, ns.BFLC.PrimaryContribution))
        graph.add((work_uri, ns.BF.contribution, first_author_contribution_uri))
        # add a node for the first author agent, a Person:
        first_author_uri = URIRef(str(first_author_contribution_uri) + "_personagent")
        graph.add((first_author_uri, RDF.type, ns.BF.Person))
        # add the first author to the contribution:
        graph.add((first_author_contribution_uri, ns.BF.agent, first_author_uri))
        # add the names of the first author:
        first_author_name = helpers.split_family_and_given_name(thesis["AUP"].strip())
        graph.add((first_author_uri, ns.SCHEMA.familyName, Literal(first_author_name[0])))
        graph.add((first_author_uri, ns.SCHEMA.givenName, Literal(first_author_name[1])))
        # add role to the first author - we can leave this out for this test implementation - but maybe we can add an additional role for this dissertation person? http://id.loc.gov/vocabulary/relators/dis makes sense!
        graph.add((first_author_contribution_uri, ns.BF.role, URIRef("http://id.loc.gov/vocabulary/relators/dis")))  # dis = dissertatant
        ## NOTE: to implement this for the real thing, we need to go through the first author we already added to the graph, and add this additional role to the existing contribution. Also, to check if there is already an affiliation with a country and ror id, and if not, add it to the existing contribution.
        # For this test, we will just add it to the first author contribution:
        if thesis_info["institute"]:
            # add the institute to the first author contribution:
            # create a node:
            affiliation_uri = URIRef(str(first_author_contribution_uri) + "_personagent_affiliation1")
            graph.add((affiliation_uri, RDF.type, ns.MADS.Affiliation))
            graph.add((first_author_contribution_uri, ns.MADS.hasAffiliation, affiliation_uri))
            # the name will be part of the organization of the affiliation:
            affilorganization_uri = URIRef(str(affiliation_uri) + "_organization")
            graph.add((affilorganization_uri, RDF.type, ns.BF.Organization))
            graph.add((affiliation_uri, ns.BF.organization, affilorganization_uri))
            # add the name of the organization:
            graph.add((affilorganization_uri, RDFS.label, Literal(thesis_info["institute"])))
            # if we have a ror id, add it to the first author contribution:
            if thesis_info["institute_ror_id"]:
                # add it as an identifiedby to the organization:
                rorid_uri = URIRef(str(affilorganization_uri) + "_rorid")
                graph.add((affilorganization_uri, ns.BF.identifiedBy, rorid_uri))
                graph.add((rorid_uri, RDF.type, ns.LOCID.rorid))
                graph.add((rorid_uri, RDF.value, Literal(thesis_info["institute_ror_id"])))
                
            # if we have a country, add it to the first author contribution affilitation as an address:
            if thesis_info["institute_country"]:
                # create an address node:
                address_uri = URIRef(str(affiliation_uri) + "_address")
                graph.add((address_uri, RDF.type, ns.MADS.Address))
                country_uri = URIRef(str(address_uri) + "_country")
                graph.add((country_uri, RDF.type, ns.MADS.Country))
                # add the country to the address:
                graph.add((country_uri, RDFS.label, Literal(thesis_info["institute_country"])))
                # add the address to the affiliation:
                graph.add((address_uri, ns.MADS.country, country_uri))
                if thesis_info["institute_country_geonames"]:
                    # add the geonames id to the country:
                    geonames_uri = URIRef(str(country_uri) + "_geonamesid")
                    graph.add((country_uri, ns.BF.identifiedBy, geonames_uri))
                    graph.add((geonames_uri, RDF.type, ns.LOCID.geonames))
                    graph.add((geonames_uri, RDF.value, Literal(thesis_info["institute_country_geonames"])))
        else:
            print("No institute found in AUP, INST or ORT, cannot add affiliation to first author contribution.")

# serialize the graph to a file:
graph.serialize("test_thesis.ttl", format="turtle")