def replace_encodings(text):
    """Replaces Star's proprietary ^DD codes with their unicode equivalents."""
    # text = html.escape(text)
    for case in dd_codes:
        text = text.replace(case[0], case[1])
    return text


# use this on affiliation strings, person names (both in AUP, AUK)
# and on Abstract and title, other text fields, like SH and UTG/UTE, KP...
dd_codes = (
    ("", "š"),
    # ('^D&lt;"', '"'),
    # ("^D&lt;,", '"'),
    # ("^D&lt;'", "'"),
    # ("^D&lt;; ", '"'),
    # ("^D&gt;", ""),
    # ('^D&gt;"', '"'),
    ('^D<"', '"'),
    ("^D<,", '"'),
    ("^D<'", "'"),
    ("^D<; ", '"'),
    ('^D>"', '"'),
    ("^D>'", "'"),
    ("^Dff", "ff"),
    # ("^D&amp;a", "ă"),
    ("^D&a", "ă"),
    # ("^D&amp;i", "ĭ"),
    ("^D&i", "ĭ"),
    # ('a^D"&amp;', "ä"),
    ('a^D"&', "ä"),
    # ('A^D"&amp;', "Ä"),
    ('A^D"&', "Ä"),
    # ('u^D"&amp;', "ü"),
    ('u^D"&', "ü"),
    # ('U^D"&amp;', "Ü"),
    ('U^D"&', "Ü"),
    # ('o^D"&amp;', "ö"),
    ('o^D"&', "ö"),
    ("^D*a", "α"),  # kleines alpha
    ("^D*A", "Α"),  # großes Alpha
    ("^D*c", "θ"),  # kleines theta
    ("^D*C", "Θ"),  # großes Theta
    ("^D*b", "β"),  # kleines beta
    ("^D*B", "Β"),  # großes Beta
    ("^D*g", "γ"),  # kleines gamma
    ("^D*G", "Γ"),  # großes Gamma
    ("^D*d", "δ"),  # kleines delta
    ("^D*D", "Δ"),  # großes Delta
    ("^D*e", "ε"),  # kleines epsilon
    ("^D*E", "Ε"),  # großes Epsilon
    ("^D*h", "η"),  # kleines eta
    ("^D*H", "Η"),  # großes Eta
    ("^D*i", "ι"),  # kleines iota
    ("^D*I", "Ι"),  # großes Iota
    ("^D*k", "κ"),  # kleines kappa
    ("^D*K", "Κ"),  # großes Kappa
    ("^D*l", "λ"),  # kleines lambda
    ("^D*L", "Λ"),  # großes Lambda
    ("^D*m", "μ"),  # kleines mu
    ("^D*M", "Μ"),  # großes Mu
    ("^D*n", "ν"),  # kleines nu
    ("^D*N", "Ν"),  # großes Nu
    # kommen nicht vor:
    # ("^D*x", "ξ"),  # kleines xi
    # ("^D*X", "Ξ"),  # großes Xi
    # ("^D*o", "ο"),  # kleines omikron
    # ("^D*O", "Ο"),  # großes Omikron
    # ("^D*u", "υ"),  # kleines ypsilon
    # ("^D*U", "Υ"),  # großes Ypsilon
    ("^D*p", "π"),  # kleines pi
    ("^D*P", "Π"),  # großes Pi
    ("^D*r", "ρ"),  # kleines rho
    ("^D*R", "Ρ"),  # großes Rho
    ("^D*s", "σ"),  # kleines sigma
    ("^D*S", "Σ"),  # großes Sigma
    ("^D*t", "τ"),  # kleines tau
    ("^D*y", "χ"),  # kleines chi
    ("^D*Y", "Χ"),  # großes Chi
    ("^D*T", "Τ"),  # großes Tau
    ("^D*v", "ψ"),  # kleines psi
    ("^D*V", "Ψ"),  # großes Psi
    ("^D*q", "φ"),  # kleines phi
    ("^D*Q", "Φ"),  # großes Phi
    ("^D*w", "ω"),  # kleines omega
    ("^D*W", "Ω"),  # großes Omega
    ("^D:I", "İ"),
    ("^D:e", "ė"),
    ("^D%S", "Š"),
    ("^D%s", "š"),
    ("^D%Z", "Ž"),
    ("^D%z", "ž"),
    ("^D%c", "č"),
    ("^D%C", "Č"),
    ("^D:c", "ć"),
    ("^D:z", "ż"),
    ("^D:Z", "Ż"),
    ("^D/l", "ł"),
    ("^D/L", "Ł"),
    ("^D/d", "đ"),
    ("^D/D", "Đ"),
    ("^D,s", "ş"),
    ("^D's", "ş"),
    ("^D,S", "Ş"),
    ("^D'S", "Ś"),
    ("^D'n", "ń"),
    ("^D'c", "ć"),
    ("^D'C", "Ć"),
    ("^D'z", "ź"),
    # ("e^D'&amp;", "é"),
    # ("E^D'&amp;", "É"),
    ("e^D'&", "é"),
    ("E^D'&", "É"),
    ("^Dre", "ę"),
    # ("^D&amp;g", "ğ"),
    ("^D&g", "ğ"),
    # n^D'&amp;
    # K^Dr&amp;
    ("^D[+", "₊"),
    # ("^D[0", "₀")
    ("^D[1", "₁"),
    ("^D[2", "₂"),
    ("^D[3", "₃"),
    ("^D[4", "₄"),
    ("^D[5", "₅"),
    ("^D[6", "₆"),
    ("^D[7", "₇"),
    ("^D[8", "₈"),
    ("^D[9", "₉"),
    # gibt es nicht, obwohl im Testdatensatz erwähnt:
    # ("^D]1", "₁"),
    # ("^D]2", "₂"),
    # ("^D]3", "₃"),
    # ("^D]4", "₄"),
    # ("^D]5", "₅"),
    # ("^D]6", "₆"),
    # ("^D]7", "₇"),
    # ("^D]8", "₈"),
    # ("^D]9", "₉"),
    # ("^D]0", "₀"),
    # ^D[ (^D[3 ^D[)
    ("^DRT", "→"),  # right arrow
    ("^D#=", "≠"),  # not equal to
    ("^DTM", "™"),
    ("^D$e", "€"),  # Euro
    # ("^D#&gt;", "≥"),  # greater than or equal to
    ("^D#>", "≥"),  # greater than or equal to
    # ("^D#&lt;", "≤"),  # less than or equal to
    ("^D#<", "≤"),  # less than or equal to
    ("^DEL", "…"),  # ellipsis/Auslassungspunkte
    ("^DIF", "∞"),  # infinity
    ("^DDS", "–"),  # n-dash/Halbgeviertstrich;
    ("^DDL", "—"),  # em-dash
    # remove html tags:
    # ("&lt;b&gt;", ""),  # bold start
    # ("&lt;/b&gt;", ""),  # bold end
    # ("&lt;i&gt;", ""),  # italic start
    # ("&lt;/i&gt;", ""),  # italic end
    # paragraph start:
    # ("&lt;p&gt;", ""),
    # # paragraph end:
    # ("&lt;/p&gt;", ""),
    # (" &amp; ", " & "),
    # (" &lt;", " < "),
    # (" &gt; ", " > "),
)


