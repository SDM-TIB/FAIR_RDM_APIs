from flask import Flask, request, jsonify, send_from_directory
from jsonpath_ng import jsonpath, parse
import json, re, os
from rdflib import Graph

app = Flask(__name__)

def isLiteral(property):
	literal_properties = {"description":"","name":"","datePublished":"","status":""}
	for prop in literal_properties:
		if prop in property:
			return True
	return False

def ro_crate_parser(file):
	g = Graph()
	g.parse(file, format="json-ld")
	g.serialize(format="turtle")
	query = """
	PREFIX schema1: <http://schema.org/> 

	SELECT ?p ?o
	WHERE {
	    ?s a schema1:Dataset;
	            ?p ?o .
	}
	"""
	results = g.query(query)
	output_dic = {}
	literal_properties = {"":""}
	for row in results:
		#print(f"Property: {str(row.p)}, Value: {str(row.o)}")
		if isLiteral(str(row.p)):
			output_dic[str(row.p)] = str(row.o)
		elif "type" in str(row.p):
			pass
		elif "about" in str(row.p):
			if str(row.p) in output_dic:
				output_dic[str(row.p)].append(str(row.o))
			else:
				output_dic[str(row.p)] = [str(row.o)]
		else:
			sub_dict = {}
			sub_query = "SELECT ?p ?o\n"
			sub_query += "WHERE {\n"
			sub_query += "<" + str(row.o) + "> ?p ?o .\n"
			sub_query += "}"

			if "isBasedOn" in str(row.p) and "doi" in str(row.o):
				sub_dict["@id"] = str(row.o)
			elif "author" in str(row.p) and "orcid" in str(row.o):
				sub_dict["orcid"] = str(row.o)
			
			inner_results = g.query(sub_query)
			
			for sub_rows in inner_results:
				if "components" not in sub_rows.p and "supports" not in sub_rows.p:
					sub_dict[str(sub_rows.p)] = str(sub_rows.o)
				else:
					component_dict = {}
					component_query = "SELECT ?p ?o\n"
					component_query += "WHERE {\n"
					component_query += "<" + str(sub_rows.o) + "> ?p ?o .\n"
					component_query += "}"

					component_results = g.query(component_query)

					for component_row in component_results:
						component_dict[str(component_row.p)] = str(component_row.o)

					if sub_rows.p not in sub_dict:
						sub_dict[str(sub_rows.p)] = [component_dict]
					else:
						sub_dict[str(sub_rows.p)].append(component_dict)

			if str(row.p) not in output_dic:
				output_dic[str(row.p)] = [sub_dict]
			else:
				output_dic[str(row.p)].append(sub_dict)
	query = """
	PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

	SELECT ?s ?p ?o
	WHERE {
	    ?s a skos:Concept;
	            ?p ?o .
	}
	"""
	results = g.query(query)
	sub_dict = {}
	for row in results:
		if row.s not in sub_dict:
			sub_dict[str(row.s)] = {str(row.p):str(row.o)}
		else:
			sub_dict[str(row.s)][str(row.p)] = str(row.o)
	output_dic["skos:Concept"] = sub_dict

	return output_dic

def execute_fuction(value, func_dic):
	func_list = {"toLower":"",
				 "tagsToList":"",
				 "edxTagsToList":"",
				 "osfApiStoragetoHtmlStorage":"",
				 "normalizeName":"",
				 "doiLink":""}
	if func_dic["function"] in func_list:
		if "toLower" == func_dic["function"]:
			value = value.lower()
		elif "tagsToList" == func_dic["function"]:
			return_value = []
			for i in value:
				return_value.append({"name": i})
			value = return_value
		elif "edxTagsToList" == func_dic["function"]:
			return_value = []
			for i in value:
				return_value.append({"name": i["name"]})
			value = return_value
		elif "osfApiStoragetoHtmlStorage" == func_dic["function"]:
			pattern = r"^https://api\.osf\.io/v2/nodes/([a-zA-Z0-9]+)/files/.*$"
			replacement = r"https://osf.io/\1/files"
			formatted_url = re.sub(pattern, replacement, value)
			if formatted_url == value:
				return "Error: URL did not match expected API format."
			value = formatted_url
		elif "normalizeName" == func_dic["function"]:
			if "," in value:
				temp_value_list = value.split(",")
				value = temp_value_list[1] + " " + temp_value_list[0]
		elif "doiLink" == func_dic["function"]:
			value = "https://doi.org/" + value
	return value

