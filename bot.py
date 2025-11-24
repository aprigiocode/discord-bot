import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree


# Armazenamento de eventos
eventos = {}

# Modal para criar nova ação


class CriarAcaoModal(Modal):
    def __init__(self, author):
        super().__init__(title="Criar Nova Ação")
        self.author = author

        self.nome = TextInput(
            label="Nome da Ação", placeholder="Digite o nome da ação", required=True)
        self.add_item(self.nome)

        self.data = TextInput(label="Data da Ação",
                              placeholder="Ex: 23/11/2025", required=True)
        self.add_item(self.data)

        self.hora = TextInput(label="Hora da Ação",
                              placeholder="Ex: 14:00", required=True)
        self.add_item(self.hora)

        self.quantidade = TextInput(
            label="Número de Participantes", placeholder="Ex: 10", required=True)
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantidade_int = int(self.quantidade.value)
            if quantidade_int <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Quantidade inválida! Use apenas números maiores que 0.", ephemeral=True)
            return

        evento_id = len(eventos) + 1
        eventos[evento_id] = {
            "nome": self.nome.value,
            "data": self.data.value,
            "hora": self.hora.value,
            "quantidade": quantidade_int,
            "participantes": [],
            "reservas": [],
            "autor_id": interaction.user.id,
            "autor_name": interaction.user.display_name,
            "finalizado": False
        }

        view = AcaoView(evento_id)
        embed = await gerar_embed(evento_id)
        await interaction.response.send_message(embed=embed, view=view)

# Gera embed estilo painel de presença


async def gerar_embed(evento_id):
    evento = eventos[evento_id]

    if evento.get("finalizado", False):
        status_texto = "⛔ Finalizado"
        cor_embed = discord.Color.dark_grey()
    elif len(evento['participantes']) >= evento['quantidade']:
        status_texto = "🔴 Cheio"
        cor_embed = discord.Color.red()
    elif len(evento['participantes']) >= evento['quantidade'] * 0.7:
        status_texto = "🟡 Quase cheio"
        cor_embed = discord.Color.gold()
    else:
        status_texto = "🟢 Aberto"
        cor_embed = discord.Color.green()

    embed = discord.Embed(
        title=f"📌 Ação: {evento['nome']}",
        description=f"Status: {status_texto}\nClique nos botões abaixo!",
        color=cor_embed
    )

    autor = bot.get_user(evento['autor_id'])
    if autor:
        embed.set_thumbnail(url=autor.display_avatar.url)

    embed.add_field(name="📅 Data", value=evento['data'], inline=True)
    embed.add_field(name="⏰ Hora", value=evento['hora'], inline=True)
    embed.add_field(
        name="👥 Vagas", value=f"{len(evento['participantes'])}/{evento['quantidade']}", inline=True)
    embed.add_field(name="📝 Responsável",
                    value=f"{evento['autor_name']}", inline=False)

    # Mini-avatar display, máximo 20 participantes visíveis
    def formatar_lista(usuarios, emoji):
        lista = " ".join(
            [f"{emoji}[{u.display_name}]({u.display_avatar.url})" for u in usuarios[:20]])
        if len(usuarios) > 20:
            lista += f" +{len(usuarios)-20}..."
        return lista or "Nenhum"

    embed.add_field(name="✅ Participantes", value=formatar_lista(
        evento['participantes'], "🟢 "), inline=False)
    embed.add_field(name="⏳ Reservas", value=formatar_lista(
        evento['reservas'], "🟡 "), inline=False)

    return embed

# View com botões funcionais


