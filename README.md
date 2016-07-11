# JSON Schema Validator

In this repo you will find the source code of our json schema validator. In the file [demo.py](https://github.com/CSWR/json_schema_validator/blob/master/demo.py) you can
see an example of how to use it.

## What the validator can do

You can load a schema from a file, from a python dictionary or from a url with or without a valid JSONPointer fragment.

So as to instantiate a schema you can use these methods: `get_schema(dictionary)`, `get_schema_from_file(path)` and
 `get_schema_from_url(url)`.
 
In case you don't want to instantiate the schema you can use the `validate(schema, document)` method inside the validator module which takes two python dictionaries and returns a `Response` object (more on the `Response` class later).

A schema object has an attribute per keyword (the not keyword's attribute is called `_not`) and a `schema.validate(dictionary)` method so as to validate a json document.

### The validate method and the Response class

When you use the method `validate()` it will return a `Response` object which you can use to get a better insight on
why the document failed.

The response object has two useful attributes:

* document_pointer: a `JSONPointer` object pointing to the node on the document that failed.
* schema_pointer: a `JSONPointer` object pointing to the node on the schema that failed.

A `JSONPointer` is a class that represents a JSONPointer and which you can use it to get the object that's being referenced and the full JSON object where the referenced one lies(lives? is?).

So as to get the referenced json schema you can use `json_pointer.get_json()`. So as to get the whole schema you can use `json_pointer.document`. And so as to get the JSONPointer string you can do `str(json_pointer)`.

If you want to get a list of nodes that are being referenced you can use `json_pointer.nodes` which is a list whose first element is the root sign (`#`) and then the nodes to the referenced document.

### InvalidSchemaException

If you try to instantiate an invalid json schema you will get this exception. If the schema has circular references you will recieve an `CircularSchemaException` which inherits from `InvalidSchemaException`.

## Tests

## External references