def metadata_parser(metadata, output):
	ldm_list_datasets = []
	property_list = {
	  "source": "example/sample_output_json.json",
	  "owner": "tib",
	  "iterator": "$.[*]",
	    "properties": [
	        {"source_property":"$['http://schema.org/name']", "ldm_property": "title"},
	        {"source_property": "$['http://schema.org/license'][*].['http://schema.org/name']", "ldm_property": "license"},
	        {"source_property": "$['http://schema.org/description']", "ldm_property": "description"},
	        {"source_property": "$['http://schema.org/datePublished']", "ldm_property": "issued"},
	        {"source_property": "$['http://schema.org/author'][*]", "ldm_property": "authors"},
	        {"source_property": "$['http://schema.org/isBasedOn'][*].['@id']", "ldm_property": "defined_in"},
	        {"source_property": "$['http://schema.org/about']", "ldm_property": "subject"},
	        {"source_property": "$['http://schema.org/keywords']", "ldm_property": "keywords"}
	    ],
	    "resources":{ 
	      "iterator": "$['http://schema.org/hasPart'][*]",
	      "properties":[
	        {"source_resource_property":"$['http://schema.org/name']","ldm_resource_property":"title"},
	        {"source_resource_property":"$['http://schema.org/encodingFormat']","ldm_resource_property":"format"},
	        {"source_resource_property":"$['http://schema.org/description']","ldm_resource_property":"description"}
	        
	      ]
	    }  
    }
	
	jsonpath_expr = parse(property_list["iterator"])
	datasets = [match.value for match in jsonpath_expr.find(metadata)]
	for row in datasets:
		ldm_dataset = {}
		for dic_property in property_list["properties"]:
			if dic_property["ldm_property"] == "authors":
				jsonpath_expr = parse(dic_property["source_property"])
				matches = [match.value for match in jsonpath_expr.find(row)]
				if len(matches) > 1:
					ldm_dataset["extra_authors"] = []
				ldm_dataset["author"] = ""
				if matches != []:
					for value in matches:
						if value == matches[0]:
							if "transformation_function" in dic_property:
								new_value = execute_fuction(value["http://schema.org/name"],dic_property["transformation_function"])
								ldm_dataset["author"] = new_value
							else:
								ldm_dataset["author"] = value["http://schema.org/name"]
							if "orcid" in value:
								ldm_dataset["orcid"] = value["orcid"]
						else:
							if "transformation_function" in dic_property:
								new_value = execute_fuction(value["http://schema.org/name"],dic_property["transformation_function"])
								if "orcid" in value:
									ldm_dataset["extra_authors"].append({"extra_author":new_value,"orcid":value["orcid"]})
								else:
									ldm_dataset["extra_authors"].append({"extra_author":new_value})
							else:
								if "orcid" in value:
									ldm_dataset["extra_authors"].append({"extra_author":value["http://schema.org/name"],"orcid":value["orcid"]})
								else:
									ldm_dataset["extra_authors"].append({"extra_author":value["http://schema.org/name"]})
			elif dic_property["ldm_property"] == "keywords":
				jsonpath_expr = parse(dic_property["source_property"])
				matches = [match.value for match in jsonpath_expr.find(row)]
				if len(matches) > 1:
					ldm_dataset["keywords"] = []
					for value in matches:
						if "transformation_function" in dic_property:
							new_value = execute_fuction(value,dic_property["transformation_function"])
							ldm_dataset["keywords"].append(new_value)
						else:
							ldm_dataset["keywords"].append(value)
			else:
				jsonpath_expr = parse(dic_property["source_property"])
				matches = [match.value for match in jsonpath_expr.find(row)]
				if matches:
					if matches[0] != None:
						if "transformation_function" in dic_property:
							value = execute_fuction(matches[0],dic_property["transformation_function"])
							ldm_dataset[dic_property["ldm_property"]] = value
						else:
							ldm_dataset[dic_property["ldm_property"]] = matches[0]
		if "resources" in property_list:
			ldm_dataset["resources"] = []
			if property_list["resources"]["iterator"] == "":
				resources_list = [row]
			else:
				jsonpath_expr = parse(property_list["resources"]["iterator"])
				resources_list = [match.value for match in jsonpath_expr.find(row)]
			for resource in resources_list:
				ldm_resource = {}
				for resource_property in property_list["resources"]["properties"]:
					jsonpath_expr = parse(resource_property["source_resource_property"])
					matches = [match.value for match in jsonpath_expr.find(resource)]
					if matches:
						if matches[0] != None:
							if "transformation_function" in resource_property:
								value = execute_fuction(matches[0],resource_property["transformation_function"])
								ldm_resource[resource_property["ldm_resource_property"]] = value
							else:
								ldm_resource[resource_property["ldm_resource_property"]] = matches[0]
				ldm_dataset["resources"].append(ldm_resource)
		if ldm_dataset["author"] != "" and "title" in ldm_dataset:
			ldm_list_datasets.append(ldm_dataset)

	with open(output + "/metadata.json", "w") as file:
		json.dump(ldm_list_datasets, file, indent=4)

	return "Metadata file generated succesfully.\n"

@app.route("/")
def home():
    return jsonify({"message": "Flask File API is running"})

@app.route("/ro_crate_integration", methods=["POST"])
def ro_crate_integration():
	output = request.form.get("output")
	source = request.form.get("source")
	converted_source = ro_crate_parser(source)
	metadata_parser(converted_source, output)
	return "Ro crate file conversion succesful.\n"


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8001, debug=True)