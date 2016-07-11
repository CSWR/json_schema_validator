from classes import *
from utils import *
import time
s = {
    "definitions": {
        "S": {
            "$ref": "#/definitions/S"
        }
    },
    "$ref": "#/definitions/S"
}

# print ("inicio test")
# schemas_schema = get_schema_from_file("wikidata.json")
# print ("schema ready")
# wikidata_json = get_json_from_file("q.json")
# print ("json ready")
# start = time.clock()
# print(schemas_schema.validate(wikidata_json))
# tiempo=time.clock() - start
# print ("Time elapsed: " + str(tiempo))



# schemas_schema = get_schema_from_file("meta_schema.json")
#schema = {"$ref": "https://raw.githubusercontent.com/MainScientist/json_schema_tests/master/schemas/someSchemas.json#/jsonPointerInteger"}

#the_schema = get_schema(schema)
#print(the_schema)

#print(the_schema.validate("boo"))









# time1 = time.time()
# validate = wikidata_schema.validate(q30)
# time2 = time.time()
# print("The function took {:.4f} ms".format((time2 - time1) * 1000))
# print(validate)
# time1 = time.time()
# validate = wikidata_schema.validate(q35)
# time2 = time.time()
# print("The function took {:.4f} ms".format((time2 - time1) * 1000))
# print(validate)

# ref_schema = get_schema({"$ref": "http://json-schema.org/draft-04/hyper-schema"})
#
# print(schemas_schema.validate({"type": "object", "properties": {"minProperties": 5}}))
#
# print(schemas_schema.anyOf[2].properties["properties"].additionalProperties.anyOf)


# print(ref_schema.validate(wikidata_json))
# print("Ref schema")

# ref_is_valid = ref_schema.validate({"type": 5})
# print(ref_is_valid)
# print("---------------")
# print("Enum schema")
# enum_schema = get_schema({"enum": ["1", 1]})
# enum_is_valid = enum_schema.validate(True)
# print(enum_is_valid.is_valid)
# print(enum_is_valid.schema_pointer.nodes)

a = 1
b = 1

circular = {
  "definitions": {
    "S": {
      "anyOf": [
        {"$ref": "#/definitions/A"},
        {"$ref": "#/definitions/S"},
        {"$ref": "#/definitions/B"}
      ]
    },
    "A": {
      "enum": [
        "a"
      ]
    },
    "B": {
      "enum": [
        "b"
      ]
    }
  },
  "$ref": "#/definitions/S"
}
print(validate_refs(circular, []))
#
# schema = {"maximum": 40}
# numb_schema = get_schema(schema)
# print(numb_schema.validate(40.000000000000000000000000000000000000000001))
#
# s = get_schema_from_file("wikidata.json")
