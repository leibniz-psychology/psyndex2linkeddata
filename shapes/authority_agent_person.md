# Shapes for Agents in PsychPorta: Person, Organization/Corporate Body

## Prefixes and Namespaces

We use properties from schema.org (schema), the German National Library's GND Ontology (gndo), and the Library of Congress' BIBFRAME Ontology (bf). We also define our own classes and properties in the PsychPorta Ontology (pxc and pxp).

```
# for properties and classes we use in the shapes:
@prefix schema: <http://schema.org/> .
@prefix gndo: <http://d-nb.info/standards/elementset/gnd#> .
@prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
@prefix pxs: <https://w3id.org/zpid/shapes/> .
@prefix pxc: <https://w3id.org/zpid/ontology/classes/> .
@prefix pxp: <https://w3id.org/zpid/ontology/properties/> .

# basic shape and rdf namespaces:
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

## Basic Person Shape

```
pxs:PersonShape
    a sh:NodeShape ;
    sh:targetClass bf:Person . # or schema:Person or both?
```
### Personal information: Names, Gender, Birth and Death Dates

#### Person Names

##### Simple string literal for a Person's full name

For convenience, we export a concatenated full name as a simple string literal. We also export the first and last name as separate literals, se below.

- exactly one comma-separated full preferred name (family name first): `schema:name "Nachname, Vorname";`
- other names used previously (such as before name changes like for marriage/divorce/maiden name) or alternatively, like with or without a middle initial: `schema:alternateName "Nachname, Vorname";` 

<!-- a table: -->
|domain|property|range|expected value|cardinality|example|
|-------|--------|--|-----------|--|-------|
|Person|`schema:name`|Literal|xsd:string|"Meier, Andrea M."|1..1|
|Person|`schema:alternateName`|Literal|xsd:string|"Müller, Andrea"|0..*|

As a shacle shape:

```SHACL
pxs:PersonShape
    sh:property [
        sh:path schema:name ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        # regex pattern for a comma-separated full name:
        sh:pattern "^[^,]+, [^,]+$" ;
    ] ;
    sh:property [
        sh:path schema:alternateName ;
        sh:minCount 0 ;
        sh:datatype xsd:string ;
        # regex pattern for a comma-separated full name:
        sh:pattern "^[^,]+, [^,]+$" ;
    ] .
```


##### Complex name for a Person with first and last name

To describe preferred and other names in more detail, we use blank nodes with gndo properties und classes:

|domain|property|cardinality|range|
|------|--------|-----------|-----|
|Person|gndo:preferredNameEntityForThePerson|1..1|gndo:NameOfThePerson|
|Person|gndo:variantNameEntityForThePerson|0..n| gndo:NameOfThePerson| 
|gndo:NameOfThePerson|schema:givenName "Given name(s), including initials"|1..1|
|gndo:NameOfThePerson|schema:familyName "Family name"|1..1| 

As a shacle shape:

```SHACL
pxs:PersonShape
    sh:property [
        sh:path gndo:preferredNameEntityForThePerson ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:node pxs:NameOfThePersonShape ;
    ] ;
    sh:property [
        sh:path gndo:variantNameEntityForThePerson ;
        sh:minCount 0 ;
        sh:node pxs:NameOfThePersonShape ;
    ] .

pxs:NameOfThePersonShape
    a sh:NodeShape ;
    sh:targetClass gndo:NameOfThePerson ;
    sh:property [
        sh:path schema:givenName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path schema:familyName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] .
```
#### Gender

We use our own gender vocabulary in SKOS (that includes undefined and nongendered values beside male and female) and a schema.org property. 

Each Person may have one optional gender value: `Person schema:gender <value>.

|domain|property|range|expected value|cardinality|example|
|Person|schema:gender|skos:Concept|-|0..1|<https://wrid.org/zpid/vocabs/gender/female>|

As a shacle shape:

```SHACL
pxs:PersonShape a sh:NodeShape ;
    sh:property [
        sh:path schema:gender ;
        sh:name "has gender of the person"@en, "hat Geschlecht der Person"@de;
        sh:maxCount 1 ;
        sh:node pxs:GenderShape ;
    ] .

pxs:GenderShape a sh:NodeShape ;
    sh:nodeKind sh:IRI ;
    sh:class skos:Concept ;
    sh:description "Must be from our gender vocabulary: https://w3id.org/zpid/vocab/gender/ (prefix 'gender:')"@en;
    rdfs:label "Geschlecht"@de, "Gender"@en;
    sh:in (gender:male gender:female gender:unknown gender:other);
    # it has to be from vocab gender:
    sh:pattern "^https://w3id.org/zpid/vocab/gender/" .
```

#### Birth and Death Dates, place of Birth


