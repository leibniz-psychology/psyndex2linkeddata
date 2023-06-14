

These are new classes and properties we needed to define because there weren't any we could reuse.

# Prefixes and Namespaces

The following namespaces are used in this ontology:

```r
# our own namespaces for properties, classes, and shacl shapes:
@prefix pxp: <https://w3id.org/zpid/ontology/properties/> .
@prefix pxc: <https://w3id.org/zpid/ontology/classes/> .
@prefix pxs: <https://w3id.org/zpid/shapes/> .

# important namespaces we reuse because ancestors of our own classes and properties are from there (superclasses and superproperties are from these namespaces):
@prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
@prefix bflc: <http://id.loc.gov/ontologies/bflc/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <https://schema.org/> .

# mainly used for mapping of properties and classes to other ontologies:
@prefix dblp: <https://dblp.org/rdf/schema#> .
@prefix bibo: <http://purl.org/ontology/bibo/>.

# basic ontology namespaces:
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix vann: <http://purl.org/vocab/vann/> .

```

# Two ontologies: Properties and Classes

## Ontology for the Properties

```r
<https://w3id.org/zpid/ontology/properties>
   rdf:type owl:Ontology ; #voaf:Vocabulary ;
   vann:preferredNamespacePrefix "pxp" ;
   vann:preferredNamespaceUri "https://w3id.org/zpid/ontology/properties/" ;
   dct:title "ZPID/PSYNDEX properties" ;
   #dct:license <...> ;
   dct:description "New properties that we need to define because there aren't any in BIBFRAME and related we can reuse"@en ;
   dct:issued "2022-07-01" ;
   dct:modified "2022-11-28"^^xsd:date ;
   skos:historyNote "See the commit history for this vocabulary at https://github.com/." ;
   #dct:publisher <...> ;
   #dct:creator <...> ;
.
```

## Ontology for the Classes

```r
<https://w3id.org/zpid/ontology/classes>
   rdf:type owl:Ontology ; #voaf:Vocabulary ;
   vann:preferredNamespacePrefix "pxc" ;
   vann:preferredNamespaceUri "https://w3id.org/zpid/ontology/classes/" ;
   dct:title "ZPID/PSYNDEX classes" ;
   #dct:license <...> ;
   dct:description "New classes that we need to define because there aren't any in BIBFRAME and related we can reuse"@en ;
   dct:issued "2022-07-01" ;
   dct:modified "2022-11-28"^^xsd:date ;
   skos:historyNote "See the commit history for this vocabulary at https://github.com/." .
```

# Classes

## Classes for Agents > Corporate Bodies/Organizations
...

## Classes for Agents > Persons

...

## Classes for Publications (Works and Instances)

### Identifiers in Publications

All identifiers are subclasses of bf:Identifier and to be used with bf:identifiedBy on a bf:Work or bf:Instance.

