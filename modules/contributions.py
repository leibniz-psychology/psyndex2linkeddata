import html
import re
from modules import helpers, local_api_lookups, mappings
from fuzzywuzzy import fuzz, process
from rdflib import RDF, RDFS, Graph, Literal, URIRef
import logging

import modules.namespace as ns

graph = Graph()

graph.bind("bf", ns.BF)
graph.bind("pxc", ns.PXC)
graph.bind("pxp", ns.PXP)
graph.bind("works", ns.WORKS)
graph.bind("contenttypes", ns.CONTENTTYPES)
graph.bind("genres", ns.GENRES)
graph.bind("pmt", ns.PMT)
graph.bind("methods", ns.METHODS)

def build_journal_person_contribution_node(contribution_id, agent_name, role):
    contribution_node = URIRef(str(contribution_id))
    graph.add((contribution_node, RDF.type, ns.BF.Contribution))
    graph.add(
        (
            contribution_node,
            ns.BF.role,
            URIRef(str(role)),
        )
    )
    agent_node = URIRef(str(contribution_node) + "_agent_new")
    graph.add((contribution_node, ns.BF.agent, agent_node))
    graph.add((agent_node, RDFS.label, Literal(agent_name)))
    graph.add((agent_node, RDF.type, ns.BF.Person))
    return contribution_node

