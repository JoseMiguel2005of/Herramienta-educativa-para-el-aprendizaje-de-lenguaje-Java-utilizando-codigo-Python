from typing import Dict, Optional, Any, List


class Type:
    def __init__(self, name: str, generic_args: List["Type"] = None):
        self.name = name
        self.generic_args = generic_args or []

    def __str__(self):
        if self.generic_args:
            args_str = ", ".join(str(t) for t in self.generic_args)
            return f"{self.name}<{args_str}>"
        return self.name


class Scope:
    def __init__(self, parent: Optional["Scope"] = None, name: str = "global"):
        self.parent = parent
        self.name = name
        self.variables: Dict[str, Type] = {}
        self.functions: Dict[str, Any] = {}
        self.classes: Dict[str, Any] = {}

    def define_var(self, name: str, var_type: Type):
        self.variables[name] = var_type

    def get_var(self, name: str) -> Optional[Type]:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get_var(name)
        return None


class Environment:
    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.needs_scanner = False
        self.defined_classes: set = set()

        # Built-in types
        self.type_object = Type("Object")
        self.type_int = Type("int")
        self.type_double = Type("double")
        self.type_boolean = Type("boolean")
        self.type_string = Type("String")
        self.type_void = Type("void")

    def push_scope(self, name: str = "local"):
        self.current_scope = Scope(parent=self.current_scope, name=name)

    def pop_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)