For DOI we reuse bf:Doi, for ISBN we reuse bf:Isbn, both on bf:Instance. (TODO: Add links to Shapes/examples describing this.)
For ISSN we reuse bf:Issn on bf:Work (if used for describing a relationship from an article to it's journal, used on the bf:Work that is linked in the bflc:Relationship node). 

The following are new subclasses of bf:Identifier for local identifiers that are used within PSYNDEX: legacy ones like DFK and PsychAuthorsID, as well as new ones like the ZPID-internal identifier for the Work and Instance and for authority agents like organizations/corporate bodies and people.


#### DFK

A subclass of bf:Identifier > bf:Local to be used via the bf:identifiedBy property on a bf:Instance.
Every instance must have exactly one local Identifier of type pxc:DFK.
Shacl shape: see pxc:DFKShape in shapes/shapes.md and shapes/shapes.ttl. 

```r
pxc:DFK a owl:Class;
    rdfs:subClassOf bf:Local;
    rdfs:label "DFK"@de, "DFK"@en;
    rdfs:comment "The DFK is the unique identifier of a publication in PSYNDEX. It is a string of 8 numbers."@en;
```

#### PsychAuthorsID for Persons in bf:Contribution

A subclass of bf:Identifier > bf:Local to be used via the bf:identifiedBy property on a bf:Person node that is part of a bf:Contribution via bf:agent.
It is used for contributors that have a PsychAuthors profile to link the ID of that profile to the contributor.

```r
pxc:PsychAuthorsID a owl:Class;
    rdfs:subClassOf bf:Local;
    rdfs:label "PsychAuthors-Kennung"@de, "PsychAuthors ID"@en;
    rdfs:comment "The PsychAuthors ID is the unique identifier of a person in our legacy psychauthors authority file of psychologists."@en;
```

### Publication Titles

#### Translated Title

This is a subclass of bf:VariantTitle (which is itself a subclass of bf:Title). 
It is used for a translation of the publication's title provided by ZPID for PSYNDEX. 
If the original work's language is German, the translated title is in English, and vice versa.

The TranslatedTitle class should be used with the property bf:title and attached to a bf:Instance.

Example of proper usage: 
<Instance> a  bf:Instance;
 bf:title [a bf:Title, pxc:TranslatedTitle; rdfs:label "the translated title goes here"@en] .


```r
pxc:TranslatedTitle a owl:Class;
    rdfs:subClassOf bf:VariantTitle;
    rdfs:label "Original title translated into English or German"@en;
rdfs:description "Title as translated either by the creator, by a ZPID cataloger/indexer or some automated translation service like Deepl. Usually contains subtitle as well; Language is en if original work language is de; if work language is en, the translated title has language en." .
```

### Publication Summaries

We defined some new Classes which are all subclasses of bf:Summary and should be used as blank nodes (or skolemized hash nodes) with bf:summary **on bf:Work**. Like bf:Summary, the actual summarizing text content is attached as a Literal to the property rdfs:label which will always have a language tag. 

We have **Abstract** and **PlainLanguageSummary**. 

#### Abstract (Work)

A subclass of bf:Summary, used for the abstract of a work. 
To be used via bf:summary property on a bf:Work.


```r
pxc:Abstract a owl:Class;
    rdfs:subClassOf bf:Summary;
    rdfs:label "Abstract"@en, "Abstract"@de;
.
```

#### Plain Language Summary (Work)

A subclass of bf:Summary, used for a short summary of a metaanalysis in plain language. 
To be used via bf:summary property on a bf:Work.

```r
pxc:PlainLanguageSummary a owl:Class;
    rdfs:subClassOf bf:Summary;
    rdfs:label "Plain Language Summary"@en, "Laienzusammenfassung"@de;
.
```

### Classes for Topics and Classifications of the Work

Information about the content of a publication or the study inside the work is described by the following classes.
We reuse bf:Topic for regular, non-weighted keywords. However, to say that one of the topics is more important, we added a classes subclass of bf:Topic called WeightedTopic.

#### Weighted Topic

For weighted vocabulary terms, that is, a topic that has more weight, is most salient than others for a work.
Problem: we want to link the uri of the vocabulary term directly, not a bnode of either class bf:Topic or pxc:WeightedTopic, but then there is no way to say which class the thing is. 
Solution: Always use a bnode, add the uri via schema/owl:sameAs to it.

A subclass of bf:Topic to be used via the bf:topic property on a bf:Work.

```r
pxc:WeightedTopic a owl:Class;
    rdfs:subClassOf bf:Topic;
    rdfs:label "Weighted Topic"@en, "Gewichtetes Schlagwort"@de;
    rdfs:comment "A topic that has more weight than others. One that is most essential in describing the work and what it is about."@en;
.
```

#### Subclasses of bf:Classification

##### Subject Heading

A subclass of bf:Classification to be used via the bf:classification property on a bf:Work.

```r
pxc:SubjectHeading a owl:Class;
    rdfs:subClassOf bf:Classification;
    rdfs:label "Psychological Subject Heading Classification"@en, "Psychologische Inhaltsklassifikation"@de;
.
```

##### Controlled Method

A subclass of bf:Classification to be used via the bf:classification property on a bf:Work. It is used to describe the scientific study methodology used to create the study described within the work.
TODO: Add link to and info about the cotrolled vocabulary of methods we use with it.

```r
pxc:ControlledMethod a owl:Class;
    rdfs:subClassOf bf:Classification;
    rdfs:label "Controlled Method Classification"@en, "Klassifikation der kontrollierten Methode"@de;
    rdfs:comment "The scientific study methodology used to create the study described within the work."@en;
.
```

#### Classes for describing a study population - subclasses of bf:DemographicGroup and bf:GeographicCoverage

Studies that are documented in scholarly works are described in PSYNDEX by their study population, that is, the group of people that were studied.
The following classes are used to describe the study population of a work: Their age group and their location. 

### Age Group

A subclass of bf:DemographicGroup to be used via the bf:demographicGroup property on a bf:Work.

```r
pxc:AgeGroup a owl:Class;
    rdfs:subClassOf bflc:DemographicGroup;
    rdfs:label "Age Group of study population or of instrument target group"@en, "Altersbereich der Studienpopulation oder der Testzielgruppe"@de; 
.
```

### Population Location

A subclass of bf:GeographicCoverage to be used via the bf:geographicCoverage property on a bf:Work.

```r
pxc:PopulationLocation a owl:Class;
    rdfs:subClassOf bf:GeographicCoverage;
    rdfs:label "Population Location"@en, "Ort der Studienpopulation"@de; 
.
```

<!-- ### pxp:seriesEnumeration 
 -->


### contributions:

```r
pxp:contributionPosition
  a rdf:Property ;
  rdfs:label "contributor position"@en ;
  rdfs:comment "Position of contributor (within the creator sequence) of the publication, starting with 1. for first author or contributor"@en ;
  rdfs:domain bf:Contribution ;
  rdfs:range xsd:integer;
  owl:equivalentProperty dblp:signatureOrdinal, <http://www.wikidata.org/entity/P478>; rdfs:subPropertyOf schema:position, bf:qualifier
.
```
  
<!-- # pxp:contributorAffiliation a owl:ObjectProperty; 
#     owl:equivalentProperty schema:affiliation;
#     rdfs:Domain bf:Contribution;
#     rdfs:range bf:Organization;    
# . 
# removed: use mads:hasAffiliation instead! -->


## Properties for Relationships:

### For articles in journals:
note: may also export a combined version as bf:part "Vol. 3, Issue 11, p. 22-56"

#### in Issue

```r
pxp:inIssue a rdf:Property;
  rdfs:label "published in journal issue"@en ;
  rdfs:comment "The issue of the journal in which the publication was published."@en ;
    rdfs:subPropertyOf bf:part, bibo:locator; # bf:part is equivalent to MARC subfield $g eg in field 773; a literal that contains volume, issue and page range of a "hosted item" - which is an article in a journal.
    owl:equivalentProperty dblp:publishedInJournalVolumeIssue, <http://purl.org/ontology/bibo/issue>, <http://prismstandard.org/namespaces/basic/2.0/issueIdentifier>, schema:issueNumber, <http://www.wikidata.org/entity/P433>;
    rdfs:domain bflc:Relationship;
    rdfs:range xsd:string;
.
```

#### in Volume

```r
pxp:inVolume a rdf:Property;
  rdfs:label "published in journal volume"@en ;
  rdfs:comment "The volume of the journal in which the publication was published."@en ;
    rdfs:subPropertyOf bf:part, bibo:locator; 
    owl:equivalentProperty dblp:publishedInJournalVolumeIssue, <http://www.wikidata.org/entity/P478>, <http://prismstandard.org/namespaces/basic/2.0/volume>, schema:volumeNumber;
    rdfs:domain bflc:Relationship;
    rdfs:range xsd:string;
.
```

#### pageStart and pageEnd
```r
pxp:pageStart a rdf:Property;
    rdfs:label "first page"@en, "erste Seite"@de;
    rdfs:comment "The page within a journal issue or a book on which an article or chapter begins; the first page of the part."@en;
    rdfs:subPropertyOf bf:part, bibo:locator;
    owl:equivalentProperty schema:pageStart, <http://prismstandard.org/namespaces/1.2/basic/startingPage>, bibo:pageStart;
    rdfs:domain bflc:Relationship;
    rdfs:range xsd:integer;
.
```

```r
pxp:pageEnd a rdf:Property;
    rdfs:label "last page"@en, "letzte Seite"@de;
    rdfs:comment "The page within a journal issue or a book on which an article or chapter ends; the last page of the part."@en;
    rdfs:subPropertyOf bf:part, bibo:locator;
    owl:equivalentProperty schema:pageEnd, <http://prismstandard.org/namespaces/1.2/basic/endingPage>, bibo:pageEnd;
    rdfs:domain bflc:Relationship;
    rdfs:range xsd:integer;
.
```

#### Article Number
```r
pxc:ArticleNumber a owl:Class;
    rdfs:label "Article number"@en, "Artikelnummer"@de;
    rdfs:comment "Alphanumerica identifier of a journal article within that journal. Usually for electronic journal articles where no start or end page is given. Value (the number/identifier) is found in a rdf:value property, as is usual for bf:Identifier subclasses.";
    rdfs:subClassOf bf:Identifier;
    .
```

#### Page Count
```r
pxp:PageCount a owl:Class;
    rdfs:subClassOf bf:Extent;
 #owl:equivalentProperty <http://purl.org/spar/fabio/hasPageCount>.
.
```

## Properties describing is-ness of Work and Instance:

```r
pxp:issuanceType a rdf:Property;
    rdfs:label "Erscheinungsform"@de, "Issuance Type"@en;
    skos:altLabel "Publication type"@en, "Publikationstyp"@de;
    rdfs:comment "Describes the type of publication an instance was issued as, including its bibliographic level (former BE field in PSYNDEX) = whether it is a standalone thing or a dependent component part. Examples: Journal Article, Edited Book"@en;
    rdfs:domain bf:Instance;
    rdfs:range skos:Concept;
    . 
```

```r
pxp:mediaCarrier a rdf:Property;
    rdfs:label "Medien-/Datenträgertyp"@de, "Media and Carrier Type"@en;
    rdfs:comment "Describes an instance's combined medium and carrier type. Close approximation of former field MT and MT2 in PSYNDEX"@en;
    rdfs:domain bf:Instance;
    rdfs:range skos:Concept;
. 
```