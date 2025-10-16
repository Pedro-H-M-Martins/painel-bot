import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from threading import Thread
from flask import Flask

# --- Configurações ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # <-- ESSENCIAL para !comandos
bot = commands.Bot(command_prefix="!", intents=intents)

# Canais e cargos
CANAL_PAINEL = 1425995003095678996
CARGOS_AUTORIZADOS = ["1422801198158844045", "Subcomandante", "Oficial Superior"]

# Cargos de patente de exemplo
PATENTES = ["1422801678939324427", "1422801198158844045", "Sargento", "Tenente", "Capitão"]
# Cursos de exemplo
CURSOS = ["Curso Tático", "Curso Operacional", "Curso Avançado"]
# Cargo estagiário
ESTAGIARIO = "Estagiário"

# Motivos de exclusão de exemplo
MOTIVOS_EXCLUSAO = ["Inatividade", "Conduta inadequada", "Pedido próprio"]

# Canal de logs
LOG_CHANNEL_ID = 1425936662223130794  # Substitua pelo ID real do canal de logs

# Variável para guardar a mensagem do painel
painel_message = None

# --- Painel ---
class PainelGerenciamento(View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.selected_member = None
        self.guild = guild
        self.member_select = None
        self.update_member_select()

        # Botões principais
        btn_excluir = Button(label="Excluir", style=discord.ButtonStyle.danger, custom_id="btn_excluir")
        btn_excluir.callback = self.excluir
        self.add_item(btn_excluir)

        btn_promover = Button(label="Promover", style=discord.ButtonStyle.success, custom_id="btn_promover")
        btn_promover.callback = self.promover
        self.add_item(btn_promover)

        btn_cursos = Button(label="Gerenciar Cursos", style=discord.ButtonStyle.secondary, custom_id="btn_cursos")
        btn_cursos.callback = self.gerenciar_cursos
        self.add_item(btn_cursos)

    def update_member_select(self):
        """Atualiza a lista de membros no dropdown"""
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in self.guild.members if not m.bot]
        if self.member_select:
            self.remove_item(self.member_select)
        self.member_select = Select(placeholder="Selecione um membro...", options=options, min_values=1, max_values=1)
        self.member_select.callback = self.selecionar_membro
        self.add_item(self.member_select)

    async def selecionar_membro(self, interaction: discord.Interaction):
        member_id = int(self.member_select.values[0])
        self.selected_member = self.guild.get_member(member_id)
        await interaction.response.send_message(f"Membro selecionado: {self.selected_member.display_name}", ephemeral=True)

    async def excluir(self, interaction: discord.Interaction):
        if not self.selected_member:
            await interaction.response.send_message("Selecione um membro primeiro!", ephemeral=True)
            return

        class MotivoSelect(View):
            def __init__(self2):
                super().__init__(timeout=None)
                options = [discord.SelectOption(label=m, value=m) for m in MOTIVOS_EXCLUSAO]
                select = Select(placeholder="Selecione o motivo", options=options)
                select.callback = self2.motivo_callback
                self2.add_item(select)
                self2.member_inner = self.selected_member

            async def motivo_callback(self2, select_interaction: discord.Interaction):
                member = self2.member_inner
                motivo = select_interaction.data["values"][0]
                await member.kick(reason=motivo)
                await select_interaction.response.send_message(f"{member.display_name} excluído! Motivo: {motivo}", ephemeral=True)
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(f"🗑️ {member.mention} foi excluído por {interaction.user.mention}. Motivo: {motivo}")

        view = MotivoSelect()
        await interaction.response.send_message("Selecione o motivo de exclusão:", view=view, ephemeral=True)

    async def promover(self, interaction: discord.Interaction):
        if not self.selected_member:
            await interaction.response.send_message("Selecione um membro primeiro!", ephemeral=True)
            return

        class PatenteSelect(View):
            def __init__(self2):
                super().__init__(timeout=None)
                options = [discord.SelectOption(label=p, value=p) for p in PATENTES]
                select = Select(placeholder="Selecione a nova patente", options=options)
                select.callback = self2.promover_callback
                self2.add_item(select)
                self2.member_inner = self.selected_member

            async def promover_callback(self2, select_interaction: discord.Interaction):
                member = self2.member_inner
                roles_remove = [r for r in member.roles if r.name in PATENTES or r.name == ESTAGIARIO]
                await member.remove_roles(*roles_remove)
                new_role = discord.utils.get(interaction.guild.roles, name=select_interaction.data["values"][0])
                if new_role:
                    await member.add_roles(new_role)
                    await select_interaction.response.send_message(f"{member.display_name} promovido para {new_role.name}", ephemeral=True)
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(f"📈 {member.mention} promovido para {new_role.name} por {interaction.user.mention}")

        view = PatenteSelect()
        await interaction.response.send_message("Selecione a nova patente:", view=view, ephemeral=True)

    async def gerenciar_cursos(self, interaction: discord.Interaction):
        if not self.selected_member:
            await interaction.response.send_message("Selecione um membro primeiro!", ephemeral=True)
            return

        class CursosSelect(View):
            def __init__(self2):
                super().__init__(timeout=None)
                options = [discord.SelectOption(label=c, value=c) for c in CURSOS]
                select = Select(placeholder="Selecione cursos", options=options, min_values=0, max_values=len(CURSOS))
                select.callback = self2.cursos_callback
                self2.add_item(select)
                self2.member_inner = self.selected_member

            async def cursos_callback(self2, select_interaction: discord.Interaction):
                member = self2.member_inner
                remove_roles = [r for r in member.roles if r.name in CURSOS]
                await member.remove_roles(*remove_roles)
                add_roles = [discord.utils.get(interaction.guild.roles, name=c) for c in select_interaction.data["values"]]
                await member.add_roles(*filter(None, add_roles))
                await select_interaction.response.send_message(f"Cursos atualizados: {', '.join(select_interaction.data['values'])}", ephemeral=True)
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(f"📘 {member.mention} teve cursos atualizados por {interaction.user.mention}: {', '.join(select_interaction.data['values'])}")

        view = CursosSelect()
        await interaction.response.send_message("Selecione os cursos:", view=view, ephemeral=True)


# --- Comando para abrir painel ---
@bot.command()
async def painel(ctx):
    global painel_message
    print(f"Comando !painel chamado por {ctx.author}")  # <-- DEBUG
    if ctx.channel.id != CANAL_PAINEL:
        await ctx.send("Este comando só funciona no canal do painel.", delete_after=10)
        return
    if ctx.author != ctx.guild.owner and not any(str(c.id) in CARGOS_AUTORIZADOS or c.name in CARGOS_AUTORIZADOS for c in ctx.author.roles):
        await ctx.send("Você não tem permissão para usar o painel.", delete_after=10)
        return

    view = PainelGerenciamento(ctx.guild)
    painel_message = await ctx.send("💼 **Painel de Gerenciamento de Membros**", view=view)
    print("Painel enviado com sucesso!")  # <-- DEBUG


# --- Eventos para manter dropdown atualizado usando referência direta ---
@bot.event
async def on_member_join(member):
    global painel_message
    if painel_message and painel_message.guild == member.guild:
        view = PainelGerenciamento(member.guild)
        await painel_message.edit(view=view)

@bot.event
async def on_member_remove(member):
    global painel_message
    if painel_message and painel_message.guild == member.guild:
        view = PainelGerenciamento(member.guild)
        await painel_message.edit(view=view)


# --- Keep alive com Flask ---
app = Flask('')

@app.route('/')
def home():
    return "Painel do bot online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
bot.run(os.environ['TOKEN'])
