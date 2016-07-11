'''
Module providing the classes for validating JSON Schemas
'''
from .classes import get_schema, get_schema_from_file, get_schema_from_url


def validate(schema, document):
    s = get_schema(schema)
    return s.validate(document)
