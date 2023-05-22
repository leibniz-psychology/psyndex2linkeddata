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