from rdflib import RDF, RDFS, Graph, Literal, URIRef

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
