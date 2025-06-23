from calendar import c
import html

import re
import sys
import os

# go up from testing/REL to the root of the project and then import modules- 
# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
# import modules
import modules.mappings as mappings
import modules.helpers as helpers
import modules.research_info as research_info
# a number of test strings found in REL fields:
rels = (
    "|b Original", # should be excluded, probably a mistake in the original data (or is the one above without |b and
    # it slipped into a new field?)
    "|b Reply",
    "|a Zhang, Da-Wei &amp; Sauce, Bruno |t Efficiency and capacity mechanisms can coexist in cognitive training |j 2023 |q Nature Reviews Psychology, 2, 127 |b Reply", # missing dfk!
    "|a Lakens, D. |t Invited commentary: Comparing the independent segments procedure with group sequential designs |j 2021 |q Psychological Methods, 26 (4), 498^DDS500. doi: 10.1037/met0000400 |b Reply",
    "|a De Tommaso, M. &amp; Prpic, V. |t Slow and fast beat sequences are represented differently through space |j 2020 |q Attention, Perception, &amp; Psychophysics 82, 2765^DDS2773 |b Comment",
    "",
    "0389778 |a Hansmann, Ralf; Scholz, Roland W. |t Arguments of usefulness and acceptance of video surveillance: An experimental study |j 2002 |q Schweizerische Zeitschrift für Soziologie, 28 (3), 425-434 |b Original",
    "0309957 |a Hansmann, Ralf |t Linking the components of a university program to the qualification profile of graduates: The case of a sustainability-oriented Environmental Science curriculum |j 2009 |q Journal of Research in Science Teaching, 46 (5), 537-569. doi:10.1002/tea.20286 |b Original",
    "0281114 |a Crott, H. W.; Hansmann, R. |t Informative intervention to improve normative functioning and output of groups |j 2003 |q Swiss Journal of Psychology, 62 (3), 177-193. doi:10.1024//1421-0185.62.3.177 |b Original",
    "0309953 |a Scholz, Roland W.; Steiner, Regula; Hansmann, Ralf |t Role of internship in higher education in environmental sciences |j 2004 |q Journal of Research in Science Teaching, 41 (1), 24-46. doi:10.1002/tea.10123 |b Original",
    "0319581 |a Hansmann, Ralf; Mieg, Harald A.; Crott, Helmut W.; Scholz, Roland W. |t Shifting students' to experts' complex systems knowledge: Effects of bootstrapping, group discussion, and case study participation |j 2003 |q International Journal of Sustainability in Higher Education, 4 (2), 151-168 |b Original",
    "0315701 |a Hansmann, Ralf; Scholz, Roland W.; Crott, Helmut W.; Mieg, Harald A. |t Higher education in environmental sciences: The effects of incorporating expert information in group discussions of a transdisciplinary case study |j 2003 |q Electronic Journal of Science Education, 7 (3), 31 pages |b Original",
    "0196546 |a Hansmann, Ralf; Crott, Helmut W.; Scholz, Roland W. |t Momentum effects in discussions on intellective tasks: Comparing informed and non-informed groups |j 2007 |q Swiss Journal of Psychology, 66 (1), 17-31. doi:10.1024/1421-0185.66.1.17 |b Original",
    "0318757 |a Hansmann, Ralf; Crott, Helmut W.; Mieg, Harald A.; Scholz, Roland W. |t Improving group processes in transdisciplinary case studies for sustainability learning |j 2009 |q International Journal of Sustainability in Higher Education, 10 (1), 33-42 |b Original",
    "0281666 |a Scholz, Roland W.; Hansmann, Ralf |t Combining experts' risk judgments on technology performance of phytoremediation: Self-confidence ratings, averaging procedures, and formative consensus building |j 2007 |q Risk Analysis, 27 (1), 225-240. doi:10.1111/j.1539-6924.2006.00871.x |b Original",
    "|a Hansmann, Ralf; Scholz, Roland W.; Francke Carl-Johan A. C.; Weymann, Martin |t Enhancing environmental awareness: Ecological and economic effects of food consumption |j 2005 |q Simulation &amp; Gaming, 36 (3), 364 - 382. doi:10.1177/1046878105279116 |b Original",
    "0279949 |a Hansmann, Ralf; Bernasconi, Petra; Smieszek, Timo; Loukopoulos, Peter; Scholz, Roland W. |t Justifications and self-organization as determinants of recycling behavior: The case of used batteries |j 2006 |q Resources, Conservation and Recycling, 47 (2), 133-159. doi:10.1016/j.resconrec.2005.10.006 |b Original",
    "0281632 |a Hansmann, Ralf; Loukopoulos, Peter; Scholz, Roland W. |t Characteristics of effective battery recycling slogans: A Swiss field study |j 2009 |q Resources, Conservation and Recycling, 53 (4), 218-230. doi:10.1016/j.resconrec.2008.12.003 |b Original",
    "0166812 |a Hansmann, Ralf; Scholz, Roland W. |t A two-step informational strategy for reducing littering behavior in a cinema |j 2003 |q Environment and Behavior, 35 (6), 752-762. doi:10.1177/0013916503254755 |b Original",
    "0280040 |a Hansmann, Ralf; Köllner, Thomas; Scholz, Roland W. |t Influence of consumers' socio-ecological and economic orientations on preferences for wood products with sustainability labels |j 2006 |q Forest Policy and Economics, 8 (3), 239-250. doi:10.1016/j.forpol.2004.06.005 |b Original",
    "0264510 |a Hoyer, Jürgen; Plag, Jens |t Generalisierte Angststörung |j 2013 |q PSYCH up2date, 7 (2), 89-104",
    "|a Scheuble, V., Mildenberger, M. &amp; Beauducel, A. |t The P300 and MFN as indicators of concealed knowledge in situations with negative and positive moral valence |j 2021 |q Biological Psychology, 162, No. 108093, doi: 10.1016/j.biopsycho.2021.108093 |b Original",
    "|a Walsh, B; Hagan, K.; Lockwood, C.  |t A systematic review comparing atypical anorexia nervosa and anorexia nervosa |j 2022 |q International Journal of Eating Disorders, 56 (4), DOI: 10.1002/eat.23856 |b Original",
    "|t DEBATE: Behavioral addictions in the ICD-11 |j 2022 |q Journal of Behavioral Addictions, 11 (2) |b Original",
    "|a Palm, Esther; Seubert, C.; Glaser, Jürgen |t Understanding employee motivation for work-to-nonwork integration behavior: A reasoned action approach |j 2019 |q ournal of Busi-ness and Psy-chology (online first, 16.08.2019)",
    "|a Palm, Esther; Seubert, C.; Glaser, Jürgen |t Bablub, füblü mübel förgel (börbel)"
)
# notable: 
# - one record may have more than one REL
# - some start with a subfield 
#   - usually |a, sometimes |t. In these cases, there is no DFK, but often a doi hidden in |q
#   - others are just the relationship type, starting with |b; these we can throw out, since nothing is actually mentioned to be linked to.
# main field: DFK, should always be present, since we don't usually link to works outside PSYNDEX; about 5100 start with a DFK. 107 don't. Of these, about 25 are mistakes (|b Original, |b Reply, etc.). The rest, about 80, are special cases (most start with a |a, 1 with just the |t) where there is no DFK, but we still want to extract the relationship type and other information.
# - subfields:
#   - |a: author(s)
#   - |t: title
#   - |j: year
#   - |q: source, may include doi
#   - |b: type of relationship, e.g. "Original" (meaning, if record is cumulative thesis: this is one chapter of this published elsewhere; otherwise: ?), "Reply", "Comment". Can be missing!
# goal: we mostly want the DFK and the relationaship type. The rest is just copied over from the dfk-referenced record.


