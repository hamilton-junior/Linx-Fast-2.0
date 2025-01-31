import random # Importa a biblioteca random para gerar cores aleatórias
import customtkinter as ctk # Importa a biblioteca customtkinter para criar a interface gráfica

# Configuração Inicial
ctk.set_appearance_mode("light")  
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configurações da janela principal
        self.title("Linx Fast 2.0")
        self.geometry("160x512")
        self.resizable(False, False)
        
        backgroundcolor="#9ed7d0"
        
        # Cria um frame principal
        mainframe = ctk.CTkFrame(self)
        mainframe.pack(fill="both", expand=True)
        mainframe.configure(fg_color=backgroundcolor)

        # Lista de botões e entradas
        self.entries = []
        buttonNames = ["N","P","C","T","E","#","S"]
        entryPlaceholders = ["Nome","Problema","CNPJ","Telefone","E-mail","Caso","Solução"]

        # Cria range(X) linhas de botões e entradas
        for i in range(7):
            
            # Cria um frame para cada linha
            row_frame = ctk.CTkFrame(mainframe)
            row_frame.configure(fg_color=backgroundcolor)
            row_frame.pack(fill="x", padx=5, pady=3)    

            # Designa uma cor aleatória para o botão
            random_color = RandomColor(self).generate_random_hex()
            # Designa uma cor de texto contrastante com a cor gerada acima
            random_color_text = RandomColor(self).get_text_color(random_color)
            
            # Cria um botão com a cor aleatória e cor de texto contrastante
            button = ctk.CTkButton(row_frame, text=buttonNames[i], width=25, height=25, fg_color=random_color, text_color=random_color_text)
            button.pack(side="left")

            # Cria uma entrada com um placeholder
            entry = ctk.CTkEntry(row_frame)
            entry.configure(placeholder_text=entryPlaceholders[i])
            entry.pack(side="right", fill="x", expand=True, padx=[5,0])
            self.entries.append(entry)
            
        # Designa outra cor aleatória para ser usada posteriormente, caso necessário
        random_color = RandomColor(self).generate_random_hex()
        # Designa uma cor de texto contrastante com a cor gerada acima
        random_color_text = RandomColor(self).get_text_color(random_color)        
        
        #Botão Intranet
        intranet_button = ctk.CTkButton(mainframe, text="IN", font=("Arial",12,"bold"),width=5, height=5, corner_radius=5,fg_color=random_color, text_color=random_color_text)
        intranet_button.pack(padx=[5,0],pady=[5,0],anchor="w")
        
        # Área de Texto Estilizada
        self.textbox = ctk.CTkTextbox(mainframe, wrap="word")
        self.textbox.pack(padx=5, pady=[10,0], fill="both", expand=True)
        self.textbox.configure(fg_color="#FFFACD", text_color="black")

        # Label de Créditos ao final do app
        creditos = ctk.CTkLabel(mainframe, text="By Hamilton Junior", font=("Arial", 8,"bold"), anchor="center", padx=5)
        creditos.pack(side="right")

class RandomColor:
    def __init__(self, min_distance=2500):
        self.min_distance = min_distance
        self.last_color = None
    
    def hex_distance(self, color1, color2):
        """Calcula a distância euclidiana entre duas cores em formato HEX."""
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
    
    def generate_random_hex(self):
        """Gera um código HEX aleatório que não seja muito próximo da cor anterior."""
        while True:
            color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            # Se já existe uma cor anterior e a distância for menor que o mínimo, gera outra cor
            if self.last_color and self.hex_distance(self.last_color, color) < self.min_distance:
                continue
            self.last_color = color
            return color

    def get_text_color(self, hex_color=None):
        """Retorna preto (#000000) ou branco (#FFFFFF) dependendo do brilho da cor de fundo."""
        if hex_color is None:
            hex_color = self.last_color  # Usa a última cor gerada se nenhum parâmetro for passado
        
        if not hex_color:
            raise ValueError("Nenhuma cor foi gerada ainda.")

        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
        return "#000000" if luminance > 128 else "#FFFFFF"




if __name__ == "__main__":
    app = App()
    app.mainloop()
