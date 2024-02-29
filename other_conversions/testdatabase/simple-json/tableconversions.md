Tabelle 1
Längerfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39)
---------------------------------------- 

                        M        SD 

---------------------------------------- 

A6 postinterferent     29.46     2.48 

A7 mittelfristig       29.44     2.53 

A8 laengerfristig      28.86     3.33 

---------------------------------------- 


as a markdown table:

| Tabelle 1 |
| Längerfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39) |
| --- |
| M | SD |
| --- | --- |
| A6 postinterferent | 29.46 | 2.48 |
| A7 mittelfristig | 29.44 | 2.53 |
| A8 laengerfristig | 28.86 | 3.33 |


as a csv table:

```csv
Tabelle 1
Längerfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39)
M,SD
A6 postinterferent,29.46,2.48
A7 mittelfristig,29.44,2.53
A8 laengerfristig,28.86,3.33
```

in html:

```html
<table class="w-1/2">
<caption>Tabelle 1: Längerfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39)</caption>
  <thead>
    <tr>
      <th></th>
      <th>M</th>
      <th>SD</th>
    </tr>
  </thead>
<tr>
	<th>A6 postinterferent</th>
	<td>29.46</td>
	<td>2.48</td></tr>
<tr>
	<th>A7 mittelfristig</th>
	<td>29.44</td>
	<td>2.53</td></tr>
<tr>
	<th>A8 laengerfristig</th>
	<td>28.86</td>
	<td>3.33</td>
</tr>
</table>
```

# another example

This table:

```
Tabelle 3
Kurzfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39)
---------------------------------------- 

                        M        SD 

---------------------------------------- 

A6 postinterferent     29.46     2.48 

A7 mittelfristig       29.44     2.53 

A8 laengerfristig      28.86     3.33 

---------------------------------------- 
```

would look like that in html as described with the pattern above:

```html
<table class="w-1/2">
<caption>Tabelle 3: Kurzfristiges Behalten; Mittelwerte und Standardabweichungen der Testleistung (Schellig, Günther, Schächtele & Schuri, 2014, S. 39)</caption>
  <thead>
    <tr>
      <th></th>
      <th>M</th>
      <th>SD</th>
    </tr>
  </thead>
<tr>
    <th>A6 postinterferent</th>
    <td>29.46</td>
    <td>2.48</td></tr>
<tr>
    <th>A7 mittelfristig</th>
    <td>29.44</td>
    <td>2.53</td></tr>
<tr>
    <th>A8 laengerfristig</th>
    <td>28.86</td>
    <td>3.33</td>
</tr>
</table>
```

# yet another example

ascii table:

```
pre&gt;------------------------------------------------------------- &lt;br/&gt; Reliabilitaets-     Stichprobe                   Koeffizient &lt;br/&gt; schätzung &lt;br/&gt; ------------------------------------------------------------- &lt;br/&gt; Halbierungs-        152 Grundschueler (4. Klasse)     .95 &lt;br/&gt; Reliabilitaet        90 HS            (5. Klasse)     .88 &lt;br/&gt;                      90 RS            (5. Klasse)     .88 &lt;br/&gt;                     103 GY            (5. Klasse)     .92 &lt;br/&gt; Wiederholungs- &lt;br/&gt; Reliabilitaet &lt;br/&gt; nach 4 Wochen       344 Grundschueler (4. Klasse)     .90 &lt;br/&gt; ------------------------------------------------------------- &lt;br/&gt;       &lt;/pre&gt;
```

html table:

```html
<table class="table-auto w-1/2 text-left">
  <thead>
    <tr class="text-left border-b-2 mt-2">
      <th>Reliabilitätsschätzung</th>
      <th class="">Stichprobe</th>
      <th>Koeffizient</th>
    </tr>
  </thead>
  <tbody>
    <tr class="align-top">
      <th class="align-top" rowspan="3">Halbierungsreliabilität</th>
      <td>90 HS (5. Klasse)</td>
      <td class="">.88</td>
    </tr>
      <tr  class="align-top">
      <td>90 RS (5. Klasse)</td>
      <td>.88</td>
    </tr>
    <tr>
      <td>103 GY (5. Klasse)</td>
      <td>.92</td>
    </tr>
    <tr  class="align-top">
      <th rowspan="1" class="pr-2">Wiederholungsreliabilität nach 4 Wochen</th>
      <td>344 Grundschüler (4. Klasse)</td>
      <td>.90</td>
    </tr>
  </tbody>
</table>
```
