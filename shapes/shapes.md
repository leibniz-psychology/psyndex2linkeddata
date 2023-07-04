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
## Identifiers for Instances

Every Instance must have exactly one local Identifier blank node of type pxc:PPId, and may have at most one optional local legacy Identifier blank node of type pxc:DFK.
Both must be attached to the Instance via the property bf:identifiedBy.

```r
pxs:InstanceShape 
 # In each bf:Instance, exactly one local Identifier blank node of type pxc:PPId must be present:
  sh:property 
  [
    # it must be attached to the Instance via the property bf:identifiedBy:
    sh:path bf:identifiedBy ;
    # it must be a bnode of class pxc:PPId:
    sh:qualifiedValueShape [ sh:class pxc:PPId; sh:nodeKind sh:BlankNode ];
    # exactly one local Identifierof this type must be present:
  	sh:qualifiedMinCount 1 ;
	sh:qualifiedMaxCount 1 ;
    sh:message "More or fewer than 1 PPId identifier present! Must be exactly 1.";
    # the shape o the identifier node itself is defined in pxs:PPIdShape:
    sh:node pxs:PPIdShape;
  ] ;
  # In each bf:Instance, at most one optional local Identifier blank node of type pxc:DFK may be present:
  sh:property [
    # it must be attached to the Instance via the property bf:identifiedBy:
    sh:path bf:identifiedBy ;
    # it must be a bnode of class pxc:DFK:
    sh:qualifiedValueShape [ sh:class pxc:DFK; sh:nodeKind sh:BlankNode ] ;
    # at most one local Identifier of this type may be present:
  	sh:qualifiedMinCount 0 ;
    sh:qualifiedMaxCount 1 ;
    sh:message "More than one DFK identifier present. No more than 1 is allowed." ;
    # the shape o the identifier node itself is defined in pxs:DFKShape:
    sh:node pxs:DFKShape ;
  ] ;
.
```

### DFK local identifier for Instances

Each Identifier of type pxc:DFK must have exactly one property rdf:value with a Literal value of datatype xsd:string that has exactly 7 digits.


```r
# define constraints on pxc:DFK:
pxs:DFKShape
    a sh:NodeShape ;
    sh:targetClass pxc:DFK ;
    # it must have a rdf:value property with exactly one value: a Literal with datatype xsd:string that has exactly 7 digits:
    sh:property [
        sh:path rdf:value ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:pattern "^[0-9]{7}$" ;
    ] .
    
#pxs:DFKSourceShape a sh:NodeShape ;
# it must have a bf:code property with exactly one value: a Literal with datatype xsd:string that has exactly the value "ZPID.PSYNDEX":
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

### PPId local identifier for Instances

Each Identifier of type pxc:PPId must have exactly one property rdf:value with a Literal value of datatype xsd:string that follows the pattern of a UUID.

```r
# define constraints on pxc:PPId:
pxs:PPIdShape a sh:NodeShape ;
    sh:targetClass pxc:PPId ;
    # it must have a rdf:value property with exactly one value: a Literal with datatype xsd:string that follows the pattern of a UUID:
    sh:property [
        sh:path rdf:value ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:pattern "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$" ;
    ] .

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

## Study-Level Metadata (Work)

### Grants

Each Work may have zero or more funding references, one per contributing funder agent, with each funder having zero or more possible grants. The funder must have a name and may have a crossref funder ID (DOI). Each grant, if it exists, must have a grant number.
The funding reference may also have an optional unstructured note with additional information about the funding (such as project names and grant recipient) - there are no separate notes per grant: only one for all grants from a given funder, so just one note per FundingReference. 

Fundings are attached to the Work as a Contribution, subclass pxc:FundingReference, via bf:contribution property. 

Each FundingReference has
- required: one Funder node of class bf:Agent (attached via bf:agent) with 
    - required: one funder name attached via rdfs:label with a Literal value of datatype xsd:string. 
    - optional: one Funder identifier of class pxc:FundRefDoi attached via bf:identifiedBy. The pxc:FundinRefDoi node has:
        - required: exactly one DOI attached via rdf:value with a Literal value of datatype xsd:string.
- optional: one or more Grant nodes of class pxc:Grant (attached via pxp:grant) with
    - required: one grant number attached via bf:identifiedBy with a Literal value of datatype xsd:string.
    - optional: one grant name attached via rdfs:label with a Literal value of datatype xsd:string.
- optional: one funding note of class bf:Note (or </fundinginfo>) attached via bf:note with a Literal value in rdfs:label of datatype xsd:string.

In PSYNDEXER terms:
Grouped Funding Reference:
- funder name
- funder identifier (DOI)
- repeatable, optional group of grants:
    - grant number
- funding note (unstructured, long string) - mostly for legacy data from former info and recipient fields

An example: 

