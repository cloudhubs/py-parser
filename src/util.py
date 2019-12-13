import ntpath
import astroid


def ast_walk(root):
    yield root
    for node in root.get_children():
        yield from ast_walk(node)


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def path_base(path):
    head, tail = ntpath.split(path)
    return head


def decipher_props(context, node_name):
    # Deciphers node properties in a given context (eg.method)
    # from a variable name
    # Purely static analysis
    res = dict()
    query = set()
    data = set()

    # Traverse tree and find expr's
    for node in ast_walk(context):
        if isinstance(node, astroid.Name) and node.name == node_name:
            if node.parent.attrname == 'query_params':
                retrieve = get_parent_instance(node, astroid.Call)
                if retrieve:
                    query.add(retrieve.args[0].value)
            if node.parent.attrname == 'data':
                retrieve = get_parent_instance(node, astroid.Call)
                if retrieve:
                    print(retrieve.args)
                    data.add(retrieve)

    res['query_params'] = query
    res['data'] = data
    return res


def get_parent_instance(node, inst):
    c_node = node
    if not c_node:
        return None

    while not isinstance(c_node, inst):
        return get_parent_instance(c_node.parent, inst)

    return c_node