# A list of names/strings that should be replaced
# with the string "Original" in any fields
# that describe the origin of the abstract (ASH1, ASN1)
abstract_origin_original = (
    "Original",
    "Journal",
    "Buch",
    "Autor",
    "Author",
    "Abstract",
    "Author abstract",
    "Author's abstract",
    "Authors abstract",
    "Journal abstract",
    "Jounrla abstract",
    "Journal Abstract",
    "Journal Abstrat",
    "Journal abstarct",
    "Journal abstrac",
    "Journal abstract",
    "Journal abstracts",
    "Journal abstradt",
    "Journal anstract",
    "Jurnal abstract",
    "Journal",
    "Report)",
    "Zeitschrift",
    "Zeitschrift)",
    "Verlag",
    "Herausgeber",
    "Audiotorium",  # ein Verlag
    "VCR",  # Verlag
    "ZFE",  # Uni als Verlag (Zentrum für Fernstudienentwicklung an der FU Hagen)
    "FIM-Psychologie",  # Uniinstitut als Verlag
    "PGFA",  # Lieferten Nachlässe, FU Hagen
    "IWF",  # Institut für Wissenschaftlichen Film, heute TIB, von der kommen die auch alle
    "IWf",
    "iwf",
    "Bundesinstitut für Bevölkerungsforschung beim Statistischen Bundesamt, Wiesbaden",
    "Fachinformationsstelle Publizistik",  # alle von GESIS
    "Freie Universität Berlin, Fachinformationsstelle Publizistik",
    "FHKT Nürtingen",  # kommen alle von Gesis
    "Institut für Arbeitsmarkt- und Berufsforschung der Bundesagentur für Arbeit, Nürnberg",
    "Institut für Arbeitsmarkt- und Berufsforschung der Bundesanstalt für Arbeit, Nürnberg",
    "PROGRIS Rachel Gutmacher-Neveling, Berlin",
)