def generate_relationship_from_rel(rel_field: str):

    ## first, make empty REL object:
    related_work = {
        "dfk": None,  # DFK of the related work
        "doi": None,  # DOI of the related work, if available
        "url": None,  # URL of the related work, if available
        "citation": None,  # citation of the related work, if available
        "relationship_type": None,  # type of relationship, e.g. "Original", "Reply", "Comment" etc.
    }
    
    # strip and clean it up first:
    rel_string = html.unescape(mappings.replace_encodings(rel_field.strip()))
    # if it starts with |b and there is no other subfield (# count of "|"" symbols is just 1), we can ignore it.
    if rel_string.startswith("|b") and rel.count("|") == 1 or rel_string == "":
        print(f"Skipping REL because empty: {rel_string}")
        return None # stop and return early, since there is nothing to extract here.
    # if it instead starts with a DFK (7-digit number), we can just return that and the relationship type.:
    elif rel_string[:7].isdigit():
        related_work["dfk"] = rel_string[:7]
        print(f"Found DFK: {related_work['dfk']}")
    else:
        
        # these are the special cases where there is no DFK, but we still want to extract the relationship type and other information.
        # first, check for a hidden doi anywhere in the string.
        # we have a neat function for that: check_for_url_or_doi(string)
        # we can expect just one doi or url in the whole string, so we can just use the first one.
        doi_or_url = helpers.check_for_url_or_doi(rel_string)
        if doi_or_url:
            # if the type is doi, we can just set it as the doi for our object:
            if doi_or_url[1] == "doi":
                related_work["doi"] = doi_or_url[0]
                print(f"Found DOI: {related_work['doi']}")
            # if the type is url, we can just set it as the url for our object:
            elif doi_or_url[1] == "url":
                related_work["url"] = doi_or_url[0]
                print(f"Found URL: {related_work['url']}")
            else: # if no doi or url, we need to send the title in |t to crossref to get the doi. Use the research_info.validate_doi_against_crossref function.
                try:
                    title = helpers.get_subfield(rel_string, "t") 
                except ValueError:
                    title = None
                try:
                    author = helpers.get_subfield(rel_string, "a")
                except ValueError:
                    author = None
                try:
                    year = helpers.get_subfield(rel_string, "j")
                except ValueError:
                    year = None
                try:
                    source = helpers.get_subfield(rel_string, "q")
                except ValueError:
                    source = None
                # concatenate into the semblance of a citation:
                if title and author and year and source:
                    citation = f"{author}: {title}; {year}; {source}"
                elif title and author and year:
                    citation = f"{author}: {title}; {year}"
                elif title and author:
                    citation = f"{author}: {title}"
                elif title and year and source:
                    citation = f"{title}; {year}; {source}"
                elif title and year:
                    citation = f"{title}; {year}"
                elif title:
                    citation = title
                else:
                    citation = None
                try:
                    related_work["doi"] = research_info.check_crossref_for_citation_doi(
                        citation, similarity_threshold=60  # low similarity threshold to get most of the RELs
                    )
                    if related_work["doi"] is not None:
                        print(f"Found DOI via Crossref: {related_work['doi']}")
                    else:
                        print(f"No DOI found via Crossref for citation: {citation}")
                        related_work["citation"] = citation
                        print(f"Using citation as fallback: {related_work['citation']}")
                # if there is an error, we can just use the citation as fallback:
                except:
                    print(f"Error checking Crossref for DOI: {citation}")
                    related_work["citation"] = citation
                    print(f"Using citation as fallback: {related_work['citation']}")
        # if there is a doi, we can extract it, otherwise we check crossref (as with RPLICs) for the title and author(s) to get the doi and double-check it as with RPLICs. We might not even need to extract the subfields, just send the whole string (minus |b) to crossref and get the doi from there - if we use a low similarity threshold, we can get the doi for most of these RELs, even if they are not perfect matches.
    # Now we need to extract the relation type from subfield |b. If there is no |b, we assume "Original", probably?
    # get subfield |b, if it exists:
    try:
        related_work["relationship_type"] = helpers.get_subfield(rel_string, "b")
    # if there is no |b, we assume "Original" (or just empty, if we don't know):
    except ValueError:
        # if there is no |b, we assume "Original"
        related_work["relationship_type"] = "Original"  
    # now return the related_work dictionary with the extracted information:
    return related_work

for index, rel in enumerate(rels):
    print(f"Processing REL {index + 1}/{len(rels)}: {rel}")
    relationship = generate_relationship_from_rel(rel)
    if relationship:
        print(f"Extracted relationship: {relationship}")
    else:
        print("No relationship extracted.")
    print("-" * 40)