def build_affiliation_nodes(graph, agent_node, agent_affiliation, agent_affiliation_country):
    """
    Builds and returns an affiliation node (URIRef) with attached organization and country/address nodes as appropriate.

    Args:
        agent_node: The URIRef of the agent (person or organization).
        agent_affiliation: The name of the affiliation organization (str or None).
        agent_affiliation_country: The name of the affiliation country (str or None).

    Returns:
        URIRef: The URIRef of the created affiliation node.
    """
    # person_affiliation = replace_encodings(person_affiliation)
    # is passed two string: the affiliation name and the affiliation country name
    # make a fragement uri node for the affiliation (use agent node as base) and make it class mads:Affiliation:
    agent_affiliation_node = URIRef(str(agent_node) + "_affiliation1")
    graph.add((agent_affiliation_node, RDF.type, ns.MADS.Affiliation))
    # make a fragment uri node for the affiliation organization and make it class bf:Organization:
    # but only for person agents. Org agents will not get an additial affiliation org node (we will pass an empty string for orgs that need an affiliation node to hold their address).
    if agent_affiliation is not None and agent_affiliation != "":
        agent_affiliation_org_node = URIRef(
            str(agent_affiliation_node) + "_organization"
        )
        graph.set((agent_affiliation_org_node, RDF.type, ns.BF.Organization))
        # add the affiliation organization node to the affiliation node:
        graph.add(
            (agent_affiliation_node, ns.MADS.organization, agent_affiliation_org_node)
        )
        # add the affiliation string to the affiliation org node:
        graph.add(
            (agent_affiliation_org_node, RDFS.label, Literal(agent_affiliation))
        )

    # Attempt a ROR lookup for the affiliation string; if the lookup fails or returns no result, no ROR ID will be added.
    # and if there is a ror id, add the ror id as an identifier:
    affiliation_ror_id = None
    if agent_affiliation is not None and agent_affiliation != "":
        affiliation_ror_id = local_api_lookups.get_ror_id_from_api(agent_affiliation)

        if affiliation_ror_id is not None and affiliation_ror_id != "null":
            # create a fragment uri node fore the identifier:
            affiliation_ror_id_node = URIRef(str(agent_affiliation_org_node) + "_rorid")
            # make it a locid:ror:
            graph.set((affiliation_ror_id_node, RDF.type, ns.LOCID.ror))
            # add the ror id as a literal to the identifier node:
            graph.add(
                (affiliation_ror_id_node, RDF.value, Literal(affiliation_ror_id))
            )
            graph.add(
                (agent_affiliation_org_node, ns.BF.identifiedBy, affiliation_ror_id_node)
            )
    else:
        affiliation_ror_id = None
    # Only try to use agent_affiliation_org_node if it was defined
    # else:
    # print("no ror id found for " + person_affiliation)
    #### unused: matching luxembourg Affiliation names to local authority table in our csv:
    # affiliation_local_id = None
    # affiliation_local_id = get_local_authority_institute(
    #     person_affiliation, person_affiliation_country
    # )
    # if affiliation_local_id is not None:
    #     # add a blank node fore the identifier:
    #     affiliation_local_id_node = BNode()
    #     # make it a pxc:OrgID:
    #     graph.add((affiliation_local_id_node, RDF.type, PXC.OrgID))
    #     graph.add(
    #         (person_affiliation_org_node, ns.BF.identifiedBy, affiliation_local_id_node)
    #     )
    #     # add the local uuid as a literal to the identifier node:
    #     graph.add(
    #         (affiliation_local_id_node, RDF.value, Literal(affiliation_local_id))
    #     )

    # TODO: sometimes people have an affiliation, but no country (no |c subfield).
    # currently we dont handle that at all and a country label "None" is added
    # where we should just not add an AffiliationAdress node with a country node at all.
    if agent_affiliation_country is None or agent_affiliation_country == "":
        # try to check if we have a ror id for the affiliation and get the country from the ror api:
        try:
            if affiliation_ror_id is not None:
                agent_affiliation_country = local_api_lookups.get_ror_org_country(affiliation_ror_id)
            else:
                agent_affiliation_country = None
        except:
            agent_affiliation_country = None

    # Only create the address and country nodes if the country is not None or empty
    if agent_affiliation_country is not None and agent_affiliation_country != "":
        person_affiliation_address_node = URIRef(
            str(agent_affiliation_node) + "_address"
        )
        graph.add((person_affiliation_address_node, RDF.type, ns.MADS.Address))
        # add a country node to the affiliation address node:
        person_affiliation_country_node = URIRef(
            str(person_affiliation_address_node) + "_country"
        )
        graph.add((person_affiliation_country_node, RDF.type, ns.MADS.Country))
        # add the country node to the affiliation address node:
        graph.add(
            (
                person_affiliation_address_node,
                ns.MADS.country,
                person_affiliation_country_node,
            )
        )
        # add the affiliation address string to the affiliation address node:
        graph.add(
            (
                person_affiliation_country_node,
                RDFS.label,
                Literal(agent_affiliation_country),
            )
        )

        # if the country is in the geonames lookup table, add the geonames uri as sameAs and the geonames id as an identifier:
        geonames_lookup_result = helpers.country_geonames_lookup(agent_affiliation_country)
        if geonames_lookup_result:
            improved_country_name, geonamesId = geonames_lookup_result
            # create a url to click and add it with sameas:
            # geonames_uri = URIRef("http://geonames.org/" + geonamesId + "/")
            # graph.add((person_affiliation_country_node, SCHEMA.sameAs, geonames_uri))
            
            # replace the country name in the affiliation address node with the improved country name:
            # graph.add(
            #     (
            #         person_affiliation_country_node,
            #         RDFS.label,
            #         Literal(improved_country_name),
            #     )
            # )
            # # and remove the old label:
            # graph.remove(
            #     (
            #         person_affiliation_country_node,
            #         RDFS.label,
            #         Literal(agent_affiliation_country),
            #     )
            # )
            # use set to replace the label with the improved country name:
            graph.set(
                (
                    person_affiliation_country_node,
                    RDFS.label,
                    Literal(improved_country_name),
                )
            )
            # print("geonames lookup: found geonames id " + geonamesId + " for country " + improved_country_name)
            # add the geonames identifier only if geonamesId is not None:
            if geonamesId is not None:
                person_affiliation_country_identifier_node = URIRef(
                    str(person_affiliation_country_node) + "_geonamesid"
                )
                # graph.add((person_affiliation_country_identifier_node, RDF.type, ns.BF.Identifier))
                graph.add(
                    (
                        person_affiliation_country_identifier_node,
                        RDF.type,
                        ns.LOCID.geonames,
                    )
                )
                graph.add(
                    (
                        person_affiliation_country_identifier_node,
                        RDF.value,
                        Literal(geonamesId),
                    )
                )
                graph.add(
                    (
                        person_affiliation_country_node,
                        ns.BF.identifiedBy,
                        person_affiliation_country_identifier_node,
                    )
                )
        # add the affiliation address node to the affiliation node:
        graph.add(
            (
                agent_affiliation_node,
                ns.MADS.hasAffiliationAddress,
                person_affiliation_address_node,
            )
        )
    # If country is missing, skip address node creation entirely
    # return the finished affiliation node with all its children and attached strings:
    return agent_affiliation_node

