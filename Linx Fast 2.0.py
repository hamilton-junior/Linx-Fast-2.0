import customtkinter

#Tema
customtkinter.set_default_color_theme("Linx-Fast-2.0/data/theme.json")  # Themes: "blue" (standard), "green", "dark-blue"

#Criação da Classe da CheckBox Frame
class MyCheckBoxFrame(customtkinter.CTkFrame):
    def __init__(self,master):
        super().__init__(master)

        #Criação da(s) CheckBox(es)
        self.cbPesquisaInterna = customtkinter.CTkCheckBox(self,text="Pesquisa Interna?")
        self.cbPesquisaInterna.grid(row=0,column=0,padx=10,pady=(10,0),sticky="w")
        self.cbColetadoLogs = customtkinter.CTkCheckBox(self,text="Coletado Logs?")
        self.cbColetadoLogs.grid(row=1,column=0,padx=10,pady=(10,0),sticky="w")
        self.cbValidadoN2 = customtkinter.CTkCheckBox(self,text="Validado com N2?")
        self.cbValidadoN2.grid(row=2,column=0,padx=10,pady=(10,0),sticky="w")

    #Define o métodof get() para retornar as Checkboxes marcadas
    def get(self):
        checked_checkboxes = []
        if self.cbColetadoLogs.get() == 1: #Se a Checkbox está marcada, então,
            checked_checkboxes.append(self.cbColetadoLogs.cget("text")) #Adicionamos o valor do atributo "text" da Checkbox ao dicionário checked_checkboxes[]
        if self.cbPesquisaInterna.get() == 1:
            checked_checkboxes.append(self.cbPesquisaInterna.cget("text"))
        if self.cbValidadoN2.get() == 1:
            checked_checkboxes.append(self.cbValidadoN2.cget("text"))
        return checked_checkboxes

#Criação da Classe da Janela Principal
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        #Criação da Interface
        self.title("Linx Fast 2.0")
        self.geometry("400x180")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


        #Criação do Frame para a(s) Checkbox(es)
        self.checkbox_frame = MyCheckBoxFrame(self)
        self.checkbox_frame.grid(row=0,column=0,padx=10,pady=(10,0),sticky="nsw")

        #Criação do(s) botão(ões)
        self.button = customtkinter.CTkButton(self, text="Copiar", command=self.button_callback)
        self.button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    #Função ao Pressionar o Botão
    def button_callback(self):
        print("Checkboxes Marcadas:",self.checkbox_frame.get())
        print("Template copiado!")

#Mantém o APP Aberto
app = App()
app.mainloop()