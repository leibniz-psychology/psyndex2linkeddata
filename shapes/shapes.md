# Shapes for Works and Instances in PsychPorta

## Prefixes and Namespaces

```r
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
@prefix pxs: <https://w3id.org/zpid/shapes/> .
@prefix pxc: <https://w3id.org/zpid/ontology/classes/> .
@prefix pxp: <https://w3id.org/zpid/ontology/properties/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

```

## Basic Work Shape

```r
pxs:WorkShape
    a sh:NodeShape ;
    sh:targetClass bf:Work .

```

## Basic Instance Shape

```r
pxs:InstanceShape
    a sh:NodeShape ;
    sh:targetClass bf:Instance .

```

## DFK local identifier for a Work

Every Work must have exactly one local Identifier of type pxc:DFK.

```r
pxs:WorkShape 
    sh:property [
        sh:path bf:identifiedBy ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:node pxs:DFKShape ;
    ] .

pxs:DFKShape
    a sh:NodeShape ;
    sh:targetClass pxc:DFK ;
    # additional constraints on pxc:DFK can be added here
    # the shape must be a bnode:
    sh:nodeKind sh:BlankNode ; 
    # the node must have class pxc:DFK:
    #sh:class pxc:DFK ;
    # sh:property [
    #     sh:path rdf:type ;
    #     sh:hasValue pxc:DFK ;
    # ] ;
     # it must have a rdf:value property with exactly one value: a Literal with datatype xsd:string that has exactly 7 digits:
    sh:property [
        sh:path rdf:value ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:pattern "^[0-9]{7}$" ;
    ] .
    
# pxc:DFKSourceShape a sh:NodeShape ;
# # it must be a bnode:
#     sh:targetClass bf:Source ; 
#     sh:nodeKind sh:BlankNode ;
#     # it must have a bf:code property with exactly one value: a Literal with datatype xsd:string that has exactly the value "ZPID.PSYNDEX":
#     sh:property [
#         sh:path bf:code ;
#         sh:nodeKind sh:Literal ;
#         sh:hasValue "ZPID.PSYNDEX" ;
#         sh:datatype xsd:string ;
#         sh:minCount 1 ;
#         sh:maxCount 1 ;
#         sh:pattern "^ZPID.PSYNDEX$" ;
#     ] .

```

## Publication (original) title (Instance)

The original title found on the publication is attached to the Instance as a blank node of class bf:Title via the property bf:title.
Every Instance must have exactly one such bf:Title bnode.
The bf:Title bnode must have exactly one property bf:mainTitle that is a Literal value with a language tag of either @de or @en.
It may have at most one additional property bf:subtitle with a Literal value with a language tag of either @de or @en.

Additionally, we have a rdfs:label for the Instance that is the concatenation of the mainTitle and subtitle.

```r
# # add new property path bf:title to InstanceShape:
# pxs:InstanceShape
#     sh:property [ 
#         sh:path bf:title ; 
#         sh:node pxs:TitleShape ;
#         sh:minCount 1 ;
#         sh:maxCount 1
# ] .

# # define constraints on bf:Title bnode:
# pxs:TitleShape
#     a sh:NodeShape ;
#     sh:class bf:Title ;

#     # bf:mainTitle must be present and have exactly one value with a language tag of either @de or @en:
#     sh:property [
#         sh:path bf:mainTitle ;
#         sh:datatype rdf:langString ;
#         sh:minCount 1 ;
#         sh:maxCount 1 ;
#         sh:in ("en","de")
#     ] ;
#     # bf:subtitle may be present and have at most one value with a language tag of either @de or @en:
#     sh:property [
#         sh:path bf:subtitle ;
#         sh:datatype rdf:langString ;
#         sh:maxCount 1 ;
#         sh:in ("en","de")
#     ] ;
# .

```

## translation of the original title (Instance)

The translation of the original title found on the publication is attached to the Instance as a blank node of class pxc:TranslatedTitle via the property bf:title.
Every Instance may have at most one such pxc:TranslatedTitle bnode.
The pxc:TranslatedTitle bnode must have exactly one property bf:mainTitle that is a Literal value with a language tag of either @de or @en.

```r
# add new property path bf:title to InstanceShape:  
# pxs:InstanceShape
#     sh:property [ 
#         sh:path bf:title ; 
#         sh:node pxs:TranslatedTitleShape ;
#         sh:maxCount 1
#     ] .

# # define constraints on pxc:TranslatedTitle bnode:
# pxs:TranslatedTitleShape
#     a sh:NodeShape ;
#     sh:class pxc:TranslatedTitle ;

#     # bf:mainTitle must be present and have exactly one value with a language tag of either @de or @en:
#     sh:property [
#         sh:path bf:mainTitle ;
#         sh:datatype rdf:langString ;
#         sh:minCount 1 ;
#         sh:maxCount 1 ;
#         sh:in ("en","de")
#     ] .

```