def generate_bf_contribution_node(graph,work_uri, record, contribution_counter):
    # will be called by functions that add AUPs and AUKS
    # adds a bf:Contribution node, adds the position from a counter, and returns the node.
    contribution_qualifier = None
    # make the node and add class:
    contribution_node = URIRef(work_uri + "#contribution" + str(contribution_counter))
    graph.add((contribution_node, RDF.type, ns.BF.Contribution))

    # add author positions:
    graph.add(
        (
            contribution_node,
            ns.PXP.contributionPosition,
            Literal(contribution_counter),
        )
    )
    # if we are in the first loop, set contribution's bf:qualifier" to "first":
    if contribution_counter == 1:
        contribution_qualifier = "first"
        graph.add((contribution_node, RDF.type, ns.BFLC.PrimaryContribution))
    # if we are in the last loop, set "contribution_qualifier" to "last":
    elif contribution_counter == len(record.findall("AUP")) + len(
        record.findall("AUK")
    ):
        contribution_qualifier = "last"
    # if we are in any other loop but the first or last, set "contribution_qualifier" to "middle":
    else:
        contribution_qualifier = "middle"
    # add the contribution qualifier to the contribution node:
    graph.add(
        (contribution_node, ns.BF.qualifier, Literal(contribution_qualifier))
    )
    # finally, return the finished contribution node so we can add our agent and affiliation data to it in their own functions:
    return contribution_node