```r
works:123456 a bf:Work ;
    bf:contribution [a bf:Contribution; pxc:FundingReference ;
    # exactly 1 funder agent:
        bf:agent [
            a bf:Agent ;
            rdfs:label "JSPS KAKENHI" ; # exactly 1 funder name; mandatory
            bf:identifiedBy [ a pxc:FundRefDoi; rdf:value "10.13039/501100001691" ]; # crossref fundref DOI, optional; we might use the crossref API to get this id! Or reconcile on the RDF/CSV dump (https://doi.crossref.org/funderNames?mode=list) from fundref with fuzzywuzzy.
            # bf:identifiedBy [
            #     a bf:Identifier, pxc:FunderID "some UUID" # local identifier, optional, form: UUID
            # ] ;
        ] ;
        bf:role <http://id.loc.gov/vocabulary/relators/spn> ; # (sponsoring body/"Träger")
        # optional: 1 or more grants:
        pxp:grant [ a pxc:Grant ;
            bf:identifiedBy [a pxc:GrantId "15K00871" ] ; # exactly 1 grant number, if the grant object exists; like Crossref "award" property
        ] ;
        pxp:grant [a pxc:Grant; 
            bf:identifiedBy [a pxc:GrantId "18KK0055" ] ; # exactly 1 grant number, if the grant object exists
        ];
        # optional: max of 1 funding note/info (this will contain destructured legacy field values from subfields |i - Info and |e - Recipient)):
        bf:note [a bf:Note, <http://id.loc.gov/vocabulary/mnotetype/fundinfo>; rdfs:label "Info: Open access funding. Recipient(s): Law, Kiely"] ; 
    ] ;
.

```

As shapes:
    
```r
pxs:WorkShape 
    sh:property [
        sh:path bf:contribution ;
        sh:qualifiedValueShape [ 
            sh:class pxc:FundingReference; 
            sh:nodeKind sh:BlankNode ];
        sh:node pxs:FundingReferenceShape ;
    ] .

pxs:FundingReferenceShape a sh:NodeShape ;
    sh:targetClass pxc:FundingReference ;
    sh:property [
        sh:path bf:agent ;
        sh:qualifiedValueShape [ 
            sh:class bf:Agent; 
            sh:nodeKind sh:BlankNode ];
        # each FundingReference must have exactly one Funder:
        sh:qualifiedMinCount 1 ;
        sh:qualifiedMaxCount 1 ;
        sh:node pxs:FunderShape ;
    ] ;
    sh:property [
        sh:path bf:role ;
        sh:nodeKind sh:IRI ;
        sh:in ( <http://id.loc.gov/vocabulary/relators/fnd> <http://id.loc.gov/vocabulary/relators/spn> ) ;
        # each FundingReference must have exactly one role:
        sh:qualifiedMinCount 1 ;
        sh:qualifiedMaxCount 1 ;
    ] ;
    sh:property [
        sh:path pxp:grant ;
        sh:qualifiedValueShape [ 
            sh:class pxc:Grant; 
            sh:nodeKind sh:BlankNode ];
        sh:node pxs:GrantShape ;
    ] ;
    sh:property [
        sh:path bf:note ;
        sh:qualifiedValueShape [ 
            sh:class bf:Note; 
            sh:nodeKind sh:BlankNode ];
        sh:node pxs:NoteShape ;
        sh:qualifiedMinCount 0 ;
        sh:qualifiedMaxCount 1 ;
    ] .

pxs:FunderShape a sh:NodeShape ;
    sh:targetClass bf:Agent ;
    # must have exactly one name of the funder:
    sh:property [
        sh:path rdfs:label ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    # may have one local funder cb id:
    # sh:property [
    #     sh:path bf:identifiedBy ;
    #     sh:qualifiedValueShape [ 
    #         sh:class bf:FunderID; 
    #         sh:nodeKind sh:BlankNode ];
    #     sh:node pxs:IdentifierShape ;
    #     sh:qualifiedMinCount 0 ;
    #     sh:qualifiedMaxCount 1 ;
    # ] ;
    # may have one crossref funder id/DOI:
    sh:property [
        sh:path bf:identifiedBy ;
        sh:qualifiedValueShape [ 
            sh:class pxc:FundRefDoi; 
            sh:nodeKind sh:BlankNode ];
        sh:node pxs:IdentifierShape ;
        sh:qualifiedMinCount 0 ;
        sh:qualifiedMaxCount 1 ;
    ] .

pxs:GrantShape a sh:NodeShape ;
# each Grant must have exactly one grant number:
    sh:property [
        sh:path bf:identifiedBy ;
        sh:qualifiedValueShape [ 
            sh:class bf:Identifier; 
            sh:nodeKind sh:BlankNode ];
        sh:node pxs:IdentifierShape ;
        sh:qualifiedMinCount 1 ;
        sh:qualifiedMaxCount 1 ;
    ] ;
    # may have one grant name:
    # sh:property [
    #     sh:path rdfs:label ;
    #     sh:datatype xsd:string ;
    #     sh:qualifiedMinCount 0 ;
    #     sh:qualifiedMaxCount 1 ;
    # ] .
.

```

TODO: add an IdentifierShape (it is always the same: rdf:value with a string; maybe a bf:code and a bf:source; however: always a different pattern :())

## Conference

Work > bf:contribution > bf:agent > bf:Meeting > rdfs:label
(role: ctb)

Make a subclass of Contribution: ConferenceReference.