```SHACL
pxs:PersonShape a sh:NodeShape ;
    sh:property [
        sh:path schema:birthDate ;
        sh:name "Date of Birth"@en, "Geburtsdatum"@de; 
        sh:nodeKind sh:Literal ;
        sh:minCount 0 ;
        sh:maxCount 1 ;
        sh:lessThan schema:deathDate ; # birth date must be before death date
        sh:minInclusive "1500-01-01"^^xsd:date ; # birth date must be after 1500-01-01
        # birth date must be a date, gYear, or gYearMonth:
        sh:or ([
            sh:datatype xsd:date;
        ]
        [
            sh:datatype xsd:gYear;
        ] 
        [
            sh:datatype xsd:gYearMonth;
        ]) ;
        sh:name "Date of Birth"@en, "Geburtsdatum"@de; 
        sh:group pxc:dates ; # group with other date properties for any interface that displays them
    ] ,
    [
        sh:path schema:deathDate ;
        sh:name "Date of Death"@en, "Sterbedatum"@de;
        sh:nodeKind sh:Literal ;
        sh:minCount 0 ;
        sh:maxCount 1 ;
        sh:lessThan schema:deathDate ; # death date must be after birth date
        sh:minInclusive "1500-01-01"^^xsd:date ; # death date must be after 1500-01-01
        # death date must be a date, gYear, or gYearMonth:
        sh:or ([
            sh:datatype xsd:date;
        ]
        [
            sh:datatype xsd:gYear;
        ] 
        [
            sh:datatype xsd:gYearMonth;
        ]) ;
        sh:goup pxc:dates ; # group with other date properties for any interface that displays them
    ]    
 .


```
 <!-- TODO: place of birth -->

### Professional information: Affiliations, Roles, and Contributions

- Contact data (email and websites): schema:email (0..n), schema:url (0..n)
- fields of interest or research: schema:knowsAbout
    - controlled: schema:knowsAbout https://w3id.org/zpid/vocabs/interests/something ; # 0..n
    - uncontrolled: schema:knowsAbout [a skos:Concept; skos:prefLabel "uncontrolled topic"]; # 0..n
- Affiliations 
- Academic degrees/history with the degree-granting org as main unit (with schema:alumniOf) and schema:OrganizationRole as a grouping blank node for qualifying the info (start and end, credentials, field of study)
- professional/work history with the employer as main unit (with schema:worksFor ... or pxp:hasRelatedCorporateBodyOfPerson? property) and schema:OrganizationRole as a grouping blank node for qualifying the info (start and end, role in organization)
- memberships (main entity is the organization, using schema:OrganizationalRole as a grouping blank node for qualifying the info like role and description). Similar to bf:Contribution.
- positions in organizations (main entity is the organization, using schema:OrganizationalRole as a grouping blank node for qualifying the info like role and description). Similar to bf:Contribution.
- contributions to publications (editorial board etc) as a simple string literal for now - as it is found in psychauthors.
- awards: schema:award (0..n) with schema:Role as a grouping blank node for qualifying the info (date, description)

#### Contact data: email and websites

|domain|property|range|expected value|cardinality|example|
|------|--------|-----|--------------|-----------|-------|
|Person|schema:email|IRI||0..1|<mailto:mail@example.org>|
|Person|schema:url|IRIl||0..1|<https://example.org/my_page>|

```SHACL
pxs:PersonShape a sh:NodeShape ;
    sh:property [
        sh:path schema:email ;
        sh:name "Email address"@en, "E-Mail-Adresse"@de;
        sh:nodeKind sh:IRI ;
        sh:datatype xsd:anyURI ;
        # must be a mailto: URI:
        sh:pattern "^mailto:" ;
        sh:minCount 0 ;
        sh:maxCount 1 ;
    ] ,
    [
        sh:path schema:url ;
        sh:name "URL"@en, "URL"@de;
        sh:nodeKind sh:IRI ;
        sh:datatype xsd:anyURI ;
        sh:minCount 0 ;
        sh:maxCount 1 ;
    ] .
```

#### Academic titles

All the titles a person wants to be used for them, as a single string:

|domain|property|range|expected value|cardinality|example|
|------|--------|-----|--------------|-----------|-------|
|Person|gndo:academicTitle|Literal|xsd:string|"Prof. Dr."|0..1|

```SHACL
pxs:PersonShape a sh:NodeShape ;
    sh:property [
        sh:path gndo:academicTitle ;
        sh:name "Academic title"@en, "Akademischer Titel"@de;
        sh:datatype xsd:string ;
        sh:minCount 0 ;
        sh:maxCount 1 ;
    ] .
```


#### Fields of interest or research


- fields of interest or research: schema:knowsAbout
    - controlled: schema:knowsAbout https://w3id.org/zpid/vocabs/interests/something ; # 0..n
    - uncontrolled: schema:knowsAbout [a skos:Concept; skos:prefLabel "uncontrolled topic"]; # 0..n

|domain|property|range|expected value|cardinality|example|
|------|--------|-----|--------------|-----------|-------|
|Person|schema:knowsAbout|skos:Concept|controlled: <https://w3id.org/zpid/vocabs/interests/something> or uncontrolled: [a skos:Concept; skos:prefLabel "uncontrolled topic"]|0..n|<https://w3id.org/zpid/vocabs/interests/psychology>|

```SHACL
pxs:PersonShape a sh:NodeShape ;
    sh:property [
        sh:path schema:knowsAbout ;
        sh:name "Field of interest or research"@en, "Forschungsgebiet"@de;
        sh:nodeKind sh:IRIorBlankNode ;
        # must be either from our controlled vocabulary of interests or a blank skos:Concept node with a prefLabel:
        sh:or ([
            sh:pattern "^https://w3id.org/zpid/vocabs/interests/" ;
        ]
        [
            sh:node pxs:UncontrolledInterestShape ;
        ]) ;
    ] .

pxs:UncontrolledInterestShape a sh:NodeShape ;
    sh:nodeKind sh:BlankNode ;
    sh:class skos:Concept ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:name "Label for uncontrolled field of interest or research"@en, "Bezeichnung für unkontrolliertes Forschungsgebiet"@de;
        sh:datatype xsd:string ;
    ] .
```