# the full function that creates a contribution node for each person in AUP:
# first, get all AUPs in a record and create a node for each of them
def add_bf_contributor_person(graph,work_uri, record):
    # initialize a counter for the contribution position and a variable for the contribution qualifier:
    # contribution_counter = 0
    # contribution_qualifier = None

    for index, person in enumerate(record.findall("AUP")):
        # count how often we've gone through the loop to see the author position:

        # do all the things a contribution needs in another function (counting and adding positions, generating fragment uri)
        contribution_node = generate_bf_contribution_node(graph,work_uri, record, index + 1)

        # make a fragment uri node for the person:
        person_node = URIRef(str(contribution_node) + "_personagent")
        graph.add((person_node, RDF.type, ns.BF.Person))

        # add the name from AUP to the person node, but only use the text before the first |: (and clean up the encoding):
        personname = mappings.replace_encodings(
            helpers.get_mainfield(person.text)
        ).strip()

        graph.add((person_node, RDFS.label, Literal(personname)))

        # initialize variables for later use:
        # (removed unused variables)

        # split personname into first and last name:
        personname_split = personname.split(",")
        try:
            familyname = personname_split[0].strip()
            givenname = personname_split[1].strip()
        except:
            familyname = personname
            givenname = ""
            logging.info(
                "no comma in personname: "
                + personname
                + " in record "
                + record.find("DFK").text
                + " - name content added as familyname + empty string for givenname."
            )

        graph.add((person_node, ns.SCHEMA.familyName, Literal(familyname)))
        graph.add((person_node, ns.SCHEMA.givenName, Literal(givenname)))
        # generate a normalized version of familyname to compare with PAUP name later:
        # personname_normalized = normalize_names(familyname, givenname)
        # for debugging, print the normalized name:
        # graph.add((person_node, PXP.normalizedName, Literal(personname_normalized)))

        # # check if there is a PAUP field in the same record that matches the personname from this AUP:
        # paId = match_paup(record, person_node, personname_normalized)
        # if paId is not None:
        #     # create a fragment uri node for the identifier:
        #     psychauthors_identifier_node = URIRef(str(person_node) + "_psychauthorsid")
        #     graph.add((psychauthors_identifier_node, RDF.type, PXC.PsychAuthorsID))
        #     graph.add((psychauthors_identifier_node, RDF.value, Literal(paId)))
        #     # add the identifier node to the person node:
        #     graph.add((person_node, ns.BF.identifiedBy, psychauthors_identifier_node))

        # call the function get_orcid to match the personname with the ORCIDs in the record - so for every person in an AUP, we check all the ORCID fields in the record for a name match:
        # orcidId = match_orcid(record, person_node, personname_normalized)
        # if orcidId is not None:
        #     # create a fragment node for the identifier:
        #     orcid_identifier_node = URIRef(str(person_node) + "_orcid")
        #     # graph.add((orcid_identifier_node, RDF.type, ns.BF.Identifier))
        #     graph.add((orcid_identifier_node, RDF.type, LOCID.orcid))
        #     graph.add((orcid_identifier_node, RDF.value, Literal(orcidId)))
        #     # add the identifier node to the person node:
        #     graph.add((person_node, ns.BF.identifiedBy, orcid_identifier_node))
        #     # add the orcid id as a sameAs link to the person node:
        #     # orcid_uri = "https://orcid.org/" + orcidId
        #     # graph.add((person_node, SCHEMA.sameAs, URIRef(orcid_uri)))
        # else:
        #     print(
        #         "no orcid found for "
        #         + personname
        #         + " in DFK "
        #         + record.find("DFK").text
        #     )

        ## -----
        # Getting Affiliations and their countries from first, CS and COU (only for first author), and then from subfields |i and |c in AUP (for newer records)
        ## -----

        # initialize variables we'll need for adding affiliations and country names from AUP |i and CS/COU/ADR:
        affiliation_string = None
        affiliation_country = None

        # match affiliations in CS and COU to first contribution/author:
        # dont add ADR here yet (even if this is the place for it - we may drop that info anyway.
        # look for the field CS:
        # if the contribution_counter is 1 (i.e. if this is the first loop/first author), add the affiliation to the person node:
        # if contribution_counter == 1:
        #     if record.find("CS") is not None:
        #         print("CS field found in record " + record.find("DFK").text)
        #         # get the content of the CS field:
        #         affiliation_string = html.unescape(
        #             mappings.replace_encodings(record.find("CS").text.strip())
        #         )

        #     if record.find("COU") is not None:
        #         # get the country from the COU field:
        #         affiliation_country = mappings.replace_encodings(
        #             helpers.sanitize_country_names(record.find("COU").text.strip())
        #         )

        ## Get affiliation from AUP |i, country from |c:
        # no looping necessary here, just check if a string |i exists in AUP and if so, add it to the person node as the affiliation string:
        affiliation_string = helpers.get_subfield(person.text, "i")

        affiliation_country = helpers.sanitize_country_names(
            helpers.get_subfield(person.text, "c")
        )

        # pass this to function build_affiliation_nodes to get a finished affiliation node:
        if (
            (affiliation_string is not None and affiliation_string.strip() != "")
            or (affiliation_country is not None and affiliation_country.strip() != "") # so the affiliation node is not added if both are None or empty
        ):
            affiliation_node = build_affiliation_nodes(
                graph, person_node, affiliation_string, affiliation_country
            )
            graph.add(
                (contribution_node, ns.MADS.hasAffiliation, affiliation_node)
            )
        else:
            print("no affiliation string or country found for " + personname + " in record   " + record.find("DFK").text + ". No affiliation node added.")
            # but why is it added anyway? is there another affiliation node added later?
        # add the role from AUP subfield |f to the contribution node:
        # extracting the role:
        # check if there is a role in |f subfield and add as a role, otherwise set role to AU
        role = extract_contribution_role(person.text, record)
        graph.set((contribution_node, ns.BF.role, add_bf_contribution_role(role)))
        

        ## --- Add the contribution node to the work node:
        graph.add((work_uri, ns.BF.contribution, contribution_node))
        # add the person node to the contribution node as a contributor:
        graph.add((contribution_node, ns.BF.agent, person_node))

### Matching PsychAuthors IDs and ORCIDs to AUPs:

# import the graph for kerndaten.ttl from PsychAuthors - we'll need it for
# matching person names to ids when the names in the records are unmatchable
# - we'll try to match alternate names from kerndaten:
kerndaten = Graph()
kerndaten.parse("ttl-data/kerndaten.ttl", format="turtle")