class AcaoView(View):
    def __init__(self, evento_id):
        super().__init__(timeout=None)
        self.evento_id = evento_id

        self.participar_button = Button(
            label="Participar", style=discord.ButtonStyle.green)
        self.participar_button.callback = self.participar
        self.add_item(self.participar_button)

        self.sair_button = Button(
            label="Sair da Ação", style=discord.ButtonStyle.red)
        self.sair_button.callback = self.sair
        self.add_item(self.sair_button)

        self.reservar_button = Button(
            label="Reservar", style=discord.ButtonStyle.blurple)
        self.reservar_button.callback = self.reservar
        self.add_item(self.reservar_button)

        self.finalizar_button = Button(
            label="Finalizar Ação", style=discord.ButtonStyle.gray)
        self.finalizar_button.callback = self.finalizar
        self.add_item(self.finalizar_button)

    async def participar(self, interaction: discord.Interaction):
        evento = eventos[self.evento_id]
        if evento.get("finalizado", False):
            await interaction.response.send_message("Esta ação já foi finalizada!", ephemeral=True)
            return

        usuario = interaction.user
        if usuario.id in [u.id for u in evento['participantes']]:
            await interaction.response.send_message("Você já está participando!", ephemeral=True)
            return

        if len(evento['participantes']) >= evento['quantidade']:
            await interaction.response.send_message("A ação está cheia! Use o botão Reservar.", ephemeral=True)
            return

        evento['participantes'].append(usuario)
        if usuario in evento['reservas']:
            evento['reservas'].remove(usuario)
        await self.atualizar_embed(interaction)
        await interaction.response.send_message(f"Você entrou na ação **{evento['nome']}**!", ephemeral=True)

    async def sair(self, interaction: discord.Interaction):
        evento = eventos[self.evento_id]
        usuario = interaction.user
        if usuario.id not in [u.id for u in evento['participantes']]:
            await interaction.response.send_message("Você não está participando desta ação.", ephemeral=True)
            return

        evento['participantes'] = [
            u for u in evento['participantes'] if u.id != usuario.id]

        # Promove primeiro da reserva
        if evento['reservas']:
            novo_participante = evento['reservas'].pop(0)
            evento['participantes'].append(novo_participante)
            try:
                await novo_participante.send(f"Você foi promovido de reserva para participante na ação **{evento['nome']}**!")
            except discord.Forbidden:
                pass

        await self.atualizar_embed(interaction)
        await interaction.response.send_message("Você saiu da ação.", ephemeral=True)

    async def reservar(self, interaction: discord.Interaction):
        evento = eventos[self.evento_id]
        usuario = interaction.user
        if usuario in evento['participantes']:
            await interaction.response.send_message("Você já está participando da ação!", ephemeral=True)
            return
        if usuario in evento['reservas']:
            await interaction.response.send_message("Você já está na lista de reservas!", ephemeral=True)
            return
        if len(evento['participantes']) < evento['quantidade']:
            await interaction.response.send_message("Ainda há vagas! Use o botão Participar.", ephemeral=True)
            return

        evento['reservas'].append(usuario)
        await self.atualizar_embed(interaction)
        await interaction.response.send_message("Você entrou na lista de reservas.", ephemeral=True)

    async def finalizar(self, interaction: discord.Interaction):
        evento = eventos[self.evento_id]
        if interaction.user.id != evento['autor_id']:
            await interaction.response.send_message("Apenas o criador da ação pode finalizá-la!", ephemeral=True)
            return

        evento['finalizado'] = True
        self.participar_button.disabled = True
        self.sair_button.disabled = True
        self.reservar_button.disabled = True
        self.finalizar_button.disabled = True

        embed = await gerar_embed(self.evento_id)
        embed.description += "\n\n⛔ Ação finalizada pelo organizador."
        await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_embed(self, interaction):
        embed = await gerar_embed(self.evento_id)
        await interaction.response.edit_message(embed=embed, view=self)

# Slash command para criar ação


@tree.command(name="acao", description="Cria uma nova ação", guild=discord.Object(id=GUILD_ID))
async def acao(interaction: discord.Interaction):
    modal = CriarAcaoModal(author=interaction.user)
    await interaction.response.send_modal(modal)


@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot conectado como {bot.user}")

# Inicialização
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

bot.run(os.environ['DISCORD_TOKEN'])


