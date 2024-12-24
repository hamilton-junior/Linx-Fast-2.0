import customtkinter

#Tema
customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

#Criação da Classe
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        #Criação da Interface
        self.title("Linx Fast 2.0")
        self.geometry("400x150")
        self.grid_columnconfigure((0,1), weight=1)


        #Criação do(s) botão(ões)
        self.button = customtkinter.CTkButton(self, text="Copiar")
        self.button.grid(row=0, column=0, padx=20, pady=20, sticky="ew", columnspan=2)

        #Criação da(s) CheckBox(es)
        self.pesquisaInterna = customtkinter.CTkCheckBox(self,text="Pesquisa Interna?")
        self.pesquisaInterna.grid(row=1,column=0,padx=20,pady=(0,20),sticky="w")
        self.validadoN2 = customtkinter.CTkCheckBox(self,text="Validado com N2?")
        self.validadoN2.grid(row=1,column=1,padx=20,pady=(0,20),sticky="w")


    def button_callback(self): #Função ao Pressionar o Botão
        print("Template copiado!")

#Mantém o APP Aberto
app = App()
app.mainloop()