def match_paups_to_contribution_nodes(graph,work_uri, record):
    # go through all PAUP fields and get the id:
    for paup in record.findall("PAUP"):
        paup_id = helpers.get_subfield(paup.text, "n")
        paup_name = helpers.get_mainfield(paup.text)
        # get the given and family part of the paup name:
        paup_split = paup_name.split(",")
        paup_familyname = paup_split[0].strip()
        paup_givenname = paup_split[1].strip()
        paupname_normalized = normalize_names(paup_familyname, paup_givenname)
        # print("paupname_normalized: " + paupname_normalized)
        # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
        for contribution in graph.objects(work_uri, ns.BF.contribution):
            # get the agent of the contribution:
            agent = graph.value(contribution, ns.BF.agent)
            # if the agent is a person, get the given and family names:
            if graph.value(agent, RDF.type) == ns.BF.Person:
                # get the given and family names of the agent:
                givenname = graph.value(agent, ns.SCHEMA.givenName)
                familyname = graph.value(agent, ns.SCHEMA.familyName)
                aupname_normalized = normalize_names(familyname, givenname)
                # print("aupname_normalized: " + aupname_normalized)
                # if the paupname_normalized matches the agent's name, add the paup_id as an identifier to the agent:
                # if paupname_normalized == aupname_normalized:
                # check using fuzzywuzzy:
                # use partial_ratio for a more lenient comparison - so we can check if one of the them is a substring of the other - for double names, etc.:
                if fuzz.partial_ratio(paupname_normalized, aupname_normalized) > 80:
                    # create a fragment uri node for the identifier:
                    paup_id_node = URIRef(str(agent) + "_psychauthorsid")
                    # make it a locid:psychAuthorsID:
                    graph.set((paup_id_node, RDF.type, ns.PXC.PsychAuthorsID))
                    # add the paup id as a literal to the identifier node:
                    graph.add((paup_id_node, RDF.value, Literal(paup_id)))
                    # add the identifier node to the agent node:
                    graph.add((agent, ns.BF.identifiedBy, paup_id_node))
                    # print("paup_id added to agent: " + paup_id)
                    # and break the loop:
                    break
        # after all loops, print a message if no match was found:
        else:
            logging.info(
                "no match found for paup_id "
                + paup_id
                + " ("
                + paup_name
                + ")"
                + " in record "
                + record.find("DFK").text
                + ". Checking name variants found in kerndaten for this id..."
            )
            # loop through the contribtors again, and check if any of the alternate names from psychauthors kerndaten match a person's name from AUP:
            for contribution in graph.objects(work_uri, ns.BF.contribution):
                # get the agent of the contribution:
                agent = graph.value(contribution, ns.BF.agent)
                # if the agent is a person, get the given and family names:
                if graph.value(agent, RDF.type) == ns.BF.Person:
                    # get the given and family names of the agent:
                    givenname = graph.value(agent, ns.SCHEMA.givenName)
                    familyname = graph.value(agent, ns.SCHEMA.familyName)
                    aupname_normalized = normalize_names(familyname, givenname)
                    # try to match the paup_id to a uri in kerndaten.ttl and check if any of the alternate names match the agent's name:
                    person_uri = URIRef("https://w3id.org/zpid/person/" + paup_id)
                    for alternatename in kerndaten.objects(
                        person_uri, ns.SCHEMA.alternateName
                    ):
                        # split the alternatename into family and given name:
                        alternatename_split = alternatename.split(",")
                        alternatename_familyname = alternatename_split[0].strip()
                        alternatename_givenname = alternatename_split[1].strip()
                        # normalize the name:
                        alternatename_normalized = normalize_names(
                            alternatename_familyname, alternatename_givenname
                        )
                        # if the alternatename matches the agent's name, add the paup_id as an identifier to the agent: again using fuzzywuzzy'S partial ratio to also match substrings of the name inside each other:
                        if (
                            fuzz.partial_ratio(
                                alternatename_normalized, aupname_normalized
                            )
                            > 80
                        ):
                            # create a fragment uri node for the identifier:
                            paup_id_node = URIRef(str(agent) + "_psychauthorsid")
                            # make it a locid:psychAuthorsID:
                            graph.set(
                                (paup_id_node, RDF.type, ns.PXC.PsychAuthorsID)
                            )
                            # add the paup id as a literal to the identifier node:
                            graph.add((paup_id_node, RDF.value, Literal(paup_id)))
                            # add the identifier node to the agent node:
                            graph.add((agent, ns.BF.identifiedBy, paup_id_node))
                            logging.info("paup_id added to agent: " + paup_id)

