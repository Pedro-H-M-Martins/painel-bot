import discord
from discord.ext import commands
from discord import ui
from flask import Flask
from threading import Thread
import os
from datetime import datetime

# ---------------- CONFIGURAÇÕES ----------------
TOKEN = os.environ['TOKEN']  # Token do bot
CANAL_PAINEL_ID = 1425995003095678996  # Canal onde ficará o painel
CANAL_LOGS_ID = 1425936662223130794   # Canal de logs separado

CARGOS = [
    {"nome": "Soldado", "id": 111111111111111111},
    {"nome": "Cabo", "id": 222222222222222222},
    {"nome": "Sargento", "id": 333333333333333333},
]

CURSOS = [
    {"nome": "Curso Básico", "id": 101},
    {"nome": "Curso Avançado", "id": 102},
]

logs_acoes = []

# ---------------- FLASK PARA RENDER ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# ---------------- BOT ----------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- FUNÇÃO DE LOG ----------------
async def registrar_log(texto: str, guild: discord.Guild):
    logs_acoes.append(texto)
    canal_logs = bot.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        await canal_logs.send(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {texto}")

# ---------------- DROPDOWNS ----------------
class MembroDropdown(ui.Select):
    def __init__(self, guild):
        membros = [discord.SelectOption(label=m.name, value=str(m.id)) for m in guild.members if not m.bot]
        super().__init__(placeholder="Selecione um membro...", options=membros, min_values=1, max_values=1, custom_id="select_membro")

class PatenteDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CARGOS]
        super().__init__(placeholder="Patente", options=options, min_values=1, max_values=1, custom_id="select_patente")

class CursoDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CURSOS]
        super().__init__(placeholder="Curso", options=options, min_values=1, max_values=1, custom_id="select_curso")

# ---------------- VIEW DO PAINEL ----------------
class PainelView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

        # ActionRow 1: Dropdown de membro
        row1 = ui.ActionRow()
        row1.add_item(MembroDropdown(guild))
        self.add_item(row1)

        # ActionRow 2: Dropdown de patente
        row2 = ui.ActionRow()
        row2.add_item(PatenteDropdown())
        self.add_item(row2)

        # ActionRow 3: Dropdown de curso
        row3 = ui.ActionRow()
        row3.add_item(CursoDropdown())
        self.add_item(row3)

        # ActionRow 4: Botões Confirmar e Remover
        row4 = ui.ActionRow()
        row4.add_item(ui.Button(label="Confirmar", style=discord.ButtonStyle.green, custom_id="acao_confirmar"))
        row4.add_item(ui.Button(label="Remover", style=discord.ButtonStyle.red, custom_id="acao_remover"))
        self.add_item(row4)


# ---------------- FUNÇÃO PARA ATUALIZAR PAINEL ----------------
async def atualizar_painel(guild: discord.Guild):
    canal = bot.get_channel(CANAL_PAINEL_ID)
    if canal:
        resumo = "\n".join(logs_acoes[-10:]) if logs_acoes else "Nenhuma ação recente."
        embed = discord.Embed(
            title="4º BpChoque – Painel de Gerenciamento",
            color=0x1ABC9C,
            description=resumo
        )
        view = PainelView(guild)
        await canal.send(embed=embed, view=view)

# ---------------- EVENTOS DE MEMBRO ----------------
@bot.event
async def on_member_join(member):
    await registrar_log(f"{member.name} entrou.", member.guild)
    await atualizar_painel(member.guild)

@bot.event
async def on_member_remove(member):
    await registrar_log(f"{member.name} removido.", member.guild)
    await atualizar_painel(member.guild)

# ---------------- COMANDO PARA ABRIR PAINEL ----------------
@bot.command()
async def painel(ctx):
    view = PainelView(ctx.guild)
    await ctx.send("Painel de gerenciamento 4ºBpChoque", view=view)

# ---------------- EVENTO DE BOTÕES ----------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return

    guild = interaction.guild
    custom_id = interaction.data['custom_id']

    # Identificar membro selecionado
    selected_member = None
    for child in interaction.message.components[0].children:
        if isinstance(child, ui.Select):
            selected_member = guild.get_member(int(child.values[0]))
            break

    # Confirmar alterações (patente + curso)
    if custom_id == "acao_confirmar":
        if selected_member:
            # Remover patente anterior + estagiário
            cargos_remover = [c['nome'] for c in CARGOS]
            cargos_remover.append("Estagiário")
            for cargo in cargos_remover:
                role = discord.utils.get(guild.roles, name=cargo)
                if role and role in selected_member.roles:
                    await selected_member.remove_roles(role)

            # Adicionar nova patente
            patente_id = int(interaction.message.components[0].children[1].values[0])
            patente_nome = next((c['nome'] for c in CARGOS if c['id'] == patente_id), None)
            if patente_nome:
                role = discord.utils.get(guild.roles, name=patente_nome)
                if role:
                    await selected_member.add_roles(role)

            # Curso
            curso_id = int(interaction.message.components[1].children[0].values[0])
            curso_nome = next((c['nome'] for c in CURSOS if c['id'] == curso_id), None)

            await registrar_log(f"{selected_member.name} atualizado: {patente_nome} / {curso_nome}", guild)
            await interaction.response.send_message(f"{selected_member.name} atualizado: {patente_nome} / {curso_nome}", ephemeral=True)
            await atualizar_painel(guild)
        else:
            await interaction.response.send_message("Selecione um membro primeiro.", ephemeral=True)

    # Remover membro
    elif custom_id == "acao_remover":
        if selected_member:
            await selected_member.kick(reason="Removido pelo painel")
            await registrar_log(f"{selected_member.name} removido do servidor.", guild)
            await interaction.response.send_message(f"{selected_member.name} removido do servidor.", ephemeral=True)
            await atualizar_painel(guild)
        else:
            await interaction.response.send_message("Selecione um membro primeiro.", ephemeral=True)

# ---------------- RODAR BOT ----------------
bot.run(TOKEN)

