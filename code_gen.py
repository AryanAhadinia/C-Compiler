class CodeGenerator:
    def __init__(self, parser, lexer):
        self.parser = parser
        self.lexer = lexer

        self.semantic_stack = list()
        self.scope_stack = list()
        self.codes_generated = dict()

        self.program_line = 0
        self.current_scope = 0
        self.temp_pointer = 500

    def code_gen(self, action):
        pass

    def get_var_scope(self, var) -> int:
        for i, scope in reversed(enumerate(self.scope_stack)):
            if var in scope:
                return i, scope[var]
        return -1, None

    def add_var_to_scope(self, var, scope_indicator):
        address = self.temp_pointer
        self.temp_pointer += 4
        self.scope_stack[scope_indicator][var] = address
        return address

    def add_code_line(self, code):
        self.codes_generated[self.program_line] = code
        self.program_line += 1

    def action_routine(self, action, id, num):
        if action[0] == "#":
            action = action[1:]
        if action == "get_temp":
            self.get_temp()
        elif action == "p_id":
            self.p_id(id)
        elif action == "p_num":
            self.p_num(num)
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
        else:
            raise Exception("Invalid action")

    def get_temp(self, len=1, size=4):
        address = self.temp_pointer
        self.temp_pointer += len * size
        return address

    def p_id(self, id):
        scope, address = self.get_var_scope(id)
        if scope == -1:
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
        result = self.get_temp()
        self.add_code_line((op, left, right, result))
        self.semantic_stack.append(result)

    def assign(self):
        right = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line(("ASSIGN", right, left, None))
        self.semantic_stack.append(result)

    def eq(self):
        self.semantic_stack.append("EQ")

    def lt(self):
        self.semantic_stack.append("LT")

    def declare_var(self):
        var = self.semantic_stack.pop()
        address = self.get_temp()
        self.scope_stack[self.current_scope][var] = address
        self.add_code_line(("ASSIGN", "#0", address, None))
        self.semantic_stack.append(address)

    def declare_array(self):
        len = int(self.semantic_stack.pop()[1:])
        var = self.semantic_stack.pop()
        address = self.get_temp(len=len)
        self.scope_stack[self.current_scope][var] = address
        for i in range(len):
            self.add_code_line(("ASSIGN", "#0", address + i * 4, None))
        self.semantic_stack.append(address)

    def compare(self):
        right = self.semantic_stack.pop()
        op = self.semantic_stack.pop()
        left = self.semantic_stack.pop()
        result = self.get_temp()
        self.add_code_line((op, left, right, result))
        self.semantic_stack.append(result)
