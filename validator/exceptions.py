class InvalidSchemaException(BaseException):
    pass


class CircularSchemaException(InvalidSchemaException):
    pass
