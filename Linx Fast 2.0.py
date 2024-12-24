import tkinter as tk
from tkinter import messagebox, filedialog
import pyperclip
import os

# Configuração inicial da janela principal
app = tk.Tk()
app.title("Linx Fast 2.0")
app.geometry("325x600")
app.configure(bg="#f0f8ff")  # Fundo mais claro
app.overrideredirect(True)  # Remove a barra padrão do Windows

# Criar barra customizada
bar_frame = tk.Frame(app, bg="#4682b4", height=30)
bar_frame.pack(fill="x")

always_on_top = tk.BooleanVar(value=False)

def mover_janela(event):
    if not always_on_top.get():
        app.geometry(f"+{event.x_root}+{event.y_root}")

def toggle_always_on_top():
    if always_on_top.get():
        app.attributes("-topmost", False)
        always_on_top.set(False)
    else:
        app.attributes("-topmost", True)
        always_on_top.set(True)

icon_label = tk.Label(bar_frame, text="≡", bg="#4682b4", fg="white", font=("Arial", 12), cursor="hand2")
icon_label.pack(side="left", padx=5)
icon_label.bind("<Button-1>", lambda e: toggle_always_on_top())

btn_minimizar = tk.Button(bar_frame, text="_", bg="#4682b4", fg="white", font=("Arial", 12), command=app.iconify, bd=0, highlightthickness=0, activebackground="#5a9fd6")
btn_minimizar.pack(side="left", padx=5)

btn_fechar = tk.Button(bar_frame, text="X", bg="#4682b4", fg="white", font=("Arial", 12), command=app.destroy, bd=0, highlightthickness=0, activebackground="#ff6347")
btn_fechar.pack(side="right", padx=5)

bar_frame.bind("<B1-Motion>", mover_janela)

# Obter o diretório onde o script está localizado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Criar template padrão, se necessário
def criar_template_padrao():
    if not os.path.exists(TEMPLATE_DIR):
        os.makedirs(TEMPLATE_DIR)
    default_template_path = os.path.join(TEMPLATE_DIR, "Abertura de Chamado.txt")
    if not os.path.exists(default_template_path):
        with open(default_template_path, "w", encoding="utf-8") as file:
            file.write("""[$Protocolo$]\n\n𝐃𝐚𝐝𝐨𝐬 𝐝𝐞 𝐂𝐨𝐧𝐭𝐚𝐭𝐨: $Nome$ - $Telefone$\n𝗖𝗡𝗣𝗝: $CNPJ$\n𝗘-𝗺𝗮𝗶𝗹: $Email$\n𝐃𝐞𝐬𝐜𝐫𝐢ç𝐚̃𝐨: $Problema$\n𝐏𝐞𝐬𝐪𝐮𝐢𝐬𝐚 𝐈𝐧𝐭𝐞𝐫𝐧𝐚: $PesquisaInterna$.\n𝐕𝐞𝐫𝐬𝐚̃𝐨 𝐝𝐨 𝐒𝐢𝐬𝐭𝐞𝐦𝐚: $Versao$\n\n---------------------------------------------------------------------------------------------""")

criar_template_padrao()

# Função para carregar o template do arquivo
def carregar_template(arquivo="Abertura de Chamado.txt"):
    caminho = os.path.join(TEMPLATE_DIR, arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return """[$Protocolo$]\n\n𝐃𝐚𝐝𝐨𝐬 𝐝𝐞 𝐂𝐨𝐧𝐭𝐚𝐭𝐨: $Nome$ - $Telefone$\n𝗖𝗡𝗣𝗝: $CNPJ$\n𝗘-𝗺𝗮𝗶𝗹: $Email$\n𝐃𝐞𝐬𝐜𝐫𝐢ç𝐚̃𝐨: $Problema$\n𝐏𝐞𝐬𝐪𝐮𝐢𝐬𝐚 𝐈𝐧𝐭𝐞𝐫𝐧𝐚: $PesquisaInterna$.\n𝐕𝐞𝐫𝐬𝐚̃𝐨 𝐝𝐨 𝐒𝐢𝐬𝐭𝐞𝐦𝐚: $Versao$\n\n---------------------------------------------------------------------------------------------"""

# Texto padrão do template
def atualizar_template(*args):
    arquivo_selecionado = var_template.get()
    template = templates.get(arquivo_selecionado, "Abertura de Chamado.txt")
    novo_template = carregar_template(template)
    global TEMPLATE
    TEMPLATE = novo_template
    atualizar_visualizacao()

def carregar_templates_disponiveis():
    arquivos = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".txt")]
    apelidos = {arquivo.replace(".txt", ""): arquivo for arquivo in arquivos}
    return apelidos

