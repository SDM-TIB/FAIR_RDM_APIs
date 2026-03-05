# api documentation

The api presented here contains routes to explore the content of a knowledgegraph

# api ip and port

127.0.0.1:5000

# 1) Return Datasets in correlation to a Paper DOI
## Output
```json
{
  "doi": "http://orkg.org/orkg/resource/TR138",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/a6765fc8-1936-465f-9158-88b863cba4f8",
      "doi": "http://orkg.org/orkg/resource/TR138",
      "author": "https://research.tib.eu/ldm/2004",
      "author_label": "Eurostat",
      "title": "Enterprises that obtained intra-group loans for R&D or other innovation activities within the enterprise group by NACE Rev. 2 activity and size class (2018)",
      "contact_person": "nodeID://b20005"
    }
  ]
}
```
## GET request example
```bash
curl -X 'GET' 'http://127.0.0.1:5000/get_dataset_attributes_by_paper_doi?doi=http://orkg.org/orkg/resource/TR138'
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
  "doi": "http://orkg.org/orkg/resource/TR138",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/a6765fc8-1936-465f-9158-88b863cba4f8",
      "doi": "http://orkg.org/orkg/resource/TR138",
      "author": "https://research.tib.eu/ldm/2004",
      "author_label": "Eurostat",
      "title": "Enterprises that obtained intra-group loans for R&D or other innovation activities within the enterprise group by NACE Rev. 2 activity and size class (2018)",
      "contact_person": "nodeID://b20005"
    }
  ]
}
```
## POST request example
```bash
curl -X 'POST' 'http://127.0.0.1:5000/get_dataset_attributes_by_paper_doi'
     -H 'Content-Type: application/json'
     -d '{"dois":[
     "http://orkg.org/orkg/resource/TR1",
     "http://orkg.org/orkg/resource/TR2",
     "https://doi.org/10.48366/R1581120",
     "http://orkg.org/orkg/resource/TR3"
     ]}'
```
# 3) Return Datasets in correlation to a Authors ORCID
## Output
```json
{
  "orcid": "https://orcid.org/0000-0003-2609-428X",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/2144e7f0-c4ca-4ed0-b679-0344c8cfd3cc",
      "author": "https://research.tib.eu/ldm/36030",
      "author_label": "Torsten Mayer-Gürr",
      "orcid": "https://orcid.org/0000-0003-2609-428X",
      "title": "GRACE monthly solutions for evaluation of background",
      "contact_person": "nodeID://b197879"
    }
  ]
}
```
## GET request example
```bash
curl -X 'GET' 'http://127.0.0.1:5000/get_dataset_attributes_by_author_orcid?orcid=https://orcid.org/0000-0003-2609-428X'
```
# 4) Return Datasets that cite a Dataset in correlation to the Authors ORCID
## Input
```json
{
  "orcid":"https://orcid.org/0000-0003-2609-428X"
}
```
## Output
```json
{
  "orcid": "https://orcid.org/0000-0003-2609-428X",
  "results": [
    {
      "dataset": "https://research.tib.eu/ldm/2144e7f0-c4ca-4ed0-b679-0344c8cfd3cc",
      "author": "https://research.tib.eu/ldm/36030",
      "author_label": "Torsten Mayer-Gürr",
      "orcid": "https://orcid.org/0000-0003-2609-428X",
      "title": "GRACE monthly solutions for evaluation of background",
      "contact_person": "nodeID://b197879"
    }
  ]
}
```
## POST request example
```bash
curl -X 'POST' 'http://127.0.0.1:5000/get_dataset_attributes_by_author_orcid' -H 'Content-Type: application/json' -d '{"orcid":"https://orcid.org/0000-0003-2609-428X"}'```
