# Linx Fast 2.0 🚀

Uma aplicação desktop desenvolvida para agilizar e padronizar a comunicação em equipes de suporte técnico, permitindo o uso de templates personalizáveis com campos dinâmicos.

## Índice

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Como Usar](#como-usar)
- [Recursos Avançados](#recursos-avançados)
- [Temas e Personalização](#temas-e-personalização)
- [Teclas de Atalho](#teclas-de-atalho)

## Visão Geral

O Linx Fast 2.0 é uma ferramenta projetada para aumentar a produtividade de equipes de suporte técnico, oferecendo uma interface intuitiva para criação, gerenciamento e uso de templates de comunicação. Com suporte a campos dinâmicos, lógica condicional e integração com NocoDB, a aplicação torna o processo de comunicação mais eficiente e padronizado.

## Funcionalidades

### Gerenciamento de Templates

- ✏️ Editor de templates com interface gráfica
- 📁 Organização em categorias
- 🔄 Sincronização com NocoDB
- ⭐ Sistema de favoritos
- 🔒 Proteção de templates importantes

### Interface Principal

- 🎯 Modo Simples para acesso rápido
- 📋 Cópia rápida para área de transferência
- 👀 Visualização prévia do resultado
- ↩️ Desfazer/Refazer alterações (Ctrl+Z/Ctrl+Y)
- 📌 Fixar janela sempre no topo
- 🔑 Definição de Senha Diária para cópia rápida

### Campos Dinâmicos

- 📝 Campos de texto expansíveis
- ☑️ Caixas de seleção (checkbox)
- 🔘 Botões de rádio
- 🔄 Switches
- 🔍 Validação de campos obrigatórios

## Como Usar

1. **Seleção de Template**
   - Escolha um template no menu suspenso superior
   - Use o botão de edição (✏️) para modificar ou criar templates
   - Modo Simples disponível para acesso rápido

2. **Preenchimento dos Campos**
   - Preencha os campos fixos e dinâmicos
   - Campos em vermelho são obrigatórios
   - Clique com botão direito em campos fixos para alternar entre modo padrão/expandido

3. **Finalização**
   - Clique em "Copiar para área de transferência" para copiar o resultado
   - Use "Visualizar Resultado" para conferir antes de copiar
   - Campos em branco serão destacados em vermelho

### Tipos de Campos

1. **Checkbox**: `$[checkbox]Campo$`
   - Retorna "Sim" ou "Não"

2. **Switch**: `$[switch]Campo$`
   - Similar ao checkbox, mais visual

3. **Radio**: `$[radio:Op1|Op2|Op3]Campo$`
   - Permite escolha entre opções predefinidas

4. **Campos Condicionais**: `$Campo?TextoSePreenchido|TextoSeVazio$`
   - Conteúdo dinâmico baseado no preenchimento

### Campos Automáticos

- 📅 Data atual: `$Agora[dd/MM/yyyy]$`
- ⏰ Hora atual: `$Agora[HH:mm:ss]$`

## Recursos Avançados

### Integração NocoDB

- Sincronização bidirecional de templates
- Importação/exportação de templates
- Versionamento e histórico de alterações

### Sistema de Logs

- Registro detalhado de operações
- Rotação automática de arquivos de log
- Níveis de log configuráveis

### Backup e Segurança

- Proteção de templates importantes
  - Favoritos
  - Protegidos

## Temas e Personalização

### Temas Disponíveis

- 🌞 Modo Claro/Escuro
- 🎨 Temas personalizados em JSON
- 🎉 Temas especiais para datas comemorativas

### Personalização

- Interface adaptável
- Campos expansíveis configuráveis
- Posicionamento e tamanho da janela salvos automaticamente

## Teclas de Atalho

- `Ctrl + Z`: Desfazer alterações nos campos
- `Ctrl + Y`: Refazer alterações nos campos
- `Tab/Shift+Tab`: Navegar entre campos
- `Esc`: Fechar janelas de diálogo

## Requisitos Técnicos

- Python 3.6+
- CustomTkinter
- Módulos adicionais: ver requirements.txt

---

Desenvolvido por Hamilton Junior 👨‍💻
