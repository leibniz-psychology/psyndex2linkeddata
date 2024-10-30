- [x] how many journals have no publisher? no_publisher.txt
- [x] how many hubs have no lissn? easy: counting says: 4661-4267 = **394** vs 4661-70 (field LISSN exisist only 70 times) = 4591. But are they all really L-ISSNs?
- [x] how many Lissns are identical between hubs? so appear more than once? we have 4222 unique issnLs, but a total of 4267 issnLs. So 45 are identical? These are probably duplicate journals that should be cleaned out and merged somehow -> duplicate_lissns.txt
- [x] how many journal versions have no issn? -> versions_without_issn.txt
- [x] how many journals have no versions? no_versions.txt -> none.
    - [x] or just one version?
- [ ] after getting the vzdId from either the versions issn or the title? how many journals have no vzdId? (and how many are identical?)
- [x] how many issns are identical between hubs? -> identical_issns_between_versions.txt
- [ ] titles that seem long or have punctiation which indicates they should be split into variant titles or a subtitle. -> very_long_titles.txt

