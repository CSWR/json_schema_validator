from .utils import *
from .exceptions import *
import os
import json
from urllib.request import urlopen


PATH = os.path.dirname(os.path.abspath(__file__))


OBJECT_KEYWORDS = ["properties", "required", "additionalProperties", "minProperties", "maxProperties", "dependencies",
                   "patternProperties"]
"""Object schema keywords."""

ARRAY_KEYWORDS = ["items", "additionalItems", "minItems", "maxItems", "uniqueItems"]
"""Array schema keywords."""

STRING_KEYWORDS = ["minLength", "maxLength", "pattern", "format"]
"""String schema keywords."""

NUMBER_KEYWORDS = ["multipleOf", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"]
"""Number schema keywords."""


class Schema:
    """
    Base class for all schemas.
    """

    COUNT = 0
    RESPONSE = 1

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        self.dict_schema = json_schema
        """dict corresponding to this schema."""

        self.whole_schema = whole_schema
        """Whole schema dict where `self.dict_schema` came from."""

        self.definitions = definitions
        self.path = path
        self.type = ""
        self.enum = []
        self.anyOf = []
        self.allOf = []
        self.oneOf = []
        self.notThis = None
        if not self.path_is_empty():
            self.definitions[self.path] = self
        if has_key(json_schema, "type"):
            self.type = json_schema['type']
        if has_key(json_schema, "enum"):
            self.enum = json_schema['enum']
        if has_key(json_schema, "anyOf"):
            self.__build_any_of(json_schema["anyOf"])
        if has_key(json_schema, "allOf"):
            self.__build_all_of(json_schema["allOf"])
        if has_key(json_schema, "oneOf"):
            self.__build_one_of(json_schema["oneOf"])
        if has_key(json_schema, "not"):
            self.__build_not(json_schema["not"])

    def path_is_empty(self):
        """
        Checks if this schema's path is an empty string. It also checks if this schema does not come from a reference.
        :return:
        """

        return self.path == ""

    def __build_all_of(self, all_of):
        for json_schema in all_of:
            self.allOf.append(self.build_child_schema(json_schema))

    def build_child_schema(self, child_schema, path=""):
        if has_key(child_schema, "$ref"):
            return self.__build_child_schema_from_reference(child_schema)
        else:
            return self.__build_child_schema_normally(child_schema, path=path)

    def __build_child_schema_from_reference(self, child_schema):
        reference = child_schema["$ref"]
        if has_key(self.definitions, reference):
            return self.definitions[reference]
        elif JSONPointer.is_json_pointer(reference):
            return self.build_child_schema(JSONPointer(self.whole_schema, reference).get_json(), path=reference)
        elif is_valid_url(reference):
            return get_schema_from_url(reference)
        else:
            return get_schema_from_file(reference)

    def __build_child_schema_normally(self, child_schema, path=""):
        if "type" in child_schema:
            schema_type = child_schema["type"]
            if isinstance(schema_type, str):
                if schema_type == "object":
                    return ObjectSchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "array":
                    return ArraySchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "string":
                    return StringSchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "number":
                    return NumberSchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "integer":
                    return IntegerSchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "boolean":
                    return BooleanSchema(child_schema, self.whole_schema, self.definitions, path)
                elif schema_type == "null":
                    return NullSchema(child_schema, self.whole_schema, self.definitions, path)
                else:
                    return Schema(child_schema, self.whole_schema, self.definitions, path)
            else:
                return MultipleSchema(child_schema, self.whole_schema, self.definitions, path)
        else:
            return MultipleSchema(child_schema, self.whole_schema, self.definitions, path)

    def __build_any_of(self, any_of):
        for json_schema in any_of:
            self.anyOf.append(self.build_child_schema(json_schema))

    def __build_one_of(self, one_of):
        for json_schema in one_of:
            self.oneOf.append(self.build_child_schema(json_schema))

    def __build_not(self, not_this):
        self.notThis = self.build_child_schema(not_this)

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.has_any_of():
            validate_any_of = self.validate_any_of(document)
            if not validate_any_of.is_valid:
                return validate_any_of
        if self.has_one_of():
            validate_one_of = self.validate_one_of(document)
            if not validate_one_of.is_valid:
                return validate_one_of
        if self.has_all_of():
            validate_all_of = self.validate_all_of(document)
            if not validate_all_of.is_valid:
                return validate_all_of
        if self.has_not():
            validate_not = self.validate_not(document)
            if not validate_not.is_valid:
                return validate_not
        if self.has_enum():
            validate_enum = self.validate_enum(document)
            if not validate_enum.is_valid:
                return validate_enum
        return Response(True, None, None)

    def has_any_of(self):
        """
        Checks if this schema's anyOf size is larger than 0.
        :return: bool.
        """

        return len(self.anyOf) > 0

    def validate_any_of(self, document):
        """
        Validates a document against the anyOf keyword of this schema.
        :param document: Dictionary.
        :return: Response object.
        """

        count_and_validate = count_and_validate_schema_array(self.anyOf, document)
        count = count_and_validate[Schema.COUNT]
        response = count_and_validate[Schema.RESPONSE]
        if count >= 1:
            return response.set_true()
        else:
            response.add_upward_document_and_schema_nodes([], self.build_nodes(["anyOf"]))
            return response

    def build_nodes(self, nodes):
        """
        Builds a list of nodes and inserts the $ref keyword if this schema comes from a reference.
        :param nodes:
        :return:
        """

        # TODO: Recordar en el path si es que el esquema corresponde a una referencia?
        # if self.path_is_empty():
        #     return nodes
        # else:
        #     nodes.insert(0, "$ref")
        #     return nodes
        return nodes

    def has_one_of(self):
        """
        Checks if this schema's oneOf size is larger than 0.
        :return: bool.
        """

        return len(self.oneOf) > 0

    def validate_one_of(self, document):
        """
        Validates a document against the oneOf keyword of this schema.
        :param document: Dictionary.
        :return: Response object.
        """

        count_and_validate = count_and_validate_schema_array(self.oneOf, document)
        count = count_and_validate[Schema.COUNT]
        response = count_and_validate[Schema.RESPONSE]
        if count == 1:
            return response.set_true()
        elif count < 1:
            response.add_upward_document_and_schema_nodes([], self.build_nodes(["oneOf"]))
            return response
        else:
            return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["oneOf"])))

    def has_all_of(self):
        """
        Checks if this schema's allOf size is larger than 0.
        :return: bool.
        """

        return len(self.allOf) > 0

    def validate_all_of(self, document):
        """
        Validates a document against the allOf keyword of this schema.
        :param document: Dictionary.
        :return: Response object.
        """

        count_and_validate = count_and_validate_schema_array(self.allOf, document)
        response = count_and_validate[Schema.RESPONSE]
        if response.is_valid:
            return response
        else:
            response.add_upward_document_and_schema_nodes([], self.build_nodes(["allOf"]))
            return response

    def has_not(self):
        """
        Checks if this schema's not is not None.
        :return: bool.
        """

        return self.notThis is not None

    def validate_not(self, document):
        """
        Validates a document against the not keyword of this schema.
        :param document: Dictionary.
        :return: Response object.
        """

        if self.notThis is not None:
            validate_not = self.notThis.validate(document)
            if not validate_not.is_valid:
                return Response(True, None, None)
            else:
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                              self.build_nodes(["not"])))
        return Response(True, None, None)

    def has_enum(self):
        """
        Checks if this schema's enum size is larger than 0.
        :return: bool.
        """

        return len(self.enum) > 0

    def validate_enum(self, document):
        """
        Validates a document against the enum keyword of this schema.
        :param document: Dictionary.
        :return: Response object.
        """

        for json_document in self.enum:
            if equals(document, json_document):
                return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                      self.build_nodes(["enum"])))


