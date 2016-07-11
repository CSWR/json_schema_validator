import re
import json
from urllib.parse import urlparse, unquote
from urllib.request import urlopen

VALID_SCHEMES = ["http", "https", "ftp"]
"""List that contains the valid url schemes that a $ref keyword can have. """

NONE = -1


class JSONPointer:
    """
    JSONPointer class representation.
    """

    def __init__(self, document, nodes):
        """
        :param document: The whole document.
        :param nodes: The list of nodes to get a sub document from the document or the JSONPointer string.
        """

        self.document = document
        if isinstance(nodes, list):
            self.nodes = nodes
        elif isinstance(nodes, str):
            self.nodes = JSONPointer.get_nodes_from_string(nodes)

    @staticmethod
    def get_nodes_from_string(string):
        """
        Gets a lsit of nodes from a JSONPointer string.
        :param string: JSONPointer string.
        :return: List of nodes.
        """
        string = unquote(string)
        if string == "":
            return ["#"]
        i = 0
        nodes = []
        s_to_add = ""
        while i < len(string):
            if string[i] == "/":
                nodes.append(s_to_add)
                s_to_add = ""
                i += 1
            elif string[i] == "~":
                if i + 1 < len(string) and string[i + 1] == "1":
                    s_to_add += "/"
                    i += 2
                elif i + 1 < len(string) and string[i + 1] == "0":
                    s_to_add += "~"
                    i += 2
            else:
                s_to_add += string[i]
                i += 1
        nodes.append(s_to_add)
        return nodes

    def add_upward_nodes(self, list_of_nodes):
        """
        Add nodes at the beginning of `self.nodes`.
        :param list_of_nodes: Nodes to insert in `self.nodes`
        """

        for i in range(len(list_of_nodes) - 1, -1, -1):
            self.nodes.insert(0, list_of_nodes[i])

    def add_downward_nodes(self, list_of_nodes):
        """
        Add nodes at the end of `self.nodes`.
        :param list_of_nodes: Nodes to append in `self.nodes`
        """

        for i in range(0, len(list_of_nodes)):
            self.nodes.append(list_of_nodes[i])

    def get_json(self):
        """
        Retrieves the sub document of `self.document` that `self.nodes` points to.
        """

        ret = self.document
        for node in self.nodes:
            if node == "#":
                continue
            else:
                if isinstance(ret, list):
                    ret = ret[int(node)]
                else:
                    ret = ret[node]
        return ret

    @staticmethod
    def is_json_pointer(reference):
        """
        Checks if a string corresponds to a JSONPointer.
        :param reference: Possible JSONPointer string.
        """

        # TODO: Improve this method's accuracy
        if reference == "" or reference[0] == "#":
            return True
        return False


class Response:
    """
    Response object that is return when validating a document against a schema object.
    """

    def __init__(self, is_valid, document_pointer, schema_pointer):
        """
        :param is_valid: boolean that is True if the document was valid against a schema.
        :param document_pointer: JSONPointer pointing to the document that failed.
        :param schema_pointer: JSONPointer pointing to the schema that was not satisfied.
        """

        self.document_pointer = document_pointer
        self.schema_pointer = schema_pointer
        self.is_valid = is_valid

    def add_upward_document_and_schema_nodes(self, document_nodes, schema_nodes):
        """
        Adds upward nodes to the document and the schema.
        :param document_nodes: Upward nodes to insert in `self.document_pointer`.
        :param schema_nodes: Upward nodes to insert in `self.schema_pointer`.
        """

        self.document_pointer.add_upward_nodes(document_nodes)
        self.schema_pointer.add_upward_nodes(schema_nodes)

    def set_document(self, document):
        """
        Sets the document that `self.document_pointer` points to.
        """

        self.document_pointer.document = document

    def set_true(self):
        """
        Sets this response to True.
        """

        self.is_valid = True
        self.document_pointer = None
        self.schema_pointer = None
        return self

    def __repr__(self):
        if self.is_valid:
            return "Valid JSON!"
        else:
            return "Document failed on: " + str(self.document_pointer.nodes) +\
                   "\nOn Schema: " + str(self.schema_pointer.nodes)

    def __bool__(self):
        return self.is_valid


def has_key(dictionary, key):
    """
    :param dictionary: Dict.
    :param key: Key.
    :return:Whether the dict has this key.
    """

    return key in dictionary


def check_pattern(pattern, string):
    """
    :param pattern: Regular expression.
    :param string: Any string.
    :return:True if the string matches the patter.
    """

    p = re.compile(pattern)
    for index in range(0, len(string)):
        if p.match(string, index):
            return True
    return False


def get_size_of_smaller(list1, list2):
    """
    Returns the size of the smaller list.
    :param list1: List object.
    :param list2: List object.
    :return: int.
    """

    if len(list1) < len(list2):
        return len(list1)
    return len(list2)


def has_all_keys(document, list_of_keys):
    """
    Checks if a document has every key in the a list of keys.
    :param document: Dict object.
    :param list_of_keys: List of keys.
    :return: bool.
    """

    for key in list_of_keys:
        if not has_key(document, key):
            return False
    return True


def find_repeated_item(a_list):
    """
    Returns the index of the first repeated item in a list. If there's none returns -1.
    :param a_list: list object.
    :return: int.
    """

    for i in range(0, len(a_list)):
        for j in range(0, len(a_list)):
            if i != j and equals(a_list[i], a_list[j]):
                return j
    return -1


def list_has_repetition(a_list):
    """
    Checks if a list has a repeated item.
    :param a_list: list object.
    :return: bool.
    """

    for item in a_list:
        if a_list.count(item) > 1:
            return True
    return False


def is_valid_url(url):
    """
    Checks if a url has a valid scheme.
    :param url: url string.
    :return: bool.
    """

    parsed = urlparse(url)
    if __is_valid_scheme(parsed.scheme):
        return True
    return False


def __is_valid_scheme(scheme):
    """
    Check if a url scheme is a valid schem.
    :param scheme: Url scheme string.
    :return: bool.
    """

    if scheme in VALID_SCHEMES:
        return True
    return False


def get_json_from_file(path):
    with open(path, encoding='utf-8') as data:
        return json.load(data)


def get_json_from_url(url):
    f = urlopen(url)
    json_string = f.read().decode("utf-8").replace("\n", "").replace("\t", "")
    return json.loads(json_string)


def equals(item1, item2):
    if type(item1) != type(item2):
        return False
    return item1 == item2