# replace these with "ZPID" if found in ASH1, ASN1, ASH2, ASN2:
abstract_origin_zpid = (
    "ZPID",
    "ZIPD",
    "zpid",
    "A.Bi.",
    "A.C.",
    "A.G.",
    "A.R.",
    "C.Si",
    "G.B.",
    "I.D.",
    "K.Si",
    "K.Si.",
    "L.F.T.",
    "M.G.",
    "M.K.",
    "pe.k",
    "R.N.",
    "R.N",
    "r",
    "Ve.K.",
    "U.R.W.",
    "u.r.w.",
    "U",
    "Deepl/ZPID",
    "DeepL/U.R.W.",
    "Andreas Kindler",
    "Angelika Zimmer",
    "Annelie Wiertz",
    "Beate Minsel",
    "Berndt Zuschlag",
    "Bert Allhoff-Cramer",
    "Detlef Herrig",
    "Dieter Reihl",
    "Dietlind Lindenmeyer",
    "Dietrich Neumann-Henneberg",
    "Donald Doenges",
    "Doris Lecheler",
    "Erwin Woellersdorfer",
    "Guenter Hinrichs",
    "Guenter Krampen",
    "Elke Bone",
    "Hans Arne Stiksrud",
    "Hans Sittauer",
    "Hans Zygowski",
    "Heide Albrecht",
    "Heide Kuntze",
    "Hella Lenders",
    "Herbert Frey",
    "Horst Graeser",
    "Houshang Khoshrouy-Sefat",
    "Joachim H. Becker",
    "Joachim H. Mueller",
    "Juergen Beling",
    "Juergen Hoeder",
    "Juergen Howe",
    "Juergen Wiesenhuetter",
    "Jutta Rohlmann",
    "Karl Hegner",
    "Lutz Gretenkord",
    "Manfred Fischer",
    "Manfred Opitz",
    "Marco Lalli",
    "Oskar Mittag",
    "Paul Klein",
    "Peter Brezovsky",
    "Peter Gerull",
    "Rainer Neppl",
    "Roland Wakenhut",
    "Rolf Roehrbein",
    "Sigrun-Heide Filipp",
    "Thomas W. Franke",
    "Udo Wolff",
    "Ulrike Fischer",
    "Wilfried Echterhoff",
    "Wolfgang Rechtien",
    "Yrla M. Labouvie",
)


# abstract_origin_iwf = [
#     "IWF",
#     "IWf",
#     "iwf",
# ]

abstract_origin_deepl = ("DeepL", "DeePL", "Deepl")

abstract_origin_krimz = "Kriminologische Zentralstelle"

# DIPF??
abstract_origin_fis_bildung = (
    "FIS Bildung",
    "FIS Bildung Koordinierungsstelle im DIPF, Frankfurt",
)


# replace these with "GESIS":
abstract_origin_gesis = (
    "GESIS Fachinformation für die Sozialwissenschaften, Bonn",
    "GESIS-IZ Sozialwissenschaften, Bonn",
    "IZ",
    "IZ Sozialwissenschaften",
    "Informationszentrum Sozialwissenschaften, Bonn",
)


# and what if "DeepL"???
# or "FIS Bildung", "GESIS Fachinformation für die Sozialwissenschaften, Bonn", "Kriminologische Zentralstelle",