class ObjectSchema(Schema):
    """
    Object schema's class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)
        self.required = []
        """List object that contains the keys that must be present in a json document that validates against this
        schema"""

        self.properties = {}
        """Dict object where each key holds a schema."""

        self.minProperties = None
        """Minimum number of properties that a json_document must have."""

        self.maxProperties = None
        """Maximum number of properties that a json_document must have."""

        self.property_dependencies = {}
        """Dict object where each key holds the list of the properties that a json document must have if that key is
        also there."""

        self.schema_dependencies = {}
        """Dict object where each key holds the schema that a json document must be valid against if the document contains
        that key."""

        self.patternProperties = {}
        """Dict where each key corresponds to a pattern and each key hold a schema that every json object's key
        that correspond to that pattern must be valid against."""

        self.additionalProperties = Schema({}, self.whole_schema, self.definitions, "")
        """If it's a schema, every property that's not inside `self.properties` must be valid against it. If it's a
        boolean, if it's False, a json document can not have any additional property."""

        if has_key(json_schema, "additionalProperties"):
            self.__build_additional_properties(json_schema["additionalProperties"])
        if has_key(json_schema, "minProperties"):
            self.minProperties = json_schema["minProperties"]
        if has_key(json_schema, "maxProperties"):
            self.maxProperties = json_schema["maxProperties"]
        if has_key(json_schema, "properties"):
            self.__build_properties(json_schema["properties"])
        if has_key(json_schema, "required"):
            self.required = json_schema["required"]
        if has_key(json_schema, "dependencies"):
            self.__build_dependencies(json_schema["dependencies"])
        if has_key(json_schema, "patternProperties"):
            self.__build_pattern_properties(json_schema["patternProperties"])

    def __build_additional_properties(self, additional_properties):
        if isinstance(additional_properties, bool):
            self.additionalProperties = additional_properties
        else:
            self.additionalProperties = self.build_child_schema(additional_properties)

    def __build_properties(self, properties):
        for key, child_schema in properties.items():
            self.properties[key] = self.build_child_schema(child_schema)

    def __build_dependencies(self, dependencies):
        for key, dependency in dependencies.items():
            if isinstance(dependency, list):
                self.property_dependencies[key] = dependency
            else:
                self.schema_dependencies[key] = self.build_child_schema(dependency)

    def __build_pattern_properties(self, patter_properties):
        for key, child_schema in patter_properties.items():
            self.patternProperties[key] = self.build_child_schema(child_schema)

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        super_validate = super().validate(document)
        if not super_validate.is_valid:
            return super_validate
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        validate_required_properties = self.validate_required_properties(document)
        if not validate_required_properties.is_valid:
            return validate_required_properties
        validate_properties = self.validate_properties(document)
        if not validate_properties.is_valid:
            return validate_properties
        validate_min_properties = self.validate_min_properties(document)
        if not validate_min_properties.is_valid:
            return validate_min_properties
        validate_max_properties = self.validate_max_properties(document)
        if not validate_max_properties.is_valid:
            return validate_max_properties
        validate_dependencies = self.validate_dependencies(document)
        if not validate_dependencies:
            return validate_dependencies
        validate_add_properties = self.validate_additional_properties(document)
        if not validate_add_properties:
            return validate_add_properties
        validate_pattern_properties = self.validate_pattern_properties(document)
        if not validate_pattern_properties:
            return validate_pattern_properties
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if not isinstance(document, dict):
            return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["type"])))
        return Response(True, None, None)

    def validate_properties(self, document):
        """
        Validates a document this schema's properties keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for key, schema in self.properties.items():
            if has_key(document, key):
                validate_property = schema.validate(document[key])
                if not validate_property.is_valid:
                    validate_property.set_document(document)
                    validate_property.add_upward_document_and_schema_nodes([key], self.build_nodes(["properties", key]))
                    return validate_property
        return Response(True, None, None)

    def validate_required_properties(self, document):
        """
        Validates a document this schema's required keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for key in self.required:
            if not has_key(document, key):
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                              self.build_nodes(["required", key])))
        return Response(True, None, None)

    def validate_min_properties(self, document):
        """
        Validates a document this schema's minProperties keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.minProperties is not None and len(document.keys()) < self.minProperties:
            return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["minProperties"])))
        return Response(True, None, None)

    def validate_max_properties(self, document):
        """
        Validates a document this schema's maxProperties keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.maxProperties is not None and len(document.keys()) > self.maxProperties:
            return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["maxProperties"])))
        return Response(True, None, None)

    def validate_dependencies(self, document):
        """
        Validates a document this schema's dependencies keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        validate_property_dependencies = self.validate_property_dependencies(document)
        if not validate_property_dependencies.is_valid:
            return validate_property_dependencies
        validate_schema_dependencies = self.validate_schema_dependencies(document)
        if not validate_schema_dependencies.is_valid:
            return validate_schema_dependencies
        return Response(True, None, None)

    def validate_property_dependencies(self, document):
        """
        Validates a document this schema's property dependencies
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for key, list_of_dependencies in self.property_dependencies.items():
            if has_key(document, key) and not has_all_keys(document, list_of_dependencies):
                return Response(False, JSONPointer(document, [key]), JSONPointer(self.whole_schema,
                                                                                 self.build_nodes(["dependencies",
                                                                                                   key])))
        return Response(True, None, None)

    def validate_schema_dependencies(self, document):
        """
        Validates a document this schema's schema dependencies.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for key, schema in self.schema_dependencies.items():
            if has_key(document, key):
                validate_dependency = schema.validate(document)
                if not validate_dependency.is_valid:
                    validate_dependency.set_document(document)
                    validate_dependency.add_upward_document_and_schema_nodes([key], self.build_nodes(["dependencies",
                                                                                                      key]))
                    return validate_dependency
        return Response(True, None, None)

    def validate_additional_properties(self, document):
        """
        Validates a document this schema's additionalProperties keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if isinstance(self.additionalProperties, bool):
            validate_additional_properties_bool = self.__validate_additional_properties_bool(document)
            if not validate_additional_properties_bool.is_valid:
                return validate_additional_properties_bool
            return Response(True, None, None)
        else:
            validate_additional_properties_schema = self.__validate_additional_property_schema(document)
            if not validate_additional_properties_schema:
                return validate_additional_properties_schema
            return Response(True, None, None)

    def validate_pattern_properties(self, document):
        for key in document:
            if self.key_is_pattern_property(key):
                for pattern in self.get_key_patterns(key):
                    patter_schema = self.patternProperties[pattern]
                    validate = patter_schema.validate(document[key])
                    if not validate:
                        validate.add_upward_document_and_schema_nodes([key], ["patternProperties",
                                                                              pattern])
                        return validate
        return Response(True, None, None)

    def __validate_additional_properties_bool(self, document):
        """
        Validates a document this schema's additionalProperties keyword when it's a bool.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if not self.additionalProperties:
            for key in document:
                if self.key_is_additional_property(key):
                    return Response(False, JSONPointer(document, [key]), JSONPointer(self.whole_schema,
                                                                                     self.build_nodes(
                                                                                         ["additionalProperties"])))
        return Response(True, None, None)

    def key_is_additional_property(self, key):
        """
        Verifies if a key is an additional property to this schema.
        :param key:
        :return: bool.
        """
        if (key not in self.properties) and (key not in self.required) and \
                not self.key_is_pattern_property(key):
            return True
        return False

    def key_is_pattern_property(self, key):
        """
        Verifies if a key corresponds to a patternProperty of this schema.
        :param key:
        :return: bool.
        """

        for patternKey in self.patternProperties:
            if check_pattern(patternKey, key):
                return True
        return False

    def get_key_patterns(self, key):
        """
        Verifies if a key corresponds to a patternProperty of this schema.
        :param key:
        :return: bool.
        """
        patterns = []
        for patternKey in self.patternProperties:
            if check_pattern(patternKey, key):
                patterns.append(patternKey)
        return patterns

    def __validate_additional_property_schema(self, document):
        """
        Validates a document this schema's additionalProperties keyword when it's a schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for key in document:
            if self.key_is_additional_property(key):
                validate_additional_key = self.additionalProperties.validate(document[key])
                if not validate_additional_key:
                    validate_additional_key.set_document(document)
                    validate_additional_key.add_upward_document_and_schema_nodes([key],
                                                                                 self.build_nodes(
                                                                                     ["additionalProperties", key]))
                    return validate_additional_key
        return Response(True, None, None)


