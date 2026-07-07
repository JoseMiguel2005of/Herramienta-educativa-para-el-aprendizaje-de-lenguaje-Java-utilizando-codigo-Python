import ast
from .environment import Environment, Type


class Analyzer(ast.NodeVisitor):
    """
    First pass: Analyzes the AST to populate the environment with
    type information, variable declarations, and function signatures.
    """

    def __init__(self, env: Environment):
        self.env = env

    def analyze(self, tree: ast.AST):
        self.visit(tree)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Register function signature in the current scope
        self.env.current_scope.functions[node.name] = {
            "node": node,
            "params": [arg.arg for arg in node.args.args],
        }

        self.env.push_scope(name=node.name)
        # Register parameters as variables in the new scope
        for arg in node.args.args:
            if arg.arg == "self":
                continue
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                arg_type = self._map_annotation(arg.annotation.id)
            else:
                arg_type = self.env.type_object
            self.env.current_scope.define_var(arg.arg, arg_type)

        self.generic_visit(node)
        self.env.pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.env.current_scope.classes[node.name] = node
        self.env.push_scope(name=node.name)
        self.generic_visit(node)
        self.env.pop_scope()

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                name = target.id
                var_type = self._infer_type(node.value)
                if not self.env.current_scope.get_var(name):
                    self.env.current_scope.define_var(name, var_type)
            elif isinstance(target, ast.Tuple):
                # Tuple unpacking: a, b = 1, 2
                if isinstance(node.value, ast.Tuple) and len(target.elts) == len(node.value.elts):
                    for tgt, val in zip(target.elts, node.value.elts):
                        if isinstance(tgt, ast.Name):
                            name = tgt.id
                            var_type = self._infer_type(val)
                            if not self.env.current_scope.get_var(name):
                                self.env.current_scope.define_var(name, var_type)
                else:
                    for tgt in target.elts:
                        if isinstance(tgt, ast.Name):
                            if not self.env.current_scope.get_var(tgt.id):
                                self.env.current_scope.define_var(tgt.id, self.env.type_object)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if isinstance(node.annotation, ast.Name):
                type_name = node.annotation.id
                java_type = self._map_annotation(type_name)
                self.env.current_scope.define_var(name, java_type)
            elif isinstance(node.annotation, ast.Subscript):
                # Handle List[int], Dict[str, int], etc.
                java_type = self._map_subscript_annotation(node.annotation)
                self.env.current_scope.define_var(name, java_type)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        # Track the loop variable type
        if isinstance(node.target, ast.Name):
            if (isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                    and node.iter.func.id == "range"):
                self.env.current_scope.define_var(node.target.id, self.env.type_int)
            else:
                self.env.current_scope.define_var(node.target.id, self.env.type_object)
        self.generic_visit(node)

    def _map_annotation(self, type_name: str) -> Type:
        mapping = {
            "int": self.env.type_int,
            "float": self.env.type_double,
            "str": self.env.type_string,
            "bool": self.env.type_boolean,
            "list": Type("java.util.List", [self.env.type_object]),
            "dict": Type("java.util.Map", [self.env.type_object, self.env.type_object]),
            "set": Type("java.util.Set", [self.env.type_object]),
            "tuple": Type("java.util.List", [self.env.type_object]),
        }
        return mapping.get(type_name, self.env.type_object)

    def _map_subscript_annotation(self, node: ast.Subscript) -> Type:
        """Handle generic type annotations like List[int], Dict[str, int]."""
        if isinstance(node.value, ast.Name):
            base = node.value.id
            if base == "List" or base == "list":
                return Type("java.util.List", [self.env.type_object])
            if base == "Dict" or base == "dict":
                return Type("java.util.Map", [self.env.type_object, self.env.type_object])
            if base == "Set" or base == "set":
                return Type("java.util.Set", [self.env.type_object])
            if base == "Tuple" or base == "tuple":
                return Type("java.util.List", [self.env.type_object])
            if base == "Optional":
                return self.env.type_object
        return self.env.type_object

    def _infer_type(self, node: ast.AST) -> Type:
        if isinstance(node, ast.Constant):
            if node.value is None:
                return self.env.type_object
            if isinstance(node.value, bool):
                return self.env.type_boolean
            if isinstance(node.value, int):
                return self.env.type_int
            if isinstance(node.value, float):
                return self.env.type_double
            if isinstance(node.value, str):
                return self.env.type_string
        elif isinstance(node, ast.Name):
            if node.id in ("True", "False"):
                return self.env.type_boolean
            if node.id == "None":
                return self.env.type_object
            return self.env.current_scope.get_var(node.id) or self.env.type_object
        elif isinstance(node, ast.BinOp):
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if isinstance(node.op, ast.Pow):
                return self.env.type_double
            if lt.name == "double" or rt.name == "double":
                return self.env.type_double
            if lt.name == "String" or rt.name == "String":
                return self.env.type_string
            return self.env.type_int
        elif isinstance(node, ast.List) or isinstance(node, ast.Tuple):
            return Type("java.util.List", [self.env.type_object])
        elif isinstance(node, ast.Dict):
            return Type("java.util.Map", [self.env.type_object, self.env.type_object])
        elif isinstance(node, ast.Set):
            return Type("java.util.Set", [self.env.type_object])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name == "input":
                    self.env.needs_scanner = True
                    return self.env.type_string
                if name == "int":
                    return self.env.type_int
                if name == "float":
                    return self.env.type_double
                if name == "str":
                    return self.env.type_string
                if name == "bool":
                    return self.env.type_boolean
                if name == "len":
                    return self.env.type_int
                if name == "abs":
                    return self.env.type_double
                if name == "min" or name == "max":
                    return self.env.type_int
                if name == "list":
                    return Type("java.util.List", [self.env.type_object])
                if name == "dict":
                    return Type("java.util.Map", [self.env.type_object, self.env.type_object])
                if name == "set":
                    return Type("java.util.Set", [self.env.type_object])
                if name == "sorted" or name == "reversed":
                    return Type("java.util.List", [self.env.type_object])
        elif isinstance(node, ast.IfExp):
            return self._infer_type(node.body)
        elif isinstance(node, ast.ListComp):
            return Type("java.util.List", [self.env.type_object])
        elif isinstance(node, ast.Compare):
            return self.env.type_boolean
        elif isinstance(node, ast.BoolOp):
            return self.env.type_boolean
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return self.env.type_boolean
            return self._infer_type(node.operand)
        elif isinstance(node, ast.JoinedStr):
            return self.env.type_string
        elif isinstance(node, ast.Lambda):
            return self.env.type_object
        return self.env.type_object
