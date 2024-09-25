import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import random
import logging
import sqlite3
import os


TOKEN = os.getenv('DISCORD_TOKEN')


intents = discord.Intents.default()
intents.messages = True  # Ensure the bot can listen to messages
intents.guilds = True  # Ensure the bot can create threads

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Set up logging to monitor issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

confessions = []  # List to track confessions
confession_channel_id = 1184664936568336444  # Replace with your specific channel ID
moderation_channel_id = 1189703235297095771  # Replace with your moderation channel ID
last_confession_message_id = None  # To track the last confession message

# List of possible embed colors
embed_colors = [
    0x8572c6, 0xf2d8b6, 0xcd7d5e, 0x9071de, 0x2299e1,
    0xd786a4, 0x8f1df6, 0x976d5c, 0xaac1cf, 0x36f977,
    0x9da541, 0x3c668d, 0x4838df, 0xd71253, 0x455095,
    0x91cfa5
]

# Create a backup of the original color list to reset when colors are exhausted
original_embed_colors = embed_colors.copy()

# Database setup
conn = sqlite3.connect('confessions.db')
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS confessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    confession_number INTEGER
)
''')

# Load the confession number
cursor.execute('SELECT confession_number FROM confessions ORDER BY id DESC LIMIT 1')
result = cursor.fetchone()
confession_number = result[0] if result else 1331

# Function to increment and save the confession number
def update_confession_number():
    global confession_number
    confession_number += 1
    cursor.execute('INSERT INTO confessions (confession_number) VALUES (?)', (confession_number,))
    conn.commit()

# Function to get a unique color for each confession
def get_unique_color():
    global embed_colors
    if not embed_colors:
        embed_colors = original_embed_colors.copy()  # Reset color list when all colors are used
    color = random.choice(embed_colors)
    embed_colors.remove(color)
    return color

# Function to get the display name based on specific user ID rules
async def get_display_name_for_author(user_id):
    special_users = {
        568583831985061918: 1129626620932673577,  # Replace this user's name with another's
        152634950443728897: 847014869391507507,  # Same for this user
        278339474033999873: 971821280116502631,   # And this one
        1174199544225988728: 1204958320494903299 # And this one
    }
    
    if user_id in special_users:
        new_user_id = special_users[user_id]
        user = await client.fetch_user(new_user_id)
        return user.name
    else:
        user = await client.fetch_user(user_id)
        return user.name

# Define the modal class for Confession Submission
class ConfessionModal(Modal):
    def __init__(self):
        super().__init__(title="Submit a Confession")

        # Confession Content Text Box
        self.confession_content = TextInput(
            label="CONFESSION CONTENT",
            style=discord.TextStyle.long,
            placeholder="Type your confession here...",
            max_length=3999,
            required=True
        )
        self.add_item(self.confession_content)

        # Attachment Text Box (Optional)
        self.attachment = TextInput(
            label="ATTACHMENT (OPTIONAL)",
            style=discord.TextStyle.short,
            placeholder="Link to an image or file (optional)",
            required=False
        )
        self.add_item(self.attachment)

    async def on_submit(self, interaction: discord.Interaction):
        global last_confession_message_id
        channel = client.get_channel(confession_channel_id)
        mod_channel = client.get_channel(moderation_channel_id)
        
        if channel is None or mod_channel is None:
            await interaction.response.send_message(
                f":x: Could not find the required channels. Please check the channel IDs.",
                ephemeral=True
            )
            return

        # Get a unique color for the confession
        confession_color = get_unique_color()

        # Prepare the embed
        embed = discord.Embed(
            title=f"Anonymous Confession (#{confession_number})",
            description=f'"{self.confession_content.value}"',
            color=confession_color
        )
        embed.set_footer(text=f"❗ If this confession is ToS-breaking or overtly hateful, you can report it using /report {confession_number}")

        mod_embed = discord.Embed(
            title=f"Anonymous Confession (#{confession_number})",
            description=f'"{self.confession_content.value}"',
            color=confession_color
        )
        mod_embed.set_footer(text=f"Submitted by: {interaction.user.name}")

        if self.attachment.value:
            embed.set_image(url=self.attachment.value)
            mod_embed.set_image(url=self.attachment.value)

        # Send to confession channel
        view = View()
        view.add_item(Button(style=discord.ButtonStyle.primary, label="Submit a Confession!", custom_id="submit_confession"))
        view.add_item(Button(style=discord.ButtonStyle.secondary, label="Reply", custom_id="reply"))

        message = await channel.send(embed=embed, view=view)
        await mod_channel.send(embed=mod_embed)  # Send to the moderation channel

        # Track the confession by adding it to the list
        confessions.append({
            "number": confession_number,
            "content": self.confession_content.value,
            "attachment_url": self.attachment.value if self.attachment.value else None,
            "message_id": message.id  # Store the message ID
        })

        # Update the last confession message ID
        if last_confession_message_id:
            try:
                last_message = await channel.fetch_message(last_confession_message_id)
                if last_message:
                    await last_message.edit(view=None)  # Remove buttons from the last confession
            except discord.NotFound:
                pass

        last_confession_message_id = message.id
        update_confession_number()  # Increment and save the confession number

        await interaction.response.send_message(
            f":white_check_mark: Your confession has been added to {channel.mention}!",
            ephemeral=True
        )

# Slash command for confessing

@tree.command(name="confess", description="Submit an anonymous confession")
async def confess(interaction: discord.Interaction, confession: str, attachment: discord.Attachment = None):
    global last_confession_message_id
    channel = client.get_channel(confession_channel_id)
    mod_channel = client.get_channel(moderation_channel_id)
    
    if channel is None or mod_channel is None:
        await interaction.response.send_message(
            f":x: Could not find the required channels. Please check the channel IDs.",
            ephemeral=True
        )
        return

    # Get a unique color for the confession
    confession_color = get_unique_color()

    # Prepare the embed
    embed = discord.Embed(
        title=f"Anonymous Confession (#{confession_number})",
        description=f'"{confession}"',
        color=confession_color
    )
    embed.set_footer(text=f"❗ If this confession is ToS-breaking or overtly hateful, you can report it using /report {confession_number}")

    mod_embed = discord.Embed(
        title=f"Anonymous Confession (#{confession_number})",
        description=f'"{confession}"',
        color=confession_color
    )
    mod_embed.set_footer(text=f"Submitted by: {interaction.user.name}")

    if attachment:
        embed.set_image(url=attachment.url)
        mod_embed.set_image(url=attachment.url)

    # Send to confession channel
    view = View()
    view.add_item(Button(style=discord.ButtonStyle.primary, label="Submit a confession!", custom_id="submit_confession"))
    view.add_item(Button(style=discord.ButtonStyle.secondary, label="Reply", custom_id="reply"))

    message = await channel.send(embed=embed, view=view)
    await mod_channel.send(embed=mod_embed)  # Send to the moderation channel

    # Track the confession by adding it to the list
    confessions.append({
        "number": confession_number,
        "content": confession,
        "attachment_url": attachment.url if attachment else None,
        "message_id": message.id  # Store the message ID
    })

    # Update the last confession message ID
    if last_confession_message_id:
        try:
            last_message = await channel.fetch_message(last_confession_message_id)
            if last_message:
                await last_message.edit(view=None)  # Remove buttons from the last confession
        except discord.NotFound:
            pass

    last_confession_message_id = message.id
    update_confession_number()  # Increment and save the confession number

    await interaction.response.send_message(
        f":white_check_mark: Your confession has been added to {channel.mention}!",
        ephemeral=True
    )

# Event handler for interactions
@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == 'submit_confession':
            modal = ConfessionModal()
            await interaction.response.send_modal(modal)
        elif interaction.data['custom_id'] == 'reply':
            # Fetch the last confession (assuming it's the one being replied to)
            original_confession = confessions[-1]
            modal = ReplyModal(original_confession=original_confession)
            await interaction.response.send_modal(modal)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    try:
        await tree.sync()  # Sync commands to make them available
        print("Slash commands synced")
    except Exception as e:
        print(f"Error syncing commands: {e}")

if __name__ == "__main__":
    client.run(TOKEN)  # Replace with your actual token

    # Close the database connection when the bot shuts down
    close_db()
