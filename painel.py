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

# ---------------- MODAL ----------------
class AlterarModal(ui.Modal, title="Alterar Patente / Curso"):
    def __init__(self, membro):
        super().__init__()
        self.membro = membro

        self.patente_select = ui.Select(
            placeholder="Escolha a nova patente",
            options=[discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CARGOS],
            custom_id="modal_patente"
        )
        self.add_item(self.patente_select)

        self.curso_select = ui.Select(
            placeholder="Escolha o curso",
            options=[discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CURSOS],
            custom_id="modal_curso"
        )
        self.add_item(self.curso_select)

    async def on_submit(self, interaction: discord.Interaction):
        # Remover patentes antigas + estagiário
        cargos_remover = [c['nome'] for c in CARGOS]
        cargos_remover.append('Estagiário')
        for cargo in cargos_remover:
            role = discord.utils.get(self.membro.guild.roles, name=cargo)
            if role in self.membro.roles:
                await self.membro.remove_roles(role)

        # Adicionar nova patente
        patente_id = int(self.patente_select.values[0])
        patente_nome = next((c['nome'] for c in CARGOS if c['id'] == patente_id), None)
        if patente_nome:
            role = discord.utils.get(self.membro.guild.roles, name=patente_nome)
            if role:
                await self.membro.add_roles(role)

        # Log e curso
        curso_id = int(self.curso_select.values[0])
        curso_nome = next((c['nome'] for c in CURSOS if c['id'] == curso_id), None)
        logs_acoes.append(f"{self.membro.name} atualizado: {patente_nome} / {curso_nome}")

        await interaction.response.send_message(
            f"{self.membro.name} atualizado: {patente_nome} / {curso_nome}", ephemeral=True
        )
        await atualizar_painel(self.membro.guild)

# ---------------- DROPDOWNS ----------------
class MembroDropdown(ui.Select):
    def __init__(self, guild):
        membros = [discord.SelectOption(label=m.name, value=str(m.id)) for m in guild.members if not m.bot]
        super().__init__(placeholder="Escolha um membro...", options=membros, min_values=1, max_values=1, custom_id="select_membro")

    async def callback(self, interaction: discord.Interaction):
        membro_id = int(self.values[0])
        membro = self.view.guild.get_member(membro_id)
        if membro:
            await interaction.response.send_modal(AlterarModal(membro))

class PatenteDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CARGOS]
        super().__init__(placeholder="Patente", options=options, min_values=1, max_values=1, custom_id="select_patente")

class CursoDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CURSOS]
        super().__init__(placeholder="Curso", options=options, min_values=1, max_values=1, custom_id="select_curso")

# ---------------- VIEW ----------------
class PainelView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

        # Row 1: membro + patente
        row1 = ui.ActionRow()
        row1.add_item(MembroDropdown(guild))
        row1.add_item(PatenteDropdown())
        self.add_item(row1)

        # Row 2: curso + botões
        row2 = ui.ActionRow()
        row2.add_item(CursoDropdown())
        row2.add_item(ui.Button(label="Confirmar", style=discord.ButtonStyle.green, custom_id="acao_confirmar"))
        row2.add_item(ui.Button(label="Remover", style=discord.ButtonStyle.red, custom_id="acao_remover"))
        self.add_item(row2)

# ---------------- FUNÇÕES ----------------
async def atualizar_painel(guild):
    canal = bot.get_channel(CANAL_PAINEL_ID)
    embed = discord.Embed(
        title="4º BpChoque – Painel de Gerenciamento",
        color=0x1ABC9C,
        description="\n".join(logs_acoes[-10:]) if logs_acoes else "Nenhuma ação recente."
    )
    view = PainelView(guild)
    await canal.send(embed=embed, view=view)

# ---------------- EVENTOS ----------------
@bot.event
async def on_member_join(member):
    logs_acoes.append(f"{member.name} entrou.")
    await atualizar_painel(member.guild)

@bot.event
async def on_member_remove(member):
    logs_acoes.append(f"{member.name} removido.")
    await atualizar_painel(member.guild)

# ---------------- COMANDO ----------------
@bot.command()
async def painel(ctx):
    view = PainelView(ctx.guild)
    await ctx.send("Painel de gerenciamento 4ºBpChoque", view=view)

# ---------------- EVENTO DE BOTÕES ----------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return

    custom_id = interaction.data['custom_id']
    guild = interaction.guild

    if custom_id == "acao_confirmar":
        await interaction.response.send_message("Clique no membro para abrir o modal e confirmar alterações.", ephemeral=True)

    elif custom_id == "acao_remover":
        selected_member = None
        for child in interaction.message.components[0].children:
            if isinstance(child, ui.Select):
                selected_member = guild.get_member(int(child.values[0]))
                break
        if selected_member:
            await selected_member.kick(reason="Removido pelo painel")
            logs_acoes.append(f"{selected_member.name} removido")
            await interaction.response.send_message(f"{selected_member.name} removido do servidor.", ephemeral=True)
            await atualizar_painel(guild)
        else:
            await interaction.response.send_message("Selecione um membro primeiro.", ephemeral=True)

# ---------------- RODAR BOT ----------------
bot.run(TOKEN)