class ArraySchema(Schema):
    """
    Array schema class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)
        self.items = Schema({}, self.whole_schema, self.definitions, "")
        self.additionalItems = True
        self.maxItems = None
        self.minItems = None
        self.uniqueItems = False
        if has_key(json_schema, "items"):
            self.__build_items(json_schema["items"])
        if has_key(json_schema, "additionalItems"):
            self.__build_additional_items(json_schema["additionalItems"])
        if has_key(json_schema, "maxItems"):
            self.maxItems = json_schema["maxItems"]
        if has_key(json_schema, "minItems"):
            self.minItems = json_schema["minItems"]
        if has_key(json_schema, "uniqueItems"):
            self.uniqueItems = json_schema["uniqueItems"]

    def __build_items(self, items):
        if isinstance(items, dict):
            self.items = self.build_child_schema(items)
        else:
            self.items = []
            for schema in items:
                self.items.append(self.build_child_schema(schema))

    def __build_additional_items(self, additionalItems):
        if isinstance(additionalItems, bool):
            self.additionalItems = additionalItems
        else:
            self.additionalItems = self.build_child_schema(additionalItems)

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        validate_super = super().validate(document)
        if not validate_super.is_valid:
            return validate_super
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        validate_items = self.validate_items(document)
        if not validate_items.is_valid:
            return validate_items
        validate_additional_items = self.validate_additional_items(document)
        if not validate_additional_items.is_valid:
            return validate_additional_items
        validate_min_items = self.validate_min_items(document)
        if not validate_min_items.is_valid:
            return validate_min_items
        validate_max_items = self.validate_max_items(document)
        if not validate_max_items.is_valid:
            return validate_max_items
        validate_unique_items = self.validate_unique_items(document)
        if not validate_unique_items.is_valid:
            return validate_unique_items
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if not isinstance(document, list):
            return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["type"])))
        return Response(True, None, None)

    def validate_items(self, document):
        """
        Validates a document against this schema's items keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if isinstance(self.items, list):
            return self.__validate_items_list(document)
        else:
            return self.__validate_items_schema(document)

    def __validate_items_list(self, document):
        """
        Validates a document against this schema's items keyword when it's a list.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for i in range(0, get_size_of_smaller(document, self.items)):
            validate_item = self.items[i].validate(document[i])
            if not validate_item.is_valid:
                validate_item.set_document(document)
                validate_item.add_upward_document_and_schema_nodes([i], self.build_nodes(["items", i]))
                return validate_item
        return Response(True, None, None)

    def __validate_items_schema(self, document):
        """
        Validates a document against this schema's items keyword when it's a schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        for i in range(0, len(document)):
            validate_element = self.items.validate(document[i])
            if not validate_element.is_valid:
                validate_element.set_document(document)
                validate_element.add_upward_document_and_schema_nodes([i], self.build_nodes(["items"]))
                return validate_element
        return Response(True, None, None)

    def validate_additional_items(self, document):
        """
        Validates a document against this schema's additionalItems keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if isinstance(self.additionalItems, bool):
            return self.__validate_additional_items_bool(document)
        else:
            return self.__validate_additional_items_schema(document)

    def __validate_additional_items_bool(self, document):
        if not self.additionalItems:
            if self.count_additional_items(document) > 0:
                return Response(False, JSONPointer(document, [len(self.items)]),
                                JSONPointer(self.whole_schema, self.build_nodes(["additionalItems"])))
        return Response(True, None, None)

    def __validate_additional_items_schema(self, document):
        additional_items = self.get_additional_items(document)
        for additional_item in additional_items:
            validate_additional_item = self.additionalItems.validate(additional_item)
            if not validate_additional_item:
                validate_additional_item.add_upward_document_and_schema_nodes([document.index(additional_item)], ["additionalItems"])
                return validate_additional_item
        return Response(True, None, None)

    def additional_items_are_allowed(self):
        """
        Checks if this schema allows additionalItems.
        :return: bool.
        """

        # TODO: is it correct to return true if self.items is a list?
        if not isinstance(self.items, list):
            return False
        if isinstance(self.additionalItems, bool):
            return self.additionalItems
        else:
            return True

        # return (isinstance(self.additionalItems, bool) and self.additionalItems) or not isinstance(self.items, list)

    def count_additional_items(self, document):
        """
        Counts how many additional items has the document according to this schema.
        :param document: Dict object.
        :return: int.
        """

        return len(self.get_additional_items(document))

    def get_additional_items(self, document):
        """
        Returns a list with the additional items that a document has according to this schema.
        :param document:
        :return:
        """

        additional_items = []
        items_size = self.get_items_size()
        if len(document) > items_size:
            for i in range(items_size, len(document)):
                additional_items.append(document[i])
        return additional_items

    def get_items_size(self):
        """
        If `self.items` is a list returns it's size. If it's a schema it returns infinity.
        :return:
        """

        if isinstance(self.items, list):
            return len(self.items)
        else:
            return float("inf")

    def validate_min_items(self, document):
        """
        Validates a document against this schema's minItems keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.minItems is not None:
            if len(document) < self.minItems:
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                              self.build_nodes(["minItems"])))
            return Response(True, None, None)
        return Response(True, None, None)

    def validate_max_items(self, document):
        """
        Validates a document against this schema's maxItems keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.maxItems is not None:
            if len(document) > self.maxItems:
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema,
                                                                              self.build_nodes(["maxItems"])))
            return Response(True, None, None)
        return Response(True, None, None)

    def validate_unique_items(self, document):
        """
        Validates a document against this schema's uniqueItems keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.uniqueItems:
            repeated_item = find_repeated_item(document)
            if repeated_item == NONE:
                return Response(True, None, None)
            return Response(False, JSONPointer(document, [repeated_item]), JSONPointer(self.whole_schema,
                                                                          self.build_nodes(["uniqueItems"])))
        else:
            return Response(True, None, None)


