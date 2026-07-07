import ast
import re
from typing import List, Tuple, Optional
from .environment import Environment, Type


class Generator:
    """
    Second pass: Generates Java code from the AST.
    Supports advanced Python patterns including list comprehensions,
    tuple unpacking, lambdas, ternary expressions, and more.
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
        self._declared_vars: set = set()
        self._lambda_counter = 0

    def generate(self, tree: ast.AST) -> str:
        for node in tree.body:
            self._visit_stmt(node)
        return self._build_java_file()

    def _build_java_file(self) -> str:
        lines = []

        # Add imports
        if self.env.needs_scanner:
            self.imports.add("java.util.Scanner")

        for imp in sorted(self.imports):
            lines.append(f"import {imp};")
        if self.imports:
            lines.append("")

        lines.append(f"public class {self.class_name} {{")

        # Inner Classes
        for cls_code in self.classes:
            for line in cls_code.split("\n"):
                lines.append(f"    {line}")
            lines.append("")

        # Methods
        for method in self.methods:
            params = ", ".join(f"{ptype} {pname}" for ptype, pname in method["params"])
            ret = method["return_type"]
            modifiers = "public static" if not self._current_class else "public"
            lines.append(f"    {modifiers} {ret} {method['name']}({params}) {{")
            for line in method["body"]:
                lines.append(f"    {line}")
            lines.append("    }")
            lines.append("")

        # Main method
        lines.append("    public static void main(String[] args) {")
        if self.env.needs_scanner:
            lines.append("        Scanner scanner = new Scanner(System.in);")
        for line in self.main_lines:
            lines.append(f"    {line}")
        lines.append("    }")
        lines.append("}")

        return "\n".join(lines)

    # ── Statement visitors ──────────────────────────────────────────

    def _visit_stmt(self, node: ast.AST):
        if isinstance(node, ast.Assign):
            self._visit_assign(node)
        elif isinstance(node, ast.AugAssign):
            self._visit_aug_assign(node)
        elif isinstance(node, ast.AnnAssign):
            self._visit_ann_assign(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._visit_expr_call(node.value)
        elif isinstance(node, ast.Expr):
            # Standalone expression (e.g. docstrings)
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                # Docstring → comment
                for docline in node.value.value.strip().split("\n"):
                    self._line(f"// {docline.strip()}")
            else:
                expr, _ = self._expr(node.value)
                self._line(f"{expr};")
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
            self._line("// pass")
        elif isinstance(node, ast.Delete):
            self._visit_delete(node)
        elif isinstance(node, ast.Assert):
            self._visit_assert(node)
        elif isinstance(node, ast.With):
            self._visit_with(node)
        elif isinstance(node, ast.Raise):
            self._visit_raise(node)
        elif isinstance(node, ast.Global) or isinstance(node, ast.Nonlocal):
            self.env.warn("global/nonlocal: Java no tiene un equivalente directo; las variables se manejan por alcance de clase.")
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            self._visit_import(node)
        else:
            self.env.warn(f"Sentencia '{type(node).__name__}' no tiene equivalente directo; se omitió.")

    def _visit_delete(self, node: ast.Delete):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._line(f"{target.id} = null;")
            elif isinstance(target, ast.Subscript):
                container, _ = self._expr(target.value)
                idx, _ = self._expr(target.slice)
                self._line(f"{container}.remove({idx});")

    def _visit_assert(self, node: ast.Assert):
        test_expr, _ = self._expr(node.test)
        if node.msg:
            msg_expr, _ = self._expr(node.msg)
            self._line(f'assert {test_expr} : {msg_expr};')
        else:
            self._line(f"assert {test_expr};")

    def _visit_with(self, node: ast.With):
        # try-with-resources
        resources = []
        for item in node.items:
            ctx_expr, _ = self._expr(item.context_expr)
            var_name = item.optional_vars.id if item.optional_vars and isinstance(item.optional_vars, ast.Name) else "_resource"
            resources.append(f"var {var_name} = {ctx_expr}")
        self._line(f"try ({'; '.join(resources)}) {{")
        self._indent += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self._indent -= 1
        self._line("}")

    def _visit_raise(self, node: ast.Raise):
        if node.exc:
            exc_expr, _ = self._expr(node.exc)
            self._line(f"throw {exc_expr};")
        else:
            self._line("throw new RuntimeException();")

    def _visit_import(self, node):
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._line(f"// import {alias.name} — no tiene equivalente directo en Java")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(a.name for a in node.names)
            self._line(f"// from {module} import {names} — no tiene equivalente directo en Java")
        self.env.warn("Los imports de Python no se traducen automáticamente al 100%.")

    def _visit_assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            self.env.warn("Asignación a múltiples targets (a = b = valor) — se genera solo la primera.")

        target = node.targets[0]
        value = node.value

        # ── Tuple unpacking: a, b = 1, 2 ──
        if isinstance(target, ast.Tuple):
            self._visit_tuple_unpack(target, value)
            return

        value_expr, value_type = self._expr(value)

        if isinstance(target, ast.Name):
            name = target.id
            if name in self._declared_vars:
                self._line(f"{name} = {value_expr};")
            else:
                self._declared_vars.add(name)
                t = self.env.current_scope.get_var(name) or value_type
                self._line(f"{t} {name} = {value_expr};")
        elif isinstance(target, ast.Subscript):
            container, ct = self._expr(target.value)
            idx, _ = self._expr(target.slice)
            if "Map" in str(ct) or "Map" in str(ct.name):
                self._line(f"{container}.put({idx}, {value_expr});")
            elif "List" in str(ct) or "List" in str(ct.name):
                self._line(f"{container}.set({idx}, {value_expr});")
            else:
                self._line(f"{container}[{idx}] = {value_expr};")
        elif isinstance(target, ast.Attribute):
            obj, _ = self._expr(target.value)
            self._line(f"{obj}.{target.attr} = {value_expr};")

    def _visit_tuple_unpack(self, target: ast.Tuple, value: ast.AST):
        """Handle a, b = 1, 2  or  a, b = func()  etc."""
        if isinstance(value, ast.Tuple):
            # Direct unpacking: a, b = 1, 2
            for tgt, val in zip(target.elts, value.elts):
                if isinstance(tgt, ast.Name):
                    val_expr, val_type = self._expr(val)
                    name = tgt.id
                    if name in self._declared_vars:
                        self._line(f"{name} = {val_expr};")
                    else:
                        self._declared_vars.add(name)
                        t = self.env.current_scope.get_var(name) or val_type
                        self._line(f"{t} {name} = {val_expr};")
        elif isinstance(value, ast.Call):
            # a, b = func() → can't really unpack in Java; generate temp + indexed access
            val_expr, _ = self._expr(value)
            tmp = "_unpack"
            self._line(f"Object[] {tmp} = (Object[]) {val_expr};")
            for i, tgt in enumerate(target.elts):
                if isinstance(tgt, ast.Name):
                    name = tgt.id
                    if name not in self._declared_vars:
                        self._declared_vars.add(name)
                        self._line(f"Object {name} = {tmp}[{i}];")
                    else:
                        self._line(f"{name} = {tmp}[{i}];")
        else:
            # Fallback: evaluate RHS once, index into it
            val_expr, _ = self._expr(value)
            for i, tgt in enumerate(target.elts):
                if isinstance(tgt, ast.Name):
                    name = tgt.id
                    if name not in self._declared_vars:
                        self._declared_vars.add(name)
                        self._line(f"Object {name} = {val_expr};")
                    else:
                        self._line(f"{name} = {val_expr};")

    def _visit_aug_assign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            op = self._aug_op(node.op)
            rhs, _ = self._expr(node.value)
            self._line(f"{name} {op}= {rhs};")
        elif isinstance(node.target, ast.Subscript):
            container, _ = self._expr(node.target.value)
            idx, _ = self._expr(node.target.slice)
            op = self._binop(node.op)
            rhs, _ = self._expr(node.value)
            self._line(f"{container}[{idx}] = {container}[{idx}] {op} {rhs};")
        elif isinstance(node.target, ast.Attribute):
            obj, _ = self._expr(node.target.value)
            attr = node.target.attr
            op = self._binop(node.op)
            rhs, _ = self._expr(node.value)
            self._line(f"{obj}.{attr} = {obj}.{attr} {op} {rhs};")

    def _visit_ann_assign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            var_type = self.env.current_scope.get_var(name) or Type("Object")
            if node.value:
                value_expr, _ = self._expr(node.value)
                self._line(f"{var_type} {name} = {value_expr};")
            else:
                self._line(f"{var_type} {name};")
            self._declared_vars.add(name)

    def _visit_expr_call(self, call: ast.Call):
        if isinstance(call.func, ast.Name) and call.func.id == "print":
            args = [self._expr(arg)[0] for arg in call.args]
            # Handle sep and end keyword args
            sep = '" "'
            for kw in call.keywords:
                if kw.arg == "sep":
                    sep, _ = self._expr(kw.value)
                elif kw.arg == "end":
                    pass  # we'd need System.out.print, handled below

            has_end = any(kw.arg == "end" for kw in call.keywords)
            print_fn = "System.out.print" if has_end else "System.out.println"

            if not args:
                self._line(f"{print_fn}();")
            elif len(args) == 1:
                self._line(f"{print_fn}({args[0]});")
            else:
                joined = f' + {sep} + '.join(f"String.valueOf({a})" for a in args)
                self._line(f"{print_fn}({joined});")
            if has_end:
                end_val = None
                for kw in call.keywords:
                    if kw.arg == "end":
                        end_val, _ = self._expr(kw.value)
                if end_val:
                    self._line(f"System.out.print({end_val});")
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
        iter_expr = node.iter

        # ── for i, v in enumerate(lst): ──
        if (isinstance(node.target, ast.Tuple)
            and isinstance(iter_expr, ast.Call)
            and isinstance(iter_expr.func, ast.Name)
            and iter_expr.func.id == "enumerate"):

            elts = node.target.elts
            if len(elts) == 2 and isinstance(elts[0], ast.Name) and isinstance(elts[1], ast.Name):
                idx_name = elts[0].id
                val_name = elts[1].id
                iterable_args = iter_expr.args
                iterable, _ = self._expr(iterable_args[0]) if iterable_args else ("/* ? */", Type("Object"))
                self._line(f"for (int {idx_name} = 0; {idx_name} < {iterable}.size(); {idx_name}++) {{")
                self._indent += 1
                self._line(f"var {val_name} = {iterable}.get({idx_name});")
                for stmt in node.body:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
                return

        # ── for k, v in dict.items(): ──
        if (isinstance(node.target, ast.Tuple)
            and isinstance(iter_expr, ast.Call)
            and isinstance(iter_expr.func, ast.Attribute)
            and iter_expr.func.attr == "items"):

            elts = node.target.elts
            if len(elts) == 2 and isinstance(elts[0], ast.Name) and isinstance(elts[1], ast.Name):
                k_name = elts[0].id
                v_name = elts[1].id
                dict_obj, _ = self._expr(iter_expr.func.value)
                self.imports.add("java.util.Map")
                self._line(f"for (Map.Entry<Object, Object> _entry : {dict_obj}.entrySet()) {{")
                self._indent += 1
                self._line(f"var {k_name} = _entry.getKey();")
                self._line(f"var {v_name} = _entry.getValue();")
                for stmt in node.body:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
                return

        # ── for x, y in zip(a, b): ──
        if (isinstance(node.target, ast.Tuple)
            and isinstance(iter_expr, ast.Call)
            and isinstance(iter_expr.func, ast.Name)
            and iter_expr.func.id == "zip"):

            elts = node.target.elts
            zip_args = iter_expr.args
            if len(elts) == 2 and len(zip_args) == 2:
                a_name = elts[0].id if isinstance(elts[0], ast.Name) else "_a"
                b_name = elts[1].id if isinstance(elts[1], ast.Name) else "_b"
                list_a, _ = self._expr(zip_args[0])
                list_b, _ = self._expr(zip_args[1])
                self._line(f"for (int _i = 0; _i < Math.min({list_a}.size(), {list_b}.size()); _i++) {{")
                self._indent += 1
                self._line(f"var {a_name} = {list_a}.get(_i);")
                self._line(f"var {b_name} = {list_b}.get(_i);")
                for stmt in node.body:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
                return

        # ── Simple target ──
        if not isinstance(node.target, ast.Name):
            self.env.warn("Bucle for con target complejo — se usó un tipo genérico.")
            # Try to handle tuple target generically
            if isinstance(node.target, ast.Tuple):
                iterable, _ = self._expr(iter_expr)
                self._line(f"for (Object _item : {iterable}) {{")
                self._indent += 1
                for i, elt in enumerate(node.target.elts):
                    if isinstance(elt, ast.Name):
                        self._line(f"var {elt.id} = ((Object[]) _item)[{i}];")
                for stmt in node.body:
                    self._visit_stmt(stmt)
                self._indent -= 1
                self._line("}")
                return
            self.env.error("Bucle for con target no soportado")
            return

        var_name = node.target.id

        # ── range() ──
        if (isinstance(iter_expr, ast.Call)
            and isinstance(iter_expr.func, ast.Name)
            and iter_expr.func.id == "range"):

            args = [self._expr(arg)[0] for arg in iter_expr.args]
            if len(args) == 1:
                self._line(f"for (int {var_name} = 0; {var_name} < {args[0]}; {var_name}++) {{")
            elif len(args) == 2:
                self._line(f"for (int {var_name} = {args[0]}; {var_name} < {args[1]}; {var_name}++) {{")
            elif len(args) == 3:
                self._line(f"for (int {var_name} = {args[0]}; {var_name} < {args[1]}; {var_name} += {args[2]}) {{")
            self.env.current_scope.define_var(var_name, Type("int"))
        else:
            # For-each loop
            iterable, t = self._expr(iter_expr)
            # Try to determine element type
            elem_type = "var"
            self._line(f"for ({elem_type} {var_name} : {iterable}) {{")
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
        # Handle decorators as comments
        for dec in node.decorator_list:
            dec_expr, _ = self._expr(dec)
            self._line(f"// @{dec_expr}")

        self.env.push_scope(name=node.name)
        saved_lines = self._current_lines
        saved_indent = self._indent
        saved_declared = self._declared_vars.copy()

        body_lines = []
        self._current_lines = body_lines
        self._indent = 0
        self._in_function = True
        self._declared_vars = set()

        params = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name == "self":
                continue
            # Check for annotation
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                java_type = self._annotation_to_java(arg.annotation.id)
            else:
                java_type = "Object"
            params.append((java_type, arg_name))
            self.env.current_scope.define_var(arg_name, Type(java_type))
            self._declared_vars.add(arg_name)

        # Handle *args and **kwargs
        if node.args.vararg:
            self.env.warn(f"*{node.args.vararg.arg}: Java no soporta *args directamente. Se tradujo como Object[].")
            params.append(("Object...", node.args.vararg.arg))
        if node.args.kwarg:
            self.env.warn(f"**{node.args.kwarg.arg}: Java no soporta **kwargs. Se omitió.")

        # Handle default values as comments
        defaults = node.args.defaults
        if defaults:
            num_no_default = len(node.args.args) - len(defaults)
            for i, default in enumerate(defaults):
                arg_idx = num_no_default + i
                if arg_idx < len(node.args.args):
                    arg_name = node.args.args[arg_idx].arg
                    default_expr, _ = self._expr(default)
                    self.env.warn(f"Parámetro '{arg_name}' tiene valor por defecto = {default_expr}. Java no soporta valores por defecto; se requiere sobrecarga.")

        # Infer return type
        return_type = "void"
        if node.returns and isinstance(node.returns, ast.Name):
            return_type = self._annotation_to_java(node.returns.id)
        elif self._has_return_value(node):
            return_type = "Object"

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
        self._declared_vars = saved_declared
        self.env.pop_scope()

    def _has_return_value(self, node: ast.FunctionDef) -> bool:
        """Check recursively if the function has a return statement with a value."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                return True
        return False

    def _annotation_to_java(self, type_name: str) -> str:
        mapping = {
            "int": "int",
            "float": "double",
            "str": "String",
            "bool": "boolean",
            "list": "List<Object>",
            "dict": "Map<Object, Object>",
            "set": "Set<Object>",
            "None": "void",
        }
        return mapping.get(type_name, type_name)

    def _visit_class(self, node: ast.ClassDef):
        saved_lines = self._current_lines
        saved_indent = self._indent
        saved_declared = self._declared_vars.copy()

        class_lines = []
        self._current_lines = class_lines
        self._indent = 1
        self._declared_vars = set()

        # Handle decorators
        for dec in node.decorator_list:
            dec_expr, _ = self._expr(dec)
            class_lines.append(f"// @{dec_expr}")

        # Support inheritance
        extends = ""
        if node.bases:
            base_name = node.bases[0].id if isinstance(node.bases[0], ast.Name) else "Object"
            extends = f" extends {base_name}"

        class_lines.append(f"static class {node.name}{extends} {{")

        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name == "__init__":
                    # Constructor
                    params = []
                    for arg in stmt.args.args[1:]:  # skip self
                        if arg.annotation and isinstance(arg.annotation, ast.Name):
                            java_type = self._annotation_to_java(arg.annotation.id)
                        else:
                            java_type = "Object"
                        params.append(f"{java_type} {arg.arg}")
                        self._declared_vars.add(arg.arg)
                    self._line(f"public {node.name}({', '.join(params)}) {{")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
                elif stmt.name == "__str__" or stmt.name == "__repr__":
                    self._line("@Override")
                    self._line("public String toString() {")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
                elif stmt.name == "__eq__":
                    self._line("@Override")
                    self._line("public boolean equals(Object other) {")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
                else:
                    params = []
                    for arg in stmt.args.args[1:]:  # skip self
                        if arg.annotation and isinstance(arg.annotation, ast.Name):
                            java_type = self._annotation_to_java(arg.annotation.id)
                        else:
                            java_type = "Object"
                        params.append(f"{java_type} {arg.arg}")
                    ret_type = "Object" if self._has_return_value(stmt) else "void"
                    self._line(f"public {ret_type} {stmt.name}({', '.join(params)}) {{")
                    self._indent += 1
                    for s in stmt.body:
                        self._visit_stmt(s)
                    self._indent -= 1
                    self._line("}")
            elif isinstance(stmt, ast.Assign):
                # Class fields
                if isinstance(stmt.targets[0], ast.Name):
                    val, vt = self._expr(stmt.value)
                    self._line(f"public {vt} {stmt.targets[0].id} = {val};")
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                # Docstring
                for docline in stmt.value.value.strip().split("\n"):
                    self._line(f"// {docline.strip()}")

        class_lines.append("}")
        self.classes.append("\n".join(class_lines))

        self._current_lines = saved_lines
        self._indent = saved_indent
        self._declared_vars = saved_declared

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
            if handler.type:
                ex_type = self._python_exception_to_java(
                    handler.type.id if isinstance(handler.type, ast.Name) else "Exception"
                )
            else:
                ex_type = "Exception"
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

    def _python_exception_to_java(self, name: str) -> str:
        mapping = {
            "ValueError": "IllegalArgumentException",
            "TypeError": "ClassCastException",
            "IndexError": "IndexOutOfBoundsException",
            "KeyError": "java.util.NoSuchElementException",
            "FileNotFoundError": "java.io.FileNotFoundException",
            "IOError": "java.io.IOException",
            "OSError": "java.io.IOException",
            "ZeroDivisionError": "ArithmeticException",
            "AttributeError": "NoSuchFieldException",
            "RuntimeError": "RuntimeException",
            "StopIteration": "java.util.NoSuchElementException",
            "NotImplementedError": "UnsupportedOperationException",
            "OverflowError": "ArithmeticException",
        }
        return mapping.get(name, "Exception")

    # ── Expression visitors ─────────────────────────────────────────

    def _expr(self, node: Optional[ast.AST]) -> Tuple[str, Type]:
        if node is None:
            return "null", Type("Object")

        # ── Constants ──
        if isinstance(node, ast.Constant):
            return self._expr_constant(node)

        # ── Names ──
        if isinstance(node, ast.Name):
            return self._expr_name(node)

        # ── Binary operations ──
        if isinstance(node, ast.BinOp):
            return self._expr_binop(node)

        # ── Unary operations ──
        if isinstance(node, ast.UnaryOp):
            return self._expr_unaryop(node)

        # ── Comparisons (with chaining support) ──
        if isinstance(node, ast.Compare):
            return self._expr_compare(node)

        # ── Boolean operations ──
        if isinstance(node, ast.BoolOp):
            op = " && " if isinstance(node.op, ast.And) else " || "
            values = [self._expr(v)[0] for v in node.values]
            return f"({op.join(values)})", Type("boolean")

        # ── Function / method calls ──
        if isinstance(node, ast.Call):
            return self._call(node)

        # ── Lists ──
        if isinstance(node, ast.List):
            return self._expr_list(node)

        # ── Dicts (with data) ──
        if isinstance(node, ast.Dict):
            return self._expr_dict(node)

        # ── Sets ──
        if isinstance(node, ast.Set):
            return self._expr_set(node)

        # ── Tuples ──
        if isinstance(node, ast.Tuple):
            return self._expr_list(node)  # Treat tuples as lists in Java

        # ── Attribute access ──
        if isinstance(node, ast.Attribute):
            val, _ = self._expr(node.value)
            if val == "this":
                return f"this.{node.attr}", Type("Object")
            return f"{val}.{node.attr}", Type("Object")

        # ── Subscript (with negative index support) ──
        if isinstance(node, ast.Subscript):
            return self._expr_subscript(node)

        # ── F-strings ──
        if isinstance(node, ast.JoinedStr):
            return self._expr_fstring(node)

        # ── Ternary: x if cond else y ──
        if isinstance(node, ast.IfExp):
            cond, _ = self._expr(node.test)
            body, bt = self._expr(node.body)
            orelse, _ = self._expr(node.orelse)
            return f"(({cond}) ? {body} : {orelse})", bt

        # ── List comprehension ──
        if isinstance(node, ast.ListComp):
            return self._expr_listcomp(node)

        # ── Lambda ──
        if isinstance(node, ast.Lambda):
            return self._expr_lambda(node)

        # ── Starred (*args in call) ──
        if isinstance(node, ast.Starred):
            inner, t = self._expr(node.value)
            return inner, t  # Just pass through

        # ── Slice ──
        if isinstance(node, ast.Slice):
            return self._expr_slice(node)

        self.env.warn(f"Expresión '{type(node).__name__}' no soportada completamente.")
        return "/* no traducido */", Type("Object")

    def _expr_constant(self, node: ast.Constant) -> Tuple[str, Type]:
        if node.value is None:
            return "null", Type("Object")
        if isinstance(node.value, bool):
            return ("true" if node.value else "false"), Type("boolean")
        if isinstance(node.value, int):
            return str(node.value), Type("int")
        if isinstance(node.value, float):
            return str(node.value), Type("double")
        if isinstance(node.value, str):
            escaped = (
                node.value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\t", "\\t")
                .replace("\r", "\\r")
            )
            return f'"{escaped}"', Type("String")
        return "null", Type("Object")

    def _expr_name(self, node: ast.Name) -> Tuple[str, Type]:
        # Built-in constants
        if node.id == "True":
            return "true", Type("boolean")
        if node.id == "False":
            return "false", Type("boolean")
        if node.id == "None":
            return "null", Type("Object")
        if node.id == "self":
            return "this", Type("Object")

        t = self.env.current_scope.get_var(node.id) or Type("Object")
        return node.id, t

    def _expr_binop(self, node: ast.BinOp) -> Tuple[str, Type]:
        left, lt = self._expr(node.left)
        right, rt = self._expr(node.right)

        if isinstance(node.op, ast.Pow):
            return f"Math.pow({left}, {right})", Type("double")

        if isinstance(node.op, ast.FloorDiv):
            return f"Math.floorDiv({left}, {right})", Type("int")

        # String multiplication: "abc" * 3
        if isinstance(node.op, ast.Mult):
            if lt.name == "String":
                return f"{left}.repeat({right})", Type("String")
            if rt.name == "String":
                return f"{right}.repeat({left})", Type("String")

        # String concatenation with +
        if isinstance(node.op, ast.Add):
            if lt.name == "String" or rt.name == "String":
                # Ensure non-string side is converted
                if lt.name != "String":
                    left = f"String.valueOf({left})"
                if rt.name != "String":
                    right = f"String.valueOf({right})"
                return f"({left} + {right})", Type("String")

        # Integer division: int / int should still use /
        if isinstance(node.op, ast.Div):
            if lt.name == "int" and rt.name == "int":
                return f"((double) {left} / {right})", Type("double")

        op = self._binop(node.op)
        result_type = lt if lt.name != "Object" else (rt if rt.name != "Object" else Type("int"))
        if lt.name == "double" or rt.name == "double":
            result_type = Type("double")
        return f"({left} {op} {right})", result_type

    def _expr_unaryop(self, node: ast.UnaryOp) -> Tuple[str, Type]:
        operand, t = self._expr(node.operand)
        if isinstance(node.op, ast.USub):
            return f"(-{operand})", t
        if isinstance(node.op, ast.UAdd):
            return f"(+{operand})", t
        if isinstance(node.op, ast.Not):
            return f"(!({operand}))", Type("boolean")
        if isinstance(node.op, ast.Invert):
            return f"(~{operand})", Type("int")
        return operand, t

    def _expr_compare(self, node: ast.Compare) -> Tuple[str, Type]:
        """Handle chained comparisons: 0 < x < 10 → (0 < x && x < 10)"""
        parts = []
        left, _ = self._expr(node.left)

        for op, comparator in zip(node.ops, node.comparators):
            right, _ = self._expr(comparator)

            if isinstance(op, ast.In):
                parts.append(f"{right}.contains({left})")
            elif isinstance(op, ast.NotIn):
                parts.append(f"!{right}.contains({left})")
            elif isinstance(op, ast.Is):
                parts.append(f"({left} == {right})")
            elif isinstance(op, ast.IsNot):
                parts.append(f"({left} != {right})")
            else:
                cmp = self._cmp_op(op)
                # Use .equals() for string comparison with == and !=
                if cmp == "==" and (self._is_string_expr(node.left) or self._is_string_comparator(comparator)):
                    parts.append(f"{left}.equals({right})")
                elif cmp == "!=" and (self._is_string_expr(node.left) or self._is_string_comparator(comparator)):
                    parts.append(f"!{left}.equals({right})")
                else:
                    parts.append(f"({left} {cmp} {right})")

            left = right  # For chained comparisons

        if len(parts) == 1:
            return parts[0], Type("boolean")
        return f"({' && '.join(parts)})", Type("boolean")

    def _is_string_expr(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if isinstance(node, ast.Name):
            t = self.env.current_scope.get_var(node.id)
            return t is not None and t.name == "String"
        return False

    def _is_string_comparator(self, node: ast.AST) -> bool:
        return self._is_string_expr(node)

    def _expr_list(self, node) -> Tuple[str, Type]:
        """Handle both ast.List and ast.Tuple."""
        self.imports.add("java.util.ArrayList")
        self.imports.add("java.util.Arrays")
        self.imports.add("java.util.List")
        elements = ", ".join(self._expr(elt)[0] for elt in node.elts)
        if elements:
            return f"new ArrayList<>(Arrays.asList({elements}))", Type("java.util.List")
        return "new ArrayList<>()", Type("java.util.List")

    def _expr_dict(self, node: ast.Dict) -> Tuple[str, Type]:
        """Handle dict literals with actual data."""
        self.imports.add("java.util.HashMap")
        self.imports.add("java.util.Map")

        if not node.keys:
            return "new HashMap<>()", Type("java.util.Map")

        # Use Map.of() for small dicts (<=10 entries), otherwise HashMap with puts
        if len(node.keys) <= 10 and all(k is not None for k in node.keys):
            pairs = []
            for k, v in zip(node.keys, node.values):
                k_expr, _ = self._expr(k)
                v_expr, _ = self._expr(v)
                pairs.append(f"{k_expr}, {v_expr}")
            return f"new HashMap<>(Map.of({', '.join(pairs)}))", Type("java.util.Map")
        else:
            # For large dicts we'd need a helper; for now use Map.of with a warning
            self.env.warn("Diccionario grande: Map.of() soporta hasta 10 pares. Se genera igualmente.")
            pairs = []
            for k, v in zip(node.keys, node.values):
                if k is None:
                    continue
                k_expr, _ = self._expr(k)
                v_expr, _ = self._expr(v)
                pairs.append(f"{k_expr}, {v_expr}")
            return f"new HashMap<>(Map.of({', '.join(pairs)}))", Type("java.util.Map")

    def _expr_set(self, node: ast.Set) -> Tuple[str, Type]:
        self.imports.add("java.util.HashSet")
        self.imports.add("java.util.Arrays")
        self.imports.add("java.util.Set")
        elements = ", ".join(self._expr(elt)[0] for elt in node.elts)
        if elements:
            return f"new HashSet<>(Arrays.asList({elements}))", Type("java.util.Set")
        return "new HashSet<>()", Type("java.util.Set")

    def _expr_subscript(self, node: ast.Subscript) -> Tuple[str, Type]:
        val, t = self._expr(node.value)
        
        # Handle slicing: lst[1:3]
        if isinstance(node.slice, ast.Slice):
            lower = self._expr(node.slice.lower)[0] if node.slice.lower else "0"
            upper = self._expr(node.slice.upper)[0] if node.slice.upper else f"{val}.size()"
            return f"{val}.subList({lower}, {upper})", t

        idx, _ = self._expr(node.slice)

        # Handle negative indexing
        if isinstance(node.slice, ast.UnaryOp) and isinstance(node.slice.op, ast.USub):
            inner_idx, _ = self._expr(node.slice.operand)
            if "List" in str(t.name) or t.name == "java.util.List":
                return f"{val}.get({val}.size() - {inner_idx})", Type("Object")
            elif t.name == "String":
                return f"{val}.charAt({val}.length() - {inner_idx})", Type("char")
            return f"{val}[{val}.length - {inner_idx}]", Type("Object")

        if "List" in str(t.name) or t.name == "java.util.List":
            return f"{val}.get({idx})", Type("Object")
        if "Map" in str(t.name) or t.name == "java.util.Map":
            return f"{val}.get({idx})", Type("Object")
        if t.name == "String":
            return f"{val}.charAt({idx})", Type("char")
        return f"{val}[{idx}]", Type("Object")

    def _expr_fstring(self, node: ast.JoinedStr) -> Tuple[str, Type]:
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                escaped = str(value.value).replace('"', '\\"')
                parts.append(f'"{escaped}"')
            elif isinstance(value, ast.FormattedValue):
                e, _ = self._expr(value.value)
                parts.append(f"String.valueOf({e})")
        return " + ".join(parts) if parts else '""', Type("String")

    def _expr_listcomp(self, node: ast.ListComp) -> Tuple[str, Type]:
        """
        [expr for var in iter if cond]
        → generates an inline helper or an IIFE-like pattern.
        For simplicity, we generate a method and call it.
        """
        self.imports.add("java.util.ArrayList")
        self.imports.add("java.util.List")

        # Generate a helper method
        self._lambda_counter += 1
        method_name = f"_listComp{self._lambda_counter}"

        # Build the method body
        body_lines = []
        body_lines.append("    List<Object> _result = new ArrayList<>();")

        # Only handle single generator for now
        gen = node.generators[0]
        if isinstance(gen.target, ast.Name):
            var_name = gen.target.id
        else:
            var_name = "_item"

        iter_expr, _ = self._expr(gen.iter)

        # Check if it's a range call
        if (isinstance(gen.iter, ast.Call)
            and isinstance(gen.iter.func, ast.Name)
            and gen.iter.func.id == "range"):
            range_args = [self._expr(a)[0] for a in gen.iter.args]
            if len(range_args) == 1:
                body_lines.append(f"    for (int {var_name} = 0; {var_name} < {range_args[0]}; {var_name}++) {{")
            elif len(range_args) == 2:
                body_lines.append(f"    for (int {var_name} = {range_args[0]}; {var_name} < {range_args[1]}; {var_name}++) {{")
            else:
                body_lines.append(f"    for (int {var_name} = {range_args[0]}; {var_name} < {range_args[1]}; {var_name} += {range_args[2]}) {{")
        else:
            body_lines.append(f"    for (var {var_name} : {iter_expr}) {{")

        # Conditions
        conditions = gen.ifs
        if conditions:
            cond_parts = [self._expr(c)[0] for c in conditions]
            combined = " && ".join(cond_parts)
            body_lines.append(f"        if ({combined}) {{")
            elt_expr, _ = self._expr(node.elt)
            body_lines.append(f"            _result.add({elt_expr});")
            body_lines.append("        }")
        else:
            elt_expr, _ = self._expr(node.elt)
            body_lines.append(f"        _result.add({elt_expr});")

        body_lines.append("    }")
        body_lines.append("    return _result;")

        self.methods.append({
            "name": method_name,
            "params": [],
            "body": body_lines,
            "return_type": "List<Object>",
        })

        return f"{method_name}()", Type("java.util.List")

    def _expr_lambda(self, node: ast.Lambda) -> Tuple[str, Type]:
        """
        lambda x: x + 1 → generates a helper method and returns its name.
        """
        self._lambda_counter += 1
        method_name = f"_lambda{self._lambda_counter}"

        body_expr, ret_type = self._expr(node.body)

        params = []
        for arg in node.args.args:
            params.append(("Object", arg.arg))

        body_lines = [f"    return {body_expr};"]

        self.methods.append({
            "name": method_name,
            "params": params,
            "body": body_lines,
            "return_type": "Object",
        })

        return method_name, Type("Object")

    def _expr_slice(self, node: ast.Slice) -> Tuple[str, Type]:
        # This is typically handled inside _expr_subscript
        parts = []
        if node.lower:
            parts.append(self._expr(node.lower)[0])
        else:
            parts.append("0")
        if node.upper:
            parts.append(self._expr(node.upper)[0])
        return ":".join(parts), Type("Object")

    # ── Call handling ───────────────────────────────────────────────

    def _call(self, node: ast.Call) -> Tuple[str, Type]:
        if isinstance(node.func, ast.Name):
            return self._call_builtin(node)
        if isinstance(node.func, ast.Attribute):
            return self._call_method(node)
        # Callable variable or complex expression
        func_expr, _ = self._expr(node.func)
        args = [self._expr(arg)[0] for arg in node.args]
        return f"{func_expr}({', '.join(args)})", Type("Object")

    def _call_builtin(self, node: ast.Call) -> Tuple[str, Type]:
        name = node.func.id
        args = [self._expr(arg)[0] for arg in node.args]

        # ── print ──
        if name == "print":
            return f"System.out.println({args[0] if args else ''})", Type("void")

        # ── input ──
        if name == "input":
            self.env.needs_scanner = True
            if args:
                return f'(System.out.print({args[0]}), scanner.nextLine()).toString()', Type("String")
            return "scanner.nextLine()", Type("String")

        # ── Type casting ──
        if name == "int":
            if args:
                return f"Integer.parseInt(String.valueOf({args[0]}))", Type("int")
            return "0", Type("int")
        if name == "float":
            if args:
                return f"Double.parseDouble(String.valueOf({args[0]}))", Type("double")
            return "0.0", Type("double")
        if name == "str":
            return f"String.valueOf({args[0]})" if args else '""', Type("String")
        if name == "bool":
            return f"Boolean.valueOf({args[0]})" if args else "false", Type("boolean")

        # ── len ──
        if name == "len":
            if args:
                return f"{args[0]}.size()", Type("int")
            return "0", Type("int")

        # ── abs, min, max, round, sum ──
        if name == "abs":
            return f"Math.abs({args[0]})", Type("double")
        if name == "min":
            if len(args) == 2:
                return f"Math.min({args[0]}, {args[1]})", Type("int")
            self.imports.add("java.util.Collections")
            return f"Collections.min({args[0]})", Type("Object")
        if name == "max":
            if len(args) == 2:
                return f"Math.max({args[0]}, {args[1]})", Type("int")
            self.imports.add("java.util.Collections")
            return f"Collections.max({args[0]})", Type("Object")
        if name == "round":
            return f"Math.round({args[0]})", Type("long")
        if name == "sum":
            # No direct Java equivalent; approximate
            return f"/* sum */ {args[0]}.stream().mapToInt(Integer::intValue).sum()", Type("int")

        # ── sorted ──
        if name == "sorted":
            self.imports.add("java.util.Collections")
            self.imports.add("java.util.ArrayList")
            self.imports.add("java.util.List")
            if args:
                return f"new ArrayList<>({args[0]}) {{ {{ Collections.sort(this); }} }}", Type("java.util.List")
            return "new ArrayList<>()", Type("java.util.List")

        # ── reversed ──
        if name == "reversed":
            self.imports.add("java.util.Collections")
            self.imports.add("java.util.ArrayList")
            if args:
                return f"new ArrayList<>({args[0]}) {{ {{ Collections.reverse(this); }} }}", Type("java.util.List")

        # ── isinstance ──
        if name == "isinstance" and len(args) == 2:
            return f"({args[0]} instanceof {args[1]})", Type("boolean")

        # ── type ──
        if name == "type":
            return f"{args[0]}.getClass()", Type("Class")

        # ── range ──
        if name == "range":
            # range is typically used in for-loops, but if used standalone
            self.env.warn("range() usado fuera de un bucle for; aproximación generada.")
            return f"/* range({', '.join(args)}) */", Type("Object")

        # ── enumerate ──
        if name == "enumerate":
            self.env.warn("enumerate() fuera de un bucle for; se requiere manejo manual.")
            return f"/* enumerate({', '.join(args)}) */", Type("Object")

        # ── list(), dict(), set(), tuple() constructors ──
        if name == "list":
            self.imports.add("java.util.ArrayList")
            if args:
                return f"new ArrayList<>({args[0]})", Type("java.util.List")
            return "new ArrayList<>()", Type("java.util.List")
        if name == "dict":
            self.imports.add("java.util.HashMap")
            return "new HashMap<>()", Type("java.util.Map")
        if name == "set":
            self.imports.add("java.util.HashSet")
            if args:
                return f"new HashSet<>({args[0]})", Type("java.util.Set")
            return "new HashSet<>()", Type("java.util.Set")
        if name == "tuple":
            self.imports.add("java.util.ArrayList")
            if args:
                return f"new ArrayList<>({args[0]})", Type("java.util.List")
            return "new ArrayList<>()", Type("java.util.List")

        # ── User-defined function call ──
        return f"{name}({', '.join(args)})", Type("Object")

    def _call_method(self, node: ast.Call) -> Tuple[str, Type]:
        obj, obj_type = self._expr(node.func.value)
        method = node.func.attr
        args = [self._expr(arg)[0] for arg in node.args]

        # ── String methods ──
        string_methods = {
            "upper": ("toUpperCase", [], Type("String")),
            "lower": ("toLowerCase", [], Type("String")),
            "strip": ("trim", [], Type("String")),
            "lstrip": ("stripLeading", [], Type("String")),
            "rstrip": ("stripTrailing", [], Type("String")),
            "replace": ("replace", args, Type("String")),
            "split": ("split", args if args else ['" "'], Type("String[]")),
            "join": (None, args, Type("String")),  # Special handling
            "startswith": ("startsWith", args, Type("boolean")),
            "endswith": ("endsWith", args, Type("boolean")),
            "find": ("indexOf", args, Type("int")),
            "index": ("indexOf", args, Type("int")),
            "count": (None, args, Type("int")),  # Special handling
            "capitalize": (None, [], Type("String")),  # Special handling
            "title": (None, [], Type("String")),  # Special handling
            "isdigit": ("matches", ['"\\\\d+"'], Type("boolean")),
            "isalpha": ("matches", ['"[a-zA-Z]+"'], Type("boolean")),
            "format": (None, args, Type("String")),  # Special handling
        }

        if method in string_methods:
            java_method, java_args, ret_type = string_methods[method]

            if method == "join":
                self.imports.add("java.util.stream.Collectors")
                if args:
                    return f"String.join({obj}, {args[0]})", ret_type
                return f"String.join({obj})", ret_type

            if method == "count":
                if args:
                    return f"({obj}.length() - {obj}.replace({args[0]}, \"\").length()) / {args[0]}.length()", ret_type

            if method == "capitalize":
                return f"({obj}.substring(0, 1).toUpperCase() + {obj}.substring(1))", ret_type

            if method == "title":
                return f"/* title() */ {obj}", ret_type

            if method == "format":
                return f"String.format({obj}, {', '.join(args)})", ret_type

            if java_method:
                return f"{obj}.{java_method}({', '.join(java_args if java_args != args else args)})", ret_type

        # ── List methods ──
        list_methods = {
            "append": ("add", args, Type("void")),
            "extend": ("addAll", args, Type("void")),
            "insert": ("add", args, Type("void")),  # add(index, element) works in Java
            "remove": ("remove", args, Type("void")),
            "pop": (None, args, Type("Object")),  # Special handling
            "clear": ("clear", [], Type("void")),
            "index": ("indexOf", args, Type("int")),
            "copy": (None, [], Type("java.util.List")),
            "sort": (None, [], Type("void")),
            "reverse": (None, [], Type("void")),
            "count": (None, args, Type("int")),
        }

        if method in list_methods:
            java_method, java_args, ret_type = list_methods[method]

            if method == "pop":
                if args:
                    return f"{obj}.remove({args[0]})", ret_type
                return f"{obj}.remove({obj}.size() - 1)", ret_type

            if method == "copy":
                self.imports.add("java.util.ArrayList")
                return f"new ArrayList<>({obj})", ret_type

            if method == "sort":
                self.imports.add("java.util.Collections")
                return f"Collections.sort({obj})", ret_type

            if method == "reverse":
                self.imports.add("java.util.Collections")
                return f"Collections.reverse({obj})", ret_type

            if method == "count":
                self.imports.add("java.util.Collections")
                return f"Collections.frequency({obj}, {args[0]})" if args else "0", ret_type

            if java_method:
                return f"{obj}.{java_method}({', '.join(java_args if java_args != args else args)})", ret_type

        # ── Dict methods ──
        dict_methods = {
            "get": (None, args, Type("Object")),
            "keys": ("keySet", [], Type("Set")),
            "values": ("values", [], Type("Collection")),
            "items": ("entrySet", [], Type("Set")),
            "update": ("putAll", args, Type("void")),
            "pop": ("remove", args, Type("Object")),
            "setdefault": (None, args, Type("Object")),
            "clear": ("clear", [], Type("void")),
        }

        if method in dict_methods:
            java_method, java_args, ret_type = dict_methods[method]

            if method == "get":
                if len(args) >= 2:
                    return f"{obj}.getOrDefault({args[0]}, {args[1]})", ret_type
                elif len(args) == 1:
                    return f"{obj}.get({args[0]})", ret_type
                return f"{obj}.get(null)", ret_type

            if method == "setdefault":
                if len(args) >= 2:
                    return f"{obj}.putIfAbsent({args[0]}, {args[1]})", ret_type
                return f"{obj}.putIfAbsent({args[0]}, null)", ret_type

            if java_method:
                return f"{obj}.{java_method}({', '.join(java_args if java_args != args else args)})", ret_type

        # ── Fallback: pass through ──
        return f"{obj}.{method}({', '.join(args)})", Type("Object")

    # ── Helpers ─────────────────────────────────────────────────────

    def _line(self, content: str):
        self._current_lines.append(" " * (self._indent * 4) + content)

    def _safe_class_name(self, name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name)
        if not cleaned:
            return "Program"
        if cleaned[0].isdigit():
            cleaned = "Program" + cleaned
        parts = re.split(r"[_\s]+", cleaned)
        return "".join(p.capitalize() for p in parts if p)

    def _binop(self, op: ast.operator) -> str:
        ops = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "/",
            ast.Mod: "%",
            ast.LShift: "<<",
            ast.RShift: ">>",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.BitAnd: "&",
        }
        return ops.get(type(op), "+")

    def _aug_op(self, op: ast.operator) -> str:
        return self._binop(op)

    def _cmp_op(self, op: ast.cmpop) -> str:
        ops = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        return ops.get(type(op), "==")
