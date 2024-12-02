- Alle Arten von Werken
- Format: alle von easyrdf (genauer: sweetrdf/easyrdf) unterstützen Formate. NICHT: framed Json.
- Beispiele in https://github.com/leibniz-psychology/psyndex2linkeddata/blob/df86df7111404e956f42542a7dbfee898cd9215e/ttl-data/bibframe_records.xml

## Spezifikation und Umsetzungsstatus
Nur markierte Punkte ([x]) werden als Teil der MVP-Spezifikation betrachtet und umgesetzt.

### Verschiedenes

- [x] remarks (Bibliographic note zum Werk) > `bf:Work, pxc:MainWork >> bf:note > bf:Note >> rdfs:label "Content of note"`
- instance.metadataOrigin - nichts in Bestanddaten gefunden -> nicht exportiert
- [x] instance.license > `bf:hasInstanceBundle.bf:usageAndAccessPolicy.` mit type `bf:UsePolicy` (Ziel ist eine URI aus dem licenses-Vokabular, zB https://w3id.org/zpid/vocabs/licenses/PUBL oder https://w3id.org/zpid/vocabs/licenses/CC_BY_4.0)
- instance.openAccessStatus > nicht in den Bestandsdaten, daher nichts migriert. Später würde es so aussehen: `bf:hasInstanceBundle.bf:usageAndAccessPolicy` mit type `bf:AccessPolicy` (Ziel ist uri aus access-Vokabular, zB https://w3id.org/zpid/vocabs/access/open oder https://w3id.org/zpid/vocabs/access/restricted) - könnte man das eventuell berechnen aus license (z.B. license eine der CCs, dann muss es ja quasi offen sein?) &/oder API-Abfrage bei OpenAlex (der OA-Status bei OpenAlex ist aber oft nicht korrekt)?
- ~~instance.peerReviewStatus~~ - fällt weg, war auch nie in Bestandsdaten

### Contributors (Work)

#### contributingPersons

- [x] contributingPersons ContributingPerson > `bfcontribution.bf:agent` (type: `bf:Person`) Hinweis: Die Knoten sind erkennbar an Schemata: für Contribution: `<https://w3id.org/zpid/resources/works/0388777_work#contribution2>` und Agent Person: `<https://w3id.org/zpid/resources/works/0388777_work#contribution2_personagent>`
- [x] contributingPerson.givenName > `bf:contribution.bf:agent.schema:givenName`
- [x] contributingPerson.familyName > `bf:contribution.bf:agent.schema:familyName`
- [x] contributingPerson.email > `bf:contribution.mads:email <mailto:person@example.org>` (Achtung: nicht an der bf:Person, sondern an der bf:Contribution - wie auch die Affiliationen und Rolle gelten die ja nur für diese Person im Kontext dieser Publikation)
- contributingPerson.normPerson - keine vorhanden in den Bestandsdaten - später in Psyndexer rekonzilieren anhand ORCID oder PsychAuthorsID, siehe weiter unten
- [x] contributingPerson.contributorRole > `bf:contribution.bf:role`
- [x] contributingPerson.orcId > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` type Identifier: `locid:orcid`
- [x] contributingPerson.affiliations Affiliation > `bf:contribution.bf:agent.mads:hasAffiliation` Achtung auch hier: an der Contribution, nicht am Agent
- [x] contributingPerson.affiliation.name > `bf:contribution.mads:hasAffiliation.mads:organization.rdfs:label` Achtung, Änderung! Nicht mehr am Agent bzw das war ein Fehler. Auch hier übrigens Schemata für die Hash-URIs der Knoten für Affiliationen: `<https://w3id.org/zpid/resources/works/0388777_work#contribution4_personagent_affiliation1>`
- [x] contributingPerson.affiliation.rorId > `bf:contribution.mads:hasAffiliation.mads:organization.bf:identifiedBy.rdf.value` Schema für Agent der Affiliation: `<https://w3id.org/zpid/resources/works/0388777_work#contribution4_personagent_affiliation1_organization>`
- [x] contributingPerson.affiliation.normCorporateBodyId - noch keine vorhanden in den Bestandsdaten - später in Psyndexer rekonzilieren anhand ror-ID der Affiliationskörperschaft, siehe weiter unten
- [x] contributingPerson.affiliation.country > (als geonames-id) `bf:contribution.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.rdfs:label` Schema für Adressknoten: `<https://w3id.org/zpid/resources/works/0388777_work#contribution5_personagent_affiliation1_address>` und für Land-Knoten: `<https://w3id.org/zpid/resources/works/0388777_work#contribution5_personagent_affiliation1_address_country>`
- [x] contributingPerson.affiliation.normCountryId > `bf:contribution.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.bf:identifiedBy.rdf:value` (Identifier type `locid:geonames`) Also Geonames-ID. Schema für den entsprechenden identifier-Knoten: `<https://w3id.org/zpid/resources/works/0388777_work#contribution5_personagent_affiliation1_address_country_geonamesid>`

#### contributingCorporateBodies

- [x] contributingCorporateBodies `ContributingCorporateBody bfcontribution.bf:agent` (type: `bf:Organization`) Schema: `<https://w3id.org/zpid/resources/works/0388426_work#contribution25_orgagent>`
- [x] contributingCorporateBody.name > `bf:contribution.bf:agent.rdfs:label` zB "CA IMAGEN Consortium"
- [x] contributingCorporateBody.contributorRole > `bf:contribution.bf:role`
- [x] contributingCorporateBody.rorId > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` type Identifier: `locid:ror` Schema: `<https://w3id.org/zpid/resources/works/0388426_work#contribution26_orgagent_rorid>` (gibt es allerdings nur äußerst selten, da beitragende Körperschaften fast immer Arbeitsgruppen sind, welche keine Ror-ID haben)
- [x] contributingCorporateBody.normCorporateBodyId - noch keine vorhanden in den Bestandsdaten - später eventuell in Psyndexer rekonzilieren anhand rorID, falls vorhanden
- [x] contributingCorporateBody.country > (wie bei Personen) `bf:contribution.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.rdfs:label` zB "Germany". Schema: `<https://w3id.org/zpid/resources/works/0388426_work#contribution25_orgagent_affiliation1_address_country>`
- [x] contributingCorporateBody.normCountryId > (wie bei Personen, als geonames-id) `bf:contribution.mads:hasAffiliation.mads:hasAffiliationAddress.mads:country.bf:identifiedBy.rdf:value` (Identifier type `locid:geonames`) Schema: `<https://w3id.org/zpid/resources/works/0388426_work#contribution25_orgagent_affiliation1_address_country_geonamesid>`
## Abstracts und Inhaltsverzeichnisse (Werk)
- [x] englishAbstract > `bf:summary.rdfs:label` (type: `pxc:Abstract`), ob english oder german: erkennbar an Sprachangabe des rdfs:label (en) z.B. rdfs:label "In the current study..."@en
- [x] germanAbstract `bf:summary.rdfs:label` (type: `pxc:Abstract`), ob english oder german: erkennbar an Sprachangabe des rdfs:label (de) zB "In dieser Studie..."@de
- [x] englishAbstractOrigin > `bf:summary.bf:adminMetadata.bflc:metadataLicensor` zB "ZPID" (unterscheidbar von germanAbstractOrigin durch Sprache des rdfs:labels, siehe oben)
- [x] germanAbstractOrigin > `bf:summary.bf:adminMetadata.bflc:metadataLicensor`
- [x] englishAbstractEditOrigin > `bf:summary.bf:adminMetadata.bf:descriptionModifier`
- [x] germanAbstractEditOrigin> `bf:summary.bf:adminMetadata.bf:descriptionModifier`
- [x] englishAbstractNote > `bf:summary.bf:usageAndAccessPolicy.rdfs:label` mit type bf:UsageAndAccessPolicy (Wert für label: viele verschiedene Strings wie "Abstract not released by publisher.", "translated by DeepL", "(c) Springer Nature Limited 2021", "(c) European Union", "(c) ZPID" etc. ...)
- [x] germanAbstractNote > wie bei englishAbstractNote: `bf:summary.bf:usageAndAccessPolicy.rdfs:label`
- neu, mvp-2.0: englishAbstractblocked > `bf:summary.bf:adminMetadata.pxp:blockedAbstract` (true/false) - kann wohl ignoriert werden, da diese Angabe in Zukunft im jeweiligen Journal vermerkt wird
- neu, mvp-2.0: germanAbstractblocked > `bf:summary.bf:adminMetadata.pxp:blockedAbstract` (true/false) - kann wohl ignoriert werden, da diese Angabe in Zukunft im jeweiligen Journal vermerkt wird
- [x] toc > `bf:tableOfContents.rdfs.label` zB: "(1) [...] (3) Kemény, F., Banfi, C., Gangl, M., Perchtold, C. M., Papousek, I., Moll, K. & Landerl, K. (2018). Print-, sublexical and lexical processing in children with reading and/or spelling deficits: An ERP study. International Journal of Psychophysiology, 130, 53-62. DOI: 10.1016/j.ijpsycho.2018.05.009"@en (kann auch @de sein) - Sprachangabe ignorieren, das unterscheiden wir in Psyndexer anscheinden nicht (ich habe es von der Abstractsprache übernommen, denn Text-ToC sind in STAR im Abstract-Feld angehängt und ich habe sie da rausgeschnitten). Schema des des ToC-Knotens: `<https://w3id.org/zpid/resources/works/0390750_work#toc>`
- [x] tocUrl > `bf:tableOfContents.rdf:value` (Wert ist url nach Muster "..dnb../04", zB `https://d-nb.info/1253236194/04"^^xsd:anyURI`). Schema Knoten siehe oben bei "toc"

## Funding (Werk)
- [x] funders Funder > `bf:contribution.bf:agent` bei contribution type `pxc:FundingReference` Schema: `<https://w3id.org/zpid/resources/works/0388777_work#fundingreference1>` und für den Agent/Funder: `<https://w3id.org/zpid/resources/works/0388777_work#fundingreference1_funder>`
- [x] funder.name > `bf:contribution.bf:agent.rdfs:label` zB "Federal Ministry of Education and Research (BMBF)"
- [x] funder.fundrefDoi > `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` identifier type: `pxc:FundrefDoi` zB "10.13039/501100002347"; Schema: `<https://w3id.org/zpid/resources/works/0388777_work#fundingreference1_funder_funderid>`
- [x] funder.note > `bf:contribution.bf:note.rdfs:label` zB "Horizon 2020 research and innovation programme"; Schema: `<https://w3id.org/zpid/resources/works/0387051_work#fundingreference1_note>
- [x] funder.grants> `bf:contribution.pxp:grant` Schema: `<https://w3id.org/zpid/resources/works/0388777_work#fundingreference1_grant1>`
- [x] funder.grant.grantId `bf:contribution.pxp:grant.bf:identifiedBy.rdf:value` bei identifier type `pxc:GrantId` zB "01EL2006A"; Schema: `<https://w3id.org/zpid/resources/works/0388777_work#fundingreference1_grant1_awardnumber>`
- funder.grant.doi - nicht in Bestandsdaten vorhanden - später aus PXR: > `bf:contribution.pxp:grant.bf:identifiedBy.rdf:value` bei identifier type `bf:Doi`

## Konferenzen (Werk)
- [x] conferenceReferences ConferenceReference > `bf:contribution.bf:agent` bei contribution type `pxc:ConferenceReference` (agent type ist `bf:Meeting`) Schema: `<https://w3id.org/zpid/resources/works/0390043_work#conferencereference1>` für die ConferenceReference und `<https://w3id.org/zpid/resources/works/0390043_work#conferencereference1_meeting>` für den Agent vom type Meeting
- [x] conferenceReference.name > `bf:contribution.bf:agent.rdfs:label` zB "40. Jahrestagung des Arbeitskreises Klinische Psychologie in der Rehabilitation 2021"
- conferenceReference.doi - nicht in Bestandsdaten - später aus PXR: `bf:contribution.bf:agent.bf:identifiedBy.rdf:value` bei identifier type `pxc:ConferenceDoi`
- [x] conferenceReference.year > `bf:contribution.bf:agent.bflc:simpleDate` zB "2021"
- [x] conferenceReference.place > `bf:contribution.bf:agent.bflc:simplePlace` zB "online"
- [x] conferenceReference.note > `bf:contribution.bf:note.rdfs:label` zB "Date(s): 12.11 bis 13.11. 2021. Psychologische Schmerztherapie in der medizinischen Rehabilitation."; Schema Note-Knoten: `<https://w3id.org/zpid/resources/works/0390043_work#conferencereference1_note>`

## InstanceBundles ("Instanzen" in PXR)

- [x] instance.formatInstances > `pxp:hasInstanceBundle.bf:hasPart` Schema für die angehängte bf:Instance (Formatinstanz): `<https://w3id.org/zpid/resources/instances/0390503#1>`
## Titel (InstanceBundle)

- [x] instance.mainTitle > `pxp:hasInstanceBundle.bf:title.bf:mainTitle` type: `bf:Title;` Sprache ist im Sprachtag (en oder de), zB "Study protocol: A non-randomised community trial to evaluate the effectiveness of the communities that care prevention system in Germany"@en; Schema für Knoten: `<https://w3id.org/zpid/resources/instancebundles/0388777#title>`
- [x] instance.subTitle > `pxp:hasInstanceBundle.bf:title.bf:subtitle` type: `bf:Title`; Sprache ist im Sprachtag (en oder de) zB "For the time after the pandemic, we need a vision and investments for the future"@en - Achtung: hängt am selben Title-Knoten wie der mainTitle, zB `<https://w3id.org/zpid/resources/instancebundles/0388777#title>`!
- [x] instance.translatedTitle > `pxp:hasInstanceBundle.bf:title.bf:mainTitle` bei title type: `bf:TranslatedTitle`; Sprache ist im Sprachtag (en oder de); zB "Studienprotokoll: Eine nicht-randomisierte Gemeinschaftsstudie zur Bewertung der Wirksamkeit des Präventionssystems \"Communities That Care\" in Deutschland"@de; Schema: `<https://w3id.org/zpid/resources/instancebundles/0388777#translatedtitle>` Anmerkung: hier gibt es nie einen subtitle, der ist immer im mainTitle integriert und wird nicht nochmal getrennt gespeichert.
- [x] instance.translatedTitleOrigin `pxp:hasInstanceBundle.bf:title.bf:adminMetadata.bflc:metadataLicensor` bei title type: `bf:TranslatedTitle` zB "ZPID"; Schema für AdminMetadata-Knoten: `<https://w3id.org/zpid/resources/instancebundles/0388777#translatedtitle_source>`

## Verlagsangaben/Publikationsangaben (InstanceBundle)

- [x] instance.placeOfPublicationString > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simplePlace` type of provision activity: `bf:Publication`
- instance.placeOfPublication Place - noch keine Normverknüpfungen in den Bestandsdaten
- [x] instance.publisherName > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simpleAgent`
- instance.publisherLink - noch keine Normverknüpfungen in den Bestandsdaten
- [x] instance.formatInstance.date > `pxp:hasInstanceBundle.bf:provisionActivity.bflc:simpleDate` (entweder YYYY - meistens; oder eher selten: YYYY-MM-DD aus unstrukturiertem PHIST mit parsedate erkannt) Achtung: am InstanceBundle, da immer nur ein Publikationsdatum im Record, auch bei zwei Formatinstanzen

## Reihenangaben für Bücher

- [x] instance.seriesTitle > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390495#seriesrel>) > bf:relatedTo > bf:Hub, bf:Series (z.B. <https://w3id.org/zpid/resources/instancebundles/0390495#seriesrel_series>) >> bf:title > bf:Title (z.B. <https://w3id.org/zpid/resources/instancebundles/0390495#seriesrel_series_title>) >> bf:mainTitle "UTB"` oder "Schriften des Sigmund-Freud-Instituts, Reihe 1, Klinische Psychoanalyse: Depression"
- instance.subSeriesTitle - nicht migriert; kommt selten vor und steht sehr inhomogen formatiert mit im Feld für den Reihen(haupt)titel - müsste wohl mal manuell auseinanderklamüsert werden wie im 2. Beispiel oben. Dann kommt auch eine Bibframe-Modellierung dafür.
- [x] instance.seriesVolume > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390495#seriesrel>) > bf:seriesEnumeration "5606"`
- [x] instance.bookEdition > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bf:editionStatement > "6., aktual. u. überarb. Aufl."`
## Kapitel und Journal Articles: Verweis auf umgebendes Buch oder Journal

- [x] instance.journalTitle > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel>) > bf:relatedTo > bf:Hub, bf:Serial (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel_journal>) >> bf:title > bf:Title (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel_journal_title>) >> bf:mainTitle "Musiktherapeutische Umschau"` - wichtig: unterscheidbar von Buchreihenangabe durch "...#journalrel" und ...#journalrel_journal in der URI (statt "...#seriesrel" und ...#seriesrel_series) sowie an bf:Seri**al** statt bf:Ser**ies** als zweiter rdf:type des bf:Hub
- instance.containingJournal - hier wird ein Journal aus unserer Journal-Datenbank verlinkt. Die Links haben wir noch nicht, bzw müssen die erst mal irgendwann in Psyndexer auto-rekonzilieren, vermutlich am besten anhand der ISSN/Lissn
- [x] instance.containingBook Instance > Falls Buch in PSYNDEX, anhand dessen via seine DFK verknüpfen: `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:identifiedBy > pxc:DFK >> rdf:value "0388327"` - aber was wird aus dem Titel von Büchern, die bisher nicht in PSYNDEX sind? Man sollte sie erkennen an Zweitklasse/typ "bflc:Uncontrolled" neben "pxc:InstanceBundle" -> Es sollen dann neue Bücher automatisch angelegt werden, denn zukünftig soll es _immer_ ein Buch zu jedem Kapitel in der Datenbank geben. Das neu angelegte Buch soll dann die folgenden Werte bekommen:
- [x] contributingPerson.givenName > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:instanceOf > bf:Work >> bf:contribution > bf:Contribution >> bf:agent > bf:Person >> schema:givenName "Ludger"`(EDRP)
- [x] contributingPerson.familyName > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:instanceOf > bf:Work >> bf:contribution > bf:Contribution >> bf:agent > bf:Person >> schema:familyName "Kühnhardt"`(EDRP)
- [x] contributingPerson.contributorRole > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:instanceOf > bf:Work >> bf:contribution > bf:Contribution >> bf:role roles:ED` (aus EDRP)
- [x] instance.mainTitle > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:title > bf:Title >> bf:mainTitle "The Bonn handbook of globality. Volume 1"` (aus BIP)
- [x] instance.bookEdition > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:editionStatement > "6., aktual. u. überarb. Aufl."` (aus SSNE) falls vorhanden
- [x] instance.seriesTitle > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> bf:seriesStatement "Jahrbuch für Psychoanalyse und Musik, Band 5" (SSSE) falls vorhanden
- [x] instance.publisherName > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >>  bf:provisionActivity > bf:Publication >> bflc:simpleAgent "Budrich"` (SSPU)
- [x] instance.formatInstance.date > Publikationsdatum des umgebenden Buchs müssen wir aus dem Datum des Kapitels entnehmen, sonst gibt es keins, sofern das Buch nicht in STAR war: `pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bf:provisionActivity > bf:Publication >> bflc:simpleDate "2021"`
- [x] instance.placeOfPublicationString > `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >>  bf:provisionActivity > bf:Publication >> bflc:simplePlace "Opladen"` (SSPU)
- [x] instance.formatinstance.isbn > (teilweise ist beides vorhanden, isbn_print und isbn_ebook, aber nicht immer; wenn ja, beide Formatinstanzen anlegen!) `bf:Work, pxc:MainWork >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship > bf:partOf > pxc:InstanceBundle >> identifiedBy > bf:Isbn (z.B. <https://w3id.org/zpid/resources/instancebundles/0389999#isbn_ebook>) >> rdf:value "rdf:value "978-3-8474-1567-1"` (hash-uri endet bei isbns für Print-Formatinstanzen in `#isbn_print` und bei Online-Formatinstanzen in `#isbn_ebook`)

- [x] instance.journalVolume > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel>) > pxp:inVolume "42"`
- [x] instance.journalIssue > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel>) > pxp:inIssue "4"`

- [x] instance.formatInstance.startPage > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel> oder <...bookrel> bei Kapiteln) > pxp:pageStart "360"` (Anmerkung: am InstanceBundle, nicht der einzelnen Formatinstanz zugeordnet)
- [x] instance.formatInstance.endPage > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel> oder <...bookrel> bei Kapiteln) > pxp:pageStart "375"`(Anmerkung: am InstanceBundle, nicht der einzelnen Formatinstanz zugeordnet)
- [x] instance.formatInstance.pageCount > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bf:extent > bf:Extent >> rdf:value "15"` (außerdem, aber ignorierbar, da immer gleich: `bf:Extent >> bf:unit <http://rdaregistry.info/termList/RDACarrierEU/1023>` (kontrollierter Begriff der RDA, steht für "page"/"Seite"); Anmerkung: am InstanceBundle, nicht der einzelnen Formatinstanz zugeordnet. Außerdem: nicht in der Relationship, sondern direkt an Instanz(-bündel).
- [x] instance.formatInstance.issn > `bf:Work, pxc:MainWork > bf:hasInstanceBundle > pxc:InstanceBundle (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496>) >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel>) >> bf:relatedTo > bf:Hub, bf:Serial (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel_journal>) >> bf:identifiedBy > bf:Issn (z.B. <https://w3id.org/zpid/resources/instancebundles/0390496#journalrel_journal_issnprint>) > rdf:value "0172-5505"` Anmerkung: es gibt potenziell sowohl "...`_issnprint`" als auch "...`_issnonline`". Beide hängen aber, wie die isbns, am Instanzbündel und sind noch nicht auf die Print- Und Online-Formatinstanzen verteilt. (Weil das ultraschwer ist, denn ist gibt zahlreiche Inkonsistenzen in den Quelldaten, die alle abgefangen müssten... vielleicht bekommst du das ja sinnvoll hin... Zum Beispiel gibt es manchmal gar keine Online-Formatinstanz, an die man die ISSN hängen könnte, weil jemand vergass, das MT2-Feld mit "Online Resource" zu füllen)
- [x] instance.formatInstance.articleNumber > `bf:Work, pxc:MainWork > pxp:hasInstanceBundle > pxc:InstanceBundle >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/instancebundles/0390655#journalrel>) >> bf:identifiedBy (z.B. <https://w3id.org/zpid/resources/instancebundles/0390655#journalrel_article_number> > rdf:value "99"` Anmerkung: am InstanceBundle, nicht der einzelnen Formatinstanz zugeordnet

