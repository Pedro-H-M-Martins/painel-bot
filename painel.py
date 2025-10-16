import discord
from discord.ext import commands
from discord import ui
import os
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# IDs configuráveis
CANAL_PAINEL_ID = 123456789012345678  # ID do canal do painel
MENSAGEM_PAINEL_ID = 987654321098765432  # ID da mensagem do painel

# Exemplo de cargos
CARGOS = [
    {"nome": "Soldado", "id": 111111111111111111},
    {"nome": "Cabo", "id": 222222222222222222},
    {"nome": "Sargento", "id": 333333333333333333},
]

# Exemplo de cursos
CURSOS = [
    {"nome": "Curso Básico", "id": 101},
    {"nome": "Curso Avançado", "id": 102},
]

# Logs de ações
logs_acoes = []

# Função para criar embed do painel
def criar_embed_painel(guild):
    embed = discord.Embed(
        title="4º BpChoque – Painel de Gerenciamento",
        color=0x1ABC9C  # verde profissional
    )

    # Agrupar membros por cargo
    for cargo in CARGOS:
        membros_cargo = [m.name for m in guild.members if not m.bot and cargo["nome"] in [r.name for r in m.roles]]
        valor = "\n".join(membros_cargo) if membros_cargo else "Nenhum membro"
        embed.add_field(name=cargo['nome'], value=valor, inline=False)

    # Últimas ações
    if logs_acoes:
        embed.add_field(
            name="Últimas Ações",
            value="\n".join(logs_acoes[-10:]),  # últimas 10 ações
            inline=False
        )
    else:
        embed.add_field(name="Últimas Ações", value="Nenhuma ação registrada.", inline=False)

    embed.set_footer(text=f"Servidor: {guild.name} | Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    return embed

# View principal do painel
class PainelView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.add_item(MembroDropdown(guild))
        self.add_item(CargoDropdown())
        self.add_item(CursoDropdown())
        self.add_item(ui.Button(label="Aprovar", style=discord.ButtonStyle.green, custom_id="acao_aprovar"))
        self.add_item(ui.Button(label="Remover", style=discord.ButtonStyle.red, custom_id="acao_remover"))

# Dropdown de membros com autocomplete
class MembroDropdown(ui.Select):
    def __init__(self, guild):
        membros = [discord.SelectOption(label=m.name, value=str(m.id)) for m in guild.members if not m.bot]
        super().__init__(placeholder="Escolha um membro...", options=membros, custom_id="select_membro", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        membro_id = int(self.values[0])
        membro = self.view.guild.get_member(membro_id)
        # Abre Modal para alterar cargo ou curso do membro
        await interaction.response.send_modal(AlterarModal(membro))

# Modal para alterar cargo ou curso
class AlterarModal(ui.Modal, title="Alterar Cargo / Curso"):
    def __init__(self, membro):
        super().__init__()
        self.membro = membro

        # Dropdown de cargos
        self.cargo_select = ui.Select(
            placeholder="Escolha um cargo",
            options=[discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CARGOS],
            custom_id="modal_cargo"
        )
        self.add_item(self.cargo_select)

        # Dropdown de cursos
        self.curso_select = ui.Select(
            placeholder="Escolha um curso",
            options=[discord.SelectOption(label=c['nome'], value=str(c['id'])) for c in CURSOS],
            custom_id="modal_curso"
        )
        self.add_item(self.curso_select)

    async def on_submit(self, interaction: discord.Interaction):
        # Altera cargo
        cargo_id = int(self.cargo_select.values[0])
        cargo_nome = next((c['nome'] for c in CARGOS if c['id'] == cargo_id), "Desconhecido")
        cargo_obj = discord.utils.get(self.membro.guild.roles, name=cargo_nome)
        if cargo_obj:
            # Remove outros cargos do painel se existirem
            cargos_ids = [c['id'] for c in CARGOS]
            cargos_objs = [discord.utils.get(self.membro.guild.roles, id=i) for i in cargos_ids]
            for r in cargos_objs:
                if r in self.membro.roles:
                    await self.membro.remove_roles(r)
            await self.membro.add_roles(cargo_obj)
        
        # Altera curso (a lógica depende de como você gerencia cursos)
        curso_id = int(self.curso_select.values[0])
        curso_nome = next((c['nome'] for c in CURSOS if c['id'] == curso_id), "Desconhecido")
        # Aqui você pode registrar curso em algum banco ou role, dependendo do seu sistema

        # Registrar log
        logs_acoes.append(f"{self.membro.name} alterado para {cargo_nome} / {curso_nome}")
        await atualizar_painel(self.membro.guild)

        await interaction.response.send_message(f"{self.membro.name} atualizado: {cargo_nome} / {curso_nome}", ephemeral=True)

# Dropdown de cargos
class CargoDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CARGOS]
        super().__init__(placeholder="Escolha um cargo...", options=options, custom_id="select_cargo", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        cargo_id = int(self.values[0])
        cargo_nome = next((c["nome"] for c in CARGOS if c["id"] == cargo_id), "Desconhecido")
        await interaction.response.send_message(f"Cargo selecionado: {cargo_nome}", ephemeral=True)

# Dropdown de cursos
class CursoDropdown(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c["nome"], value=str(c["id"])) for c in CURSOS]
        super().__init__(placeholder="Escolha um curso...", options=options, custom_id="select_curso", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        curso_id = int(self.values[0])
        curso_nome = next((c["nome"] for c in CURSOS if c["id"] == curso_id), "Desconhecido")
        await interaction.response.send_message(f"Curso selecionado: {curso_nome}", ephemeral=True)

# Comando para enviar ou atualizar o painel
@bot.command()
async def painel(ctx):
    canal = bot.get_channel(CANAL_PAINEL_ID)
    mensagem = await canal.fetch_message(MENSAGEM_PAINEL_ID)
    embed = criar_embed_painel(ctx.guild)
    view = PainelView(ctx.guild)
    await mensagem.edit(embed=embed, view=view)
    await ctx.send("Painel atualizado!", delete_after=5)

# Atualização automática ao entrar ou sair
@bot.event
async def on_member_join(member):
    await atualizar_painel(member.guild, f"{member.name} entrou.")

@bot.event
async def on_member_remove(member):
    await atualizar_painel(member.guild, f"{member.name} removido.")

# Função para atualizar painel
async def atualizar_painel(guild, acao=None):
    canal = bot.get_channel(CANAL_PAINEL_ID)
    mensagem = await canal.fetch_message(MENSAGEM_PAINEL_ID)
    if acao:
        logs_acoes.append(acao)
    embed = criar_embed_painel(guild)
    view = PainelView(guild)
    await mensagem.edit(embed=embed, view=view)

# Rodando o bot
bot.run(os.environ['TOKEN'])

