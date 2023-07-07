import enum


class SemanticErrorMessage(enum.Enum):
    SCOPING = "#{}: Semantic Error! '{}' is not defined."
    VOID_TYPE = "#{}: Semantic Error! Illegal type of void for '{}'."
    FORMAL_PARAMS_NUM_MATCHING = (
        "#{}: Semantic Error! Mismatch in numbers of arguments of '{}'."
    )
    BREAK_STATEMENT = "#{}: Semantic Error! No 'repeat ... until' found for 'break'."
    TYPE_MISMATCH = (
        "#{}: Semantic Error! Type mismatch in operands, Got {} instead of {}."
    )
    FORMAL_PARAM_TYPE_MATCHING = "#{}: Semantic Error! Mismatch in type of argument {} of '{}'. Expected '{}' but got '{}' instead."
    NO_ERROR = "The input program is semantically correct."
    CODE_NOT_GENERATED = "The code has not been generated."


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
        self.codes_generated = dict()
        self.break_scope = list()
        self.break_stack = list()
        self.semantic_errors = list()
        self.func_declare = {"id": None, "type": None, "params": []}

        self.program_line = 2
        self.current_scope = 0
        self.temp_pointer = 500

        self.last_id = None
        self.last_num = None
        self.last_type = None
        self.funcs = list()
        self.funcs_args = dict()
        self.codes_generated[0] = ("ASSIGN", "#4", 0, None)
        self.codes_generated[1] = ("JP", 2, None, None)
        self.temp_pointer += 4
        self.current_func = None
        self.current_function_arg_checking = list()
        self.in_loop = False

        self.address_type_mapping = {} # TODO: default

    def get_var_scope(self, var) -> int:
        for i, scope in reversed(list(enumerate(self.scope_stack))):
            if var in scope:
                return i, scope[var]["addr"]
        return -1, None

    def add_var_to_scope(self, var, scope_indicator):
        address = self.get_temp()
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
        print(action, self.last_id, self.last_num, self.last_type, self.lexer.lineno)
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
        elif action == "output":
            self.output()
        elif action == "call_index":
            self.call_index()
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
        elif action == "declare_func_start":
            self.declare_func_start()
        elif action == "declare_func_end":
            self.declare_func_end()
        elif action == "func_params_end":
            self.func_params_end()
        elif action == "add_int_param":
            self.add_int_param()
        elif action == "add_array_param":
            self.add_array_param()
        elif action == "loop_start":
            self.loop_start()
        elif action == "loop_end":
            self.loop_end()
        elif action == "func_call_args_start":
            self.func_call_args_start()
        elif action == "func_call_args_end":
            self.func_call_args_end()
        elif action == "arg_type_check":
            pass
        else:
            raise Exception("Invalid action")

    def get_temp(self, len=1, size=4):
        address = self.temp_pointer
        self.temp_pointer += len * size
        if len == 1:
            self.address_type_mapping[address] = "int"
        else:
            for i in range(1, len):
                self.address_type_mapping[address + i * size] = "int"
            self.address_type_mapping[address - size] = "array"
        return address
    
    def get_type(self, address):
        address = str(address)
        if address.startswith("#"):
            return "int"
        elif address.startswith("@"):
            return "int"
        else:
            return self.address_type_mapping[int(address)]

    def p_id(self, id):
        scope, address = self.get_var_scope(id)
        if scope == -1:
            if self.last_type is None:
                self.semantic_errors.append(
                    SemanticErrorMessage.SCOPING.value.format(self.lexer.lineno, id)
                )
                self.semantic_stack.append('INVALID')
                return
            address = self.add_var_to_scope(id, self.current_scope)
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
        if left == "INVALID" or right == "INVALID":
            return
        type_left = self.get_type(left)
        type_right = self.get_type(right)
        if type_left == "array" or type_right == "array":
            self.semantic_errors.append(
                SemanticErrorMessage.TYPE_MISMATCH.value.format(
                    self.lexer.lineno, "array", "int"
                )
            )
            self.semantic_stack.append("INVALID")
            return
        result = self.get_temp()
        self.add_code_line((op, left, right, result))
        self.semantic_stack.append(result)

    def assign(self):
        right = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        if left == "INVALID" or right == "INVALID":
            return
        type_left = self.get_type(left)
        type_right = self.get_type(right)
        if type_left == "array" or type_right == "array":
            self.semantic_errors.append(
                SemanticErrorMessage.TYPE_MISMATCH.value.format(
                    self.lexer.lineno, "array", "int"
                )
            )
            self.semantic_stack.append("INVALID")
            return
        self.add_code_line(("ASSIGN", right, left, None))
        self.semantic_stack.append(left)

    def eq(self):
        self.semantic_stack.append("EQ")

    def lt(self):
        self.semantic_stack.append("LT")

    def declare_var(self):
        if self.last_type == "void":
            self.semantic_errors.append(
                SemanticErrorMessage.VOID_TYPE.value.format(
                    self.lexer.lineno - 1, self.last_id
                )
            )
            self.last_type = None
            return
        address = self.semantic_stack.pop()
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.semantic_stack.append(address)
        self.scope_stack[self.current_scope][self.last_id] = dict()
        self.scope_stack[self.current_scope][self.last_id]["addr"] = address
        self.scope_stack[self.current_scope][self.last_id]["type"] = self.last_type
        self.last_type = None

    def declare_array(self):
        length = int(self.semantic_stack.pop()[1:])
        address = self.semantic_stack.pop()
        self.get_temp(len=length)
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.semantic_stack.append(address)
        self.scope_stack[self.current_scope][self.last_id] = dict()
        self.scope_stack[self.current_scope][self.last_id]["addr"] = address
        self.scope_stack[self.current_scope][self.last_id]["type"] = "array"
        self.last_type = None

    def compare(self):
        right = self.semantic_stack.pop()
        op = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        if left == "INVALID" or right == "INVALID":
            return
        type_left = self.get_type(left)
        type_right = self.get_type(right)
        if type_left == "array" or type_right == "array":
            self.semantic_errors.append(
                SemanticErrorMessage.TYPE_MISMATCH.value.format(
                    self.lexer.lineno, "array", "int"
                )
            )
            self.semantic_stack.append("INVALID")
            return
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

    def call_index(self):
        index = self.semantic_stack.pop()
        array = self.semantic_stack.pop()
        if index == "INVALID" or array == "INVALID":
            return
        if self.get_type(index) != "int":
            self.semantic_errors.append(
                SemanticErrorMessage.TYPE_MISMATCH.value.format(
                    self.lexer.lineno, "int", "array"
                )
            )
            self.semantic_stack.append("INVALID")
            return
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
        if self.in_loop == False:
            self.semantic_errors.append(
                SemanticErrorMessage.BREAK_STATEMENT.value.format(self.lexer.lineno)
            )
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
        self.current_scope += 1

    def scope_exit(self):
        self.last_num = None
        self.last_id = None
        self.last_type = None
        self.scope_stack.pop()
        self.current_scope -= 1

    def declare_func_start(self):
        self.func_declare["id"] = self.last_id
        self.func_declare["type"] = self.last_type
        self.func_declare["params"] = []
        self.funcs.append(self.last_id)
        self.funcs_args[self.last_id] = []

    def declare_func_end(self):
        self.scope_stack[self.current_scope][self.func_declare["id"]][
            "params"
        ] = self.func_declare["params"]
        self.scope_stack[self.current_scope][self.func_declare["id"]][
            "type"
        ] = self.func_declare["type"]
        self.func_declare = {"id": None, "type": None, "params": []}

    def add_int_param(self):
        self.func_declare["params"].append({"id": self.last_id, "type": "int"})

    def add_array_param(self):
        self.func_declare["params"].append({"id": self.last_id, "type": "array"})

    def get_func_params(self, func_id):
        for i, scope in enumerate(reversed(self.scope_stack)):
            if func_id in scope:
                if 'params' in scope[func_id]:
                    return scope[func_id]["params"]
                else:
                    continue
        return None

    def func_call_args_start(self):
        self.current_func = self.last_id
        check_func = self.get_func_params(self.current_func)
        if check_func is None:
            return
        _, self.current_func_address = self.get_var_scope(self.current_func)

    def func_call_args_end(self):
        # args number and type check
        check_func = self.get_func_params(self.current_func)
        if check_func is None:
            return
        args = []
        counter = -1
        while self.semantic_stack[counter] != str(self.current_func_address):
            args.append(self.semantic_stack[counter])
            counter -= 1
        args.reverse()
        func_params = self.get_func_params(self.current_func)
        print(self.current_func)
        print(self.current_func_address)
        print(self.scope_stack)
        print(args)
        print(func_params)
        if len(args) != len(func_params):
            self.semantic_errors.append(
                SemanticErrorMessage.FORMAL_PARAMS_NUM_MATCHING.value.format(
                    self.lexer.lineno, self.current_func
                )
            )
            self.semantic_stack.append("INVALID")
            return
        for i, arg in enumerate(args):
            if self.get_type(arg) != func_params[i]["type"]:
                self.semantic_errors.append(
                    SemanticErrorMessage.FORMAL_PARAM_TYPE_MATCHING.value.format(
                        self.lexer.lineno,
                        i + 1,
                        self.current_func,
                        self.current_function_arg_checking[i],
                        self.get_type(arg),
                    )
                )
                self.semantic_stack.append("INVALID")
                return
        self.current_func = None
        self.current_function_arg_checking = list()

    def loop_start(self):
        self.in_loop = True

    def loop_end(self):
        self.in_loop = False

    def output(self):
        value = self.semantic_stack.pop()
        self.add_code_line(("PRINT", value, None, None))
        self.semantic_stack.pop()
        self.semantic_stack.append(value)

    def to_code_string(self, path):
        if len(self.semantic_errors) > 0:
            with open(path, "w") as f:
                f.write(f"{SemanticErrorMessage.CODE_NOT_GENERATED.value}")
        else:
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

    def to_semantic_errors(self, path):
        with open(path, "w") as f:
            if len(self.semantic_errors) == 0:
                f.write(SemanticErrorMessage.NO_ERROR.value)
            else:
                f.write("\n".join(self.semantic_errors) + "\n")