class IntegerSchema(Schema):
    """
    Integer Schema class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)
        self.multipleOf = None
        self.minimum = None
        self.maximum = None
        self.exclusiveMinimum = False
        self.exclusiveMaximum = False

        if has_key(json_schema, "multipleOf"):
            self.multipleOf=(json_schema["multipleOf"])
        if has_key(json_schema, "minimum"):
            self.minimum = json_schema["minimum"]
        if has_key(json_schema, "maximum"):
            self.maximum = json_schema["maximum"]
        if has_key(json_schema, "exclusiveMinimum"):
            self.exclusiveMinimum = json_schema["exclusiveMinimum"]
        if has_key(json_schema, "exclusiveMaximum"):
            self.exclusiveMaximum = json_schema["exclusiveMaximum"]

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        super_validate = super().validate(document)
        if not super_validate.is_valid:
            return super_validate
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        validate_multiple_of = self.validate_multiple_of(document)
        if not validate_multiple_of.is_valid:
            return validate_multiple_of
        validate_minimum = self.validate_minimum(document)
        if not validate_minimum.is_valid:
            return validate_minimum
        validate_maximum = self.validate_maximum(document)
        if not validate_maximum.is_valid:
            return validate_maximum
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if isinstance(document, int) and not isinstance(document, bool):
            return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["type"])))

    def validate_multiple_of(self, document):
        """
        Validates a document against this schema's multipleOf keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if self.multipleOf is not None and document != 0:
            if not (document / self.multipleOf).is_integer():
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["multipleOf"])))
        return Response(True, None, None)

    def validate_minimum(self, document):
        """
        Validates a document against this schema's minimum and exclusiveMinimum keywords.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if self.minimum is not None:
            if document >= self.minimum:
                if self.exclusiveMinimum and document == self.minimum:
                    return Response(False, JSONPointer(document, []),
                                    JSONPointer(self.whole_schema, self.build_nodes(["exclusiveMinimum"])))
                return Response(True, None, None)
            return Response(False, JSONPointer(document, []),
                            JSONPointer(self.whole_schema, self.build_nodes(["minimum"])))
        return Response(True, None, None)

    def validate_maximum(self, document):
        """
        Validates a document against this schema's maximum and exclusiveMaximum keywords.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if self.maximum is not None:
            if document <= self.maximum:
                if self.exclusiveMaximum and document == self.maximum:
                    return Response(False, JSONPointer(document, []),
                                    JSONPointer(self.whole_schema, self.build_nodes(["exclusiveMaximum"])))
                return Response(True, None, None)
            return Response(False, JSONPointer(document, []),
                            JSONPointer(self.whole_schema, self.build_nodes(["maximum"])))
        return Response(True, None, None)


