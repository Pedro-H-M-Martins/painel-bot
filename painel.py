import discord
from discord.ext import commands
from discord import ui
import os
from flask import Flask
from threading import Thread

# --- INTENTS ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURAÇÃO ---
CANAL_LOGS_ID = 1425936662223130794  # Canal de logs
PATENTES = [
    {"nome": "Soldado", "id": 111111111111111111},
    {"nome": "Cabo", "id": 222222222222222222},
    {"nome": "Sargento", "id": 333333333333333333},
]
CURSOS = [
    {"nome": "Curso Básico", "id": 101},
    {"nome": "Curso Avançado", "id": 102},
]

# --- FLASK PARA MANTER RENDER ATIVO ---
app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

Thread(target=run).start()

# --- FUNÇÕES AUXILIARES ---
async def enviar_log(guild, mensagem_log):
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        await canal_logs.send(mensagem_log)

def filtrar_membros(guild, filtro):
    filtro_lower = filtro.lower()
    membros_filtrados = [m for m in guild.members if not m.bot and filtro_lower in m.name.lower()]
    return membros_filtrados[:25]

# --- MODAL PROFISSIONAL ---
class PainelModal(ui.Modal, title="Painel de Gerenciamento 4º BpChoque"):
    def __init__(self, guild, filtro_membro=""):
        super().__init__()
        self.guild = guild

        # INPUT de filtro para membros
        self.filtro_input = ui.TextInput(
            label="Filtrar Membro (digite parte do nome)",
            placeholder="Ex: Pedro",
            required=False,
            max_length=50
        )
        self.add_item(self.filtro_input)

        # Dropdown de membros
        membros_filtrados = filtrar_membros(guild, filtro_membro)
        membros_opts = [discord.SelectOption(label=m.name, value=str(m.id)) for m in membros_filtrados]
        self.membros_select = ui.Select(
            placeholder="Escolha um membro...",
            options=membros_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_membros"
        )
        self.add_item(self.membros_select)

        # Dropdown de patentes
        patentes_opts = [discord.SelectOption(label=p['nome'], value=str(p['id'])) for p in PATENTES]
        self.patente_select = ui.Select(
            placeholder="Alterar Patente",
            options=patentes_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_patente"
        )
        self.add_item(self.patente_select)

        # Dropdown de cursos
        cursos_opts = [discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CURSOS]
        self.curso_select = ui.Select(
            placeholder="Alterar Curso",
            options=cursos_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_curso"
        )
        self.add_item(self.curso_select)

        # Botões de ação
        self.aprovar = ui.Button(label="Aprovar", style=discord.ButtonStyle.green, custom_id="painel_btn_aprovar")
        self.remover = ui.Button(label="Remover", style=discord.ButtonStyle.red, custom_id="painel_btn_remover")
        self.excluir = ui.Button(label="Excluir", style=discord.ButtonStyle.danger, custom_id="painel_btn_excluir")
        self.add_item(self.aprovar)
        self.add_item(self.remover)
        self.add_item(self.excluir)

    async def on_submit(self, interaction: discord.Interaction):
        filtro_digitado = self.filtro_input.value or ""
        membros_filtrados = filtrar_membros(self.guild, filtro_digitado)
        if not membros_filtrados:
            await interaction.response.send_message("Nenhum membro encontrado com esse filtro.", ephemeral=True)
            return

        membro_id = int(self.membros_select.values[0])
        membro = self.guild.get_member(membro_id)
        if not membro:
            await interaction.response.send_message("Membro não encontrado.", ephemeral=True)
            return

        # ALTERAR PATENTE
        patente_id = int(self.patente_select.values[0])
        patente_nome = next((p['nome'] for p in PATENTES if p['id']==patente_id), "Desconhecido")
        patente_obj = discord.utils.get(self.guild.roles, name=patente_nome)

        if patente_obj:
            cargos_a_remover = [discord.utils.get(self.guild.roles, name=r['nome']) for r in PATENTES]
            estagiario = discord.utils.get(self.guild.roles, name="Estagiário")
            if estagiario:
                cargos_a_remover.append(estagiario)
            for r in cargos_a_remover:
                if r and r in membro.roles:
                    await membro.remove_roles(r)
            await membro.add_roles(patente_obj)

        # ALTERAR CURSO
        curso_id = int(self.curso_select.values[0])
        curso_nome = next((c['nome'] for c in CURSOS if c['id']==curso_id), "Desconhecido")

        # LOG
        acao_msg = f"{membro.name} atualizado: Patente={patente_nome} / Curso={curso_nome}"
        await enviar_log(self.guild, acao_msg)
        await interaction.response.send_message(f"{acao_msg}", ephemeral=True)

# --- VIEW PARA ABRIR MODAL ---
class PainelView(ui.View):
    def __init__(self, guild, filtro_membro=""):
        super().__init__(timeout=None)
        self.guild = guild
        self.filtro_membro = filtro_membro

    @ui.button(label="Abrir Painel", style=discord.ButtonStyle.blurple, custom_id="painel_btn_abrir")
    async def abrir_modal(self, button: ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(PainelModal(self.guild, self.filtro_membro))

# --- COMANDO ---
@bot.command()
async def painel(ctx, filtro: str = ""):
    view = PainelView(ctx.guild, filtro)
    await ctx.send("Clique para abrir o painel de gerenciamento:", view=view)

# --- EVENTOS DE MEMBRO ---
@bot.event
async def on_member_join(member):
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        await canal_logs.send(f"{member.name} entrou no servidor.")

@bot.event
async def on_member_remove(member):
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        await canal_logs.send(f"{member.name} foi removido do servidor.")

# --- EXECUÇÃO ---
bot.run(os.environ['TOKEN'])
