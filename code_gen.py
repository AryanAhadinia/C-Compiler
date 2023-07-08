class CodeGenerator:
    def __init__(self, parser, lexer):
        self.parser = parser
        self.lexer = lexer

        self.semantic_stack = list()
        self.scope_stack = [
            {
                "output": {
                    "addr": 0,
                    "type": "int",
                    "params": [{"id": "a", "type": "int"}],
                }
            }
        ]
        self.codes_generated = {
            0: ("ASSIGN", "#4", 0, None),
            1: ("JP", 2, None, None),
        }
        self.break_scope = list()
        self.break_stack = list()

        self.program_line = len(self.codes_generated)
        self.temp_pointer = 500

        self.last_id = None
        self.last_num = None
        self.last_type = None
        self.in_loop = False

    def get_var_scope(self, var) -> int:
        for i, scope in reversed(list(enumerate(self.scope_stack))):
            if var in scope:
                return i, scope[var]["addr"]
        return -1, None

    def add_var_to_scope(self, var, scope_indicator, length=1):
        address = self.get_temp(len=length)
        self.scope_stack[scope_indicator][var] = dict()
        self.scope_stack[scope_indicator][var]["addr"] = address
        return address

    def add_code_line(self, code):
        self.codes_generated[int(self.program_line)] = code
        self.program_line += 1

    def store_code_line(self, code, line):
        if isinstance(line, str):
            if line.startswith("#") or line.startswith("@"):
                line = line[1:]
        self.codes_generated[int(line)] = code

    def code_gen(self, action):
        if action[0] == "#":
            action = action[1:]

        if action == "get_temp":
            self.get_temp()
        elif action == "p_id":
            self.p_id(self.last_id)
        elif action == "p_num":
            self.p_num(self.last_num)
        elif action == "add":
            self.add()
        elif action == "sub":
            self.sub()
        elif action == "mult":
            self.mult()
        elif action == "arithmetic":
            self.arithmetic()
        elif action == "assign":
            self.assign()
        elif action == "eq":
            self.eq()
        elif action == "lt":
            self.lt()
        elif action == "declare_var":
            self.declare_var()
        elif action == "declare_array":
            self.declare_array()
        elif action == "compare":
            self.compare()
        elif action == "label":
            self.label()
        elif action == "save":
            self.save()
        elif action == "jp":
            self.jp()
        elif action == "jpf":
            self.jpf()
        elif action == "jpf_save":
            self.jpf_save()
        elif action == "call":
            # TODO
            self.output()
        elif action == "array_index":
            self.array_index()
        elif action == "exp_end":
            self.exp_end()
        elif action == "break":
            self.save_break()
        elif action == "jp_break":
            self.jp_break()
        elif action == "scope_enter":
            self.scope_enter()
        elif action == "scope_exit":
            self.scope_exit()
        elif action == "loop_start":
            self.loop_start()
        elif action == "loop_end":
            self.loop_end()
        elif action == "call":
            pass
        elif action == "add_arg":
            pass
        else:
            raise Exception("Invalid action")

    def get_temp(self, len=1, size=4):
        address = self.temp_pointer
        self.temp_pointer += len * size
        return address

    def p_id(self, id):
        if self.last_type is not None:
            self.semantic_stack.append(id)
        else:
            scope, address = self.get_var_scope(id)
            self.semantic_stack.append(str(address))

    def p_num(self, num):
        self.semantic_stack.append("#" + str(num))

    def add(self):
        self.semantic_stack.append("ADD")

    def sub(self):
        self.semantic_stack.append("SUB")

    def mult(self):
        self.semantic_stack.append("MULT")

    def arithmetic(self):
        right = self.semantic_stack.pop()
        op = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line((op, left, right, result))
        self.semantic_stack.append(result)

    def assign(self):
        right = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        self.add_code_line(("ASSIGN", right, left, None))
        self.semantic_stack.append(left)

    def eq(self):
        self.semantic_stack.append("EQ")

    def lt(self):
        self.semantic_stack.append("LT")

    def declare_var(self):
        id = self.semantic_stack.pop()
        address = self.add_var_to_scope(id, -1)
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.semantic_stack.append(address)
        self.scope_stack[-1][self.last_id] = dict()
        self.scope_stack[-1][self.last_id]["addr"] = address
        self.scope_stack[-1][self.last_id]["type"] = self.last_type
        self.last_type = None

    def declare_array(self):
        length = int(self.semantic_stack.pop()[1:])
        id = self.semantic_stack.pop()
        address = self.add_var_to_scope(id, -1, length + 1)
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.semantic_stack.append(address)
        self.scope_stack[-1][self.last_id] = dict()
        self.scope_stack[-1][self.last_id]["addr"] = address
        self.scope_stack[-1][self.last_id]["type"] = "array"
        self.last_type = None

    def compare(self):
        right = self.semantic_stack.pop()
        op = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line((op, left, right, result))
        self.semantic_stack.append(result)

    def label(self):
        self.semantic_stack.append(self.program_line)
        self.break_scope.append(len(self.scope_stack))

    def save(self):
        self.label()
        self.program_line += 1

    def jp(self):
        code_line = self.semantic_stack.pop()
        self.store_code_line(("JP", self.program_line, None, None), code_line)

    def jpf(self):
        condition = self.semantic_stack.pop()
        jump_address = self.semantic_stack.pop()
        self.add_code_line(("JPF", condition, jump_address, None))

    def jpf_save(self):
        code_line = self.semantic_stack.pop()
        condition = self.semantic_stack.pop()
        self.store_code_line(("JPF", condition, self.program_line + 1, None), code_line)
        self.save()

    def array_index(self):
        index = self.semantic_stack.pop()
        array = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line(("MULT", index, "#4", result))
        self.add_code_line(("ADD", f"#{array}", result, result))
        self.semantic_stack.append("@" + str(result))

    def exp_end(self):
        self.semantic_stack.pop()
        self.last_num = None
        self.last_id = None
        self.last_type = None

    def save_break(self):
        self.break_stack.append((self.break_scope[-1], self.program_line))
        self.program_line += 1

    def jp_break(self):
        for i, (scope, line) in enumerate(reversed(self.break_stack)):
            if scope == self.break_scope[-1]:
                self.codes_generated[line] = (
                    "JP",
                    f"{self.program_line+1}",
                    None,
                    None,
                )
                self.break_stack.pop(len(self.break_stack) - 1 - i)
        self.break_scope.pop()

    def scope_enter(self):
        self.last_num = None
        self.last_id = None
        self.last_type = None
        self.scope_stack.append({})

    def scope_exit(self):
        self.last_num = None
        self.last_id = None
        self.last_type = None
        self.scope_stack.pop()

    def loop_start(self):
        self.in_loop = True

    def loop_end(self):
        self.in_loop = False

    def output(self):
        value = self.semantic_stack.pop()
        self.add_code_line(("PRINT", value, None, None))

    def to_code_string(self, path):
        self.codes_generated = dict(sorted(self.codes_generated.items()))
        with open(path, "w") as f:
            for i, code_line in self.codes_generated.items():
                output = f"{i}\t("
                for code in code_line:
                    if code is not None:
                        output += f"{code}, "
                    else:
                        output += ", "
                output = output[:-2] + ")\n"
                f.write(output)