def match_orcids_to_contribution_nodes(graph,work_uri, record):
    # go through all ORCID fields and get the id:
    for orcid in record.findall("ORCID"):
        # print("orcid: " + orcid.text)
        orcid_id = helpers.get_subfield(orcid.text, "u")
        orcid_name = helpers.get_mainfield(orcid.text)
        # is the orcid well formed?
        # clean up the orcid_id by removing spaces that sometimes sneak in when entering them in the database:
        if orcid_id is not None and " " in orcid_id:
            logging.warning(
                "warning: orcid_id contains spaces, cleaning it up: " + orcid_id
            )
        orcid_id = orcid_id.replace(" ", "")
        # by the way, here is a regex pattern for valid orcids:
        orcid_pattern = re.compile(
            r"^(https?:\/\/(orcid\.)?org\/)?(orcid\.org\/)?(\/)?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])$"
        )
        if orcid_pattern.match(orcid_id):
            # remove the prefixes and slashes from the orcid id:
            orcid_id = orcid_pattern.match(orcid_id).group(5)
        else:
            # warn if it doesn't match the pattern for well-formed orcids:
            logging.warning(f"warning: invalid orcid: {orcid_id}")
        # get the given and family part of the orcid name:
        # make sure we give an error message when we can't split:
        try:
            orcid_split = orcid_name.split(",")
            orcid_familyname = orcid_split[0].strip()
            orcid_givenname = orcid_split[1].strip()
            orcidname_normalized = normalize_names(orcid_familyname, orcid_givenname)
        except:
            logging.info(
                "couldn't split orcid name into given and family name: "
                + orcid_name
                + " in record "
                + record.find("DFK").text
                + ". Using the full name as a fallback."
            )
            orcidname_normalized = (
                orcid_name  # if we can't split, just try the full name
            )
        # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person - and match names to those in the orcid field:
        for contribution in graph.objects(work_uri, ns.BF.contribution):
            # get the agent of the contribution:
            agent = graph.value(contribution, ns.BF.agent)
            # if the agent is a person, get the given and family names:
            if graph.value(agent, RDF.type) == ns.BF.Person:
                # get the given and family names of the agent:
                givenname = graph.value(agent, ns.SCHEMA.givenName)
                familyname = graph.value(agent, ns.SCHEMA.familyName)
                aupname_normalized = normalize_names(familyname, givenname)

                # if the orcidname_normalized matches the agent's name, add the orcid_id as an identifier to the agent:

                # check using fuzzywuzzy - use partial_ratio to check if one of the them is a substring of the other:
                if fuzz.partial_ratio(aupname_normalized, orcidname_normalized) > 80:
                    # create a fragment uri node for the identifier:
                    orcid_id_node = URIRef(str(agent) + "_orcid")
                    # make it a locid:orcid:
                    graph.set((orcid_id_node, RDF.type, ns.LOCID.orcid))
                    # add the orcid id as a literal to the identifier node:
                    graph.add((orcid_id_node, RDF.value, Literal(orcid_id)))
                    # add the identifier node to the agent node:
                    graph.add((agent, ns.BF.identifiedBy, orcid_id_node))
                    # print("orcid_id added to agent: " + orcid_id)
                    # and break the loop:
                    break
        # after all loops, print a message if no match was found:
        else:
            logging.info(
                "no match found for orcid_id "
                + orcid_id
                + " ("
                + orcid_name
                + ") in record "
                + record.find("DFK").text
            )

