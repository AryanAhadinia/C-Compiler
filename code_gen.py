class CodeGenerator:
    def __init__(self, parser, lexer):
        self.parser = parser
        self.lexer = lexer

        self.semantic_stack = list()
        self.break_scope = list()
        self.break_stack = list()

        self.temp_pointer = 500

        self.stack_pointer = 100
        self.return_address = 104
        self.print_param = 108

        self.scope_stack = [
            {
                "output": {
                    "addr": 1,
                    "type": "int",
                    "params": [{"id": "a", "type": "int"}],
                }
            }
        ]
        self.address_scope_stack = [
            [],
        ]
        self.codes_generated = {
            0: ("JP", 9, None, None), #TODO
            1: ("SUB", self.stack_pointer, "#4", self.stack_pointer),
            2: ("ASSIGN", f"@{self.stack_pointer}", self.return_address, None),
            3: ("SUB", self.stack_pointer, "#4", self.stack_pointer),
            4: ("ASSIGN", f"@{self.stack_pointer}", self.print_param, None),
            5: ("PRINT", self.print_param, None, None),
            6: ("ASSIGN", "#0", f"@{self.stack_pointer}", None),
            7: ("ADD", "#4", self.stack_pointer, self.stack_pointer),
            8: ("JP", f"@{self.return_address}", None, None),
            9: ("ASSIGN", "#4000", self.stack_pointer, None),
            10: ("ASSIGN", "#0", self.return_address, None),
        }
        self.waiting_function_jumps = {}

        self.program_line = len(self.codes_generated)

        self.last_id = None
        self.last_num = None
        self.last_type = None
        self.current_function_name = None
        self.current_function_type = None
        self.declaring_function_params = []
        self.jumped_to_main = False

    def get_var_scope(self, var) -> int:
        for i, scope in reversed(list(enumerate(self.scope_stack))):
            if var in scope:
                return i, scope[var]["addr"]
        return -1, None

    def add_var_to_scope(self, var, scope_indicator, type, length=1):
        address = self.get_temp(length=length)
        self.scope_stack[scope_indicator][var] = dict()
        self.scope_stack[scope_indicator][var]["addr"] = address
        self.scope_stack[scope_indicator][var]["type"] = type
        return address

    def add_code_line(self, code):
        self.codes_generated[int(self.program_line)] = code
        self.program_line += 1

    def store_code_line(self, code, line):
        if isinstance(line, str):
            if line.startswith("#") or line.startswith("@"):
                line = line[1:]
        self.codes_generated[int(line)] = code

    def push_to_stack(self, addr):
        self.add_code_line(("ASSIGN", addr, f"@{self.stack_pointer}", None))
        self.add_code_line(("ADD", "#4", self.stack_pointer, self.stack_pointer))

    def pop_from_stack(self, write_back_addr):
        self.add_code_line(("SUB", self.stack_pointer, "#4", self.stack_pointer))
        self.add_code_line(("ASSIGN", f"@{self.stack_pointer}", write_back_addr, None))

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
            self.call()
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
        elif action == "declaring_function":
            self.declaring_function()
        elif action == "start_declaring_params":
            self.start_declaring_params()
        elif action == "end_declaring_params":
            self.end_declaring_params()
        elif action == "signature_declared":
            self.signature_declared()
        elif action == "declare_array_param":
            self.declare_array_param()
        elif action == "declare_int_param":
            self.declare_int_param()
        elif action == "function_declared":
            self.function_declared()
        elif action == "push_return_address":
            self.push_return_address()
        elif action == "pop_return_address":
            self.pop_return_address()
        elif action == "push_return_value":
            self.push_return_value()
        elif action == "pop_return_value":
            self.pop_return_value()
        elif action == "push_state":
            self.push_state()
        elif action == "pop_state":
            self.pop_state()
        elif action == "return_void":
            self.return_void()
        elif action == "return_int":
            self.return_int()
        elif action == "default_return":
            self.default_return()
        elif action == "push_arg":
            self.push_arg()
        elif action == "pop_args":
            self.pop_args()
        else:
            print(action)
            raise Exception("Invalid action")

    def get_temp(self, length=1, size=4):
        address = self.temp_pointer
        self.temp_pointer += length * size
        for i in range(length):
            self.address_scope_stack[-1].append(address + i * 4)
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
        address = self.add_var_to_scope(id, -1, "int")
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.scope_stack[-1][self.last_id] = dict()
        self.scope_stack[-1][self.last_id]["addr"] = address
        self.scope_stack[-1][self.last_id]["type"] = self.last_type
        self.last_type = None

    def declare_array(self):
        length = int(self.semantic_stack.pop()[1:])
        id = self.semantic_stack.pop()
        address = self.add_var_to_scope(id, -1, "array", length + 1)
        self.add_code_line(("ASSIGN", f"#{address + 4}", address, None))
        for i in range(length):
            self.add_code_line(("ASSIGN", "#0", address + 4 + i * 4, None))
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

    def call(self):
        function_addr = self.semantic_stack.pop()
        self.add_code_line(("JP", function_addr, None, None))

    def array_index(self):
        index = self.semantic_stack.pop()
        array = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line(("MULT", index, "#4", result))
        self.add_code_line(("ADD", f"{array}", result, result))
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
        if not self.jumped_to_main:
            self.waiting_function_jumps[self.program_line] = "main"
            self.program_line += 1
            self.jumped_to_main = True
        self.last_num = None
        self.last_id = None
        self.last_type = None
        self.scope_stack.append({})
        self.address_scope_stack.append([])

    def scope_exit(self):
        self.last_num = None
        self.last_id = None
        self.last_type = None
        self.scope_stack.pop()
        self.address_scope_stack.pop()

    def declaring_function(self):
        self.current_function_name = self.last_id
        self.current_function_type = self.last_type

    def start_declaring_params(self):
        self.declaring_function_params = []

    def end_declaring_params(self):
        pass

    def signature_declared(self):
        self.current_function_name = self.semantic_stack.pop()
        self.scope_stack[-2][self.current_function_name] = {
            "addr": self.program_line,
            "type": self.current_function_type,
            "params": self.declaring_function_params,
        }
        for line, function_name in self.waiting_function_jumps.items():
            if function_name == self.current_function_name:
                self.store_code_line(("JP", self.program_line, None, None), line)

    def declare_array_param(self):
        self.declaring_function_params.append(
            {
                "id": self.semantic_stack.pop(),
                "type": "array",
            }
        )
        self.add_var_to_scope(self.last_id, -1, "array")

    def declare_int_param(self):
        self.declaring_function_params.append(
            {
                "id": self.semantic_stack.pop(),
                "type": "int",
            }
        )
        self.add_var_to_scope(self.last_id, -1, "int")

    def push_state(self):
        for address_scope in self.address_scope_stack[-2:]:
            for addr in address_scope:
                self.push_to_stack(addr)

    def pop_state(self):
        for address_scope in reversed(self.address_scope_stack[-2:]):
            for addr in reversed(address_scope):
                self.pop_from_stack(addr)

    def push_return_address(self):
        self.push_to_stack(f"#{self.program_line + 3}")

    def pop_return_address(self):
        if self.current_function_name != "main":
            self.pop_from_stack(self.return_address)

    def push_return_value(self):
        addr = self.semantic_stack.pop()
        self.push_to_stack(addr)

    def pop_return_value(self):
        addr = self.get_temp()
        self.pop_from_stack(addr)
        self.semantic_stack.append(addr)

    def return_void(self):
        self.push_to_stack("#0")
        self.add_code_line(("JP", f"@{self.return_address}", None, None))

    def return_int(self):
        addr = self.semantic_stack.pop()
        self.push_to_stack(addr)
        self.add_code_line(("JP", f"@{self.return_address}", None, None))

    def default_return(self):
        self.push_to_stack("#0")
        if self.current_function_name != "main":
            self.add_code_line(("JP", f"@{self.return_address}", None, None))

    def function_declared(self):
        self.current_function_name = None

    def push_arg(self):
        arg_addr = self.semantic_stack.pop()
        self.push_to_stack(arg_addr)

    def pop_args(self):
        for var in reversed(self.scope_stack[-1]):
            self.pop_from_stack(self.scope_stack[-1][var]["addr"])

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
