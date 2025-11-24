import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Armazenamento dos eventos
eventos = {}

class EventoView(View):
    def __init__(self, evento_id):
        super().__init__(timeout=None)
        self.evento_id = evento_id

    @discord.ui.button(label="Participar", style=discord.ButtonStyle.green)
    async def participar(self, interaction: discord.Interaction, button: Button):
        evento = eventos[self.evento_id]
        usuario = interaction.user

        if usuario.id in [u.id for u in evento['participantes']]:
            await interaction.response.send_message("Você já está participando!", ephemeral=True)
            return

        if len(evento['participantes']) >= evento['quantidade']:
            # Coloca na lista de reservas
            if usuario.id in [u.id for u in evento['reservas']]:
                await interaction.response.send_message("Você já está na lista de reservas!", ephemeral=True)
            else:
                evento['reservas'].append(usuario)
                await interaction.response.send_message("O evento está cheio! Você foi adicionado à lista de reservas.", ephemeral=True)
            return

        evento['participantes'].append(usuario)
        await self.atualizar_embed(interaction)

    @discord.ui.button(label="Sair do evento", style=discord.ButtonStyle.red)
    async def sair(self, interaction: discord.Interaction, button: Button):
        evento = eventos[self.evento_id]
        usuario = interaction.user

        if usuario.id in [u.id for u in evento['participantes']]:
            evento['participantes'] = [u for u in evento['participantes'] if u.id != usuario.id]
            # Se houver reservas, move o primeiro da lista
            if evento['reservas']:
                proximo = evento['reservas'].pop(0)
                evento['participantes'].append(proximo)
            await self.atualizar_embed(interaction)
            await interaction.response.send_message("Você saiu do evento.", ephemeral=True)
            return

        if usuario.id in [u.id for u in evento['reservas']]:
            evento['reservas'] = [u for u in evento['reservas'] if u.id != usuario.id]
            await self.atualizar_embed(interaction)
            await interaction.response.send_message("Você saiu da lista de reservas.", ephemeral=True)
            return

        await interaction.response.send_message("Você não está participando nem na lista de reservas.", ephemeral=True)

    @discord.ui.button(label="Finalizar evento", style=discord.ButtonStyle.grey)
    async def finalizar(self, interaction: discord.Interaction, button: Button):
        evento = eventos[self.evento_id]
        if interaction.user.id != evento['responsavel'].id:
            await interaction.response.send_message("Somente o responsável pode finalizar o evento.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Evento **{evento['nome']}** finalizado",
            description=f"Responsável: {evento['responsavel'].mention}",
            color=discord.Color.red()
        )
        participantes_texto = ", ".join([u.mention for u in evento['participantes']]) if evento['participantes'] else "Nenhum"
        reservas_texto = ", ".join([u.mention for u in evento['reservas']]) if evento['reservas'] else "Nenhum"
        embed.add_field(name="Participantes", value=participantes_texto, inline=False)
        embed.add_field(name="Reservas", value=reservas_texto, inline=False)

        await interaction.response.edit_message(embed=embed, view=None)
        eventos.pop(self.evento_id)

    async def atualizar_embed(self, interaction):
        evento = eventos[self.evento_id]
        embed = discord.Embed(
            title=f"Evento: {evento['nome']}", color=discord.Color.blue()
        )
        embed.add_field(name="Data", value=evento['data'], inline=True)
        embed.add_field(name="Hora", value=evento['hora'], inline=True)
        embed.add_field(name="Vagas", value=f"{len(evento['participantes'])}/{evento['quantidade']}", inline=True)
        embed.add_field(name="Responsável", value=evento['responsavel'].mention, inline=True)

        participantes_texto = "\n".join([f"{u.display_name}" for u in evento['participantes']]) if evento['participantes'] else "Nenhum"
        reservas_texto = "\n".join([f"{u.display_name}" for u in evento['reservas']]) if evento['reservas'] else "Nenhum"
        embed.add_field(name="Participantes", value=participantes_texto, inline=False)
        embed.add_field(name="Reservas", value=reservas_texto, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

# Modal para criar ação
class CriarAcaoModal(Modal):
    def __init__(self):
        super().__init__(title="Criar nova ação")
        self.nome = TextInput(label="Nome da ação", placeholder="Ex: Treinamento", required=True)
        self.data = TextInput(label="Data", placeholder="Ex: 23/11/2025", required=True)
        self.hora = TextInput(label="Hora", placeholder="Ex: 14:00", required=True)
        self.quantidade = TextInput(label="Quantidade de participantes", placeholder="Ex: 10", required=True)
        self.add_item(self.nome)
        self.add_item(self.data)
        self.add_item(self.hora)
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantidade = int(self.quantidade.value)
        except ValueError:
            await interaction.response.send_message("Quantidade inválida! Use apenas números.", ephemeral=True)
            return

        evento_id = len(eventos) + 1
        eventos[evento_id] = {
            "nome": self.nome.value,
            "data": self.data.value,
            "hora": self.hora.value,
            "quantidade": quantidade,
            "responsavel": interaction.user,
            "participantes": [],
            "reservas": []
        }

        view = EventoView(evento_id)
        embed = discord.Embed(
            title=f"Evento: {self.nome.value}", color=discord.Color.blue()
        )
        embed.add_field(name="Data", value=self.data.value, inline=True)
        embed.add_field(name="Hora", value=self.hora.value, inline=True)
        embed.add_field(name="Vagas", value=f"0/{quantidade}", inline=True)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=True)
        embed.add_field(name="Participantes", value="Nenhum", inline=False)
        embed.add_field(name="Reservas", value="Nenhum", inline=False)

        await interaction.response.send_message(embed=embed, view=view)

# Comando slash
@bot.tree.command(name="acao", description="Criar uma nova ação")
async def acao(interaction: discord.Interaction):
    await interaction.response.send_modal(CriarAcaoModal())

# Inicialização
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

bot.run(os.environ['DISCORD_TOKEN'])
