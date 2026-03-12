# API documentation

The API presented here contain route for the creation of a knowledge graph

# Description

This API is a service that transforms heterogeneous data sources into RDF knowledge graphs using SDM-RDFizer executed with RML mappings. The API allows users to submit datasets and RML mapping rules, automatically execute the transformation process, and output the resulting knowledge graph to a specified output folder.

## routes

kg_creation [POST]

# Integration dataset metadata into a set template.
## Example of Input Mapping
```
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rr: <http://www.w3.org/ns/r2rml#>.
@prefix rml: <http://semweb.mmlab.be/ns/rml#>.

<#Author> a rr:TriplesMap;
  rml:logicalSource [
    rml:source "authors.csv";
    rml:referenceFormulation ql:CSV;
  ];
  rr:subjectMap [
    rr:template "https://research.tib.eu/ldm/{author_id}";
    rr:class pro:Author;
  ];
  rr:predicateObjectMap [
    rr:predicate rdfs:label;
    rr:objectMap [
      rml:reference "author_name";
    ]
  ];
  rr:predicateObjectMap [
    rr:predicate owl:sameAS;
    rr:objectMap [
      rr:template "https://orcid.org/{orcid}";
    ]
  ].
```
## Example of Source Data
```csv
author_id,author_name,orcid
0,Norman Gentsch,
1,Aaron N. Sexton,
2,Ismael Soto,
3,Ildar Baimuratov,
4,Hamed Babaei Giglou,
5,Ana M. Palacio-Castro,
6,Markus Stocker,
7,Kévin Boutillier,0009-0001-0356-4421
```
## Example of Output
```
<https://research.tib.eu/ldm/0> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/0> <http://www.w3.org/2000/01/rdf-schema#label> "Norman Gentsch".
<https://research.tib.eu/ldm/1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/1> <http://www.w3.org/2000/01/rdf-schema#label> "Aaron N. Sexton".
<https://research.tib.eu/ldm/2> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/2> <http://www.w3.org/2000/01/rdf-schema#label> "Ismael Soto".
<https://research.tib.eu/ldm/3> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/3> <http://www.w3.org/2000/01/rdf-schema#label> "Ildar Baimuratov".
<https://research.tib.eu/ldm/4> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/4> <http://www.w3.org/2000/01/rdf-schema#label> "Hamed Babaei Giglou".
<https://research.tib.eu/ldm/5> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/5> <http://www.w3.org/2000/01/rdf-schema#label> "Ana M. Palacio-Castro".
<https://research.tib.eu/ldm/6> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/6> <http://www.w3.org/2000/01/rdf-schema#label> "Markus Stocker".
<https://research.tib.eu/ldm/7> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/spar/pro/Author>.
<https://research.tib.eu/ldm/7> <http://www.w3.org/2000/01/rdf-schema#label> "Kévin Boutillier".
<https://research.tib.eu/ldm/7> <http://www.w3.org/2002/07/owl#sameAS> <https://orcid.org/0009-0001-0356-4421>.
```

## POST request example
```bash
curl -X POST http://127.0.0.1:8001/kg_creation \
  -F "mapping=/path/to/mapping.ttl" \
  -F "output=/path/to/output"
```

## Parameters
- mapping: Indicates the path to the input mapping file.
- output: Indicates path to the folder where the knowledge graph will be generated.