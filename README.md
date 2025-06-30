# Structure of works and instances

Each Work 
- is bf:Work and has an identifier/uri of the form https://w3id.org/zpid/resources/works/0397056.
- has (for the moment) **exactly 1 instance** which is attached as a blank node via `bf:hasInstance > bf:Instance`.
- has (for now) exactly one (1) language, a uri attached via`bf:language` (e.g. http://id.loc.gov/vocabulary/iso639-2/eng)
- has 1 or more numbered Contribution blank nodes attached via `bf:contribution > bf:Contribution`. Each Contribution...
    - has exactly one (1) `pxp:contributionPosition` Literal (int) with a number (e.g. 1) that states its order/position in the list of contributions 
    - (probably unimportant for migration; inspired by OpenAlex) has exactly one (1) `bf:qualifier` Literal (string) that states whether the contribution is "first", "last", or "middle" (anything between first and last)
    - may have 0 or more **adffiliation** blank nodes that collects the affiliated org and its name, as well as the address (just the country  with a label and a geonames id and a geonames uri): `mads:hasAffiliation > mads:Affiliation`. Each of these...
        - may have 0 or 1 **affiliated organization** as a `mads:organization > mads:Organization` blank node with a `rdfs:label`Literal that contains the name of the organization as a string (e.g. "Department of Molecular Psychology, Institute of Psychology and Education, Ulm University")
        - may have 0 or 1 **affiliation address** as a `mads:hasAffiliationAddress > mads:Address > mads:country > mads:Country` blank node with ...
            - a `rdfs:label` Literal that contains the name of the **affiliation country** as a string (e.g. "GERMANY")
            - a **geonames identifier** blank node: `bf:identifiedBy > bf:Identifier, "http://id.loc.gov/vocabulary/identifiers/geonames"` with an `rdf:value` Literal that contains the geonames id of the country as a string (e.g. "2921044")
            - the **geonames uri** of the country  (e.g. "http://sws.geonames.org/2921044/") via `schema:sameAs`	
    - a Contribution may also have 0 or 1 **email** (if the person/agent in the contr. is the corresponding author) as a mailto: uri via `mads:email` (e.g. mailto:ex@ample.org) 
    - has exactly one (1) **contribution role** skos:Concept from our roles vocabulary in Skosmos via `bf:role`, e.g. "https://w3id.org/zpid/vocabs/roles/AU" for "author"
    - has exactly one (1) **contributing agent** blank node attached via `bf:agent > bf:Person` (we haven't converted contributions by corporate bodies yet, so only bf:Person). Each person ...
        - has 1 full name in `rdfs:label` (e.g. "Döring, Nicola")
        - has 1 first name in `schema:givenName` (e.g. "Nicola")
        - has 1 last name in `schema:familyName` (e.g. "Döring")
        - may have at most one (1) **psychauthors id** (a local identifier) blank node attached via `bf:identifiedBy > bf:Identifier, bf:Local, pxc:PsychAuthorsID` with an `rdf:value` Literal that contains the psychauthors id of the person as a string (e.g. "p00935UR") - there is also a convenient, clickable link to the psychauthors page in `schema:mainEntityOfPage` such as https://www.psychauthors.de/psychauthors/index.php?wahl=forschung&amp;uwahl=psychauthors&amp;uuwahl=p00935UR (for testing, not needed for migration)
        - may have at most one (1) ORCID identifier blank node attached via `bf:identifiedBy > bf:Identifier, "http://id.loc.gov/vocabulary/identifiers/orcid"` with an `rdf:value` Literal that contains the ORCID id of the person as a string (e.g. "0000-0002-1927-4156")	(for convenvience, there is also a schema:sameAs with a clickable ORCID link - not needed for migration)
- has one abstract `bf:summary > pxc:Abstract` with:
    - always one (1) `rdfs:label` with the abstract text as a string (language tagged)
    - one optional adminMetadata blank node for origin and possible editor of the abstract: `bf:adminMetadata > bf:AdminMetadata` with
        - one optional `bflc:metadataLicensor` Literal (string) that is the actual source/origin string of the abstract (e.g. "Original" or "ZPID" or rarely "DeepL")
        - one optional `bf:descriptionModifier` Literal (string) that states who made changes to the abstract text later (usually "ZPID")
- may have one secondary abstract `bf:summary > pxc:Abstract, pxc:SecondaryAbstract` with:
    - if it exists, always one (1) `rdfs:label` with the secondary abstract text as a string (language tagged)
    - one optional adminMetadata blank node for origin and possible editor of the abstract: `bf:adminMetadata > bf:AdminMetadata` with
        - one optional `bflc:metadataLicensor` Literal (string) that is the actual source/origin string of the translation (e.g. "ZPID" or "DeepL", rarely "Original")
        - one optional `bf:descriptionModifier` Literal (string) that states who made changes to the abstract text later (usually "ZPID")



Each Instance
- is, for now, a bnode of its encapsulating bf:Work, attached via `bf:hasInstance > bf:Instance`
- has class bf:Instance
- has exactly one (1) **DFK identifier** blank node: `bf:identifiedBy > bf:Local, pxc:DFK` which has
    - one `bf:source > bf:Source` blank node with exactly one `bf:code` Literal with value "ZPID.PSYNDEX" (unimportant for migration)
    - one `rdf:value` Literal with exactly 7 digits: this is **the actual DFK string**.
- has exactly one (1) **original title** (`bf:title > bf:Title`) which is a blank node with a `bf:mainTitle` Literal (language tagged) and one optional `bf:subtitle Literal` (language tagged)(there is also always a concatenated version of both in rdfs:label for easier querying, not needed for migration!)
- _may_ have at most 1 translated title in `bf:title > pxc:TranslatedTitle` which is a blank node with only a `bf:mainTitle` Literal, language tagged. (Translated Title has NO bf:subtitle Literal) (There is also always a "generic" copy of the translated title in rdfs:label for easier querying)
    - the translated title node also has one (1) source bnode: `bf:adminMetadata > bf:AdminMetadata` with a `bflc:metadataLicensor` Literal (string) that is the actual source/origin string of the translation (e.g. "DeepL" or "ZPID")
- 
## RDF-XML

The XML version (`ttl-data/bibframe-records.xml`) contains all the properties and blank nodes in nested form (even the instance). For example, a work in the RDF-XML file looks like this:

```xml
<bf:Work rdf:about="https://w3id.org/zpid/resources/works/0390704">
    <bf:hasInstance>
      <bf:Instance rdf:nodeID="N5df743317aa1491fba51ff66e89129a8">
        <bf:instanceOf rdf:resource="https://w3id.org/zpid/resources/works/0390704"/>
        <bf:identifiedBy>
          <bf:Local rdf:nodeID="Nfbd154a6e1014435b4c61a761d02647a">
            <rdf:type rdf:resource="https://w3id.org/zpid/ontology/classes/DFK"/>
            <bf:source>
              <bf:Source rdf:nodeID="Nc72bc028370a4e479ceb3ed399fd9337">
                <bf:code>ZPID.PSYNDEX.DFK</bf:code>
              </bf:Source>
            </bf:source>
            <rdf:value>0390704</rdf:value>
          </bf:Local>
        </bf:identifiedBy>
        <bf:title>
          <bf:Title rdf:nodeID="N4e5c95c21c9b4105baf09bf9f699dfd4">
            <bf:mainTitle xml:lang="de">Digitalisierung: Veränderungsmanagement zwischen analogen und digitalen Welten</bf:mainTitle>
            <rdfs:label xml:lang="de">Digitalisierung: Veränderungsmanagement zwischen analogen und digitalen Welten</rdfs:label>
          </bf:Title>
        </bf:title>
        <bf:title>
          <pxc:TranslatedTitle rdf:nodeID="Nc79d4e637ae040cc99b4c34892d5a69d">
            <bf:mainTitle xml:lang="en">Digitalization: Change management between analog and digital worlds</bf:mainTitle>
            <rdfs:label xml:lang="en">Digitalization: Change management between analog and digital worlds</rdfs:label>
            <bf:adminMetadata>
              <bf:AdminMetadata rdf:nodeID="Na0a54990990b44bc941068043dbf90ff">
                <bflc:metadataLicensor>ZPID</bflc:metadataLicensor>
              </bf:AdminMetadata>
            </bf:adminMetadata>
          </pxc:TranslatedTitle>
        </bf:title>
      </bf:Instance>
    </bf:hasInstance>
    <bf:language rdf:resource="http://id.loc.gov/vocabulary/iso639-2/ger"/>
    <bf:contribution>
      <bf:Contribution rdf:nodeID="Nd0b54436f681420990ea657fb4052ea2">
        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bflc/PrimaryContribution"/>
        <pxp:contributionPosition rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">1</pxp:contributionPosition>
        <bf:qualifier>first</bf:qualifier>
        <mads:hasAffiliation>
          <mads:Affiliation rdf:nodeID="Na1e60abdbefc415893cd3e5ad57582d8">
            <mads:organization>
              <bf:Organization rdf:nodeID="Nb845f4e97c26496a86f4bf927deed77a">
                <rdfs:label>Senior-Referat Veränderungsmanagement, DB Fernverkehr AG</rdfs:label>
              </bf:Organization>
            </mads:organization>
            <mads:hasAffiliationAddress>
              <mads:Address rdf:nodeID="N8cbe384fa3e24dcba5f2d4042bac9a6b">
                <mads:country>
                  <mads:Country rdf:nodeID="N10fe3614da7f4e059481356a057c92b1">
                    <rdfs:label>GERMANY</rdfs:label>
                    <schema:sameAs rdf:resource="http://geonames.org/2921044/"/>
                    <bf:identifier>
                      <bf:Identifier rdf:nodeID="N54eef818e23e44138cb70faa78d0962d">
                        <rdf:type rdf:resource="http://id.loc.gov/vocabulary/identifiers/geonames"/>
                        <rdf:value>2921044</rdf:value>
                      </bf:Identifier>
                    </bf:identifier>
                  </mads:Country>
                </mads:country>
              </mads:Address>
            </mads:hasAffiliationAddress>
          </mads:Affiliation>
        </mads:hasAffiliation>
        <mads:email rdf:resource="mailto:Jan.Kretzschmar@deutschebahn.com"/>
        <bf:role rdf:resource="https://w3id.org/zpid/vocabs/roles/AU"/>
        <bf:agent>
          <bf:Person rdf:nodeID="Nd6d468a1ec1242daad5e38a0c3686cf4">
            <rdfs:label>Kretzschmar, Jan</rdfs:label>
            <schema:familyName>Kretzschmar</schema:familyName>
            <schema:givenName>Jan</schema:givenName>
          </bf:Person>
        </bf:agent>
      </bf:Contribution>
    </bf:contribution>
    <bf:contribution>
      <bf:Contribution rdf:nodeID="N426862a9a34a400b97fc05439045d837">
        <pxp:contributionPosition rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">2</pxp:contributionPosition>
        <bf:qualifier>middle</bf:qualifier>
        <mads:hasAffiliation>
          <mads:Affiliation rdf:nodeID="N2631c69329ed4cb7955da04d9d91c281">
            <mads:organization>
              <bf:Organization rdf:nodeID="Ne7bb39d764ec443fa9bd25a751307829">
                <rdfs:label>Spezialist Veränderungsmanagement, Deutsche Bahn AG</rdfs:label>
              </bf:Organization>
            </mads:organization>
            <mads:hasAffiliationAddress>
              <mads:Address rdf:nodeID="Nb624be37e040426f92fb8a4707eec4e4">
                <mads:country>
                  <mads:Country rdf:nodeID="N08351671fbba4034813c0f5d050897a0">
                    <rdfs:label>GERMANY</rdfs:label>
                    <schema:sameAs rdf:resource="http://geonames.org/2921044/"/>
                    <bf:identifier>
                      <bf:Identifier rdf:nodeID="Nc5df539a980b4b1f984081154b46a7f5">
                        <rdf:type rdf:resource="http://id.loc.gov/vocabulary/identifiers/geonames"/>
                        <rdf:value>2921044</rdf:value>
                      </bf:Identifier>
                    </bf:identifier>
                  </mads:Country>
                </mads:country>
              </mads:Address>
            </mads:hasAffiliationAddress>
          </mads:Affiliation>
        </mads:hasAffiliation>
        <bf:role rdf:resource="https://w3id.org/zpid/vocabs/roles/AU"/>
        <bf:agent>
          <bf:Person rdf:nodeID="N9f36d201443b4db688680416fb05a19c">
            <rdfs:label>Buckel, Christoph</rdfs:label>
            <schema:familyName>Buckel</schema:familyName>
            <schema:givenName>Christoph</schema:givenName>
          </bf:Person>
        </bf:agent>
      </bf:Contribution>
    </bf:contribution>
    <bf:contribution>
      <bf:Contribution rdf:nodeID="Nf90a517e3da8495f9f180d60170c0419">
        <pxp:contributionPosition rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">3</pxp:contributionPosition>
        <bf:qualifier>last</bf:qualifier>
        <mads:hasAffiliation>
          <mads:Affiliation rdf:nodeID="N8bfe17a8d2ae41bc9b97b5fcec05b839">
            <mads:organization>
              <bf:Organization rdf:nodeID="Ne67268fc9ab34b268149b389c866ed55">
                <rdfs:label>Projekt Veränderungsmanagement, DB Fernverkehr AG</rdfs:label>
              </bf:Organization>
            </mads:organization>
            <mads:hasAffiliationAddress>
              <mads:Address rdf:nodeID="Nf3bd60f1249c49da9cae7388ef7335b7">
                <mads:country>
                  <mads:Country rdf:nodeID="N85f1e9ece36242cc853783c6aa24f9fe">
                    <rdfs:label>GERMANY</rdfs:label>
                    <schema:sameAs rdf:resource="http://geonames.org/2921044/"/>
                    <bf:identifier>
                      <bf:Identifier rdf:nodeID="N00c1aadee7a24facbbd94efa3a961755">
                        <rdf:type rdf:resource="http://id.loc.gov/vocabulary/identifiers/geonames"/>
                        <rdf:value>2921044</rdf:value>
                      </bf:Identifier>
                    </bf:identifier>
                  </mads:Country>
                </mads:country>
              </mads:Address>
            </mads:hasAffiliationAddress>
          </mads:Affiliation>
        </mads:hasAffiliation>
        <bf:role rdf:resource="https://w3id.org/zpid/vocabs/roles/AU"/>
        <bf:agent>
          <bf:Person rdf:nodeID="N2d3d6bdf1488478f8658d69bedfe4e16">
            <rdfs:label>Perlwitz, Andreas</rdfs:label>
            <schema:familyName>Perlwitz</schema:familyName>
            <schema:givenName>Andreas</schema:givenName>
          </bf:Person>
        </bf:agent>
      </bf:Contribution>
    </bf:contribution>
    <bf:summary>
      <pxc:Abstract rdf:nodeID="N33b58ec2760d48f6ad332e8ced3379de">
        <rdfs:label xml:lang="de">Im Gespräch zwischen den Autoren werden Vor- und Nachteile sowie Chancen und Risiken der digitalen Begegnung mit Blick auf (psychodramatische) Organisationsberatung diskutiert.</rdfs:label>
        <bf:adminMetadata>
          <bf:AdminMetadata rdf:nodeID="N84bdfd26884d490d85bd4e244b0322ad">
            <bflc:metadataLicensor>Original</bflc:metadataLicensor>
            <bf:descriptionModifier>ZPID</bf:descriptionModifier>
          </bf:AdminMetadata>
        </bf:adminMetadata>
      </pxc:Abstract>
    </bf:summary>
    <bf:summary>
      <pxc:Abstract rdf:nodeID="N341d311e992a48cd9cf9f1eba829f804">
        <rdf:type rdf:resource="https://w3id.org/zpid/ontology/classes/SecondaryAbstract"/>
        <rdfs:label xml:lang="en">In this article of the Zeitschrift für Psychodrama und Soziometrie (ZPS) the advantages and disadvantages of digital encounters are addressed, and opportunities and risks are highlighted. Organizational consulting with both digital and analog methods receives criticism and praise. Team development is considered with respect to the dichotomy between personal and digital contact-antitheses exist in this space that were not before conceivable but can now be viewed from a newly gained perspective made possible through the effects of actual experience. If both worlds are cleverly combined, a new range of possibilities exists-and the consultant's context changes. Digital collaboration increases and analogue methods gain value: the results being that people have more time for important encounters, they can use the prospects of efficiency and transparency that the digital world offers while not losing sight of the fact that real-life encounters and physical contact are important. (c) Springer Fachmedien Wiesbaden GmbH</rdfs:label>
        <bf:adminMetadata>
          <bf:AdminMetadata rdf:nodeID="Na6325fd3183949a783837b95f3db868b">
            <bflc:metadataLicensor>Original</bflc:metadataLicensor>
          </bf:AdminMetadata>
        </bf:adminMetadata>
      </pxc:Abstract>
    </bf:summary>
</bf:Work>
```

# Other things a Work may have (not strictly neccessary for first test migration)
... and subject to change:

Works may also have 0 or more linked preregistration works, which are attached via `bflc:relationship > bflc:Relationship > bf:supplement > bf:Work` and have a `bf:genreForm <https://w3id.org/zpid/vocabs/genres/preregistration>` (a skos:Concept uri) and a `bf:hasInstance > bf:Instance` blank node with a `bf:electronicLocator` Literal that contains the url of the preregistration as a string (e.g. "https://aspredicted.org/3g8sd.pdf") and/or a DOI, attached as a blank node with a string value via `bf:identifiedBy > bf:Doi > rdf:value`. The relationship itself is a blank node with a `bflc:relation <https://w3id.org/zpid/vocabs/relations/hasPreregistration>` (a skos:Concept) that states the type of relation, "has Preregistration".
The preregistration work may also have 0 or one (1) `bf:note > bf:Note > rdfs:label`with a string Literal that gives additional information about the preregistration (e.g. "Preregistration of Study 1 of the article").

```xml
<bf:Work>
    <bflc:relationship>
      <bflc:Relationship rdf:nodeID="N5971d2a0ea524f639421f23529614865">
        <bf:supplement>
          <bf:Work rdf:nodeID="Nb8c7839548ad44478002810874524982">
            <bf:genreForm rdf:resource="https://w3id.org/zpid/vocabs/genres/preregistration"/>
            <bf:hasInstance>
              <bf:Instance rdf:nodeID="N91a7711ca2f74ddcbe8a2b67b8531310">
                <bf:electronicLocator rdf:resource="https://cordis.europa.eu/project/id/646696"/>
                <bf:identifiedBy>
                  <bf:Identifier rdf:nodeID="Na55fe0fbd3134402bbdc5889c9903df9">
                    <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Doi"/>
                    <rdf:value>10.3030/646696</rdf:value>
                  </bf:Identifier>
                </bf:identifiedBy>
              </bf:Instance>
            </bf:hasInstance>
          </bf:Work>
        </bf:supplement>
        <bflc:relation rdf:resource="https://w3id.org/zpid/vocabs/relations/hasPreregistration"/>
        <bf:note>
          <bf:Note rdf:nodeID="N82962e3169a149a6b07695d34ab6be25">
            <rdfs:label>Study 2</rdfs:label>
          </bf:Note>
        </bf:note>
      </bflc:Relationship>
    </bflc:relationship>
</bf:Work>
```

# TODO: Fields to convert

## Werk

- [x] LA -> bf:language
- [ ] LA2!
- [x] ABH
  - [x] move from bnode to fragment uri
- [x] ABN
  - [x] move from bnode to fragment uri
- [x] extract Table of Contents from end of ABH
    - [x] move from bnode to fragment uri - except for urls?
- [x] AUP, PAUP, ORCID, CS, COU -> bf:contribution > bf:Contribution > bf:agent > bf:Person mit Affiliationen und Ror-ID-Lookup der Affiliation per API, Geonames-ID-Lookup des Affiliationslandes
    - [x] move from bnode to fragment uri
      - [x] Contribution node itself
      - [x] agent
      - [x] email
      - [x] role
      - [x] ORCID
      - [x] PAUP
      - [x] affiliation
      - [x] affil org
      - [x] affil address
      - [x] country 
      - [x] fix countries in affiliation with "None" label string
- [x] AUK (Körperschaften als Verfasser)
  - [x] restructure to make a generic contribution function?
  - [x] name (+ content of |i) -> rdfs:label
  - [x] optional (!) country - incl. geonames id - after lookup!
  - [x] get ror-id from API and add as identifier node
- [x] ABH: String endet in Lizenzierungsangaben (aber vorher das ToC abziehen!) wie "(C) Thieme"... -> Lizengeber erkennen und als Vokabularbegriff aus abstractnote-Vok exportieren. Format: [a pxc:Abstract ; bf:usageAndAccessPolicy [a bf:UsageAndAccessPolicy [rdfs:label "(C) Thieme"@en, ; rdf:value "vocabs/Thieme"^^^xsd:anyURI]]]. Wenn Abstract in ABH "leer" (also "Kein Abstract vorhanden"/"No abstract available" oder ähnlich, + nur kurzer String unter x Zeichen den Vok-Begriff vocabs/.../NoAbstract...)

### Beziehungen zu anderen Werken
- [x] REL -> Werk > bflc:relationship > bflc:Relationship > bf:relatedTo > bf:Work
- [x] TESTO (nur jeweils Subfeld |n und |c von TESTO und TESTG) -> Werk > bflc:relationship >> bflc:Relationship > bf:relatedTo > bf:Work

### Keywords/Classifications

- [x] CT with weighting
  - [x] skosmos lookup for uri
- [x] IT
- [x] SH mit weighting
- [ ] UTE/UTG?
- [ ] KP (Keyphrase)
- [x] CM

### Population:
- [ ] AGE (Achtung, hier passiert künstiches Upposting - wenn zb Preschool Age, dann immer auch Childood. Das verwässert die Suche. Eventuell muss ich da das Vokabular/Skosmos zur Migration nutzen: nur Leaf Nodes, also nur die niedrigsten Unterbegriffe mit exportieren - Skosmos-API: hat keinen Unterbegriff?) - und wie migrieren? Mit verschachtelter SKOS-Hierarchie direkt im Werk? als Work > concept > broader > concept!?
- [ ] PLOC
- [ ] SAM (manchmal |m |m , aber eigentlich nur noch ein |m, sonst nichts) (Human, Inanimate, Animal) 

### Open Science
- [x] GRANT -> bf:contribution > bf:FundingReference mit fundref-lookup per API bei Crossref
- [x] CF (only keeping for BE=SS and SM) -> bf:contribution > bf:ConferenceReference
- [x] DATAC (Forschungsdatenlink)
  - [x] move from bnode to fragment uri, making sure not to collapse several into one!
- [x] URLAI, das andere Forschungsdatenfeld nur für PsychData (sollte immer http://dx.doi.org/10.5160/psychdata.stuh96ko20 - 9-stellige alphanumerische ID - sein oder mit http://doi.org/10.5160/psychdata.stuh96ko20 oder https://doi.org oder - selten aber osf-Link drin!)
- [x] PRREG -> Work > bflc:relationship > bflc:Relationship > bf:supplement > bf:Work
  - [x] move from bnode to fragment uri, make sure not to collapse 2 or more into one by counting up or something.
- [x] RPLIC

### Dissertationen
- [x] GRAD 
- [x] PROMY
- [x] INST
- [x] ORT
- [x] HRF
- [x] KRF

## Instanzen/-bündel
- [x] DFK -> Instance > bf:identifiedBy > bf:Local, pxc:DFK
- [x] split work and instance, add uris based on DFK (simple - one work, one instance bundle; no multiple instances yet)
- [x] instancebundle with up to two instances, if we can get them based on MT2 etc.

### Titel und co
- [x] TI, TIL (Sprache) -> bf:title > bf:Title > bf:mainTitle
  - [x] move from bnode to fragment uri
- [x] TIU, TIUL -> bf:title > bf:Title > bf:subtitle
  - [x] move from bnode to fragment uri
- [x] TIUE (Übersetzung) -> bf:title > pxc:TranslatedTitle > bf:mainTitle
  - [x] move from bnode to fragment uri


- [ ] Lizenz! COPR -> |d Creative Commons Namensnennung - Nicht-kommerziell - Keine Bearbeitung |e Creative Commons Attribution - Non-Commercial - No-Derivatives |c CC BY-NC-ND 4.0 (Subfelder: |d (deutscher Name), |e (Englischer Name), |c (Kurzname))


### Veröffentlichung
- [x] BE
- [ ] DT -> Genre?
- [x] MT, MT2 an den einzelnen Instanzen
- [X] DOI
- [X] URN
- [X] URLAI

- [x] SE - Buchreihe -> auftrennen, Instanz > bflc:relationship >> bflc:Relationship > bf:hasSeries >> bf:Series/bf:Instance/bf:Uncontrolled ; bf:seriesStatement
  > bf:title > bf:Title > bf:mainTitle "Buchreihehntitel" ;
> bf:seriesEnumeration "Band 1" 
- [ ] NE - Edition -> Instanz > bf:editionStatement "2., überarb. Aufl." 

- [x] PY (nur Jahr)/PHIST (volles Datum in Subfeld |o: DD.MM.JJJJ) -> vorerst beim nur beim Instanbündel > bf:provisionActivity > bf:Publication > bflc:simpleDate (entweder "YYYY" wenn aus PY oder "YYYY-MM-DD" wenn aus PHIST)
- [x] PU v, o, zb "|v Budrich |o Opladen |i 978-3-8474-2429-1 |e 978-3-8474-1567-1" -> Verlag, Ort => -> InstanzBundle > bf:provisionActivity > bf:Publication > bf:agent > bf:Agent > bf:label "Budrich" ; bf:place > bf:Place > bf:label "Opladen" ; bzw simplePlace und simpleAgent und Literale- sollen die anderern sich doch um das Verknüpfen mit Normdaten kümmern!
  - [x] PU |i und |e: ISBN, E-ISBN an die Instanz > bf:identifiedBy > bf:Isbn > rdf:value "978-3-8474-2429-1" ; bf:identifiedBy > bf:Isbn > rdf:value "978-3-8474-1567-1"
  - [ ] (später vielleicht Verlage schon mit Fuzzywuzzy rekonzilieren!)



- [ ] PREIS -> in BN auslagern. Note an der Instanz? Trotzdem noch vorsichtshalber als bf:acquisitionTerms "Preis: 12,99 €" in Instanz?

### Biblio für Unselbständige:
#### Journal Article
- [x] JT
- [x] JBD
- [x] JHFT
- [x] ISSN, EISSN
- [x] PAGE -> aufsplitten in Start- und Endseite, Artikelnummer. Jeweils ins passende Feld. Wenn nicht absolute Zahl (Seitensumme), dann in Relationship zum Journal!

#### Chapter
- [ ] BIP - Titel des Buches
- [ ] EDRP - Herausgeber des Buches
- [x] SSDFK 
- [ ] SSNE - Edition
- [ ] SSSE - Buchreihe mit Band
- [ ] SSPU ? Veröffentlichungsangaben des ganzen Buchs

## General things

- [x] replace ^DD codes
- [x] unescape html entities


----

## Conversion and Migration status of PXR fields:

## Verschiedenes

- [ ] remarks (Bibliographic note zum Werk?) > `bf:note.rdfs:label`
- [ ] instance.metadataOrigin ??? nicht sicher, ob in Bestandsdaten, muss ich noch durchkämmen - scheint irgendwi in einem der `MK`-Felder zu stecken
- [x] instance.license > `bf:hasInstanceBundle.bf:usageAndAccessPolicy.` mit type `bf:UsePolicy` (Ziel ist eine URI aus dem licenses-Vokabular, zB https://w3id.org/zpid/vocabs/licenses/PUBL oder https://w3id.org/zpid/vocabs/licenses/CC_BY_4_0)
- [ ] instance.openAccessStatus > `bf:hasInstanceBundle.bf:usageAndAccessPolicy` mit type `bf:AccessPolicy` (Ziel ist uri aus access-Vokabular, zB https://w3id.org/zpid/vocabs/access/open oder https://w3id.org/zpid/vocabs/access/restricted) - berechnen  aus license & API-Abfrage bei OpenAlex?
- ~~instance.peerReviewStatus~~ - fällt weg, war auch nie in Bestandsdaten

### Contributors (Work)

#### contributingPersons

- [x] contributingPersons	ContributingPerson > `bfcontribution.bf:agent` (type: `bf:Person`)
- [x] contributingPerson.givenName > `bf:contribution.bf:agent.schema:givenName`
- [x] contributingPerson.familyName > `bf:contribution.bf:agent.schema:familyName`
- [x] contributingPerson.email > `bf:contribution.mads:email`               
- contributingPerson.normPerson - noch keine vorhanden in den Bestandsdaten -
- [x] contributingPerson.contributorRole > `bf:contribution.bf:role`
- [x] contributingPerson.orcId > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` type Identifier: `locid:orcid`
- [x] contributingPerson.affiliations	Affiliation > `bf:contribution.bf:agent.mads:hasAffiliation`
- [x] contributingPerson.affiliation.name > `bf:contribution.bf:agent.mads:hasAffiliation.mads:organization.rdfs:label`
- [x] contributingPerson.affiliation.rorId > `bf:contribution.bf:agent.mads:hasAffiliation.mads:organization.bf:identifiedBy.rdf.value`
- [x] contributingPerson.affiliation.normCorporateBodyId - noch keine vorhanden in den Bestandsdaten -              
- [x] contributingPerson.affiliation.country > (als geonames-id) `bf:contribution.bf:agent.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.rdfs:label`
- [x] contributingPerson.affiliation.normCountryId > `bf:contribution.bf:agent.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.bf:identifiedBy.rdf:value` (Identifier type `locid:geonames`)

#### contributingCorporateBodies

- [x] contributingCorporateBodies	`ContributingCorporateBody bfcontribution.bf:agent` (type: `bf:Organization`)
- [x] contributingCorporateBody.name > `bf:contribution.bf:agent.rdfs:label`
- [x] contributingCorporateBody.contributorRole > `bf:contribution.bf:role`
- [x] contributingCorporateBody.rorId > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` type Identifier: `locid:ror`
- [x] contributingCorporateBody.normCorporateBodyId - noch keine vorhanden in den Bestandsdaten -                
- [x] contributingCorporateBody.country > (wie bei Personen) `bf:contribution.bf:agent.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.rdfs:label`
- [x] contributingCorporateBody.normCountryId	> (wie bei Personen, als geonames-id) `bf:contribution.bf:agent.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.bf:identifiedBy.rdf:value` (Identifier type `locid:geonames`)

## Abstracts und Inhaltsverzeichnisse (Werk)
- [x] englishAbstract > `bf:summary.rdfs:label` (type: `pxc:Abstract`), ob english oder german: erkennbar an Sprachangabe des rdfs:label (en)
- [x] germanAbstract `bf:summary.rdfs:label` (type: `pxc:Abstract`), ob english oder german: erkennbar an Sprachangabe des rdfs:label (de)
- [x] englishAbstractOrigin > `bf:summary.bf:adminMetadata.bflc:metadataLicensor`
- [x] germanAbstractOrigin > `bf:summary.bf:adminMetadata.bflc:metadataLicensor`
- [x] englishAbstractEditOrigin > `bf:summary.bf:adminMetadata.bf:descriptionModifier`
- [x] germanAbstractEditOrigin> `bf:summary.bf:adminMetadata.bf:descriptionModifier`
- [x] englishAbstractNote > `bf:summary.bf:usageAndAccessPolicy.rdfs:label`  (Wert: viele verschiedene Strings wie "Abstract not released by publisher.", "translated by DeepL", "(c) Springer Nature Limited 2021", "(c) European Union", "(c) ZPID" etc. ...)
- [x] germanAbstractNote > wie bei englishAbstractNote:  `bf:summary.bf:usageAndAccessPolicy.rdfs:label`
- [x] englishAbstractblocked > `bf:summary.bf:adminMetadata.pxp:blockedAbstract` (true/false)
- [x] germanAbstractblocked > `bf:summary.bf:adminMetadata.pxp:blockedAbstract` (true/false)
- [x] toc > `bf:tableOfContents.rdfs.label`
- [x] tocUrl > `bf:tableOfContents.rdf:value` (Wert ist url nach Muster "..dnb../04")

## Funding (Werk)
- [x] funders	Funder > `bf:contribution.bf:agent` bei contribution type `pxc:FundingReference`
- [x] funder.name > `bf:contribution.bf:agent.rdfs:label`
- [x] funder.fundrefDoi > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` identifier type: `pxc:FundrefDoi`
- [x] funder.note > `bf:contribution.bf:note.rdfs:label`
- [x] funder.grants> `bf:contribution.pxp:grant`
- [x] funder.grant.grantId `bf:contribution.pxp:grant.bf:identifiedBy.rdf:value` bei identifier type `pxc:GrantId`
- funder.grant.doi - nicht in Bestandsdaten vorhanden - später aus PXR: > `bf:contribution.pxp:grant.bf:identifiedBy.rdf:value` bei identifier type `bf:Doi`

## Konferenzen (Werk)
- [x] conferenceReferences	ConferenceReference > `bf:contribution.bf:agent` bei contribution type `pxc:ConferenceReference` (agent type ist `bf:Meeting`)
- [x] conferenceReference.name > `bf:contribution.bf:agent.rdfs:label`
- conferenceReference.doi - nicht in Bestandsdaten - später aus PXR: `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` bei identifier type `pxc:ConferenceDoi`
- [x] conferenceReference.year >  `bf:contribution.bf:agent.bflc:simpleDate` 
- [x] conferenceReference.place > `bf:contribution.bf:agent.bflc:simpleDate`
- [x] conferenceReference.note > `bf:contribution.bf:note.rdfs:label`


## InstanceBundles ("Instanzen" in PXR)

- [x] instance.formatInstances > `pxp:hasInstanceBundle.bf:hasPart` (Array, bisher immer nur 1-2 Instanzen darin)

## Titel (InstanceBundle)

- [x] instance.mainTitle > `pxp:hasInstanceBundle.bf:title.bf:mainTitle` type: `bf:Title;` Sprache ist im Sprachtag (en oder de)
- [x] instance.subTitle > `pxp:hasInstanceBundle.bf:title.bf:subitle` type: `bf:Title`; Sprache ist im Sprachtag (en oder de)
- [x] instance.translatedTitle > `pxp:hasInstanceBundle.bf:title.bf:mainTitle` bei title type: `bf:TranslatedTitle`; Sprache ist im Sprachtag (en oder de)
- [x] instance.translatedTitleOrigin `pxp:hasInstanceBundle.bf:title.bf:adminMetadata.bflc:metadataLicensor` bei title type: `bf:TranslatedTitle`

## Verlagsangaben/Publikationsangaben (InstanceBundle)

- [x] instance.placeOfPublicationString > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simplePlace` type of provision activity: `bf:Publication`
- instance.placeOfPublication	Place - noch keine Normverknüpfungen in den Bestandsdaten
- [x] instance.publisherName > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simpleAgent`
- instance.publisherLink - noch keine Normverknüpfungen in den Bestandsdaten
- [x] instance.formatInstance.date > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simpleDate` (entweder YYYY - meistens; oder eher selten: YYYY-MM-DD aus unstrukturiertem PHIST mit parsedate erkannt) Achtung: am InstanceBundle, da immer nur ein Publikationsdatum im Record, auch bei zwei Formatinstanzen

## Reihenangaben für Bücher

- [x] instance.seriesTitle
- [-] instance.subSeriesTitle
- [x] instance.seriesVolume
- [ ] instance.bookEdition

## Kapitel und Journal Articles: Verweis auf umgebendes Buch oder Journal

- [x] instance.journalTitle
- [x] instance.containingJournal
- [ ] instance.containingBook	Instance

- [x] instance.journalVolume
- [x] instance.journalIssue

- [x] instance.formatInstance.startPage
- [x] instance.formatInstance.endPage
- [ ] instance.formatInstance.pageCount
- [x] instance.formatInstance.issn
- [x] instance.formatInstance.articleNumber

## Links und Identifier der Instanzen selbst 

- [x] instance.dfk > `pxp:hasInstanceBundle.bf:identifiedBy.rdf:value` bei identifier type `pxc:DFK`
- [x] instance.formatInstance.isbn > `pxp:hasInstanceBundle.bf:identifiedBy.rdf:value` bei identifier type `bf:Isbn` (hash-uri endet bei isbns für Print-OFrmatinstanzen in `#isbn_print` und bei Online-Formatinstanzen in `#isbn_ebook` )
- [x] instance.formatInstance.publicationUrls > `pxp:hasInstanceBundle.bf:hasPart.bf:electronicLocator`
- [x] instance.formatInstance.publicationUrns `pxp:hasInstanceBundle.bf:hasPart.bf:identifiedBy.rdf:value` bei identifier type `bf:Urn`
- [x] instance.formatInstance.doi > `pxp:hasInstanceBundle.bf:hasPart.bf:identifiedBy.rdf:value` bei identifier type `bf:Doi`

## Status
- [ ] publishingStatus
- [ ] psyFoMoStatus

## ? (Personen/Körperschaften als Thema?)
- concernedPersonIds  - nicht in den Bestandsdaten
- concernedCorporateBodyIds - nicht in den Bestandsdaten

## Verwandte Werke (Werk)
- [x] relatedWorks	RelatedWork
- [x] relatedWork.relationType
- [x] relatedWork.objectWork
- [x] relatedWork.doi
- [x] relatedWork.citation
- [x] relatedWork.url

- [x] relatedTestOrMeasures	RelatedTestOrMeasure
- [x] relatedTestOrMeasure.relationType
- [x] relatedTestOrMeasure.shortName
- [x] relatedTestOrMeasure.longName
- [x] relatedTestOrMeasure.test
- [x] relatedTestOrMeasure.itemsComplete
- [x] relatedTestOrMeasure.remark

## Plain Language Summaries (Werk)
- englishShortPls - nicht in den Bestandsdaten
- englishShortPlsOrigin - nicht in den Bestandsdaten
- longPlsDoi - nicht in den Bestandsdaten
- longPlsUrl - nicht in den Bestandsdaten
- longPlsStatus - nicht in den Bestandsdaten

## Verschlagwortung (Werk)
- [x] controlledKeywords > `bf:subject.owl:sameAs` bei subject type `bf:Topic` und zusätzlich `pxc:WeightedTopic` wenn gewichtet. (Wert ist eine Uri aus dem "terms"-Vokabular wie zB https://w3id.org/zpid/vocabs/terms/02370)
- [x] subjectClassifications
- [ ] methodClassifications	-
- [ ] ageGroups
- [ ] simplePopulationLocations
- [ ] populationLocation	Place
- [ ] sampleCharacteristics
- [ ] authorKeywords
- [ ] uncontrolledKeywords


## Dissertationsangaben (Werk)
- [x] degreeGranted
- [x] dateDegreeGranted
- [x] thesisAdvisor	Person
- [x] thesisAdvisorGivenName
- [x] thesisAdvisorFamilyName
- [x] thesisReviewerGivenName
- [x] thesisReviewerFamilyName
- [x] thesisReviewer	Person

## referenceWorks (Werk) 
- [x] referencedWorks	ReferencedWork
- [x] referencedWork.authors	string		0..n	-
- [x] referencedWork.title	string		1..1	-
- [x] referencedWork.publicationYear	integer		0..1	-
- [x] referencedWork.doi	string	{Doi}	0..1	-
- [x] referencedWork.citation?
<!-- - [ ] referencedWork.journalName	string		0..1	-
- [ ] referencedWork.journalVolume	string	{*Regex*:/^[0-9]+$/}	0..1	-
- [ ] referencedWork.journalIssue	string	{*Regex*:/^(?:\d+(?:-\d+)?|Supp|S\d+)$/}	0..1	-
- [ ] referencedWork.journalSites	string		0..1	- -->


## Typen von Werk und Instanz
- [x] contentType -> `bf:content` (Wert ist Uri aus content-Vokabular, zB https://w3id.org/zpid/vocabs/contenttypes/text)
- [ ] genre - muss noch abgeleitet werden aus verschiedenen Feldern. > `bf:genreForm` (Wert ist Uri aus genres-Vokabular, zB https://w3id.org/zpid/vocabs/genres/ResearchPaper)
- [x] instance.publicationType > `pxp:issuanceType`  (Wert ist Uri aus issuances-Vokabular, zB https://w3id.org/zpid/vocabs/issuances/JournalArticle)
- [x] instance.formatInstance.carrierType `pxp:mediaCarrier` (Wert ist Uri aus mediacarriers-Vokabular, zB https://w3id.org/zpid/vocabs/mediacarriers/Online)

## Links zu Forschungsdaten 
- [x] researchData	ResearchData	> `bflc:relationship` type der relationship ist immer: `pxc:ResearchDataRelationship`
- [x] researchData.relation	> `bflc:relationship.bflc:relation`  (Werte: später entweder "relations:hasResearchData" oder "relations:hasAnalyticCode", bisher gibt es im Bestand aber nur welche mit "relations:hasResearchData")
- [x] researchData.doi	`bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy` (bei identifier type `bf:Doi`) (Node ist DOI als volle URL an)
- [x] researchData.url	`bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:electronicLocator`
- [x] researchData.access	`bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:usageAndAccessPolicy` (Wert ist Uri aus access-Vokabular, bisher immer bei allen im Bestand verlinkten Forschungsdaten: https://w3id.org/zpid/vocabs/access/open) Achtung: in den aktuell verlinkten Daten noch nicht geändert, wird aber Direktlink auf URI des Vokabularbegriffs sein, statt owl.sameAs-Beziehung.


## Links zu Präregistrierungen
- [x] preregisteredStudies	PreregisteredStudy	> `bflc:relationship` type der relationship ist immer: `pxc:PreregistrationRelationship`
- [x] preregisteredStudy.doi >	`bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.rdf:value` (bei identifier type `bf:Doi`)
- [x] preregisteredStudy.url >	`bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:electronicLocator`
- [x] preregisteredStudy.trialNumber > `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.rdf:value` (bei identifier type `pxc:TrialNumber`)	- kompliziert aus Infofeld PRREG |i geparst und nur angehängt, wenn nicht schon Teil der URL einer schon existierenden pxc:PreregistrationRelationship. 
- [x] preregisteredStudy.trialRegistry	> an der TrialNumber als "assigner": `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.bf:assigner` (Wert ist Uri aus assigner-Vokabular, zB https://w3id.org/zpid/vocabs/trialregs, zB https://w3id.org/zpid/vocabs/trialregs/prospero; hat auch type `pxc:TrialRegistry`)
- [x] **preregisteredStudy.note**  `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:note.rdfs:label` (Wert ist String) - aber dafür gibt es gar kein Feld in PSYNDEXER?

## Links zu replizierten Studien #
- [x] replicatedStudies	ReplicatedStudy		0..n	-
- [x] replicatedStudy.relationType	string	{ControlledTerm[group=relations, collection=PSYNDEXoriginalDataRelations]->id}	1..1	-
- [x] replicatedStudy.doi	string	{Doi}	0..1	-
- [x] replicatedStudy.url	string	{Url}	0..1	-
- [x] replicatedStudy.studyId	string	{Work->id}	0..1	-
- [x] replicatedStudy.citation