class NumberSchema(IntegerSchema):
    """
    Number Schema class.
    """

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if (isinstance(document, float) or isinstance(document, int)) and not isinstance(document, bool):
            return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["type"])))


class StringSchema(Schema):
    """
    String Schema class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)
        self.minLength = None
        self.maxLength = None
        self.pattern = None

        if has_key(json_schema, "minLength"):
            self.minLength = (json_schema["minLength"])
        if has_key(json_schema, "maxLength"):
            self.maxLength = json_schema["maxLength"]
        if has_key(json_schema, "pattern"):
            self.pattern = json_schema["pattern"]

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        super_validate = super().validate(document)
        if not super_validate.is_valid:
            return super_validate
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        validate_min_len=self.validate_min_len(document)
        if not validate_min_len.is_valid:
            return validate_min_len
        validate_max_len=self.validate_max_len(document)
        if not validate_max_len.is_valid:
            return validate_max_len
        validate_pattern=self.validate_pattern(document)
        if not validate_pattern.is_valid:
            return validate_pattern
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if isinstance(document, str):
            return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["type"])))

    def validate_min_len(self, document):
        """
        Validates a document against this schema's minLength keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if self.minLength is not None:
            if self.minLength > len(document):
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["minLength"])))
        return Response(True, None, None)

    def validate_max_len(self, document):
        """
        Validates a document against this schema's maxLength keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if self.maxLength is not None:
            if self.maxLength < len(document):
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["minLength"])))
        return Response(True, None, None)

    def validate_pattern(self, document):
        """
        Validates a document against this schema's pattern keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """
        if self.pattern is not None:
            if not check_pattern(self.pattern, document):
                return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["pattern"])))
        return Response(True, None, None)


