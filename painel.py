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

# Exemplo de cargos (nome + ID + cor)
CARGOS = [
    {"nome": "Soldado", "id": 111111111111111111, "emoji": "🟢"},
    {"nome": "Cabo", "id": 222222222222222222, "emoji": "🔵"},
    {"nome": "Sargento", "id": 333333333333333333, "emoji": "🟡"},
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
        embed.add_field(name=f"{cargo['emoji']} {cargo['nome']}", value=valor, inline=False)

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

# View do painel com botões e dropdowns
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
        membros = [
            discord.SelectOption(label=m.name, value=str(m.id))
            for m in guild.members if not m.bot
        ]
        super().__init__(placeholder="Escolha um membro...", options=membros, custom_id="select_membro", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        membro_id = int(self.values[0])
        membro = self.view.guild.get_member(membro_id)
        await interaction.response.send_message(f"Membro selecionado: {membro.name}", ephemeral=True)

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

# Função para atualizar painel e registrar log
async def atualizar_painel(guild, acao=None):
    canal = bot.get_channel(CANAL_PAINEL_ID)
    mensagem = await canal.fetch_message(MENSAGEM_PAINEL_ID)
    if acao:
        logs_acoes.append(acao)
    embed = criar_embed_painel(guild)
    view = PainelView(guild)
    await mensagem.edit(embed=embed, view=view)

# Rodando o bot
bot.run(os.environ['DISCORD_TOKEN'])
