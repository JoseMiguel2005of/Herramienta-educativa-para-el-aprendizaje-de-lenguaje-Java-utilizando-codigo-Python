import ast
import re
from typing import List, Tuple, Any, Optional
from .environment import Environment, Type

class Generator:
    """
    Second pass: Generates Java code from the AST.
    """
    def __init__(self, env: Environment, class_name: str = "Program"):
        self.env = env
        self.class_name = self._safe_class_name(class_name)
        
        self.main_lines: List[str] = []
        self.methods: List[dict] = []
        self.classes: List[str] = []
        self.imports: set = set()
        
        self._current_lines: List[str] = self.main_lines
        self._indent = 2
        self._in_function = False
        self._current_class = None

    def generate(self, tree: ast.AST) -> str:
        for node in tree.body:
            self._visit_stmt(node)
        return self._build_java_file()

    def _build_java_file(self) -> str:
        lines = []
        
        # Add imports
        if self.env.needs_scanner:
            self.imports.add("java.util.Scanner")
        if any("List" in str(t.name) for s in self._all_scopes(self.env.global_scope) for t in s.variables.values()):
            self.imports.add("java.util.List")
            self.imports.add("java.util.ArrayList")
        if any("Map" in str(t.name) for s in self._all_scopes(self.env.global_scope) for t in s.variables.values()):
            self.imports.add("java.util.Map")
            self.imports.add("java.util.HashMap")
            
        for imp in sorted(self.imports):
            lines.append(f"import {imp};")
        if self.imports:
            lines.append("")

        lines.append(f"public class {self.class_name} {{")

        # Inner Classes
        for cls_code in self.classes:
            lines.extend(f"    {line}" for line in cls_code.split("\n"))
            lines.append("")

        # Methods
        for method in self.methods:
            params = ", ".join(f"{ptype} {pname}" for ptype, pname in method["params"])
            ret = method["return_type"]
            modifiers = "public static" if not self._current_class else "public"
            lines.append(f"    {modifiers} {ret} {method['name']}({params}) {{")
            lines.extend(f"    {line}" for line in method["body"])
            lines.append("    }")
            lines.append("")

        # Main method
        lines.append("    public static void main(String[] args) {")
        if self.env.needs_scanner:
            lines.append("        Scanner scanner = new Scanner(System.in);")
        lines.extend(f"    {line}" for line in self.main_lines)
        lines.append("    }")
        lines.append("}")

        return "\n".join(lines)

    def _all_scopes(self, scope) -> List:
        scopes = [scope]
        # Since we don't keep child references in Scope directly, this is just a rough heuristic.
        # A more robust approach tracks all scopes created.
        return scopes

    def _line(self, content: str):
        self._current_lines.append(" " * (self._indent * 4) + content)

    def _visit_stmt(self, node: ast.AST):
        if isinstance(node, ast.Assign):
            self._visit_assign(node)
        elif isinstance(node, ast.AugAssign):
            self._visit_aug_assign(node)
        elif isinstance(node, ast.AnnAssign):
            self._visit_ann_assign(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._visit_expr_call(node.value)
        elif isinstance(node, ast.If):
            self._visit_if(node)
        elif isinstance(node, ast.For):
            self._visit_for(node)
        elif isinstance(node, ast.While):
            self._visit_while(node)
        elif isinstance(node, ast.FunctionDef):
            self._visit_function(node)
        elif isinstance(node, ast.ClassDef):
            self._visit_class(node)
        elif isinstance(node, ast.Return):
            self._visit_return(node)
        elif isinstance(node, ast.Try):
            self._visit_try(node)
        elif isinstance(node, ast.Break):
            self._line("break;")
        elif isinstance(node, ast.Continue):
            self._line("continue;")
        elif isinstance(node, ast.Pass):
            pass
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            self.env.warn("Los imports de Python no se traducen automáticamente al 100%.")
        else:
            self.env.error(f"Sentencia no soportada: {type(node).__name__}")

    def _visit_assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            self.env.error("Asignación múltiple no soportada")
            return

        target = node.targets[0]
        value_expr, value_type = self._expr(node.value)

        if isinstance(target, ast.Name):
            name = target.id
            if name in getattr(self, '_declared_vars', set()):
                self._line(f"{name} = {value_expr};")
            else:
                if not hasattr(self, '_declared_vars'):
                    self._declared_vars = set()
                self._declared_vars.add(name)
                # Fetch type from environment if analyzer found it, else fallback
                t = self.env.current_scope.get_var(name) or value_type
                self._line(f"{t} {name} = {value_expr};")
        elif isinstance(target, ast.Subscript):
            container = self._expr(target.value)[0]
            index = self._expr(target.slice)[0]
            # Java arrays vs Lists
            if "List" in str(value_type) or value_type.name == "Object":
                self._line(f"{container}.set({index}, {value_expr});")
            else:
                self._line(f"{container}[{index}] = {value_expr};")
        elif isinstance(target, ast.Attribute):
            obj = self._expr(target.value)[0]
            self._line(f"{obj}.{target.attr} = {value_expr};")

    def _visit_aug_assign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            op = self._aug_op(node.op)
            rhs, _ = self._expr(node.value)
            self._line(f"{name} {op}= {rhs};")

    def _visit_ann_assign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            var_type = self.env.current_scope.get_var(name) or Type("Object")
            if node.value:
                value_expr, _ = self._expr(node.value)
                self._line(f"{var_type} {name} = {value_expr};")
            else:
                self._line(f"{var_type} {name};")

    def _visit_expr_call(self, call: ast.Call):
        if isinstance(call.func, ast.Name) and call.func.id == "print":
            args = [self._expr(arg)[0] for arg in call.args]
            if not args:
                self._line("System.out.println();")
            elif len(args) == 1:
                self._line(f"System.out.println({args[0]});")
            else:
                joined = " + \" \" + ".join(f"String.valueOf({a})" for a in args)
                self._line(f"System.out.println({joined});")
        else:
            expr, _ = self._expr(call)
            self._line(f"{expr};")

    def _visit_if(self, node: ast.If):
        cond, _ = self._expr(node.test)
        self._line(f"if ({cond}) {{")
        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1

        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self._visit_else_if(node.orelse[0])
            else:
                self._line("} else {")
                self._indent += 1
                for stmt in node.orelse:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
        else:
            self._line("}")

    def _visit_else_if(self, node: ast.If):
        cond, _ = self._expr(node.test)
        self._line(f"}} else if ({cond}) {{")
        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1

        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self._visit_else_if(node.orelse[0])
            else:
                self._line("} else {")
                self._indent += 1
                for stmt in node.orelse:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
        else:
            self._line("}")

    def _visit_for(self, node: ast.For):
        if not isinstance(node.target, ast.Name):
            self.env.error("Bucle for complejo no soportado")
            return

        var_name = node.target.id
        iter_expr = node.iter

        if isinstance(iter_expr, ast.Call) and isinstance(iter_expr.func, ast.Name) and iter_expr.func.id == "range":
            args = [self._expr(arg)[0] for arg in iter_expr.args]
            if len(args) == 1:
                self._line(f"for (int {var_name} = 0; {var_name} < {args[0]}; {var_name}++) {{")
            elif len(args) == 2:
                self._line(f"for (int {var_name} = {args[0]}; {var_name} < {args[1]}; {var_name}++) {{")
            elif len(args) == 3:
                self._line(f"for (int {var_name} = {args[0]}; {var_name} < {args[1]}; {var_name} += {args[2]}) {{")
            self.env.current_scope.define_var(var_name, Type("int"))
        else:
            # Foreach loop
            iterable, t = self._expr(iter_expr)
            self._line(f"for (Object {var_name} : {iterable}) {{")
            self.env.current_scope.define_var(var_name, Type("Object"))

        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1
        self._line("}")

    def _visit_while(self, node: ast.While):
        cond, _ = self._expr(node.test)
        self._line(f"while ({cond}) {{")
        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1
        self._line("}")

    def _visit_function(self, node: ast.FunctionDef):
        self.env.push_scope(name=node.name)
        saved_lines = self._current_lines
        saved_indent = self._indent
        
        body_lines = []
        self._current_lines = body_lines
        self._indent = 0
        self._in_function = True

        params = []
        for arg in node.args.args:
            params.append(("Object", arg.arg))
            self.env.current_scope.define_var(arg.arg, Type("Object"))

        return_type = "void"
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
        if has_return:
            return_type = "Object" # Basic inference

        for stmt in node.body:
            self._visit_stmt(stmt)

        self.methods.append({
            "name": node.name,
            "params": params,
            "body": body_lines,
            "return_type": return_type,
        })

        self._current_lines = saved_lines
        self._indent = saved_indent
        self._in_function = False
        self.env.pop_scope()

    def _visit_class(self, node: ast.ClassDef):
        # Very basic Class generation
        saved_lines = self._current_lines
        saved_indent = self._indent
        
        class_lines = []
        self._current_lines = class_lines
        self._indent = 1
        
        # Support inheritance
        extends = ""
        if node.bases:
            base_name = node.bases[0].id if isinstance(node.bases[0], ast.Name) else "Object"
            extends = f" extends {base_name}"
            
        self._current_lines.append(f"public static class {node.name}{extends} {{")
        
        # In a real compiler we'd separate fields and methods.
        # For now, we'll just visit the body.
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name == "__init__":
                    # Constructor
                    params = []
                    for arg in stmt.args.args[1:]: # skip self
                        params.append(f"Object {arg.arg}")
                    self._line(f"public {node.name}({', '.join(params)}) {{")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
                else:
                    params = []
                    for arg in stmt.args.args[1:]: # skip self
                        params.append(f"Object {arg.arg}")
                    self._line(f"public Object {stmt.name}({', '.join(params)}) {{")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
            elif isinstance(stmt, ast.Assign):
                # Class fields
                if isinstance(stmt.targets[0], ast.Name):
                    val, _ = self._expr(stmt.value)
                    self._line(f"public Object {stmt.targets[0].id} = {val};")
                    
        self._current_lines.append("}")
        self.classes.append("\n".join(class_lines))
        
        self._current_lines = saved_lines
        self._indent = saved_indent

    def _visit_return(self, node: ast.Return):
        if node.value:
            expr, _ = self._expr(node.value)
            self._line(f"return {expr};")
        else:
            self._line("return;")

    def _visit_try(self, node: ast.Try):
        self._line("try {")
        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1
        
        for handler in node.handlers:
            ex_type = handler.type.id if isinstance(handler.type, ast.Name) else "Exception"
            ex_name = handler.name or "e"
            self._line(f"}} catch ({ex_type} {ex_name}) {{")
            self._indent += 1
            for stmt in handler.body:
                self._visit_stmt(stmt)
            self._indent -= 1
            
        if node.finalbody:
            self._line("} finally {")
            self._indent += 1
            for stmt in node.finalbody:
                self._visit_stmt(stmt)
            self._indent -= 1
            
        self._line("}")

    def _expr(self, node: Optional[ast.AST]) -> Tuple[str, Type]:
        if node is None:
            return "null", Type("Object")
            
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return ("true" if node.value else "false"), Type("boolean")
            if isinstance(node.value, int):
                return str(node.value), Type("int")
            if isinstance(node.value, float):
                return str(node.value), Type("double")
            if isinstance(node.value, str):
                escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"', Type("String")
            return "null", Type("Object")
            
        if isinstance(node, ast.Name):
            t = self.env.current_scope.get_var(node.id) or Type("Object")
            # Convert self to this
            if node.id == "self":
                return "this", Type("Object")
            return node.id, t
            
        if isinstance(node, ast.BinOp):
            left, lt = self._expr(node.left)
            right, rt = self._expr(node.right)
            if isinstance(node.op, ast.Pow):
                return f"Math.pow({left}, {right})", Type("double")
            op = self._binop(node.op)
            return f"({left} {op} {right})", (lt if lt.name != "Object" else Type("int"))
            
        if isinstance(node, ast.UnaryOp):
            operand, t = self._expr(node.operand)
            if isinstance(node.op, ast.USub): return f"(-{operand})", Type("int")
            if isinstance(node.op, ast.Not): return f"(!({operand}))", Type("boolean")
            
        if isinstance(node, ast.Compare):
            left, _ = self._expr(node.left)
            right, _ = self._expr(node.comparators[0])
            op = self._cmp_op(node.ops[0])
            return f"({left} {op} {right})", Type("boolean")
            
        if isinstance(node, ast.BoolOp):
            op = " && " if isinstance(node.op, ast.And) else " || "
            values = [self._expr(v)[0] for v in node.values]
            return f"({op.join(values)})", Type("boolean")
            
        if isinstance(node, ast.Call):
            return self._call(node)
            
        if isinstance(node, ast.List):
            self.imports.add("java.util.ArrayList")
            self.imports.add("java.util.Arrays")
            elements = ", ".join(self._expr(elt)[0] for elt in node.elts)
            if elements:
                return f"new ArrayList<>(Arrays.asList({elements}))", Type("java.util.List")
            return "new ArrayList<>()", Type("java.util.List")
            
        if isinstance(node, ast.Dict):
            self.imports.add("java.util.HashMap")
            return "new HashMap<>()", Type("java.util.Map")
            
        if isinstance(node, ast.Attribute):
            val, _ = self._expr(node.value)
            if val == "this": # Special handling for class instance vars
                return f"this.{node.attr}", Type("Object")
            return f"{val}.{node.attr}", Type("Object")
            
        if isinstance(node, ast.Subscript):
            val, t = self._expr(node.value)
            idx, _ = self._expr(node.slice)
            if "List" in str(t.name):
                return f"{val}.get({idx})", Type("Object")
            return f"{val}[{idx}]", Type("Object")
            
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    parts.append(f'"{value.value}"')
                elif isinstance(value, ast.FormattedValue):
                    e, _ = self._expr(value.value)
                    parts.append(f"String.valueOf({e})")
            return " + ".join(parts), Type("String")

        self.env.error(f"Expresión no soportada: {type(node).__name__}")
        return "/* no traducido */", Type("Object")

    def _call(self, node: ast.Call) -> Tuple[str, Type]:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            args = [self._expr(arg)[0] for arg in node.args]
            
            if name == "print":
                return f"System.out.println({args[0] if args else ''})", Type("void")
            if name == "input":
                self.env.needs_scanner = True
                prompt = args[0] if args else '""'
                return f"scanner.nextLine()", Type("String")
            if name == "int": return f"Integer.parseInt({args[0]})", Type("int")
            if name == "float": return f"Double.parseDouble({args[0]})", Type("double")
            if name == "str": return f"String.valueOf({args[0]})", Type("String")
            if name == "len": return f"{args[0]}.length()", Type("int") # Usually .size() for lists, but approximation
            
            return f"{name}({', '.join(args)})", Type("Object")
            
        if isinstance(node.func, ast.Attribute):
            obj, t = self._expr(node.func.value)
            method = node.func.attr
            args = [self._expr(arg)[0] for arg in node.args]
            
            # Map Python methods to Java equivalents
            if method == "append": method = "add"
            elif method == "pop": method = "remove"
            elif method == "keys": method = "keySet"
            
            return f"{obj}.{method}({', '.join(args)})", Type("Object")
            
        return "/* call */", Type("Object")

    def _safe_class_name(self, name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name)
        if not cleaned: return "Program"
        if cleaned[0].isdigit(): cleaned = "Program" + cleaned
        parts = re.split(r"[_\s]+", cleaned)
        return "".join(p.capitalize() for p in parts if p)

    def _binop(self, op: ast.operator) -> str:
        if isinstance(op, ast.Add): return "+"
        if isinstance(op, ast.Sub): return "-"
        if isinstance(op, ast.Mult): return "*"
        if isinstance(op, ast.Div): return "/"
        if isinstance(op, ast.FloorDiv): return "/"
        if isinstance(op, ast.Mod): return "%"
        return "+"
        
    def _aug_op(self, op: ast.operator) -> str:
        return self._binop(op)
        
    def _cmp_op(self, op: ast.cmpop) -> str:
        if isinstance(op, ast.Eq): return "=="
        if isinstance(op, ast.NotEq): return "!="
        if isinstance(op, ast.Lt): return "<"
        if isinstance(op, ast.LtE): return "<="
        if isinstance(op, ast.Gt): return ">"
        if isinstance(op, ast.GtE): return ">="
        return "=="
