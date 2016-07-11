from validator import get_schema, get_schema_from_file


file = "validator/meta_schema.json"
schema = get_schema_from_file(file)

print(schema.validate({"type": "string"}))

get_schema({"type": 1})
