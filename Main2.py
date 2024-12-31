import re
import turtle
import time
import os
import math
import random
import pickle
import pygame
import threading
import tkinter as tk
from tkinter import scrolledtext

class BasicInterpreter:
    def __init__(self):
        self.variables = {}  # To store variables
        self.arrays = {}  # To store arrays
        self.program = {}  # Program lines
        self.current_line = None  # Current line of execution
        self.loop_stack = []  # Stack for FOR/NEXT loops
        self.call_stack = []  # Stack for GOSUB/RETURN
        self.data = []  # DATA values
        self.data_pointer = 0  # Pointer for DATA
        self.file_handles = {}  # File handles for I/O
        self.functions = {}  # User-defined functions
        self.procedures = {}  # User-defined subroutines
        self.graphics_initialized = False  # Graphics state
        self.debug_mode = False  # Debugging flag
        self.pygame_initialized = False  # Pygame state
        self.expression_cache = {}  # Cache for expressions
        self.command_history = []  # Command history
        self.program_history = []  # History of program states
        self.help_text = """Available Commands:
        PRINT <expr>       - Prints expression
        LET <var> = <expr> - Assigns a value to a variable
        IF <condition> THEN <stmt> - Conditional execution
        GOTO <line>       - Jumps to a line number
        FOR <var> = <start> TO <end> [STEP <step>] - Loop
        NEXT <var>        - Next iteration of loop
        LIST               - Lists all program lines
        RUN                - Starts the program execution
        HELP               - Displays help text
        """

    def parse_program(self, code):
        """Parse the input BASIC code into line-numbered statements."""
        self.program = {}  # Clear previous program
        for line in code.strip().split("\n"):
            if line.strip():
                parts = line.split(maxsplit=1)
                line_number = int(parts[0])
                statement = parts[1] if len(parts) > 1 else ""
                self.program[line_number] = statement
        self.current_line = min(self.program.keys())

    def evaluate_expression(self, expr):
        """Evaluate a BASIC expression with caching."""
        if expr in self.expression_cache:
            return self.expression_cache[expr]
        
        try:
            expr = expr.replace("ABS", "abs")
            expr = expr.replace("LEN", "len")
            expr = expr.replace("SIN", "math.sin")
            expr = expr.replace("COS", "math.cos")
            expr = expr.replace("TAN", "math.tan")
            expr = expr.replace("LOG", "math.log")
            expr = expr.replace("EXP", "math.exp")
            expr = expr.replace("PI", str(math.pi))
            expr = expr.replace("RND", "random.random")
            expr = expr.replace("DEGREES", "math.degrees")
            expr = expr.replace("RADIANS", "math.radians")
            expr = expr.replace("DATE$", "time.strftime('%Y-%m-%d')")
            expr = expr.replace("TIME$", "time.strftime('%H:%M:%S')")
            expr = expr.replace("DATE", "time.localtime()")
            expr = expr.replace("TIME", "time.localtime()")
            
            result = eval(expr, {"math": __import__("math"), "random": __import__("random"), "time": time}, self.variables)
            
            # Cache the result for future use
            self.expression_cache[expr] = result
            return result
        except Exception as e:
            raise ValueError(f"Invalid expression: {expr} ({e})")

    def execute_line(self, line):
        """Execute a single line of BASIC code with extended features."""
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
                if self.evaluate_expression(condition.strip()):
                    self.execute_line(then_part.strip())

            elif line.startswith("SELECT CASE"):
                condition = line[12:].strip()
                case_found = False
                for case in self.program[self.current_line + 1:]:
                    if case.startswith("CASE"):
                        case_value = case[5:].strip()
                        if self.evaluate_expression(condition.strip()) == self.evaluate_expression(case_value):
                            self.execute_line(case)
                            case_found = True
                            break
                    elif case.startswith("END SELECT"):
                        break
                if not case_found:
                    print("No matching case found.")

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

            elif line.startswith("DEF FN"):
                parts = line[7:].split("=")
                function_name = parts[0].strip()
                function_body = parts[1].strip()
                self.functions[function_name] = function_body

            elif line.startswith("CALL"):
                function_name = line[5:].strip()
                if function_name in self.functions:
                    self.execute_line(self.functions[function_name])
                else:
                    raise ValueError(f"Function {function_name} not defined.")

            elif line.startswith("DATE") or line.startswith("TIME"):
                print(self.evaluate_expression(line))

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

            elif line.startswith("WAIT"):
                seconds = int(line[5:].strip())
                time.sleep(seconds)

            elif line.startswith("REM"):
                pass  # Ignore comments

            elif line.startswith("RUN"):
                self.run()

            elif line.startswith("NEW"):
                self.program.clear()
                self.variables.clear()
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

            elif line.startswith("LIST"):
                for ln in sorted(self.program.keys()):
                    print(f"{ln} {self.program[ln]}")

            elif line.startswith("HELP"):
                print(self.help_text)

            else:
                raise ValueError(f"Unknown command: {line}")

        except Exception as e:
            print(f"Error on line {self.current_line}: {e}")
            if self.debug_mode:
                input("Press Enter to continue...")

    def run(self):
        """Run the BASIC program."""
        try:
            while self.current_line in self.program:
                line_code = self.program[self.current_line]
                next_line = sorted([ln for ln in self.program if ln > self.current_line])
                self.current_line = next_line[0] if next_line else None
                self.execute_line(line_code)
        except Exception as e:
            print(f"Execution halted: {e}")

    def save_program(self, filename):
        """Save the current program to a file."""
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"Program saved to {filename}.")

    def load_program(self, filename):
        """Load a program from a file."""
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                loaded_interpreter = pickle.load(f)
                self.__dict__ = loaded_interpreter.__dict__
            print(f"Program loaded from {filename}.")
        else:
            print(f"Error: File {filename} not found.")

    def initialize_graphics(self):
        """Initialize graphics if not already done."""
        if not self.graphics_initialized:
            turtle.setup(800, 600)
            turtle.speed(0)
            self.graphics_initialized = True

    def close_graphics(self):
        """Close the graphics window."""
        if self.graphics_initialized:
            turtle.done()

# GUI Interface
def start_gui():
    root = tk.Tk()
    root.title("BASIC Interpreter")

    # Code input area
    code_input = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=15)
    code_input.pack(pady=10)

    # Result output area
    output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=10)
    output_box.pack(pady=10)

    interpreter = BasicInterpreter()

    def run_program():
        program_code = code_input.get("1.0", tk.END).strip()
        interpreter.parse_program(program_code)
        output_box.delete("1.0", tk.END)
        interpreter.run()

    run_button = tk.Button(root, text="Run Program", command=run_program)
    run_button.pack()

    root.mainloop()

start_gui()