funder_names_replacelist = (
    ("DFG", "Deutsche Forschungsgemeinschaft (DFG)"),
    ("German Research Council", "Deutsche Forschungsgemeinschaft (DFG)"),
    ("German Research Society (DFG)", "Deutsche Forschungsgemeinschaft (DFG)"),
    (
        "German Research Society (Deutsche Forschungsgemeinschaft, DFG)",
        "Deutsche Forschungsgemeinschaft (DFG)",
    ),
    (
        "German Research Society (Deutsche Forschungsgemeinschaft)",
        "Deutsche Forschungsgemeinschaft (DFG)",
    ),
    ("Priority Program Xprag.de", "Deutsche Forschungsgemeinschaft (DFG)"),
    ("Heisenberg Fellowship", "Deutsche Forschungsgemeinschaft (DFG)"),
    ("DFG Heisenberg Program", "Deutsche Forschungsgemeinschaft (DFG)"),
    (
        "DFG Research Training Group Computational Cognition",
        "Deutsche Forschungsgemeinschaft (DFG)",
    ),
    ("Villigst e.V.", "Villigst"),
    ("Bial Foundation in Porto, Portugal", "Bial Foundation"),
    ("European Union's Horizon 2020 research and innovation programme", "Horizon 2020"),
    ("European Union's Horizon 2020 research and innovation program", "Horizon 2020"),
    ("H.W. & J. Hector Stiftung", "Hector Stiftung"),
    (
        "German Federal Ministry of Education and Research (BMBF)",
        "Bundesministerium für Bildung und Forschung (BMBF)",
    ),
    (
        "German Federal Ministry of Education and Research",
        "Bundesministerium für Bildung und Forschung (BMBF)",
    ),
    (
        "Federal Ministry of Education and Research in Germany",
        "Bundesministerium für Bildung und Forschung (BMBF)",
    ),
    (
        "German Federal Ministry for Family Affairs, Senior Citizens, Women and Youth",
        "Bundesministerium für Familie, Senioren, Frauen und Jugend (BMFSFJ)",
    ),
    (
        "Experimental Psychology Society Small Grants Scheme",
        "Experimental Psychology Society",
    ),
    ("German Pension Insurance Rheinland-Pfalz", "Deutsche Rentenversicherung"),
    ("Episcopal Foundation Cusanuswerk", "Cusanuswerk"),
    ("ZHAW Seed Money", "ZHAW"),
    (
        'Doctoral College "Imaging the Mind" (FWF, Austrian Science Fund)',
        "Austrian Science Fund (FWF)",
    ),
    (
        "Christian Doppler Forschungsgesellschaft in Österreich",
        "Christian Doppler Forschungsgesellschaft",
    ),
    # actually, anytime the name contains "Emmy Noether, copy the whole name into the note, then replace with DFG"
    # also, anytime it ends in "grant", or "programme" or "program", remove that part- it may match better!
)