class BooleanSchema(Schema):
    """
    Boolean Schema class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        super_validate = super().validate(document)
        if not super_validate.is_valid:
            return super_validate
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if isinstance(document, bool):
            return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["type"])))


class NullSchema(Schema):
    """
    Null Schema class.
    """

    def __init__(self, json_schema, whole_schema, definitions, path):
        """
        :param json_schema: schema as a python dict object.
        :param whole_schema: the whole first schema.
        :param path: the path that was used to call this schema inside a $ref (can be an empty string if it was not
        called from a $ref).
        :param definitions: integer that indicates where inside `definitions` are this schema definitions.
        :return: None.
        """

        super().__init__(json_schema, whole_schema, definitions, path)

    def validate(self, document):
        """
        Validates a document against this schema.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        super_validate = super().validate(document)
        if not super_validate.is_valid:
            return super_validate
        validate_type = self.validate_type(document)
        if not validate_type.is_valid:
            return validate_type
        return Response(True, None, None)

    def validate_type(self, document):
        """
        Validates a document against this schema's type keyword.
        :param document: document to validate.
        :return: Response object with pointers to the document and corresponding schema that failed (if it fails).
        """

        if document is None:
            return Response(True, None, None)
        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, self.build_nodes(["type"])))


class MultipleSchema(Schema):

    def __init__(self, json_schema, whole_schema, definitions, path):
        super().__init__(json_schema, whole_schema, definitions, path)
        if has_key(json_schema, "type"):
            self.type = json_schema["type"]
            self.validates_any = False
        else:
            self.type = infer_type(json_schema)
            self.validates_any = True
        self.schemas = {}
        for type in self.type:
            if type == "object":
                self.schemas[type] = ObjectSchema(json_schema, whole_schema, definitions, "")
            elif type == "string":
                self.schemas[type] = StringSchema(json_schema, whole_schema, definitions, "")
            elif type == "number":
                self.schemas[type] = NumberSchema(json_schema, whole_schema, definitions, "")
            elif type == "integer":
                self.schemas[type] = IntegerSchema(json_schema, whole_schema, definitions, "")
            elif type == "array":
                self.schemas[type] = ArraySchema(json_schema, whole_schema, definitions, "")
            elif type == "boolean":
                self.schemas[type] = BooleanSchema(json_schema, whole_schema, definitions, "")
            elif type == "null":
                self.schemas[type] = NullSchema(json_schema, whole_schema, definitions, "")

    def validate(self, document):
        validate_super = super().validate(document)
        if not validate_super:
            return validate_super
        if isinstance(document, str):
            if "string" not in self.schemas:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
            else:
                return self.schemas["string"].validate(document)
        elif isinstance(document, bool):
            if "boolean" not in self.schemas:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
            else:
                return Response(True, None, None)
        elif isinstance(document, int):
            if "integer" not in self.schemas:
                if "number" not in self.schemas:
                    if self.validates_any:
                        return Response(True, None, None)
                    else:
                        return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
                else:
                    return self.schemas["number"].validate(document)
            else:
                return self.schemas["integer"].validate(document)
        elif isinstance(document, dict):
            if "object" not in self.schemas:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
            else:
                return self.schemas["object"].validate(document)
        elif isinstance(document, list):
            if "array" not in self.schemas:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
            else:
                return self.schemas["array"].validate(document)
        elif isinstance(document, float):
            if "number" in self.schemas:
                return self.schemas["number"].validate(document)
            elif "integer" in self.schemas:
                return self.schemas["integer"].validate(document)
            else:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
        elif document is None:
            if "null" not in self.schemas:
                if self.validates_any:
                    return Response(True, None, None)
                else:
                    return Response(False, JSONPointer(document, []), JSONPointer(self.whole_schema, ["type"]))
            else:
                return Response(True, None, None)


