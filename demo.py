from validator import get_schema
from validator.utils import get_json_from_file


file = get_json_from_file("validator/meta_schema.json")
schema = get_schema(file)

print(schema.validate(file))

get_schema({"type": "string"})