# list of country names, geonames ids, and 2-digit ISO-3166 alpha2 country codes
# First few countries ordered first by DACHLUX, then by amount of publications from that country in openalex
# based on openalex data (filter by institution)
# for faster search
geonames_countries = (
    ("Germany", "2921044", "DE"),
    ("Austria", "2782113", "AT"),
    ("Switzerland", "2658434", "CH"),
    ("Luxembourg", "2960313", "LU"),
    ("United States", "6252001", "US"),
    ("United Kingdom", "2635167", "GB"),
    ("Peoples Republic of China", "1814991", "CN"),
    ("Japan", "1861060", "JP"),
    ("France", "3017382", "FR"),
    ("Canada", "6251999", "CA"),
    ("India", "1269750", "IN"),
    ("Italy", "3175395", "IT"),
    ("Brazil", "3469034", "BR"),
    ("Australia", "2077456", "AU"),
    ("Spain", "2510769", "ES"),
    ("Russia", "2017370", "RU"),
    ("South Korea", "1835841", "KR"),
    ("Netherlands", "2750405", "NL"),
    ("Indonesia", "1643084", "ID"),
    ("Poland", "798544", "PL"),
    ("Sweden", "2661886", "SE"),
    ("Afghanistan", "1149361", "AF"),
    ("Albania", "783754", "AL"),
    ("Algeria", "2589581", "DZ"),
    ("Argentina", "3865483", "AR"),
    ("Armenia", "174982", "AM"),
    ("Azerbaijan", "587116", "AZ"),
    ("Bahrain", "290291", "BH"),
    ("Bangladesh", "1210997", "BD"),
    ("Barbados", "3374084", "BB"),
    ("Belarus", "630336", "BY"),
    ("Belorussia", "630336", "BY"),
    ("Belgium", "2802361", "BE"),
    ("Benin", "2395170", "BJ"),
    ("Bhutan", "1252634", "BT"),
    ("Bolivia", "3923057", "BO"),
    ("Bosnia", "3277605", "BA"),
    ("Bosnia and Herzegovina", "3277605", "BA"),
    ("Botswana", "933860", "BW"),
    ("Bulgaria", "732800", "BG"),
    ("Burkina Faso", "2361809", "BF"),
    ("Burkina", "2361809", "BF"),
    ("Burundi", "433561", "BI"),
    ("Bahamas", "3572887", "BS"),
    ("Cambodia", "1831722", "KH"),
    ("Cameroon", "2233387", "CM"),
    ("Kanada", "6251999", "CA"),
    ("Central African Republic", "239880", "CF"),
    ("Chile", "3895114", "CL"),
    ("China", "1814991", "CN"),
    ("Colombia", "3686110", "CO"),
    ("Congo", "2260494", "CG"),
    ("Congo Republic", "2260494", "CG"),
    ("Congo Democratic Republic", "203312", "CD"),
    ("Costa Rica", "3624060", "CR"),
    ("Croatia", "3202326", "HR"),
    ("Cuba", "3562981", "CU"),
    ("Cyprus", "146669", "CY"),
    ("Czech Republic", "3077311", "CZ"),
    ("Denmark", "2623032", "DK"),
    ("Deutschland", "2921044", "DE"),
    ("Dominica", "3575830", "DM"),
    ("Ecuador", "3658394", "EC"),
    ("Egypt", "357994", "EG"),
    ("El Salvador", "3585968", "SV"),
    ("Estonia", "453733", "EE"),
    ("Eswatini", "934841", "SZ"),
    ("Ethiopia", "337996", "ET"),
    ("Fiji", "2205218", "FJ"),
    ("Finland", "660013", "FI"),
    ("French Polynesia", "4030656", "PF"),
    ("Gabon", "2400553", "GA"),
    ("Gambia", "2413451", "GM"),
    ("Georgia", "614540", "GE"),
    ("German Democratic Republic", "2933590", "DD"),
    ("Ghana", "2300660", "GH"),
    ("Greece", "390903", "GR"),
    ("Guatemala", "3595528", "GT"),
    ("Guinea", "2420477", "GN"),
    ("Honduras", "3608932", "HN"),
    ("Hong Kong", "1819730", "HK"),
    ("Hong Kong SAR", "1819730", "HK"),
    ("Hungary", "719819", "HU"),
    ("Iceland", "2629691", "IS"),
    ("Iran", "130758", "IR"),
    ("Iraq", "99237", "IQ"),
    ("Ireland", "2963597", "IE"),
    ("Israel", "294640", "IL"),
    ("Ivory Coast", "2287781", "CI"),
    ("Jamaica", "3489940", "JM"),
    ("Jordan", "248816", "JO"),
    ("Kazakhstan", "1522867", "KZ"),
    ("Kenya", "192950", "KE"),
    ("Korea", "1835841", "KR"),
    ("Kosovo", "831053", "XK"),
    ("Kuwait", "285570", "KW"),
    ("Kyrgyzstan", "1527747", "KG"),
    ("Lao People's Democratic Republic", "1655842", "LA"),
    ("Latvia", "458258", "LV"),
    ("Lebanon", "272103", "LB"),
    ("Liberia", "2275384", "LR"),
    ("Liechtenstein", "3042058", "LI"),
    ("Lithuania", "597427", "LT"),
    ("Macau", "1821275", "MO"),
    ("Macedonia", "718075", "MK"),
    ("Madagascar", "1062947", "MG"),
    ("Malawi", "927384", "MW"),
    ("Malaysia", "1733045", "MY"),
    ("Mali", "2453866", "ML"),
    ("Malta", "2562770", "MT"),
    ("Mauritius", "934292", "MU"),
    ("Mexico", "3996063", "MX"),
    ("Moldova", "617790", "MD"),
    ("Mongolia", "2029969", "MN"),
    ("Montenegro", "3194884", "ME"),
    ("Morocco", "2542007", "MA"),
    ("Mozambique", "1036973", "MZ"),
    ("Myanmar", "1327865", "MM"),
    ("Malawi", "927384", "MW"),
    ("Namibia", "3355338", "NA"),
    ("Nepal", "1282988", "NP"),
    ("Niederlande", "2750405", "NL"),
    ("The Netherlands", "2750405", "NL"),
    ("New Zealand", "2186224", "NZ"),
    ("Nigeria", "2328926", "NG"),
    ("North Korea", "1873107", "KP"),
    ("North Macedonia", "718075", "MK"),
    ("Northern Ireland", "2641364", "GB"),
    ("Norway", "3144096", "NO"),
    ("Oman", "286963", "OM"),
    ("Pakistan", "1168579", "PK"),
    ("Palestine", "6254930", "PS"),
    ("Panama", "3703430", "PA"),
    ("Paraguay", "3437598", "PY"),
    ("People's Republic of China", "1814991", "CN"),
    ("Peru", "3932488", "PE"),
    ("Philippines", "1694008", "PH"),
    ("Portugal", "2264397", "PT"),
    ("Puerto Rico", "4566966", "PR"),
    ("Qatar", "289688", "QA"),
    ("Republic of Korea", "1835841", "KR"),
    ("Republic of Macedonia", "718075", "MK"),
    ("Romania", "798549", "RO"),
    ("Rwanda", "49518", "RW"),
    ("Saudi Arabia", "102358", "SA"),
    ("Scotland", "2638360", "GB"),
    ("Senegal", "2245662", "SN"),
    ("Serbia", "6290252", "RS"),
    ("Serbia and Montenegro", "6290252", "RS"),
    ("Sierra Leone", "2403846", "SL"),
    ("Singapore", "1880251", "SG"),
    ("Slovakia", "3057568", "SK"),
    ("Slovenia", "3190538", "SI"),
    ("Somalia", "51537", "SO"),
    ("South Africa", "953987", "ZA"),
    ("Sri Lanka", "1227603", "LK"),
    ("Sudan", "366755", "SD"),
    ("Suriname", "3382998", "SR"),
    ("Schweiz", "2658434", "CH"),
    ("Syria", "163843", "SY"),
    ("Taiwan", "1668284", "TW"),
    ("Tajikistan", "1220409", "TJ"),
    ("Tanzania", "149590", "TZ"),
    ("Thailand", "1605651", "TH"),
    ("Togo", "2363686", "TG"),
    ("Tonga", "4032283", "TO"),
    ("Trinidad and Tobago", "3573591", "TT"),
    ("Tunisia", "2464461", "TN"),
    ("Turkey", "298795", "TR"),
    ("Turkmenistan", "1218197", "TM"),
    ("Uganda", "226074", "UG"),
    ("Ukraine", "690791", "UA"),
    ("United Arab Emirates", "290557", "AE"),
    ("UAE", "290557", "AE"),
    ("UK", "2635167", "GB"),
    ("US", "6252001", "US"),
    ("USA", "6252001", "US"),
    ("Uruguay", "3439705", "UY"),
    ("Uzbekistan", "1512440", "UZ"),
    ("Vanuatu", "2134431", "VU"),
    ("Vatican City State", "3164670", "VA"),
    ("Yugoslavia", "783754", "YU"),
    ("Venezuela", "3625428", "VE"),
    ("Vietnam", "1562822", "VN"),
    ("Zaire", "2260494", "CG"),
    ("Zambia", "895949", "ZM"),
    ("Zimbabwe", "878675", "ZW"),
    ("Österreich", "2782113", "AT"),
    ("Czech Republic", "3077311", "CZ"),
    ("Czechia", "3077311", "CZ"),
    ("Taiwan", "1668284", "TW"),
)

