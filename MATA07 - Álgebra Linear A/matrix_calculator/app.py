from matrix import Matrix
from terminal import file
from terminal import parser
import os, sys

class Application(object):

    __matrices = dict()
    __command_log = []
    __show_matrix = True
    __show_old_commands = False
    __current_matrix_name = None

    def __convert_to_numeric_type(self, string):
        return parser.parse_complex_value(string) if "(" in string else float(string)

    def __delete_matrix(self, name):
        self.__matrices.pop(name)

        # Verifica se a matriz deletada era a que estava em uso.
        if name == self.__current_matrix_name:
            self.__current_matrix_name = None

    def __execute_instructions(self, filename):
        line_counter = 0
        
        for instruction in file.load_instructions(filename):
            line_counter += 1
            
            if not instruction: continue

            try:
                self.execute(instruction.replace("\n", "").strip())
            except Exception as error:
                self.__wait_user("[Linha {}] ERRO: {}".format(line_counter, error))
                break

    def __load_matrices(self, filename):
        try: self.__matrices.update(file.load_matrices(filename, convert_to = Matrix))
        except FileNotFoundError: raise FileNotFoundError("Esse arquivo não existe.")
            
    def __set_application_config(self, name, value):
        # O valor deve ser obrigatoriamente "true" ou "false".
        if not value.lower() in ["true", "false"]: raise ValueError("Você deve informar a configuração! (true ou false)")
        value = True if value.lower() == "true" else False

        if name == "show": self.__show_matrix = value
        elif name == "log": self.__show_old_commands = value

    def __set_current_matrix(self, name):
        if not name in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(name))
        self.__current_matrix_name = name

    def __wait_user(self, message):
        input((message if message else "") + " (Pressione ENTER)")
            
    def __execute_application_operation(self, command):
        # Carrega as matrizes de um arquivo.
        if command["command"] == "load": self.__load_matrices(command["args"])

        # Salva as matrizes em um arquivo.
        elif command["command"] == "save": file.save_matrices(command["args"], self.__matrices)

        # Deleta uma matriz do dicionário de matrizes.
        elif command["command"] == "delete": self.__delete_matrix(command["args"])

        # Carrega instruções de um arquivo e as executa.
        elif command["command"] == "execute": self.__execute_instructions(command["args"])

        # Altera a configuração de imprimir a matriz na tela.
        elif command["command"] == "show": self.__set_application_config("show", command["args"])

        # Altera a configuração de salvar as instruções.
        elif command["command"] == "log": self.__set_application_config("log", command["args"])          
            
        # Imprime uma lista com todas as matrizes disponíveis.
        elif command["command"] == "list": self.__wait_user(self.print_matrices())

        # Imprime uma lista com todas as propriedades da matriz atual.
        elif command["command"] == "prop": self.__wait_user(self.print_matrix_properties(command["args"]))

        # Define uma matriz a ser usada nas operações elementares.
        elif command["command"] == "use": self.__set_current_matrix(command["args"])

        # Imprime uma lista de comando do terminal.
        elif command["command"] == "help": self.print_command_list()

        # Encerra a aplicação.
        elif command["command"] == "exit": self.stop()

        # Caso nenhuma condição acima seja atendida, o comando não existe.
        else: raise ValueError("Esse comando não existe.")

    def __execute_arithmetic_operation(self, command):
        # Obtém a matriz definida pelo usuário para ser utilizada.
        try: matrix = self.__matrices[self.__current_matrix_name]
        except: raise KeyError("Nenhuma matriz está sendo utilizada no momento.")

        # Substitui os E(posição) pelos seus respectivos valores.
        for element in command["elements"]:
            row, column = element[1:].split(",")
            row, column = int(row), int(column)

            # Obtém o valor a partir da posição do elemento.
            try: value = matrix.get(row, column)
            except: raise IndexError("A posição E{},{} não existe.".format(row, column))

            # Formata o valor caso ele seja complexo.
            if isinstance(value, complex): value = "complex({},{})".format(value.real, value.imag)

            # Insere o valor na expressão.
            command["expression"] = command["expression"].replace(element, str(value))

        # Realiza o cálculo.
        try: input("Resultado: " + str(eval(command["expression"])).replace("(","").replace(")","").replace("j","i"))
        except: raise SyntaxError("A expressão está incorreta!")
    
    def __execute_elementary_operation(self, command):
        # Obtém a matriz definida pelo usuário para ser utilizada.
        try: matrix = self.__matrices[self.__current_matrix_name]
        except: raise KeyError("Nenhuma matriz está sendo utilizada no momento.")

        # Transforma os valores recebidos para os seus respectivos tipos.
        row1, row2 = int(command["row1"]), (int(command["row2"]) if command["row2"] else None)
        scalar = self.__convert_to_numeric_type(command["scalar"]) if command["scalar"] else 1

        # Verifica se o escalar é zero, pois, não é possível dividir um número por zero
        # e multiplicação de linha por zero não é uma operação elementar.
        if scalar == 0:
            if command["operator"] == "/=": raise ValueError("Não é possível dividir um número por zero!")
            else: raise ValueError("Multiplicar uma linha por zero não é uma operação elementar!")

        # Troca a posição de duas linhas.
        if command["operator"] == "<>":
            if not row2: raise SyntaxError("Informe a linha que deseja trocar.")
            if command["scalar"]: raise SyntaxError("Não é possível realizar essa operação com um escalar.")
            matrix.interchange_rows(row1, row2)

        # Verifica se as linhas são iguais.
        elif command["operator"] == "==":
            if not row2: raise SyntaxError("Informe a linha que deseja verificar a igualdade.")
            if command["scalar"]: raise SyntaxError("Não é possível realizar essa operação com um escalar.")
            input(matrix.get_row(row1) == matrix.get_row(row2))
            
        # Soma, ou subtrai, uma linha por outra linha.
        elif command["operator"] in "+=-=":
            if row1 == row2: raise ValueError("Somar ou subtrair pela mesma linha não é uma operação elementar!")
            if not row2: raise SyntaxError("Somas e subtrações de linhas são feitas apenas por outras linhas!")
            matrix.add_row(row1, row2, scalar * (-1 if "-" in command["operator"] else 1))

        # Multiplica, ou divide, uma linha por um escalar. 
        else:
            if row2: raise SyntaxError("Não é possível multiplicar ou dividir uma linha por outra!")
            if not command["scalar"]: raise SyntaxError("Informe o escalar para multiplicar ou dividir a linha.")
            matrix.multiply_row(row1, scalar, div = True if command["operator"] == "/=" else False)
            
    def __execute_matrix_operation(self, command):
        # Obtém a matriz conjugada.
        if command["operator"] in ["c", "ct", "tc"]:
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if command["y"]: raise SyntaxError("Por qual motivo o \"{}\" está presente?".format(command["y"]))
            self.__matrices[command["var"]] = self.__matrices[command["x"]].conjugate()

        # Obtém a matriz transposta.
        if command["operator"] in ["t", "ct", "tc"]:
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if command["y"]: raise SyntaxError("Por qual motivo o \"{}\" está presente?".format(command["y"]))
            self.__matrices[command["var"]] = self.__matrices[command["x"]].transpose()
            
        # Obtém a matriz adjunta ou cofatora.
        if command["operator"] in ["adj", "cof"]:
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if command["y"]: raise SyntaxError("Por qual motivo o \"{}\" está presente?".format(command["y"]))
            
            try:
                if command["operator"] == "adj": self.__matrices[command["var"]] = self.__matrices[command["x"]].get_adjugate_matrix()
                if command["operator"] == "cof": self.__matrices[command["var"]] = self.__matrices[command["x"]].get_cofactor_matrix()
            except: raise IndexError("Não é possível realizar essa operação em uma matriz '{}x{}'".format(*self.__matrices[command["x"]].get_order()))

        # Obtém a inversa da matriz.
        if command["operator"] == "inv":
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if command["y"]: raise SyntaxError("Por qual motivo o \"{}\" está presente?".format(command["y"]))

            try: self.__matrices[command["var"]] = self.__matrices[command["x"]].get_matrix_inverse()
            except: raise Exception("Essa matriz não é inversível.")

        # Obtém o menor complementar da matriz.
        elif command["operator"].startswith("m"):
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if command["y"]: raise SyntaxError("Por qual motivo o \"{}\" está presente?".format(command["y"]))

            row, column = command["operator"][1:].replace("(","").replace(")", "").split(",")

            # Obtém e atribui à variável o menor complementar da matriz.
            try: self.__matrices[command["var"]] = self.__matrices[command["x"]].get_matrix_minor(int(row), int(column))
            except: raise IndexError("Matrizes '{}x{}' não possuem menor complementar.".format(*self.__matrices[command["x"]].get_order()))

        # Soma ou subtrai as matrizes.
        elif command["operator"] in "+-":

            # Verifica se existem duas matrizes.
            if not command["x"].isalpha() or not command["y"].isalpha():
                raise SyntaxError("Para operações de soma e subtração, é necessário duas matrizes.")

            # Verifica se elas existem.
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["x"]))
            if not command["y"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe.".format(command["y"]))

            # Faz a soma, ou subtração, das matrizes.
            try:
                if command["operator"] == "+": self.__matrices[command["var"]] = self.__matrices[command["x"]] + self.__matrices[command["y"]]
                else: self.__matrices[command["var"]] = self.__matrices[command["x"]] - self.__matrices[command["y"]]
            except: raise ValueError("Ambas as matrizes devem ter a mesma ordem!")

        # Multiplica ou divide as matrizes.
        elif command["operator"] in "*/":

            # Verifica se existe pelo menos uma matriz.
            if not command["x"].isalpha():
                raise SyntaxError("Informe uma matriz à esquerda para operações de multiplicação e divisão.")

            # Verifica se as matrizes existem.
            if not command["x"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe!".format(command["x"]))
            if command["y"].isalpha() and not command["y"] in self.__matrices: raise KeyError("A matriz \"{}\" não existe!".format(command["y"]))

            x = self.__matrices[command["x"]]
            y = self.__matrices[command["y"]] if command["y"].isalpha() else self.__convert_to_numeric_type(command["y"])

            # Divide a matriz por um escalar.
            if command["operator"] == "/":
                if isinstance(y, Matrix): raise ValueError("Não é possível dividir uma matriz por outra!")
                if y == 0: raise ValueError("Não é possível dividir por zero!")

            # Faz o produto das matrizes.
            try:
                if command["operator"] == "*": self.__matrices[command["var"]] = x * y
                else: self.__matrices[command["var"]] = x / y
            except: raise ValueError("O número de colunas da matriz à esquerda deve ser o número de linhas da matriz à direita!")

    def clear_terminal(self):
        """
        Limpa a tela do terminal.
        """
        if "win" in sys.platform: os.system("cls")
        else: os.system("clear")  

    def execute(self, command):
        """
        Executa uma instrução.
        """
        self.__command_log.append(command)
        command = parser.parse_command(command)
        
        options = {
            "application": self.__execute_application_operation,
            "matrix": self.__execute_matrix_operation,
            "elementary": self.__execute_elementary_operation,
            "arithmetic": self.__execute_arithmetic_operation
        }
        return options[command["operation"]](command)

    def get_user_input(self):
        """
        Obtém o input do usuário.
        """
        command = input("Command> ").strip()
        print()
        return command
        
    def print_current_matrix(self):
        """
        Imprime a matrix que está sendo usada.
        """
        if self.__current_matrix_name:
            print("Atualmente usando a matriz \"{}\". [{} {}]".format(
                self.__current_matrix_name, len(self.__matrices),
                "disponíveis" if len(self.__matrices) > 1 else "disponível"
            ))

            # Mostra a matriz, caso o usuário queira.
            if self.__show_matrix:
                print()
                print(self.__matrices[self.__current_matrix_name])
                
        else:
            print("Atualmente nenhuma matriz está sendo usada. [{} {}]".format(
                len(self.__matrices), "disponíveis" if len(self.__matrices) > 1 else "disponível"
            ))
        print("\n")

    def print_command_list(self):
        """
        Imprime uma lista com todos os comandos do terminal.
        """
        print("Lista de Comandos do Terminal:")
        print("{:<23} | Deleta uma matriz".format("- delete <matrix>"))
        print("{:<23} | Carrega um arquivo de instruções e as executa".format("- execute <arquivo.ext>"))
        print("{:<23} | Encerra o programa".format("- exit"))
        print("{:<23} | Mostra uma lista com todos os comandos do terminal".format("- help"))
        print("{:<23} | Mostra uma lista com todas as matrizes".format("- list"))
        print("{:<23} | Carrega um arquivo contendo matrizes".format("- load <arquivo.ext>"))
        print("{:<23} | Mostra os comandos anteriores".format("- log <true | false>"))
        print("{:<23} | Mostra uma lista com todas as propriedades da matriz".format("- prop <matrix>"))
        print("{:<23} | Salva as matrizes em um arquivo".format("- save <arquivo.ext>"))
        print("{:<23} | Mostra a matriz que está sendo utilizada".format("- show <true | false>"))
        print("{:<23} | Define uma matriz para ser utilizada".format("- use <matrix>"))
        input()

    def print_matrix_properties(self, name):
        """
        Imprime as propriedades da matriz.
        """
        try: matrix = self.__matrices[name]
        except: raise KeyError("A matriz \"{}\" não existe!".format(name))
        
        print("Propriedades da Matrix:")
        print("- Anti-hermitiana:", matrix.is_skew_hermitian())
        print("- Anti-simétrica:", matrix.is_skew_symmetric())
        print("- Coluna:", matrix.is_column())
        print("- Complexa:", matrix.is_complex())
        print("- Determinante:", str(matrix.get_determinant()).replace("(","").replace(")","").replace("j","i") if matrix.is_square() else "N/D")
        print("- Diagonal:", matrix.is_diagonal())
        print("- Escalar:", matrix.is_scalar())
        print("- Identidade:", matrix.is_identity())
        print("- Hermitiana:", matrix.is_hermitian())
        print("- Linha:", matrix.is_row())
        print("- Normal:", matrix.is_normal())
        print("- Nula:", matrix.is_null())
        print("- Ortogonal:", matrix.is_orthogonal())
        print("- Quadrada:", matrix.is_square())
        print("- Simétrica:", matrix.is_symmetric())
        print("- Traço:", str(matrix.get_trace()).replace("(","").replace(")","").replace("j","i") if matrix.is_square() else "N/D")
        print("- Triangular Inferior:", matrix.is_lower_triangular())
        print("- Triangular Superior:", matrix.is_upper_triangular())
        
    def print_matrices(self):
        if self.__matrices: 
            print("Lista de Matrizes:")
            
            for name in self.__matrices.keys():
                print("- {} <{},{}>".format(name, *self.__matrices[name].get_order()))
        else: print("Nenhuma matriz disponível. Use o comando \"load <arquivo.ext>\".")

    def print_old_commands(self):
        """
        Imprime todos os comandos executados anteriormente.
        """
        for command in self.__command_log:
            print("Command>", command)

    def run(self):
        """
        Inicia a execução do programa.
        """
        self.__finish = False

        # Executa o método enquanto não pedir para encerrar.
        while not self.__finish:
            self.clear_terminal()
            self.print_current_matrix()

            # Mostra todos os comandos antigos.
            if self.__show_old_commands:
                self.print_old_commands()
            
            # Executa a instrução do usuário.
            try: self.execute(self.get_user_input())
            except Exception as error: self.__wait_user("ERRO: {}".format(error))

    def stop(self):
        """
        Encerra a aplicação.
        """
        self.__finish = True
            
            
if __name__ == "__main__":
    application = Application()
    application.run()
