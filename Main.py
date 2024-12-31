import re
import turtle
import time
import os
import random
import math
import msvcrt

class BasicInterpreter:
    def __init__(self):
        self.variables = {}        # To store variables
        self.arrays = {}           # To store arrays
        self.program = {}          # Program lines
        self.current_line = None   # Current line of execution
        self.loop_stack = []       # Stack for FOR/NEXT loops
        self.call_stack = []       # Stack for GOSUB/RETURN
        self.data = []             # DATA values
        self.data_pointer = 0      # Pointer for DATA
        self.file_handles = {}     # File handles for I/O
        self.graphics_initialized = False  # Graphics state
        self.debug_mode = False    # Debugging flag
        self.start_time = None     # Timer start time
        self.is_running = False    # Flag to indicate whether program is running

    def parse_program(self, code):
        """Parse the input BASIC code into line-numbered statements."""
        for line in code.strip().split("\n"):
            if line.strip():
                parts = line.split(maxsplit=1)
                line_number = int(parts[0])
                statement = parts[1] if len(parts) > 1 else ""
                self.program[line_number] = statement
        self.current_line = min(self.program.keys())

    def evaluate_expression(self, expr):
        """Evaluate a BASIC expression."""
        try:
            expr = expr.replace("ABS", "abs")
            expr = expr.replace("LEN", "len")
            expr = expr.replace("SIN", "math.sin")
            expr = expr.replace("COS", "math.cos")
            expr = expr.replace("TAN", "math.tan")
            expr = expr.replace("LOG", "math.log")
            expr = expr.replace("EXP", "math.exp")
            expr = expr.replace("SQR", "math.sqrt")
            expr = expr.replace("RND", "random.random")
            expr = expr.replace("PI", "math.pi")
            expr = expr.replace("TRIM$", "lambda s: s.strip()")
            expr = expr.replace("MID$", "lambda s, i, n: s[i-1:i-1+n]")
            expr = expr.replace("LEFT$", "lambda s, n: s[:n]")
            expr = expr.replace("RIGHT$", "lambda s, n: s[-n:]")
            expr = expr.replace("VAL", "float")
            expr = expr.replace("STR$", "str")
            expr = expr.replace("CHR$", "chr")
            expr = expr.replace("ASC", "ord")
            expr = expr.replace("INT", "int")
            expr = expr.replace("FLOOR", "math.floor")
            expr = expr.replace("CEIL", "math.ceil")
            expr = expr.replace("ROUND", "round")
            return eval(expr, {"math": math, "random": random}, self.variables)
        except Exception as e:
            raise ValueError(f"Invalid expression: {expr} ({e})")

    def execute_line(self, line):
        """Execute a single line of BASIC code."""
        try:
            if line.startswith("PRINT"):
                to_print = line[6:].strip()
                if to_print.startswith('"') and to_print.endswith('"'):
                    print(to_print.strip('"'))
                else:
                    print(self.evaluate_expression(to_print))

            elif line.startswith("LET"):
                parts = line[4:].split("=")
                var_name = parts[0].strip()
                var_value = self.evaluate_expression(parts[1].strip())
                self.variables[var_name] = var_value

            elif line.startswith("INPUT"):
                var_name = line[6:].strip()
                user_input = input(f"Enter value for {var_name}: ")
                self.variables[var_name] = self.evaluate_expression(user_input)

            elif line.startswith("IF"):
                condition, then_part = line[3:].split("THEN")
                if "ELSE" in then_part:
                    then_part, else_part = then_part.split("ELSE")
                    if self.evaluate_expression(condition.strip()):
                        self.execute_line(then_part.strip())
                    else:
                        self.execute_line(else_part.strip())
                else:
                    if self.evaluate_expression(condition.strip()):
                        self.execute_line(then_part.strip())

            elif line.startswith("GOTO"):
                target_line = int(line[5:].strip())
                if target_line in self.program:
                    self.current_line = target_line
                else:
                    raise ValueError(f"Invalid GOTO target: {target_line}")

            elif line.startswith("FOR"):
                parts = line[4:].split()
                var_name, start, _, end, *step = parts[0], parts[2], parts[3], parts[4:]
                self.variables[var_name] = self.evaluate_expression(start)
                self.loop_stack.append((self.current_line, var_name, self.evaluate_expression(end), self.evaluate_expression(step[1]) if step else 1))

            elif line.startswith("NEXT"):
                var_name = line[5:].strip()
                if self.loop_stack:
                    loop_start, loop_var, loop_end, loop_step = self.loop_stack[-1]
                    self.variables[loop_var] += loop_step
                    if self.variables[loop_var] <= loop_end:
                        self.current_line = loop_start
                    else:
                        self.loop_stack.pop()

            elif line.startswith("GOSUB"):
                target_line = int(line[6:].strip())
                if target_line in self.program:
                    self.call_stack.append(self.current_line)
                    self.current_line = target_line
                else:
                    raise ValueError(f"Invalid GOSUB target: {target_line}")

            elif line.startswith("RETURN"):
                if self.call_stack:
                    self.current_line = self.call_stack.pop()
                else:
                    raise ValueError("RETURN without GOSUB")

            elif line.startswith("DATA"):
                self.data.extend(line[5:].split(","))

            elif line.startswith("READ"):
                var_name = line[5:].strip()
                if self.data_pointer < len(self.data):
                    self.variables[var_name] = self.evaluate_expression(self.data[self.data_pointer])
                    self.data_pointer += 1
                else:
                    raise ValueError("Out of DATA")

            elif line.startswith("OPEN"):
                match = re.match(r'OPEN "(.*?)" FOR (INPUT|OUTPUT) AS #(\d+)', line, re.IGNORECASE)
                if match:
                    filename, mode, handle = match.groups()
                    mode = "r" if mode.upper() == "INPUT" else "w"
                    self.file_handles[int(handle)] = open(filename, mode)
                else:
                    raise ValueError("Invalid OPEN statement")

            elif line.startswith("CLOSE"):
                handle = int(line[6:].strip())
                if handle in self.file_handles:
                    self.file_handles[handle].close()
                    del self.file_handles[handle]
                else:
                    raise ValueError(f"Invalid file handle: {handle}")

            elif line.startswith("PRINT#"):
                match = re.match(r'PRINT#(\d+), (.+)', line, re.IGNORECASE)
                if match:
                    handle, content = match.groups()
                    handle = int(handle)
                    if handle in self.file_handles:
                        self.file_handles[handle].write(content.strip('"') + "\n")
                    else:
                        raise ValueError(f"Invalid file handle: {handle}")

            elif line.startswith("CLS"):
                self.initialize_graphics()
                turtle.clear()

            elif line.startswith("PLOT"):
                self.initialize_graphics()
                x, y = map(int, line[5:].split(","))
                turtle.penup()
                turtle.goto(x, y)
                turtle.pendown()
                turtle.dot()

            elif line.startswith("LINE"):
                self.initialize_graphics()
                x1, y1, x2, y2 = map(int, line[5:].split(","))
                turtle.penup()
                turtle.goto(x1, y1)
                turtle.pendown()
                turtle.goto(x2, y2)

            elif line.startswith("CIRCLE"):
                self.initialize_graphics()
                x, y, radius = map(int, line[7:].split(","))
                turtle.penup()
                turtle.goto(x, y - radius)
                turtle.pendown()
                turtle.circle(radius)

            elif line.startswith("RECTANGLE"):
                self.initialize_graphics()
                x1, y1, x2, y2 = map(int, line[10:].split(","))
                turtle.penup()
                turtle.goto(x1, y1)
                turtle.pendown()
                turtle.goto(x2, y1)
                turtle.goto(x2, y2)
                turtle.goto(x1, y2)
                turtle.goto(x1, y1)

            elif line.startswith("STOP"):
                print("Program stopped.")
                self.current_line = None

            elif line.startswith("END"):
                print("Program ended.")
                self.current_line = None

            elif line.startswith("LIST"):
                for ln in sorted(self.program.keys()):
                    print(f"{ln} {self.program[ln]}")

            elif line.startswith("TRACE"):
                self.debug_mode = not self.debug_mode
                print(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}")

            elif line.startswith("WAIT"):
                seconds = int(line[5:].strip())
                time.sleep(seconds)

            elif line.startswith("INKEY$"):
                key = msvcrt.getch()
                print(f"Key pressed: {key.decode()}")
                return key.decode()

            elif line.startswith("REM"):
                pass  # Ignore comments

            elif line.startswith("RUN"):
                self.run()

            elif line.startswith("NEW"):
                self.program.clear()
                print("Program cleared.")

            elif line.startswith("SAVE"):
                filename = line[5:].strip()
                self.save_program(filename)

            elif line.startswith("LOAD"):
                filename = line[5:].strip()
                self.load_program(filename)

            elif line.startswith("QUIT"):
                print("Quitting the interpreter.")
                self.current_line = None

            else:
                print(f"Unknown command: {line}")

        except Exception as e:
            print(f"Error: {e}")

    def initialize_graphics(self):
        """Initialize graphics if not already done."""
        if not self.graphics_initialized:
            turtle.setup(800, 600)
            turtle.speed(0)
            self.graphics_initialized = True

    def run(self):
        """Run the program."""
        while self.current_line is not None:
            self.execute_line(self.program[self.current_line])
            self.current_line = self.get_next_line()

    def get_next_line(self):
        """Get the next line number to execute."""
        next_lines = sorted([ln for ln in self.program.keys() if ln > self.current_line])
        return next_lines[0] if next_lines else None

    def save_program(self, filename):
        """Save the current program to a file."""
        with open(filename, 'w') as f:
            for ln, stmt in sorted(self.program.items()):
                f.write(f"{ln} {stmt}\n")
        print(f"Program saved to {filename}.")

    def load_program(self, filename):
        """Load a program from a file."""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                code = f.read()
            self.parse_program(code)
            print(f"Program loaded from {filename}.")
        else:
            print(f"Error: File {filename} not found.")