def get_schema(json_schema, whole_schema=None):
    """
    This method recieves a dict object and return the corresponding schema object. If it's not a valid schema it will
    raise an exception.
    :param json_schema: Dict object.
    :return: Schema object.
    """

    if not validate_refs(json_schema, []):
        raise MalformedSchemaException()

    if whole_schema is None:
        meta_schema_json = get_json_from_file(PATH + os.sep + "meta_schema.json")
        meta_schema = __get_corresponding_schema(meta_schema_json, meta_schema_json, {}, "")
        if not meta_schema.validate(json_schema):
            raise InvalidSchemaException()
        whole_schema = json_schema

    if has_key(json_schema, "$ref"):
        return __get_schema_from_ref(json_schema, whole_schema)
    else:
        return __get_corresponding_schema(json_schema, whole_schema, {}, "")


def __get_schema_from_ref(json_schema, whole_schema):
    """
    Resolves a schema that contains a $ref.
    :param json_schema: JSONSchema that contains a reference.
    :return: Schema object.
    """

    reference = json_schema["$ref"]
    if JSONPointer.is_json_pointer(reference):
        if whole_schema is None:
            whole_schema = json_schema
        return get_schema_from_json_pointer(JSONPointer(whole_schema, reference).get_json(), whole_schema, reference)
    elif is_valid_url(reference):
        return get_schema_from_url(reference)
    else:
        return get_schema_from_file(reference)


def get_schema_from_json_pointer(referenced, whole_schema, reference):
    return __get_corresponding_schema(referenced, whole_schema, {}, reference)


def get_schema_from_url(url):
    """
    Opens a connection to the url and retrieves the schema object that's in it.
    :param url: url pointing a schema.
    :return: Schema object.
    """

    fragment = "#" + urlparse(url).fragment
    f = urlopen(url)
    json_string = f.read().decode("utf-8").replace("\n", "").replace("\t", "")
    schema = json.loads(json_string)
    if JSONPointer.is_json_pointer(fragment):
        return get_schema(JSONPointer(schema, fragment).get_json(), whole_schema=schema)
    else:
        # TODO: Fragments that are not JSONPointers
        return get_schema(schema)