templates = carregar_templates_disponiveis()
var_template = tk.StringVar(value=list(templates.keys())[0] if templates else "Abertura de Chamado")
TEMPLATE = carregar_template(list(templates.values())[0] if templates else "Abertura de Chamado.txt")

# Função para atualizar o texto de pré-visualização dinamicamente
def atualizar_visualizacao(*args):
    final_text = TEMPLATE
    for campo, entrada in entradas.items():
        valor = entrada.get().strip()
        final_text = final_text.replace(f"${campo}$", valor if valor else f"${campo}$")
    final_text = final_text.replace("$PesquisaInterna$", "Sim" if var_pesquisa.get() else "Não")
    template_text.configure(state="normal")
    template_text.delete("1.0", tk.END)
    template_text.insert("1.0", final_text)
    template_text.configure(state="disabled")

# Função para copiar o conteúdo para a área de transferência
def copiar_template():
    texto = template_text.get("1.0", tk.END).strip()
    pyperclip.copy(texto)
    messagebox.showinfo("Copiado", "Texto copiado para a área de transferência.")

# Função para copiar Wildcard ou valor
def copiar_wildcard_ou_valor(campo):
    valor = entradas[campo].get().strip()
    if valor:
        pyperclip.copy(valor)
    else:
        pyperclip.copy(f"${campo}$")

# Campos e ícones
campos = [
    ("Nome", "👤"),
    ("Problema", "⚠️"),
    ("CNPJ", "🏢"),
    ("Telefone", "📞"),
    ("Email", "✉️"),
    ("Protocolo", "📄"),
    ("Versao", "📌"), #🛠️✨
]

entradas = {}

for i, (campo, icone) in enumerate(campos):
    frame = tk.Frame(app, bg="#f0f8ff")
    frame.pack(anchor="w", pady=5, fill="x")
    tk.Label(frame, text=icone, bg="#f0f8ff", font=("Arial", 14)).pack(side="left", padx=5)
    entrada = tk.Entry(frame, width=30, relief="flat", highlightbackground="#4682b4", highlightthickness=1)
    entrada.pack(side="left", fill="x", expand=True, padx=5)
    entrada.bind("<KeyRelease>", atualizar_visualizacao)
    entrada.bind("<FocusIn>", lambda e, widget=entrada: widget.configure(highlightthickness=2))
    entrada.bind("<FocusOut>", lambda e, widget=entrada: widget.configure(highlightthickness=1))
    entradas[campo] = entrada
    btn_wildcard = tk.Button(frame, text="Copiar", command=lambda c=campo: copiar_wildcard_ou_valor(c), bg="#4682b4", fg="white", relief="flat", font=("Arial", 10))
    btn_wildcard.pack(side="right")

# Checkbox para pesquisa interna
var_pesquisa = tk.BooleanVar(value=False)
checkbox_frame = tk.Frame(app, bg="#f0f8ff")
checkbox_frame.pack(anchor="w", pady=5, fill="x")
tk.Label(checkbox_frame, text="Pesquisa Interna:", bg="#f0f8ff", font=("Arial", 12)).pack(side="left", padx=5)
tk.Checkbutton(checkbox_frame, variable=var_pesquisa, bg="#f0f8ff", activebackground="#f0f8ff", command=atualizar_visualizacao).pack(side="left")

# Selecionar template
template_frame = tk.Frame(app, bg="#f0f8ff")
template_frame.pack(anchor="w", pady=5, fill="x")
tk.Label(template_frame, text="Template:", bg="#f0f8ff", font=("Arial", 12)).pack(side="left", padx=5)
tk.OptionMenu(template_frame, var_template, *(templates.keys() if templates else ["template_padrao"]), command=atualizar_template).pack(side="left")

# Campo do template e botões
template_text = tk.Text(app, height=10, width=30, relief="flat", highlightbackground="#4682b4", highlightthickness=1)
template_text.pack(pady=10, fill="x")
template_text.insert("1.0", TEMPLATE)
template_text.configure(state="disabled", bg="#e6f7ff")

btn_copiar = tk.Button(app, text="Copiar Texto", command=copiar_template, bg="#4682b4", fg="white", relief="flat", font=("Arial", 12))
btn_copiar.pack(pady=5)

# Atualização inicial do texto de pré-visualização
atualizar_visualizacao()

app.mainloop()