### Match email addresses and older affiliations in CS and COU to contribution nodes:
def match_email_to_contribution_nodes(graph,work_uri, record):
    # there is only ever one email field in a record, so we can just get it.
    # unless there is also a field emid, the email will be added to the first contribution node.
    # if there is an emid, the email will be added to the person with a name matching the name in emid.
    # fortunately, the name in EMID should always be exactly the same as the one in an AUP field
    # (unlike for PAUP and ORCID, :eyeroll:) so matching the names is pretty easy.
    # First get the email:
    if record.find("EMAIL") is not None:
        # cleaning up the horrible mess that star makes of any urls and email
        # addresses (it replaces _ with space, but there is no way to
        # differentiate between an underscore-based space and a real one...):
        email = html.unescape(
            mappings.replace_encodings(record.find("EMAIL").text.strip())
        )
        # replace spaces with _, but only if it doesnt come directly before a dot:
        email = re.sub(r"\s(?=[^\.]*\.)", "_", email)
        # if a space comes directly before a dot or after a dot, remove it:
        email = re.sub(r"\s\.", ".", email)
        email = re.sub(r"\.\s", ".", email)
        # check if this is a valid email:
        email_pattern = re.compile(
            r"^([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22))*\x40([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d))*$"
        )
        # check if email matches the regex in email_pattern:
        if email_pattern.match(email):
            email = "mailto:" + email
            # if there is an emid, the email will be added to the person with a name matching the name in emid.

            # get the emid:
            try:
                emid_name = record.find("EMID").text
            except:
                emid_name = None
            if emid_name is not None:
                # go through all bf:Contribution nodes of this work_uri, and get the given and family names of the agent, if it is a person:
                for contribution in graph.objects(work_uri, ns.BF.contribution):
                    # get the agent of the contribution:
                    agent = graph.value(contribution, ns.BF.agent)
                    # if the agent is a person, get the given and family names:
                    if graph.value(agent, RDF.type) == ns.BF.Person:
                        # get the given and family names of the agent:
                        name = graph.value(agent, RDFS.label)
                        emid_name = mappings.replace_encodings(emid_name).strip()
                        # if the emid_name matches the agent's name, add the email as a mads:email to the agent:
                        if fuzz.partial_ratio(emid_name, name) > 80:
                            # add to contribution node:
                            graph.add((contribution, ns.MADS.email, URIRef(email)))
                            # and break the loop, since we only need to add the email to one person:
                            break
            # if after all loops, no match was found for EMID in the AUP-based name,
            # add the email to the first contribution node:
            else:
                # finding the contribution node from those the work_uri has that has pxp:contributionPosition 1:
                for contribution in graph.objects(work_uri, ns.BF.contribution):
                    # dont get the agent at all, but just the position of the contribution:
                    position = graph.value(
                        contribution, ns.PXP.contributionPosition
                    )
                    if int(position) == 1:
                        # add to contribution node:
                        graph.add((contribution, ns.MADS.email, URIRef(email)))
                        # break after position 1 - since we only need the first contribution node:
                        break
        else:
            logging.warning(
                f"invalid email found in record {record.find('DFK').text}: {email}, discarding email"
            )

def match_CS_COU_affiliations_to_first_contribution(graph,work_uri, record):
    # get the content of CS:
    try:
        affiliation = record.find("CS").text
    except:
        affiliation = ""
    # get the country from COU:
    try:
        country = record.find("COU").text
    except:
        country = ""
    #
    # if there is a CS field, add the affiliation to the first contribution node:
    if affiliation and country:
        # get the first contribution node:
        for contribution in graph.objects(work_uri, ns.BF.contribution):
            agent_node = graph.value(
                contribution, ns.BF.agent
            )  # get the agent of the contribution
            # dont get the agent at all, but just the position of the contribution:
            position = graph.value(contribution, ns.PXP.contributionPosition)
            if (
                position is not None
                and int(position) == 1
                and graph.value(agent_node, RDF.type) == ns.BF.Person
            ):
                # add the affiliation to the contribution node using the function we already have for it:
                print("adding CS affiliation to first contribution node in record: " + record.find("DFK").text + " - " + affiliation)
                graph.add(
                    (
                        contribution,
                        ns.MADS.hasAffiliation,
                        build_affiliation_nodes(graph, agent_node, affiliation, country),
                    )
                )
                break

