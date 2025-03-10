# Reduierte Personendaten

Haben nur die wichtigsten Informationen über Personen, die in den Daten vorkommen:
- preferred name
- alternative Namen
- Identifikatoren
- ob die Person Psychologe ist

## Personen-Knoten

Jede Person hat einen eigenen Knoten, der über die URL `https://w3id.org/zpid/authorities/agents/persons/p_` und einer eindeutigen ID verknüpft ist - die base58-kodierte Version einer UID. die man bei Bedarf auch wieder daraus herstellen kann. Beispiel: `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z>`

Jeder Personen-Knoten hat die Klassen `schema:Person` und `bf:Person` und hat die unten unter Namen und Identifikatoren beschriebenen Eigenschaften und Verknüpfungen.

Beispiel für eine Person mit 2 verschiedenen Identifikatoren, 1 preferred Name und 2 alternativen Namen, außerdem ist bekannt, dass die Person Psychologe ist: 

```rdf
persons:p_48HNJzvbj7MDYwki2ZHv6j a bf:Person,
        schema:Person ;
    bf:identifiedBy <https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#gndid>,
        <https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#orcid> ;
    gndo:preferredNameEntityForThePerson <https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#prefname> ;
    gndo:variantNameEntityForThePerson <https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#varname_1>,
        <https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#varname_2> ;
    pxp:isPsychologist true .
```

## isPsychologist

Einige Personen haben das Property `pxp:isPsychologist` mit dem Wert `true` oder `false`. Diese Personen sind Psychologen. Wenn sie das Property nicht haben, ist unbekannt, ob sie Psychologen sind. Praktisch kann aber false dafür gesetzt werden.

## Namen:

Jede Person hat 
- genau einen preferred name, der über das Property `gndo:preferredNameEntityForThePerson` mit der Person verknüpft ist. Der Knote hat die Endung #prefname, z.B. `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z#prefname>`.
- 0 bis mehere alternative Namen, die über das Property `gndo:variantNameEntityForThePerson` mit der Person verknüpft sind. Der Knoten hat die Endung #varname_1 (bis n), zB `<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#varname_2>` (Wenn es keine alternativen Namen gibt, gibt es auch keinen Knoten für das Property.)

Alle Namen haben 
- die Klasse `gndo:NameOfThePerson` 
- haben immer einen `schema:familyName` und `schema:givenName`


Folglich: 
- `personName.givenNames`: `schema:givenName` (es sind alle Vornamen zusammen in einem String)
- `personName.familyName`: `schema:familyName` (der Nachname)
- `personName.isPreferredName`: erkennbar an der Endung des Knotens, z.B. `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z#prefname>`bzw am Property `gndo:preferredNameEntityForThePerson`. Die Nicht-Preferred-Namen haben wie oben beschrieben die Endung #varname_1 (bis n) und die Verknüpfung über `gndo:variantNameEntityForThePerson`.


Beispiel für die Namensknoten der obigen Person:

```rdf
<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#prefname> a gndo:NameOfThePerson ;
    schema:familyName "Michael Dominik" ;
    schema:givenName "Krämer" .

<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#varname_1> a gndo:NameOfThePerson ;
    schema:familyName "Krämer" ;
    schema:givenName "Michael D." .

<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#varname_2> a gndo:NameOfThePerson ;
    schema:familyName "Kraemer" ;
    schema:givenName "Michael D. D." .

```


## Identifikatoren:

Es gibt potenziell drei Typen von Identifikatoren in den Daten:
- gndid (erkennbar an einem Knoten mit Hash-URL, die in #gndid endet, z.B. `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z#gndid>`) 
- orcid (endet in #orcid, z.B. `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z#orcid>`)
- psychauthorsid (endet in #psychauthorsid, z.B. `<https://w3id.org/zpid/authorities/agents/persons/p_12Av2Kr68epMxKMtWKGp6Z#psychauthorsid>`)

Wenige Personen haben alle drei Typen, die meisten haben nur einen oder zwei Typen. Die fehlenden Typen haben dann auch keine Knoten.

Jeder Identifikator ist ein eigener Knoten, der mit der Person verknüpft ist, und zwar über bf:identifiedBy. Der Identifikator-Knoten hat eine rdf:value, die die eigentliche Id enthält. Der Typ des Identifikators ist erkennbar an der Klasse des Knotens.

- `personId.personId`: immer `rdf:value` eines Identfikator-Knotens, zB `<https://w3id.org/zpid/authorities/agents/persons/p_12GRDvq5aVf4SNR9dbv9Fn#gndid> rdf:value "118540278"`
- personId.idTyp: erkennbar an der Klasse des Knotens, 
    - gnd-Ids: `<https://w3id.org/zpid/authorities/agents/persons/p_12GRDvq5aVf4SNR9dbv9Fn#gndid> a locid:gnd`, 
    - orcid-Ids: `<https://w3id.org/zpid/authorities/agents/persons/p_12GRDvq5aVf4SNR9dbv9Fn#orcid> a locid:orcid`,
    - psychauthors-Ids: `<https://w3id.org/zpid/authorities/agents/persons/p_12GRDvq5aVf4SNR9dbv9Fn#psychauthorsid> a pxc:PsychAuthorsId`


Beispiel für die Identifikatoren der obigen Person:

```rdf
<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#gndid> a locid:gnd ;
    rdf:value "1260424693" .

<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#orcid> a locid:orcid ;
    rdf:value "0000-0002-9883-5676" .

# eine PsychAuthorsId ist nicht vorhanden, aber wenn es eine gäbe, würde sie so aussehen:
<https://w3id.org/zpid/authorities/agents/persons/p_48HNJzvbj7MDYwki2ZHv6j#psychauthorsid> a pxc:PsychAuthorsId ; 
    rdf:value "p00091MK" .

```