## Links und Identifier der Instanzen selbst

- [x] instance.dfk > `pxp:hasInstanceBundle.bf:identifiedBy.rdf:value` bei identifier type `pxc:DFK` , zB "0379753"; Schema Identifier-Knoten: `<https://w3id.org/zpid/resources/instancebundles/0388777#dfk>`
- [x] instance.formatInstance.isbn > `pxp:hasInstanceBundle.bf:identifiedBy.rdf:value` bei identifier type `bf:Isbn` zB "978-3-8474-1567-1"; (Schema: hash-uri endet bei isbns für Print-Formatinstanzen in `#isbn_print` und bei Online-Formatinstanzen in `#isbn_ebook` ; zB `<https://w3id.org/zpid/resources/instancebundles/0389999#isbn_ebook`)
- [x] instance.formatInstance.publicationUrls > `pxp:hasInstanceBundle.bf:hasPart.bf:electronicLocator` zB `<https://dspace.uevora.pt/rdpc/bitstream/10174/24817/1/E-book.Inter.Seminar.29th.Sept.pdf>` (bei uns leider oft an der Print-Formatinstanz, bzw. es gibt nur ein MT Print, aber es ist ein Ebook oder sogar PDF verlinkt. Da kann ich leider nicht viel machen, außer mit viel Gehirnschmalz und Raterei, und dafür ist erstmal keine Zeit)
- [x] instance.formatInstance.publicationUrns `pxp:hasInstanceBundle.bf:hasPart.bf:identifiedBy.rdf:value` bei identifier type `bf:Urn` zB "urn:nbn:at:at-ubg:1-120765"; Schema Identifier-Knoten: `<urn:nbn:at:at-ubg:1-120765>`
- [x] instance.formatInstance.doi > `pxp:hasInstanceBundle.bf:hasPart.bf:identifiedBy.rdf:value` bei identifier type `bf:Doi`, zB "10.1002/bsl.2547"; Schema Identifier-Knoten: die DOI als URI, also zB `<https://doi.org/10.1002/bsl.2547>`

