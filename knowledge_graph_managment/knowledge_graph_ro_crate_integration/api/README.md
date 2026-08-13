# API documentation

The API presented here contain the route for the integration of datasets from RO-Crate source files

# Description

This API is a service that maps dataset metadata provided in the RO-Crate format to the corresponding properties in the Leibniz Data Manager (LDM). It allows users to submit their own RO-Crate metadata files and map their existing metadata properties to the template representing the properties of a dataset in the LDM. The API then generates the corresponding output file in a specified output folder. The purpose of this service is to transform dataset metadata into the structure required by the LDM dataset template, facilitating the import of datasets into the platform.
## routes

integration [POST]

# Integration dataset metadata into a set template.
## Example of Source Data
```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.1/context",
    {
      "qudt": "http://qudt.org/schema/qudt/"
    },
    {
      "unit": "http://qudt.org/vocab/unit/"
    },
    {
      "skos": "http://www.w3.org/2004/02/skos/core#"
    },
    {
      "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
    },
    {
      "base": "null://null/"
    },
    {
      "Component": "base:Component",
      "Constraint": "base:Constraint",
      "Measure": "base:Measure",
      "ObjectOfInterest": "base:ObjectOfInterest",
      "Operation": "base:Operation",
      "Property": "base:Property",
      "Statement": "base:Statement",
      "Unit": "base:Unit",
      "Variable": "base:Variable",
      "components": "base:components",
      "concepts": "base:concepts",
      "constraint": "base:constraint",
      "notation": "base:notation",
      "objectOfInterest": "base:objectOfInterest",
      "operation": "base:operation",
      "property": "base:property",
      "qudt:unit": "http://qudt.org/schema/qudt/unit",
      "rdfs:label": "http://www.w3.org/2000/01/rdf-schema#label",
      "rdfs:seeAlso": "http://www.w3.org/2000/01/rdf-schema#seeAlso",
      "skos:Concept": "http://www.w3.org/2004/02/skos/core#Concept",
      "skos:closeMatch": "http://www.w3.org/2004/02/skos/core#closeMatch",
      "skos:definition": "http://www.w3.org/2004/02/skos/core#definition",
      "skos:exactMatch": "http://www.w3.org/2004/02/skos/core#exactMatch",
      "stringMatch": "base:stringMatch",
      "supports": "base:supports"
    }
  ],
  "@graph": [
    {
      "@id": "./",
      "@type": "Dataset",
      "about": [],
      "author": [
        {
          "@id": "#9128a363-d786-4252-a979-05633eb2e7aa"
        },
        {
          "@id": "#58875464-a687-4ed5-a1d1-70c76afa4497"
        }
      ],
      "datePublished": "2026-06-09T21:01:11+00:00",
      "description": "Proof-of-concept evaluation of additive log-fidelity quantum k-means for hybrid product quantization.\nThis draft uses already-versioned GitHub artifacts and static paper-table CSV transcriptions for Digits, Fashion-MNIST 8x8, and Signed-Mirror-64, without rerunning experiments.",
      "hasPart": [
        {
          "@id": "d59z7iyh.py"
        },
        {
          "@id": "3kotfl06.json"
        }
      ],
      "isBasedOn": [
        {
          "@id": "#d1982270-07a7-4ec7-98a5-b603cb0fd157"
        }
      ],
      "license": {
        "@id": "https://creativecommons.org/licenses/by/4.0/"
      },
      "name": "Additive Log-Fidelity Quantum k-Means for Hybrid Product Quantization",
      "publisher": {
        "@id": "https://ror.org/04aj4c181"
      },
      "status": "unpublished"
    },
    {
      "@id": "ro-crate-metadata.json",
      "@type": "CreativeWork",
      "about": {
        "@id": "./"
      },
      "conformsTo": {
        "@id": "https://w3id.org/ro/crate/1.1"
      }
    },
    {
      "@id": "https://ror.org/0304hq317",
      "@type": [
        "Organization"
      ],
      "name": "Leibniz University Hannover",
      "url": "https://www.uni-hannover.de/"
    },
    {
      "@id": "#9128a363-d786-4252-a979-05633eb2e7aa",
      "@type": "Person",
      "affiliation": {
        "@id": "https://ror.org/0304hq317"
      },
      "familyName": "Jesinghaus",
      "givenName": "Christian",
      "name": "Christian Jesinghaus"
    },
    {
      "@id": "#58875464-a687-4ed5-a1d1-70c76afa4497",
      "@type": "Person",
      "affiliation": {
        "@id": "https://ror.org/0304hq317"
      },
      "familyName": "Rellermeyer",
      "givenName": "Jan S.",
      "name": "Jan S. Rellermeyer"
    },
    {
      "@id": "#be3fcf71-fc48-4b11-8a88-0c9853570202",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Product quantization",
      "rdfs:seeAlso": null,
      "skos:definition": "A vector quantization method that partitions vectors into blocks and represents each block by a codeword index."
    },
    {
      "@id": "#2f3c4580-1f4b-4b56-bd13-ea74f874d553",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Additive log-fidelity objective",
      "rdfs:seeAlso": null,
      "skos:definition": "A product-quantization-compatible objective obtained by applying a negative logarithm to multiplicative product-state fidelities."
    },
    {
      "@id": "#60f0c9be-0e71-4a28-a6be-098f212ac222",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Quantum k-means",
      "rdfs:seeAlso": null,
      "skos:definition": "A family of k-means-like clustering approaches using quantum-inspired or quantum-computed similarity or distance evaluations."
    },
    {
      "@id": "#3b6cdbe1-f7e3-4b85-8382-7eae9f7c4053",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Fidelity",
      "rdfs:seeAlso": null,
      "skos:definition": "A similarity measure between quantum states; in the real pure-state setting used here it is the squared inner product of normalized vectors."
    },
    {
      "@id": "#fdca95fe-127e-4faf-8545-f1324018d96a",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Product-quantized k-nearest neighbors",
      "rdfs:seeAlso": null,
      "skos:definition": "A k-nearest-neighbor pipeline that retrieves or classifies using approximate distances from product-quantized codebooks."
    },
    {
      "@id": "#31c53cf9-9847-4218-a356-ce065e35dcab",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Shot-based swap-test fidelity estimator",
      "rdfs:seeAlso": null,
      "skos:definition": "A simulator-based estimator of fidelity using a finite number of swap-test shots."
    },
    {
      "@id": "#6324c7b3-6ff8-46b4-8da8-64c801ad5478",
      "@type": [
        "skos:Concept"
      ],
      "rdfs:label": "Sign-aware encoding",
      "rdfs:seeAlso": null,
      "skos:definition": "A representation that separates positive and negative vector components before normalization to remove raw-fidelity sign ambiguity."
    },
    {
      "@id": "d59z7iyh.py",
      "@type": [
        "File",
        "SoftwareSourceCode"
      ],
      "encodingFormat": "text/x-python",
      "name": "d59z7iyh.py"
    },
    {
      "@id": "https://creativecommons.org/licenses/by/4.0/",
      "@type": [
        "CreativeWork"
      ],
      "description": "This work is licensed under Creative Commons Attribution 4.0 International. To view a copy of this license, visit https://creativecommons.org/licenses/by/4.0/",
      "identifier": "https://creativecommons.org/licenses/by/4.0/",
      "name": "CC BY 4.0"
    },
    {
      "@id": "https://ror.org/04aj4c181",
      "@type": [
        "Organization"
      ],
      "name": "TIB - Leibniz Information Centre for Science and Technology",
      "url": "https://www.tib.eu"
    },
    {
      "@id": "#068e96c1-170b-49d8-b970-26c294b77218",
      "@type": [
        "Organization"
      ],
      "name": null,
      "url": null
    },
    {
      "@id": "#cf704957-a772-46a1-9f6b-f504e6b7e9b3",
      "@type": [
        "Periodical"
      ],
      "name": null,
      "publisher": {
        "@id": "#068e96c1-170b-49d8-b970-26c294b77218"
      }
    },
    {
      "@id": "#f14640fc-fd29-4dd4-9be2-8be7b97d03fc",
      "@type": [
        "PublicationIssue"
      ],
      "datePublished": null,
      "isPartOf": {
        "@id": "#cf704957-a772-46a1-9f6b-f504e6b7e9b3"
      }
    },
    {
      "@id": "#d1982270-07a7-4ec7-98a5-b603cb0fd157",
      "@type": [
        "ScholarlyArticle"
      ],
      "abstract": "",
      "author": [
        {
          "@id": "#9128a363-d786-4252-a979-05633eb2e7aa"
        },
        {
          "@id": "#58875464-a687-4ed5-a1d1-70c76afa4497"
        }
      ],
      "isPartOf": {
        "@id": "#f14640fc-fd29-4dd4-9be2-8be7b97d03fc"
      },
      "name": "Additive Log-Fidelity Quantum k-Means for Hybrid Product Quantization"
    },
    {
      "@id": "#590d7425-cc8a-49a2-b368-1e1cfab925d9",
      "@type": [
        "Statement"
      ],
      "concepts": [
        {
          "@id": "#be3fcf71-fc48-4b11-8a88-0c9853570202"
        },
        {
          "@id": "#2f3c4580-1f4b-4b56-bd13-ea74f874d553"
        },
        {
          "@id": "#3b6cdbe1-f7e3-4b85-8382-7eae9f7c4053"
        }
      ],
      "notation": "LinguisticStatement",
      "rdfs:label": "Negative log-fidelity yields an additive objective compatible with product quantization."
    },
    {
      "@id": "3kotfl06.json",
      "@type": [
        "File"
      ],
      "components": [],
      "encodingFormat": "application/ld+json",
      "name": "3kotfl06.json",
      "supports": [
        {
          "@id": "#590d7425-cc8a-49a2-b368-1e1cfab925d9"
        }
      ]
    }
  ]
}
```
## Example of Output
```json
[
    {
        "title": "Additive Log-Fidelity Quantum k-Means for Hybrid Product Quantization",
        "license": "CC BY 4.0",
        "description": "Proof-of-concept evaluation of additive log-fidelity quantum k-means for hybrid product quantization.\nThis draft uses already-versioned GitHub artifacts and static paper-table CSV transcriptions for Digits, Fashion-MNIST 8x8, and Signed-Mirror-64, without rerunning experiments.",
        "issued": "2026-06-09T21:01:11+00:00",
        "extra_authors": [
            {
                "extra_author": "Jan S. Rellermeyer"
            }
        ],
        "author": "Christian Jesinghaus",
        "resources": [
            {
                "title": "d59z7iyh.py",
                "format": "text/x-python"
            },
            {
                "title": "3kotfl06.json",
                "format": "application/ld+json"
            }
        ]
    }
]
```

## POST request example
```bash
curl -X POST http://127.0.0.1:8001/ro_crate_integration \
  -F "source=/path/to/example.json" \
  -F "output=/path/to/output"
```

## Parameters
- source: Indicates the path to the RO crate source file.
- output: Indicates path to the folder where the output file will be generated.