copr_publ = ()

copr_auth = ()

copr_pdm = ()

copr_cc0 = ()


## issuance types:
issuancetypes: (
    ("SS", "Edited Book", "Buch: Sammelwerk"),
    ("SM", "Authored Book", "Buch: Monografie"),
    ("US", "Chapter", "Kapitel"),
    ("UZ", "Journal Article", "Zeitschriftenartikel"),
    ("SH", "Gray Literature", "Graue Literatur"),
    ("SR", "Gray Literature", "Graue Literatur"),
    ("UR", "Chapter", "Kapitel"),
)

cm_mapping_lookup = [
    # things that lose their cm and only become genre ScholarlyWork:
    {
        "old_cm": "15300",
        "name": "historical source",
        "new_cm": "",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "18650",
        "name": "workshop",
        "new_cm": "",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    # things that get a "nonempirical" replacement cm and genre ScholarlyWork:
    {
        "old_cm": "12100",
        "name": "theoretical study",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "12200",
        "name": "theoretical discussion",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "12300",
        "name": "terminological/conceptual contribution",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "12400",
        "name": "professional statement",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13200",
        "name": "overview",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15100",
        "name": "historical study",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10310",
        "name": "illustrative case report",
        "new_cm": "10000",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    # things that get a custom/specific replacement cm and genre ScholarlyWork:
    {
        "old_cm": "10400",
        "name": "experience report",
        "new_cm": "10020",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11100",
        "name": "methodological study",
        "new_cm": "10010",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11300",
        "name": "intervention method description",
        "new_cm": "10030",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11200",
        "name": "assessment method description",
        "new_cm": "10040",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "",
    },
    # things that lose their cm and only become genre ResearchPaper because they were secondary cms where the primary cm given to the work should already map to something sensible:
    {
        "old_cm": "10150",
        "name": "multicenter study",
        "new_cm": "",
        "new_genre": "ResearchPaper",  # what if the primary cm doesn't result in a ResearchPaper? Then we have double genres that may conflict...
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10600",
        "name": "data reanalysis",
        "new_cm": "",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10700",
        "name": "study replication",
        "new_cm": "",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10800",
        "name": "preregistered study",
        "new_cm": "",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    # things that become generic "nonempirical" cm and genre ResearchPaper:
    {
        "old_cm": "13100",
        "name": "literature review",
        "new_cm": "10000",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    # things keeping their cm, but getting genre ResearchPaper:
    {
        "old_cm": "10110",
        "name": "experimental study",
        "new_cm": "10110",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10100",
        "name": "empirical study",
        "new_cm": "10100",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10120",
        "name": "longitudinal empirical study",
        "new_cm": "10120",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10130",
        "name": "qualitative empirical study",
        "new_cm": "10130",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10140",
        "name": "meta-analysis",
        "new_cm": "10140",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    # things that become genre ResearchPaper and also move to a new, specific cm:
    {
        "old_cm": "10111",
        "name": "randomized experimental study",
        "new_cm": "10111",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10112",
        "name": "quasi-experimental study",
        "new_cm": "10110",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13110",
        "name": "systematic review",
        "new_cm": "10150",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10300",
        "name": "clinical case report",
        "new_cm": "10160",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "10200",
        "name": "illustrative empirical data",
        "new_cm": "10100",
        "new_genre": "ResearchPaper",
        "sh": "",
        "ct": "",
    },
    # things moving from cm to a directly equivalent genre:
    {
        "old_cm": "10500",
        "name": "study project",
        "new_cm": "10000",
        "new_genre": "StudyProtocol",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11400",
        "name": "treatment program",
        "new_cm": "",
        "new_genre": "TreatmentManual",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11500",
        "name": "guidelines",
        "new_cm": "",
        "new_genre": "Guidelines",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "11600",
        "name": "patient information",
        "new_cm": "",
        "new_genre": "PatientInformation",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13300",
        "name": "handbook",
        "new_cm": "",
        "new_genre": "Handbook",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13400",
        "name": "textbook",
        "new_cm": "",
        "new_genre": "Textbook",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13500",
        "name": "self-help guide",
        "new_cm": "",
        "new_genre": "SelfHelpGuide",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "13600",
        "name": "educational audiovisual media",
        "new_cm": "",
        "new_genre": "CourseMaterial",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14100",
        "name": "comment",
        "new_cm": "",
        "new_genre": "Comment",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14120",
        "name": "comment appended",
        "new_cm": "",
        "new_genre": "Comment",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14110",
        "name": "comment reply",
        "new_cm": "",
        "new_genre": "CommentReply",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14200",
        "name": "errata",
        "new_cm": "",
        "new_genre": "Correction",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14300",
        "name": "book/media review",
        "new_cm": "",
        "new_genre": "MediaReview",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "14310",
        "name": "test review",
        "new_cm": "",
        "new_genre": "TestReview",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15200",
        "name": "biography",
        "new_cm": "",
        "new_genre": "Biography",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15210",
        "name": "autobiography/personal account",
        "new_cm": "",
        "new_genre": "Autobiography",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15240",
        "name": "laudation",
        "new_cm": "",
        "new_genre": "Laudation",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15270",
        "name": "obituary",
        "new_cm": "",
        "new_genre": "Obituary",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "15340",
        "name": "selected readings",
        "new_cm": "",
        "new_genre": "SelectedReadings",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "17100",
        "name": "directory",
        "new_cm": "",
        "new_genre": "Directory",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "17200",
        "name": "dictionary",
        "new_cm": "",
        "new_genre": "Dictionary",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "17300",
        "name": "bibliography",
        "new_cm": "",
        "new_genre": "Bibliography",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "17350",
        "name": "link collection",
        "new_cm": "",
        "new_genre": "LinkCollection",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "18400",
        "name": "interview",
        "new_cm": "",
        "new_genre": "Interview",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "18500",
        "name": "panel discussion",
        "new_cm": "",
        "new_genre": "PanelDiscussion",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "18600",
        "name": "conference proceedings",
        "new_cm": "",
        "new_genre": "ConferenceProceedings",
        "sh": "",
        "ct": "",
    },
    {
        "old_cm": "16300",
        "name": "discussion of science structures",
        "new_cm": "",
        "new_genre": "ScholarlyWork",  
        "it": "Research",
        "sh": "3400",
        "ct": "",
    },
    {
        "old_cm": "16100",
        "name": "professional policies/standards",
        "new_cm": "",
        "new_genre": "ScholarlyWork",
        "sh": "3400",
        "ct": "",
    },
    {
        "old_cm": "16200",
        "name": "discussion of service structures",
        "new_cm": "",
        "new_genre": "ScholarlyWork",
        "sh": "",
        "ct": "22394",
    },
    {
        "old_cm": "15320",
        "name": "reprint",
        "new_cm": "",
        "new_genre": "",
        "sh": "",
        "ct": "",
    },
]

# add another array or object for combos of mediatypes and DT/BE -&gt; see SPARQL Anything version (VALUES)


# VALUES (?dt ?dt2 ?mt ?work_type ?content_type ?instance_type ?media_type ?carrier_type ?mediacarrier ?issuancetype)
# type_combos =   [


#   # online publications:
#   ("10" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:JournalArticle) # online article
#   ("05" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:Chapter) # online chapter
#   ("04" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:EditedBook) # online edited book
#   ("01" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:AuthoredBook) # online authored book
#   ("61" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:AuthoredBook) # online dissertation
#   ("25" UNDEF "Online Medium" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:Gray) # online report

#   ## dissertations in microfiche or on computer disks:
#   ("61" UNDEF "Microfiche" bf:Text rdaco:1020 UNDEF rdamt:1002 rdact:1022 pmt:Microfiche pit:AuthoredBook) # microfiche dissertation
#   ("61" UNDEF "Optical Disc" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1013 pmt:ElectronicDisc pit:AuthoredBook) # cd-rom or floppy disk dissertation
#   ## audio:
#   ("40" "41" "Optical Disc"  bf:NonMusicAudio rdaco:1012 bf:Electronic rdamt:1001 rdact:1004 pmt:ElectronicDisc pit:Monograph)
#   ("40" UNDEF "Online Medium"  bf:NonMusicAudio rdaco:1012 bf:Electronic rdamt:1001 rdact:1018 pmt:Online pit:Monograph)
#   ("40" "41" "Magnetic Tape"  bf:NonMusicAudio rdaco:1012 UNDEF rdamt:1001 rdact:1007 pmt:MagneticTape pit:Monograph)
#   # videos/films:
#   ("40" UNDEF "Optical Disc"  bf:MovingImage rdaco:1023 bf:Electronic rdamt:1008 rdact:1060 pmt:ElectronicDisc pit:Monograph)
#   ("40" "42" "Online Medium" bf:MovingImage rdaco:1023 bf:Electronic rdamt:1008 rdact:1018 pmt:Online pit:Monograph)
#    ("40" UNDEF "Magnetic Tape"  bf:MovingImage rdaco:1023 UNDEF rdamt:1008 rdact:1052 pmt:MagneticTape pit:Monograph)
#   ("40" UNDEF "Film"  bf:MovingImage rdaco:1023 UNDEF rdamt:1005 rdact:1034 pmt:FilmReelRoll pit:Monograph)
#   # slides:
#   ("40" UNDEF "Photographic Slides" bf:Text rdaco:1020 UNDEF rdamt:1005 rdact:1039 pmt:OverheadTransparency pit:Monograph) # these are always overheads!
#     # (UNDEF UNDEF "Print" bf:Text rdaco:1020 bf:Print rdamt:1007 rdact:1049 pmt:Print) # Print texts in general
#     ("10" UNDEF "Print" bf:Text rdaco:1020 bf:Print rdamt:1007 rdact:1049 pmt:Print pit:JournalArticle) # Print journal articles
#     ("05" UNDEF "Print" bf:Text rdaco:1020 bf:Print rdamt:1007 rdact:1049 pmt:Print pit:Chapter), # Print chapters
#   # (UNDEF UNDEF "eBook" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online ) # ebooks in general
#   ("01" UNDEF "eBook" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:AuthoredBook), # ebooks authored
#   ("04" UNDEF "eBook" bf:Text rdaco:1020 bf:Electronic rdamt:1003 rdact:1018 pmt:Online pit:EditedBook), # ebooks edited
#   # anything without MT: - we just don't know!
#   # ( UNDEF UNDEF UNDEF bf:Text bf:Print "unmediated" rdact:1049)
# ]


# 22797775,5:     &lt;AUP&gt;|i University of Heidelberg; Institute of Gerontology |c GERMANY&lt;/AUP&gt;
# 21735290,5:     &lt;AUP&gt;|i Psychiatrische Universitätsklinik Zürich; Klinik für affektive Erkrankungen und Allgemeinpsychiatrie |c SWITZERLAND&lt;/AUP&gt;
# 20378729,5:     &lt;AUP&gt;|i Universität Potsdam; Department Psychologie |c GERMANY&lt;/AUP&gt;
# 19948633,5:     &lt;AUP&gt;|i Universität Osnabrück; Sportwissenschaften |c GERMANY&lt;/AUP&gt;
# 29381181,5:     &lt;AUP&gt;Anonymus A |i |c &lt;/AUP&gt;
# 29381182,5:     &lt;AUP&gt;Anonymus B |i |c &lt;/AUP&gt;
# 29381183,5:     &lt;AUP&gt;Anonymus C |i |c &lt;/AUP&gt;
# 29381184,5:     &lt;AUP&gt;Anonymus D |i |c &lt;/AUP&gt;

# 24500320,5:     &lt;AUP&gt;NN&lt;/AUP&gt;
# 24500475,5:     &lt;AUP&gt;NN&lt;/AUP&gt;
