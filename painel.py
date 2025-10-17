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

# --- FLASK PARA RENDER ---
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

# --- VIEW DO PAINEL ÚNICO ---
class PainelView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.membro_selecionado = None
        self.patente_selecionada = None
        self.curso_selecionado = None

        # --- Quadrado 1: Selecionar Membro ---
        membros_opts = [discord.SelectOption(label=m.name, value=str(m.id)) for m in guild.members if not m.bot]
        self.membros_select = ui.Select(
            placeholder="Escolha um membro...",
            options=membros_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_membros"
        )
        self.membros_select.callback = self.selecionar_membro
        self.add_item(self.membros_select)

        # --- Quadrado 2: Alterar Patente ---
        patentes_opts = [discord.SelectOption(label=p['nome'], value=str(p['id'])) for p in PATENTES]
        self.patente_select = ui.Select(
            placeholder="Alterar Patente",
            options=patentes_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_patente"
        )
        self.patente_select.callback = self.selecionar_patente
        self.add_item(self.patente_select)

        # --- Quadrado 3: Alterar Curso ---
        cursos_opts = [discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CURSOS]
        self.curso_select = ui.Select(
            placeholder="Alterar Curso",
            options=cursos_opts,
            min_values=1,
            max_values=1,
            custom_id="painel_select_curso"
        )
        self.curso_select.callback = self.selecionar_curso
        self.add_item(self.curso_select)

        # --- Quadrado 4: Ações ---
        btn_confirmar = ui.Button(label="Confirmar Alterações", style=discord.ButtonStyle.green)
        btn_confirmar.callback = self.confirmar_alteracoes
        self.add_item(btn_confirmar)

        btn_remover = ui.Button(label="Remover Membro", style=discord.ButtonStyle.red)
        btn_remover.callback = self.remover_membro
        self.add_item(btn_remover)

    # --- CALLBACKS ---
    async def selecionar_membro(self, interaction: discord.Interaction):
        membro_id = int(self.membros_select.values[0])
        self.membro_selecionado = self.guild.get_member(membro_id)
        await interaction.response.send_message(f"Membro selecionado: {self.membro_selecionado.name}", ephemeral=True)

    async def selecionar_patente(self, interaction: discord.Interaction):
        patente_id = int(self.patente_select.values[0])
        self.patente_selecionada = next((p for p in PATENTES if p['id']==patente_id), None)
        await interaction.response.send_message(f"Patente selecionada: {self.patente_selecionada['nome']}", ephemeral=True)

    async def selecionar_curso(self, interaction: discord.Interaction):
        curso_id = int(self.curso_select.values[0])
        self.curso_selecionado = next((c for c in CURSOS if c['id']==curso_id), None)
        await interaction.response.send_message(f"Curso selecionado: {self.curso_selecionado['nome']}", ephemeral=True)

    async def confirmar_alteracoes(self, interaction: discord.Interaction):
        if not self.membro_selecionado:
            await interaction.response.send_message("Selecione um membro primeiro.", ephemeral=True)
            return

        # Aplicar Patente
        if self.patente_selecionada:
            patente_nome = self.patente_selecionada['nome']
            patente_obj = discord.utils.get(self.guild.roles, name=patente_nome)

            # Remover patente antiga + estagiário
            cargos_remover = [discord.utils.get(self.guild.roles, name=r['nome']) for r in PATENTES]
            estagiario = discord.utils.get(self.guild.roles, name="Estagiário")
            if estagiario:
                cargos_remover.append(estagiario)
            for r in cargos_remover:
                if r and r in self.membro_selecionado.roles:
                    await self.membro_selecionado.remove_roles(r)
            if patente_obj:
                await self.membro_selecionado.add_roles(patente_obj)

        # Aplicar Curso
        curso_nome = None
        if self.curso_selecionado:
            curso_nome = self.curso_selecionado['nome']

        # Log
        msg = f"{self.membro_selecionado.name} atualizado"
        if self.patente_selecionada:
            msg += f": Patente={self.patente_selecionada['nome']}"
        if curso_nome:
            msg += f" / Curso={curso_nome}"
        await enviar_log(self.guild, msg)
        await interaction.response.send_message(f"Ações aplicadas: {msg}", ephemeral=True)

    async def remover_membro(self, interaction: discord.Interaction):
        if not self.membro_selecionado:
            await interaction.response.send_message("Selecione um membro primeiro.", ephemeral=True)
            return
        await self.membro_selecionado.kick(reason="Removido pelo painel")
        await enviar_log(self.guild, f"{self.membro_selecionado.name} removido pelo painel")
        await interaction.response.send_message(f"{self.membro_selecionado.name} removido do servidor.", ephemeral=True)
        self.membro_selecionado = None

# --- COMANDO PARA ABRIR O PAINEL ---
@bot.command()
async def painel(ctx):
    view = PainelView(ctx.guild)
    await ctx.send("Painel de Gerenciamento 4º BpChoque:", view=view)

# --- EVENTOS DE MEMBRO ---
@bot.event
async def on_member_join(member):
    await enviar_log(member.guild, f"{member.name} entrou no servidor.")

@bot.event
async def on_member_remove(member):
    await enviar_log(member.guild, f"{member.name} foi removido do servidor.")

# --- EXECUÇÃO ---
bot.run(os.environ['TOKEN'])