def get_schema_from_file(file):
    """
    Retrieves a schema from the local file system.
    :param file: path to the schema.
    :return: Schema object.
    """
    return get_schema(get_json_from_file(file))


def __get_corresponding_schema(json_schema, whole_schema, definitions, path):
    """
    Private method that infers the type of a json schema and builds its object accordingly.
    :param json_schema: dict representing a json schema.
    :param whole_schema: the whole schema where the `json_schema` comes from.
    :param definitions: a dict that contains all the schema definitions that have been built so far.
    :param path: if `json_schema` was retrieved from a reference, this parameter is the path used to get to it.
    :return: Schema object.
    """
    if has_key(json_schema, "$ref"):
        return __get_schema_from_ref(json_schema, whole_schema=whole_schema)
    if "type" in json_schema:
        schema_type = json_schema["type"]
        if isinstance(schema_type, str):
            if schema_type == "object":
                return ObjectSchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "array":
                return ArraySchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "string":
                return StringSchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "number":
                return NumberSchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "integer":
                return IntegerSchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "boolean":
                return BooleanSchema(json_schema, whole_schema, definitions, path)
            elif schema_type == "null":
                return NullSchema(json_schema, whole_schema, definitions, path)
        else:
            return MultipleSchema(json_schema, whole_schema, definitions, path)
    else:
        return MultipleSchema(json_schema, whole_schema, definitions, path)


def last_valid_schema_index(schema_array, document):
    """
    Validates an array of schemas and returns the index of the last schema that the document was valid against.
    :param schema_array: Array of schema objects.
    :param document: Dict to validate.
    :return: int.
    """

    last_valid_index = -1
    for i in range(0, len(schema_array)):
        if schema_array[i].validate(document).is_valid:
            last_valid_index = i
    return last_valid_index


def count_and_validate_schema_array(schema_array, document):
    """
    Validates a document against an array of schemas. If it validates against all of them returns a tuple where the
    first element is how many schemas the document was valid against and the second is a True Response Object.
    If it is not valid against one or more schemas the first element of the response is how many schemas the document
    was valid against and the second is a Response Object that points to the last schema that was invalid against the
    document.
    :param schema_array:
    :param document:
    :return:
    """

    count = 0
    last_invalid = None
    last_invalid_index = -1
    for i in range(0, len(schema_array)):
        schema = schema_array[i]
        schema_validate = schema.validate(document)
        if schema_validate.is_valid:
            count += 1
        else:
            last_invalid = schema_validate
            last_invalid_index = i
    if last_invalid_index == NONE:
        return count, Response(True, None, None)
    else:
        last_invalid.add_upward_document_and_schema_nodes([], [last_invalid_index])
        return count, last_invalid


def infer_type(json_schema):
    """
    Infers the type of a schema.
    :param json_schema: Dict representig a json schema.
    :return: string with the corresponding type. If it has type it returns an empty string.
    """
    if has_key(json_schema, "type"):
        return json_schema["type"]
    else:
        r = []
        for key in json_schema:
            if OBJECT_KEYWORDS.count(key) == 1 and "object" not in r:
                r.append("object")
            elif ARRAY_KEYWORDS.count(key) == 1 and "array" not in r:
                r.append("array")
            elif STRING_KEYWORDS.count(key) == 1 and "string" not in r:
                r.append("string")
            elif NUMBER_KEYWORDS.count(key) == 1 and "number" not in r:
                r.append("number")
        return r


def validate_refs(d, traveled, full_schema=None):
    if full_schema is None:
        full_schema = d
    if not isinstance(d, dict):
        return True
    if "$ref" in d:
        if d["$ref"] not in traveled:
            if isinstance(d["$ref"], str) and JSONPointer.is_json_pointer(d["$ref"]):
                traveled.append(d["$ref"])
                referred = JSONPointer(full_schema, JSONPointer.get_nodes_from_string(d["$ref"]))
                if not validate_refs(referred.get_json(), traveled, full_schema):
                    return False
        else:
            return False
    for key in ["anyOf", "allOf"]:
        if key in d:
            for sch in d[key]:
                if not validate_refs(sch, traveled, full_schema):
                    return False
    if "not" in d:
        if not validate_refs(d["not"], traveled, full_schema):
            return False
    if "definitions" in d:
        for sch in d["definitions"]:
            if not validate_refs(sch, [], full_schema):
                return False
    # for key in d:
    #     if isinstance(d, dict):
    #         if not validate_refs(d[key], [], full_schema):
    #             return False
    #     elif isinstance(d, list):
    #         for element in d:
    #             if isinstance(element, dict):
    #                 if not validate_refs(element, [], full_schema):
    #                     return False
    return True
