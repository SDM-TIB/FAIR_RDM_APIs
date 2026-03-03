# FAIR_RDM_APIs
[TODO] infotext

# 1) Return Datasets in correlation to a DOI
## Output
```json
{
  "doi": "http://orkg.org/orkg/resource/TR3",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/17",
      "author_label": "Anna Beer",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/18",
      "author_label": "Mauricio Brunet",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/19",
      "author_label": "Vibhav Srivastava",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/20",
      "author_label": "Maria-Esther Vidal",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    }
  ]
}
```
## GET request example
```bash
curl -X 'GET' 'http://127.0.0.1:5000/get_paper_info_by_doi?doi=http://orkg.org/orkg/resource/TR3'
```
# 2) Return Datasets in correlation with several DOI
## Input
```json
{
  "dois": [
    "http://orkg.org/orkg/resource/TR1",
    "http://orkg.org/orkg/resource/TR2",
    "https://doi.org/10.48366/R1581120",
    "http://orkg.org/orkg/resource/TR3"
  ]
}
```
## Output
```json
{
  "requested_count": 4,
  "found_count": 7,
  "results": [
    {
      "doi": "http://orkg.org/orkg/resource/TR3",
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/17",
      "author_label": "Anna Beer",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "doi": "http://orkg.org/orkg/resource/TR3",
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/18",
      "author_label": "Mauricio Brunet",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "doi": "http://orkg.org/orkg/resource/TR3",
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/19",
      "author_label": "Vibhav Srivastava",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "doi": "http://orkg.org/orkg/resource/TR3",
      "dataset": "https://research.tib.eu/ldm/9e7d3aa5-120c-499e-83b9-28c45b79060f",
      "author": "https://research.tib.eu/ldm/20",
      "author_label": "Maria-Esther Vidal",
      "title": "LDM Demo",
      "contact_person": "nodeID://b10200",
      "license": "http://www.opendefinition.org/licenses/cc-by-sa"
    },
    {
      "doi": "http://orkg.org/orkg/resource/TR2",
      "dataset": "https://research.tib.eu/ldm/95cb0c2e-b382-47f2-8e94-9aaf988d74f5",
      "author": "https://research.tib.eu/ldm/7",
      "author_label": "Kévin Boutillier",
      "title": "Semantic Vocabularies for Digital Product Passport and After-Sales Service (ORKG Comparison)",
      "contact_person": "nodeID://b10188",
      "license": "http://www.opendefinition.org/licenses/cc-by"
    },
    {
      "doi": "https://doi.org/10.48366/R1581120",
      "dataset": "https://research.tib.eu/ldm/95cb0c2e-b382-47f2-8e94-9aaf988d74f5",
      "author": "https://research.tib.eu/ldm/7",
      "author_label": "Kévin Boutillier",
      "title": "Semantic Vocabularies for Digital Product Passport and After-Sales Service (ORKG Comparison)",
      "contact_person": "nodeID://b10188",
      "license": "http://www.opendefinition.org/licenses/cc-by"
    },
    {
      "doi": "http://orkg.org/orkg/resource/TR1",
      "dataset": "https://research.tib.eu/ldm/95cb0c2e-b382-47f2-8e94-9aaf988d74f5",
      "author": "https://research.tib.eu/ldm/7",
      "author_label": "Kévin Boutillier",
      "title": "Semantic Vocabularies for Digital Product Passport and After-Sales Service (ORKG Comparison)",
      "contact_person": "nodeID://b10188",
      "license": "http://www.opendefinition.org/licenses/cc-by"
    }
  ]
}
```
## POST request example
```bash
curl -X 'POST' 'http://127.0.0.1:5001/get_paper_info_by_several_doi' \
     -H 'Content-Type: application/json' \
     -d '{
       "dois": [
         "http://orkg.org/orkg/resource/TR1",
         "http://orkg.org/orkg/resource/TR2",
         "https://doi.org/10.48366/R1581120",
         "http://orkg.org/orkg/resource/TR3"
       ]
     }'
```
# 3) Return Datasets in correlation to a Authors ORCID
## Output
```json
{
  "orcid": "https://orcid.org/0000-0001-6636-8148",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/a79664af-9493-4a8b-a5cf-c1fc79763961",
      "author": "https://research.tib.eu/ldm/10001",
      "author_label": "Warner Brueckmann",
      "orcid": "https://orcid.org/0000-0001-6636-8148",
      "title": "(Table 1) Hydrocarbon gas composition of sediment and gas hydrate collected in video-guided grabs from Chapopote",
      "contact_person": "nodeID://b47577"
    }
  ]
}
```
## GET request example
```bash
curl -X 'GET' 'http://127.0.0.1:5002/get_paper_info_by_orcid?orcid=https://orcid.org/0000-0001-6636-8148'
```
# 4) Return Datasets that cite a Dataset in correlation to the Authors ORCID
## Input
```json
```
## Output
```json
```
## GET request example
```bash
```