## Status
- [x] publishingStatus (aus den Feldern STAF und STAI zusammengesetzt): `bf:Work, pxc:MainWork >> bf:adminMetadata > bf:AdminMetadata >> bf:status > pxc:PublishingStatus >> rdfs:label "created"` (oder "bib_indexed", "request_for_approval", "published")
- [x] psyFoMoStatus (aus Feldern MK, falls diese den Wert "PsyFomo" oder "PsyPlus" haben): `bf:Work, pxc:MainWork >> bf:adminMetadata > bf:AdminMetadata >> bf:status > pxc:PsyFoMoStatus >> rdfs:label "PsyFoMo"` (oder "PsyPlus") 

## ? (Personen/Körperschaften als Thema?)
- concernedPersonIds - nicht in den Bestandsdaten
- concernedCorporateBodyIds - nicht in den Bestandsdaten

## Verwandte Werke (Werk)
- [x] relatedWorks RelatedWork > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>)`
- [x] relatedWork.relationType > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>) >> bflc:relation relations:xxx` (alles aus dem Vokabular https://w3id.org/zpid/vocabs/relations/, zB `relations:translationOf`
- [x] relatedWork.objectWork > `bf:Work, pxc:MainWork > bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>) bf:relatedTo > bf:Work >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bf:identifiedBy > pxc:DFK >> rdf:value "0379753"` (als DFK des Instanzbündels/der Instanz, muss später damit in Psyndexer konsolidiert/rekonziliert werden)
- [x] relatedWork.doi > `bf:Work, pxc:MainWork > bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:identifiedBy > bf:Doi (z.B. <https://doi.org/10.17605/OSF.IO/45CRZ>) >> rdf:value "10.17605/OSF.IO/45CRZ"`
- [x] relatedWork.citation > `bf:Work, pxc:MainWork > bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:preferredCitation "Citation for the related pub"`
- [x] relatedWork.url > `bf:Work, pxc:MainWork > bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#workrel1>) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:electronicLocator <https://dspace.uevora.pt/rdpc/bitstream/10174/24817/1/E-book.Inter.Seminar.29th.Sept.pdf>`

- [x] relatedTestOrMeasures RelatedTestOrMeasure > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> bf:relatedTo > pxc:Test` (wenn Test _nicht_ in unserer Datenbank: zusätzlich neben type `pxc:Test` auch `bflc:Uncontrolled`)
- [x] relatedTestOrMeasure.relationType > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) > bflc:relation https://w3id.org/zpid/vocabs/relations/usesTest` (oder: https://w3id.org/zpid/vocabs/relations/analyzesTest)
- [x] relatedTestOrMeasure.shortName > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> bf:relatedTo > pxc:Test >> bf:title > bf:AbbreviatedTitle > bf:mainTitle "FEMOLA"`
- [x] relatedTestOrMeasure.longName > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> bf:relatedTo > pxc:Test >> bf:title > bf:Title > bf:mainTitle "Fragebogen zur Erfassung der Motivation für die Wahl des Lehramtsstudiums"`
- [x] relatedTestOrMeasure.test > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> bf:relatedTo > pxc:Test >> bf:identifiedBy > pxc:PsytkomTestId >> rdf:value "6300"` (wenn Test selbst nicht nur pxc:Test, sondern auch bflc:Uncontrolled ist, fehlt diese ID immer, denn dann ist es ein Test, der nicht in der Datenbank steht)``
- [x] relatedTestOrMeasure.itemsComplete > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> pxp:allItemsInWork true/false` Vorsicht: _nicht_ am Knoten des Tests, sondern der Relationship, da es sich um eine Angabe zum eigentlichen Werk handelt und nicht direkt zum Test selbst.
- [x] relatedTestOrMeasure.remark > `bf:Work, pxc:MainWork >> bflc:relationship > bflc:Relationship (z.B. <https://w3id.org/zpid/resources/works/0390002_work#testrel1>) >> bf:note > bf:Note >> rdfs:label "Watt, H. M. G., Richardson, P. W., Klusmann, U., Kunter, M., Beyer, B., Trautwein, U. & Baumert, J. (2012). Motivations for choosing teaching as a career: An international comparison using the FIT-Choice scale. Teaching and Teacher Education, 28(6), 791 - 805. https://doi.org/10.1016/j.tate.2012.03.003"` Vorsicht: _nicht_ am Knoten des Tests, sondern der Relationship, da es sich um eine Anmerkung zum Test im Kontext des eigentlichen Werk handeln kann.

## Plain Language Summaries (Werk)
- englishShortPls - nicht in den Bestandsdaten
- englishShortPlsOrigin - nicht in den Bestandsdaten
- longPlsDoi - nicht in den Bestandsdaten
- longPlsUrl - nicht in den Bestandsdaten
- longPlsStatus - nicht in den Bestandsdaten

## Verschlagwortung (Werk)
- [x] controlledKeywords > `bf:subject.owl:sameAs` bei subject type `bf:Topic` und zusätzlich `pxc:WeightedTopic` wenn gewichtet. (Wert ist eine Uri aus dem "terms"-Vokabular wie zB https://w3id.org/zpid/vocabs/terms/02370)
- [x] subjectClassifications > `bf:Work, pxc:MainWork >> bf:classification > pxc:SubjectHeading (wenn gewichtet: zusätzlich pxc:SubjectHeadingWeighted) (z.B. <https://w3id.org/zpid/resources/works/0388777_work#subjectheading1>) >> owl:sameAs <https://w3id.org/zpid/vocabs/class/3370>`
- [x] methodClassifications > `bf:Work, pxc:MainWork >> bf:classification > pxc:ControlledMethod (wenn gewichtet zusätzlich noch pxc:ControlledMethodWeighted) (z.B. <https://w3id.org/zpid/resources/works/0388777_work#controlledmethod1>) >> owl:sameAs <https://w3id.org/zpid/vocabs/methods/20000>`
- [x] ageGroups > `bf:Work, pxc:MainWork >> bflc:demographicGroup > pxc:AgeGroup >> owl:sameAs <https://w3id.org/zpid/vocabs/age/adulthood>` oder anderes Concept aus https://w3id.org/zpid/vocabs/age/AgeGroups
- [x] simplePopulationLocations > `bf:Work, pxc:MainWork >> bf:geographicCoverage > pxc:PopulationLocation >> rdfs:label "Germany"`
- [x] populationLocation Place > `bf:Work, pxc:MainWork >> bf:geographicCoverage > pxc:PopulationLocation >> owl:sameAs <https://www.geonames.org/2921044>` (oder: `bf:identifiedBy > locid:geonamesid >> rdf:value "2921044")` (geonames-ID mit sameas + uri oder identifiedBy... - was ist leichter zu parsen, mb?)
- [x] sampleCharacteristics > `bf:Work, pxc:MainWork >> pxp:sampleCharacteristic sam:Human` (die möglichen Werte aus
https://w3id.org/zpid/vocabs/sam/SampleCharacteristics sind: "Human" "Inanimate" oder "Animal")
- [x] authorKeywords > `bf:Work, pxc:MainWork >> bf:subject > pxc:AuthorKeywords >> rdfs:label "Legasthenie, Rechtschreibschwäche, Evaluation, Wirksamkeitsprüfung, Sindelar-Methode, Vorläuferfunktionen, Teilleistungsschwäche, dyslexia, spelling disability, writing disability, efficacy, evaluation, Sindelar-Method, partial developmental deficits, information processing"`
- [x] uncontrolledKeywords > `bf:Work, pxc:MainWork >> bf:subject > pxc:UncontrolledTopic >> rdfs:label "group psychotherapy"`

## Dissertationsangaben (Werk)
- [x] degreeGranted > `bf:Work, pxc:MainWork >> bf:disseration > bf:Disseration >> bf:degree "Dr. rer. nat."`
- [x] dateDegreeGranted > `bf:Work, pxc:MainWork >> bf:disseration > bf:Disseration >> bf:date "2017"`
- [x] thesisAdvisor Person > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_advisor>) > bf:role <https://id.loc.gov/vocabulary/relators/dgs>` (an der Rolle **dgs** erkennbar, außerdem an ...#thesis_advisor). Wichtig: _nicht_ im "Dissertation"-Knoten, sondern eine Contribution mit ganz bestimmter Rolle!
- [x] thesisAdvisorGivenName > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_advisor>) > bf:agent > bf:Person >> schema:givenName "K. W."`
- [x] thesisAdvisorFamilyName > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_advisor>) > bf:agent > bf:Person >> schema:familyName "Kallus"`
- [x] thesisReviewer Person > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_reviewer1>) > bf:role <https://id.loc.gov/vocabulary/relators/dgc>` - an der Rolle **dgc** (degree committee member) erkennbar, außerdem an ...#thesis_reviewer1. Wichtig: _nicht_ im "Dissertation"-Knoten, sondern eine Contribution mit ganz bestimmter Rolle! Wichtig: hier können mehrere Reviewer vorkommen, aber bitte nur den ersten (`_reviewer1`) importieren, da wir damals festgelegt haben, dass das Feld nicht wiederholbar sein soll. Wir wollen aber für später die weiteren Reviewer aufbewahren, daher werden sie vorerst mit exportiert.
- [x] thesisReviewerGivenName > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_reviewer1>) > bf:agent > bf:Person >> schema:givenName "P."`
- [x] thesisReviewerFamilyName > `bf:Work, pxc:MainWork >> bf:contribution > bf:Contribution (z.B. <https://w3id.org/zpid/resources/works/0390297_work#thesis_reviewer1>) > bf:agent > bf:Person >> schema:givenName "Jiménez"`

## referencedWorks (Werk) - gestrichen!
- referencedWorks ReferencedWork
- referencedWork.authors string 0..n -
- referencedWork.title string 1..1 -
- referencedWork.publicationYear integer 0..1 -
- referencedWork.doi string {Doi} 0..1 -
- referencedWork.journalName string 0..1 -
- referencedWork.journalVolume string {*Regex*:/^[0-9]+$/} 0..1 -
- referencedWork.journalIssue string {*Regex*:/^(?:\d+(?:-\d+)?|Supp|S\d+)$/} 0..1 -
- referencedWork.journalSites string 0..1 -

## Typen von Werk und Instanz
- [x] contentType > `bf:Work, pxc:MainWork >> bf:content <https://w3id.org/zpid/vocabs/contenttypes/text>` (Wert ist Uri aus content-Vokabular, fast immer https://w3id.org/zpid/vocabs/contenttypes/text)
- [x] genre > `bf:Work, pxc:MainWork >> bf:genreForm genres:ResearchPaper` (Wert ist Uri aus genres-Vokabular, zB https://w3id.org/zpid/vocabs/genres/ResearchPaper)
- [x] instance.publicationType > `pxp:hasInstanceBundle.pxp:issuanceType` (Wert ist Uri aus issuances-Vokabular, zB https://w3id.org/zpid/vocabs/issuances/JournalArticle) ; immer am pxc:InstanceBundle
- [x] instance.formatInstance.carrierType `pxp:hasInstanceBundle.bf:hasPart.pxp:mediaCarrier` (Wert ist Uri aus mediacarriers-Vokabular, zB https://w3id.org/zpid/vocabs/mediacarriers/Online) - immer an der Formatinstanz (bf:Instance)

## Links zu Forschungsdaten
- [x] researchData ResearchData > `bflc:relationship` type der relationship ist immer: `pxc:ResearchDataRelationship` Schema: `<https://w3id.org/zpid/resources/works/0387049_work#ResearchDataRelationship1>`
- [x] researchData.relation > `bflc:relationship.bflc:relation` (Werte: später entweder "relations:hasResearchData" oder "relations:hasAnalyticCode", bisher gibt es im Bestand aber nur welche mit "relations:hasResearchData")
- [x] researchData.doi `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.rdf:value` (bei identifier type `bf:Doi`) zB "10.17605/OSF.IO/45CRZ" (Node ist DOI als volle URL, zB <https://doi.org/10.17605/OSF.IO/45CRZ>`)
- [x] researchData.url `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:electronicLocator` zB `<https://osf.io/3yna4/?view_only=c6ebabdbbdca42d4a25367ea655b74f7>`
- [x] researchData.access `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:usageAndAccessPolicy` (Wert ist Uri aus access-Vokabular, bisher immer bei allen im Bestand verlinkten Forschungsdaten: https://w3id.org/zpid/vocabs/access/open)

## Links zu Präregistrierungen
- [x] preregisteredStudies PreregisteredStudy > `bflc:relationship` type der relationship ist immer: `pxc:PreregistrationRelationship` Schema: `<https://w3id.org/zpid/resources/works/0387046_work#PreregistrationRelationship1>`
- [x] preregisteredStudy.doi > `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.rdf:value` (bei identifier type `bf:Doi`) - Node ist vollständige DOI-URL wie bei researchdata
- [x] preregisteredStudy.url > `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:electronicLocator` zB `<https://clinicaltrials.gov/ct2/show/NCT03418142>`
- [x] preregisteredStudy.trialNumber > `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.rdf:value` (bei identifier type `pxc:TrialNumber`) zB "NCT03418142" - kompliziert aus Infofeld PRREG |i geparst und nur angehängt, wenn nicht schon Teil der URL einer schon existierenden pxc:PreregistrationRelationship.
- [x] preregisteredStudy.trialRegistry > an der TrialNumber als "assigner": `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:identifiedBy.bf:assigner` (Wert ist Uri aus assigner-Vokabular, https://w3id.org/zpid/vocabs/trialregs, zB https://w3id.org/zpid/vocabs/trialregs/prospero; hat auch type `pxc:TrialRegistry`)
- dachte irgendwie, wir hätten das geplant, aber nicht gefunden:
- neu, mvp-2.0: **preregisteredStudy.note** `bflc:relationship.bf:supplement.bf:Work.bf:hasInstance.bf:note.rdfs:label` (Wert ist String, zB "Study 2", ""first preregistration", "amended preregistration")

## Links zu replizierten Studien #
- [x] replicatedStudies ReplicatedStudy 0..n > `bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1)`
- [x] replicatedStudy.relationType string {ControlledTerm[group=relations, collection=PSYNDEXoriginalDataRelations]->id} 1..1 > `bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1) >> bflc:relation relations:isReplicationOf` (oder: `relations:isReanalysisOf`)
- [x] replicatedStudy.doi string {Doi} 0..1 > `bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:identifiedBy > bf:Doi (z.B. <https://doi.org/10.17605/OSF.IO/5R3YP>) >> rdf:value "10.17605/OSF.IO/5R3YP"`  Anmerkung: DOI hängt an der bf:Instance der replizierten Studie, nicht am bf:Work.
- [x] replicatedStudy.url string {Url} 0..1 >`bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:electronicLocator (z.B. <https://osf.io/3yna4/?view_only=c6ebabdbbdca42d4a25367ea655b74f7>)`  Anmerkung: Url hängt an der bf:Instance der replizierten Studie, nicht am bf:Work
- [x] replicatedStudy.studyId string {Work->id} 0..1 > erstmal als DFK: `bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1) >> bf:relatedTo > bf:Work >> pxp:hasInstanceBundle > pxc:InstanceBundle >> bf:identifiedBy > pxc:DFK >> rdf:value "0379753"`  Anmerkung: vom Werk direkt zum Werk der replizierten Studie in der Psyndex-Datenbank via DFK, falls vorhanden; muss in Psyndexer rekonziliert werden
- [x] replicatedStudy.citation > `bf:Work, pxc:MainWork >> bflc:relationship > pxc:ReplicationRelationship (z.B. <https://w3id.org/zpid/resources/works/0387049_work#ReplicationRelationship1) >> bf:relatedTo > bf:Work >> bf:hasInstance > bf:Instance >> bf:preferredCitation "Citation for article"` Anmerkung: Citation hängt an der bf:Instance der replizierten Studie, da immer eine konkrete Instanz in einem Journal zitiert wird.