## Now we add the Coporate Body contributions to the work node (from field AUK "korporative Autoren"):
def add_bf_contributor_corporate_body(graph,work_uri, record):
    # adds all corporate body contributors from any of the record's AUK fields as contributions.
    contribution_counter = len(record.findall("AUP"))

    for org in record.findall("AUK"):
        # count up the contribution_counter:
        contribution_counter += 1
        # generate a contribution node, including positions, and return it:
        contribution_node = generate_bf_contribution_node(graph,
            work_uri, record, contribution_counter
        )
        # do something:
        # read the text in AUK and add it as a label:
        # create a fragment uri node for the agent:
        org_node = URIRef(str(contribution_node) + "_orgagent")
        graph.add((org_node, RDF.type, ns.BF.Organization))

        ## extracting the role:
        role = extract_contribution_role(org.text, record)
        # check if there is a role in |f subfield and add as a role, otherwise set role to AU
        graph.set((contribution_node, ns.BF.role, add_bf_contribution_role(role)))

        try:
            # get the name (but exclude any subfields - like role |f, affiliation |i and country |c )
            org_name = mappings.replace_encodings(helpers.get_mainfield(org.text))
            # org_name = mappings.replace_encodings(org.text).strip()
        except:
            logging.warning(
                f"{record.find('DFK').text}: skipping malformed AUK: {org.text}"
            )
            continue
        # get ror id of org from api:
        org_ror_id = local_api_lookups.get_ror_id_from_api(org_name)
        # if there is a ror id, add the ror id as an identifier:
        if org_ror_id is not None and org_ror_id != "null":
            # create a fragment uri node fore the identifier:
            org_ror_id_node = URIRef(str(org_node) + "_rorid")
            # make it a locid:ror:
            graph.set((org_ror_id_node, RDF.type, ns.LOCID.ror))
            # add the ror id as a literal to the identifier node:
            graph.add((org_ror_id_node, RDF.value, Literal(org_ror_id)))
            graph.add((org_node, ns.BF.identifiedBy, org_ror_id_node))
        # else:
        #     print("ror-api: no ror id found for " + org_name)

        # get any affiliation in |i and add it to the name:
        try:
            org_affiliation_name = helpers.get_subfield(org.text, "i")
            # print("org affiliation:" + org_affiliation_name)
        except:
            org_affiliation_name = None
            # print("AUK subfield i: no affiliation for org " + org_name)
        if org_affiliation_name is not None:
            org_name = org_name + "; " + org_affiliation_name
        # # get country name in |c, if it exists:
        try:
            org_country = helpers.get_subfield(org.text, "c")
            # print("AUK subfield c: org country:" + org_country)
        except:
            org_country = None
            # print("AUK subfield c: no country for org " + org_name)
        if org_country is not None:
            # generate a node for the country, clean up the label, look up the geonames id and then add both label and geonamesid node to the org node!
            affiliation_node = build_affiliation_nodes(graph,org_node, "", org_country)
            # add the affiliation node to the contribution node:
            graph.add(
                (contribution_node, ns.MADS.hasAffiliation, affiliation_node)
            )

        # TODO: we should probably check for affiliations and countries in fields CS and COU for records that have only AUKS or AUK as first contribution? we already did the same for persons.

        # add the name as the org node label:
        graph.add((org_node, RDFS.label, Literal(org_name)))

        ## --- Add the contribution node to the work node:
        graph.add((work_uri, ns.BF.contribution, contribution_node))
        # add the org node to the contribution node as a contributor:
        graph.add((contribution_node, ns.BF.agent, org_node))

def normalize_names(familyname, givenname):
    # given a string such as "Forkmann, Thomas"
    # return a normalized version of the name by
    # replacing umlauts and ß with their ascii equivalents and making all given names abbreviated:
    familyname_normalized = (
        familyname.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    # generate an abbreviated version of givenname (only the first letter),
    # (drop any middle names or initials, but keep the first name):
    fullname_normalized = familyname_normalized
    if givenname:
        givenname_abbreviated = givenname[0] + "."
        # generate a normalized version of the name by concatenating the two with a comma as the separator:
        fullname_normalized = familyname_normalized + ", " + givenname_abbreviated
    return fullname_normalized

def extract_contribution_role(contributiontext, record):
    role = helpers.get_subfield(contributiontext, "f")
    if role is not None:
        # if we find a role, return it:
        if role == "VE":
        # if the role is VE (Verfasser), we will replace it with AU (they were used interchangeably
        # in the past, but we only kept AU):
            role = "AU"
        # Also: RE was used for Interviewers, but only in Interviews, 
        # otherwise they meant "Redaktion", so replace with ED
        elif role == "RE":
            # check if any CM of the record contains "interview", then replace
            # role with "IVR" (interviewer), otherwise with "ED" (editor):
            if "interview" in record.find("CM").text:
                role = "IVR"
            else:
                role = "ED"
        return role
    else:
        # if none is found, add the default role AU:
        return "AU"

def add_bf_contribution_role(role):
    # # return role_uri,
    # # generate a node of type bf:Role:
    # graph.add((role, RDF.type, ns.BF.Role))
    # # construct the uri for the bf:Role object:
    # role_uri = URIRef(ROLES + role)
    # # add the uri to the role node:
    # graph.add((role, RDF.value, role_uri))
    # # return the new node:
    # return role
    return URIRef(ns.ROLES + role)