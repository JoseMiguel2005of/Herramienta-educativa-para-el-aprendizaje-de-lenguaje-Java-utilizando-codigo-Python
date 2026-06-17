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
        # In a more advanced implementation, we'd infer return types here.
        # For now, just register the existence of the function.
        self.env.current_scope.functions[node.name] = {
            "node": node,
            "params": [arg.arg for arg in node.args.args]
        }
        
        self.env.push_scope(name=node.name)
        # Register parameters as variables in the new scope
        for arg in node.args.args:
            # We assume Object if no annotation, or we could look at arg.annotation
            self.env.current_scope.define_var(arg.arg, self.env.type_object)
            
        self.generic_visit(node)
        self.env.pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.env.current_scope.classes[node.name] = node
        self.env.push_scope(name=node.name)
        self.generic_visit(node)
        self.env.pop_scope()

    def visit_Assign(self, node: ast.Assign):
        # Very basic type inference for assignments
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            var_type = self._infer_type(node.value)
            if not self.env.current_scope.get_var(name):
                self.env.current_scope.define_var(name, var_type)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if isinstance(node.annotation, ast.Name):
                type_name = node.annotation.id
                java_type = self._map_annotation(type_name)
                self.env.current_scope.define_var(name, java_type)
        self.generic_visit(node)
        
    def _map_annotation(self, type_name: str) -> Type:
        mapping = {
            "int": self.env.type_int,
            "float": self.env.type_double,
            "str": self.env.type_string,
            "bool": self.env.type_boolean,
            "list": Type("java.util.List", [self.env.type_object]),
            "dict": Type("java.util.Map", [self.env.type_object, self.env.type_object]),
        }
        return mapping.get(type_name, self.env.type_object)

    def _infer_type(self, node: ast.AST) -> Type:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool): return self.env.type_boolean
            if isinstance(node.value, int): return self.env.type_int
            if isinstance(node.value, float): return self.env.type_double
            if isinstance(node.value, str): return self.env.type_string
        elif isinstance(node, ast.Name):
            return self.env.current_scope.get_var(node.id) or self.env.type_object
        elif isinstance(node, ast.BinOp):
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if lt.name == "double" or rt.name == "double": return self.env.type_double
            if lt.name == "String" or rt.name == "String": return self.env.type_string
            return self.env.type_int
        elif isinstance(node, ast.List):
            return Type("java.util.List", [self.env.type_object])
        elif isinstance(node, ast.Dict):
            return Type("java.util.Map", [self.env.type_object, self.env.type_object])
        elif isinstance(node, ast.Set):
            return Type("java.util.Set", [self.env.type_object])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "input":
                self.env.needs_scanner = True
                return self.env.type_string
            # Simple heuristic for common casts
            if isinstance(node.func, ast.Name):
                if node.func.id == "int": return self.env.type_int
                if node.func.id == "float": return self.env.type_double
                if node.func.id == "str": return self.env.type_string
                if node.func.id == "bool": return self.env.type_boolean
        return self.env.type_object
