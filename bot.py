import os
import json
import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

SERVER_ID = 1537896001770102855

SUPPORT_ROLE_ID = 1537902591030202431
SECOND_SUPPORT_ROLE_ID = 1537905436282454106

RULES_CHANNEL_NAME = "😒rules"

DATA_FILE = "accepted_users.json"


# =========================================================
# ACCEPTED USERS
# =========================================================

def load_accepted_users():

    if not os.path.exists(DATA_FILE):
        return set()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return set(
            int(user_id)
            for user_id in data
        )

    except Exception:

        return set()


accepted_users = load_accepted_users()


def save_accepted_users():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            list(accepted_users),
            file,
            indent=4
        )


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()

intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# SUPPORT CHECK
# =========================================================

def is_support(member: discord.Member):

    return any(
        role.id in [
            SUPPORT_ROLE_ID,
            SECOND_SUPPORT_ROLE_ID
        ]
        for role in member.roles
    )


# =========================================================
# TICKET OWNER
# =========================================================

def get_ticket_owner(channel):

    if not channel.topic:
        return None

    try:

        parts = channel.topic.split(":")

        if parts[0] == "claimed":

            return int(parts[1])

        return int(parts[0])

    except Exception:

        return None


# =========================================================
# RULES
# =========================================================

RULES_TEXT = """
# 😒 Sliqad Rules

Welcome to **Sliqad**!

Please read the rules carefully before accepting them.

### 1. Be Respectful
Treat every member with respect.
Harassment, bullying, discrimination and personal attacks are not allowed.

### 2. No Spam
Do not spam messages, mentions, emojis or commands.

### 3. No Advertising
Advertising other servers, websites, social media or services without permission is not allowed.

### 4. No NSFW Content
Sexual, pornographic or inappropriate content is not allowed.

### 5. No Malicious Content
Do not send viruses, malware, scams or malicious links.

### 6. Follow Discord's Rules
You must follow Discord's Terms of Service and Community Guidelines.

### 7. Respect Staff
Please respect the decisions of the staff team.

### 8. Use Channels Correctly
Use the correct channel for the correct topic.

### 9. No Unnecessary Drama
Do not intentionally cause arguments or problems in the community.

### 10. Have Fun! 🎉
Enjoy Sliqad and have a great time!

---

By clicking **✅ I Accept the Rules**, you confirm that you have read and accepted these rules.
"""


# =========================================================
# FIND RULES CHANNEL
# =========================================================

def get_rules_channel(guild):

    return discord.utils.find(
        lambda channel:
        isinstance(channel, discord.TextChannel)
        and channel.name == RULES_CHANNEL_NAME,
        guild.text_channels
    )


# =========================================================
# EXEMPT USERS
# =========================================================

def should_be_exempt(member: discord.Member):

    # ONLY BOTS ARE EXEMPT.
    #
    # Admins, Support and normal users
    # ALL have to accept the rules.

    if member.bot:
        return True

    return False


# =========================================================
# LOCK MEMBER
# =========================================================

async def lock_member(
    member: discord.Member,
    rules_channel: discord.TextChannel
):

    if should_be_exempt(member):
        return

    if member.id in accepted_users:
        return

    guild = member.guild

    for channel in guild.text_channels:

        try:

            # RULES CHANNEL
            if channel.id == rules_channel.id:

                await channel.set_permissions(
                    member,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=False,
                    reason="Rules not accepted"
                )

            # EVERY OTHER CHANNEL
            else:

                await channel.set_permissions(
                    member,
                    view_channel=False,
                    send_messages=False,
                    reason="Rules not accepted"
                )

        except discord.Forbidden:

            print(
                f"❌ Cannot lock #{channel.name}"
            )

        except discord.HTTPException:

            pass


# =========================================================
# UNLOCK MEMBER
# =========================================================

async def unlock_member(
    member: discord.Member,
    rules_channel: discord.TextChannel
):

    guild = member.guild

    for channel in guild.text_channels:

        if channel.id == rules_channel.id:
            continue

        try:

            await channel.set_permissions(
                member,
                overwrite=None,
                reason="Rules accepted"
            )

        except discord.Forbidden:

            print(
                f"❌ Cannot unlock #{channel.name}"
            )

        except discord.HTTPException:

            pass


# =========================================================
# RULES VIEW
# =========================================================

class RulesView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(
        label="I Accept the Rules",
        emoji="✅",
        style=discord.ButtonStyle.green,
        custom_id="accept_rules"
    )

    async def accept_rules(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):

            return

        if member.id in accepted_users:

            await interaction.response.send_message(
                "✅ You have already accepted the rules.",
                ephemeral=True
            )

            return

        rules_channel = get_rules_channel(
            member.guild
        )

        if rules_channel is None:

            await interaction.response.send_message(
                "❌ The rules channel could not be found.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            accepted_users.add(
                member.id
            )

            save_accepted_users()

            await unlock_member(
                member,
                rules_channel
            )

            await interaction.followup.send(
                "✅ **Rules accepted!**\n\n"
                "You now have access to the server. "
                "Welcome to **Sliqad!** 🎉",
                ephemeral=True
            )

            print(
                f"✅ {member} accepted the rules."
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ I don't have enough permissions "
                "to unlock you.",
                ephemeral=True
            )

        except Exception as error:

            print(
                f"❌ Rules error: {error}"
            )

            await interaction.followup.send(
                "❌ Something went wrong.",
                ephemeral=True
            )


# =========================================================
# NEW MEMBER
# =========================================================

@bot.event
async def on_member_join(
    member: discord.Member
):

    if member.id in accepted_users:
        return

    guild = member.guild

    rules_channel = get_rules_channel(
        guild
    )

    if rules_channel is None:

        print(
            "⚠️ 😒rules does not exist yet."
        )

        return

    await lock_member(
        member,
        rules_channel
    )

    print(
        f"🔒 {member} must accept the rules."
    )


# =========================================================
# SETUP RULES COMMAND
# =========================================================

@bot.tree.command(
    name="setup-rules",
    description="Create and configure the server rules."
)

async def setup_rules(
    interaction: discord.Interaction
):

    if not isinstance(
        interaction.user,
        discord.Member
    ):

        return

    # Only admins/server owner can SET UP the rules.
    # This does NOT exempt them from accepting the rules.

    if not (
        interaction.user.guild_permissions.administrator
        or interaction.user.id == interaction.guild.owner_id
    ):

        await interaction.response.send_message(
            "❌ Only server administrators can use this command.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    guild = interaction.guild

    # =====================================================
    # FIND / CREATE RULES CHANNEL
    # =====================================================

    rules_channel = get_rules_channel(
        guild
    )

    if rules_channel is None:

        try:

            rules_channel = await guild.create_text_channel(
                RULES_CHANNEL_NAME,
                reason="Sliqad Rules System"
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ I cannot create `😒rules`.\n\n"
                "Give the bot **Manage Channels** permission.",
                ephemeral=True
            )

            return

    # =====================================================
    # SEND RULES
    # =====================================================

    embed = discord.Embed(
        title="😒 Sliqad Rules",
        description=RULES_TEXT,
        color=discord.Color.green()
    )

    embed.set_footer(
        text="Sliqad • Read the rules before joining."
    )

    try:

        await rules_channel.send(
            embed=embed,
            view=RulesView()
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I cannot send messages in `😒rules`.",
            ephemeral=True
        )

        return

    # =====================================================
    # RULES CHANNEL
    # =====================================================

    try:

        await rules_channel.set_permissions(
            guild.default_role,
            view_channel=True,
            read_message_history=True,
            send_messages=False
        )

    except Exception:

        pass

    # =====================================================
    # LOCK ALL EXISTING MEMBERS
    # =====================================================

    locked = 0
    skipped = 0

    for member in guild.members:

        if should_be_exempt(member):

            skipped += 1
            continue

        if member.id in accepted_users:

            skipped += 1
            continue

        await lock_member(
            member,
            rules_channel
        )

        locked += 1

        await asyncio.sleep(0.1)

    # =====================================================
    # RESULT
    # =====================================================

    await interaction.followup.send(
        "✅ **Rules system successfully configured!**\n\n"
        f"🔒 Members locked: **{locked}**\n"
        f"✅ Already accepted: **{skipped}**\n\n"
        f"Rules channel: {rules_channel.mention}",
        ephemeral=True
    )

    print(
        f"🔒 Locked {locked} members."
    )


# =========================================================
# TICKET FORM
# =========================================================

class TicketForm(discord.ui.Modal):

    def __init__(self, ticket_type):

        if ticket_type == "video":

            title = "💡 Video Idea"

        else:

            title = "🆘 Help / Support"

        super().__init__(
            title=title
        )

        self.ticket_type = ticket_type

        self.description = discord.ui.TextInput(
            label="What is your idea/problem?",
            placeholder="Please explain your idea or problem...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=5,
            max_length=2000
        )

        self.add_item(
            self.description
        )


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild
        user = interaction.user

        # =================================================
        # CHECK EXISTING TICKET
        # =================================================

        existing_ticket = discord.utils.find(
            lambda channel:
            channel.category is not None
            and channel.category.name == "Support Tickets"
            and channel.topic is not None
            and (
                channel.topic == str(user.id)
                or channel.topic.startswith(
                    f"{user.id}:"
                )
            ),
            guild.text_channels
        )

        if existing_ticket:

            await interaction.response.send_message(
                f"❌ You already have an open ticket:\n"
                f"{existing_ticket.mention}",
                ephemeral=True
            )

            return

        # =================================================
        # SUPPORT ROLES
        # =================================================

        support_role = guild.get_role(
            SUPPORT_ROLE_ID
        )

        second_support_role = guild.get_role(
            SECOND_SUPPORT_ROLE_ID
        )

        if support_role is None:

            await interaction.response.send_message(
                "❌ Support role not found.",
                ephemeral=True
            )

            return

        # =================================================
        # CATEGORY
        # =================================================

        category = discord.utils.get(
            guild.categories,
            name="Support Tickets"
        )

        if category is None:

            category = await guild.create_category(
                "Support Tickets"
            )

        # =================================================
        # TYPE
        # =================================================

        if self.ticket_type == "video":

            ticket_type_name = "Video Idea"
            prefix = "idea"
            color = discord.Color.blue()

        else:

            ticket_type_name = "Help / Support"
            prefix = "help"
            color = discord.Color.green()

        # =================================================
        # PERMISSIONS
        # =================================================

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                ),

            support_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True
                )
        }

        if second_support_role:

            overwrites[
                second_support_role
            ] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

        username = (
            user.name
            .lower()
            .replace(" ", "-")
        )

        ticket_name = (
            f"{prefix}-{username}"
        )

        # =================================================
        # CREATE TICKET
        # =================================================

        try:

            ticket_channel = await guild.create_text_channel(
                ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"{user.id}:{self.ticket_type}",
                reason="Support Ticket"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot create the ticket channel.",
                ephemeral=True
            )

            return

        # =================================================
        # TICKET EMBED
        # =================================================

        if self.ticket_type == "video":

            title = "💡 Video Idea"

            message = (
                f"Hello {user.mention}! 👋\n\n"
                "Thank you for submitting your video idea!"
            )

        else:

            title = "🆘 Help / Support"

            message = (
                f"Hello {user.mention}! 👋\n\n"
                "Thank you for contacting support!"
            )

        embed = discord.Embed(
            title=title,
            description=message,
            color=color
        )

        embed.add_field(
            name="👤 Created By",
            value=user.mention,
            inline=True
        )

        embed.add_field(
            name="📌 Type",
            value=ticket_type_name,
            inline=True
        )

        embed.add_field(
            name="📝 Description",
            value=self.description.value,
            inline=False
        )

        embed.set_footer(
            text="Sliqad Support"
        )

        mentions = (
            f"{user.mention} "
            f"{support_role.mention}"
        )

        if second_support_role:

            mentions += (
                f" {second_support_role.mention}"
            )

        await ticket_channel.send(
            content=mentions,
            embed=embed,
            view=TicketButtons()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: "
            f"{ticket_channel.mention}",
            ephemeral=True
        )


# =========================================================
# TICKET SELECT MENU
# =========================================================

class TicketTypeSelect(
    discord.ui.Select
):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Video Idea",
                description="I have an idea for a video.",
                emoji="💡",
                value="video"
            ),

            discord.SelectOption(
                label="Help / Support",
                description="I need help.",
                emoji="🆘",
                value="support"
            )
        ]

        super().__init__(
            placeholder="Choose what you need...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_type_select"
        )


    async def callback(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            TicketForm(
                self.values[0]
            )
        )


class TicketTypeView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=60
        )

        self.add_item(
            TicketTypeSelect()
        )


# =========================================================
# TICKET BUTTONS
# =========================================================

class TicketButtons(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    # =====================================================
    # CLAIM
    # =====================================================

    @discord.ui.button(
        label="Claim Ticket",
        emoji="🛡️",
        style=discord.ButtonStyle.blurple,
        custom_id="claim_ticket"
    )

    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_support(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Only the Support Team can claim tickets.",
                ephemeral=True
            )

            return

        channel = interaction.channel

        if channel.topic and channel.topic.startswith(
            "claimed:"
        ):

            await interaction.response.send_message(
                "❌ This ticket is already claimed.",
                ephemeral=True
            )

            return

        ticket_type = "support"

        if channel.topic:

            parts = channel.topic.split(":")

            if len(parts) >= 2:

                ticket_type = parts[-1]

        await channel.edit(
            topic=(
                f"claimed:"
                f"{interaction.user.id}:"
                f"{ticket_type}"
            )
        )

        await interaction.response.send_message(
            f"🛡️ Ticket claimed by "
            f"{interaction.user.mention}."
        )


    # =====================================================
    # CLOSE
    # =====================================================

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket"
    )

    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        owner_id = get_ticket_owner(
            channel
        )

        allowed = (
            isinstance(
                interaction.user,
                discord.Member
            )
            and (
                is_support(
                    interaction.user
                )
                or interaction.user.id == owner_id
            )
        )

        if not allowed:

            await interaction.response.send_message(
                "❌ Only the ticket creator or Support Team "
                "can close this ticket.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 Closing ticket in **5 seconds**..."
        )

        await asyncio.sleep(5)

        try:

            await channel.delete(
                reason="Ticket closed"
            )

        except Exception:

            pass


    # =====================================================
    # DELETE
    # =====================================================

    @discord.ui.button(
        label="Delete Ticket",
        emoji="🗑️",
        style=discord.ButtonStyle.gray,
        custom_id="delete_ticket"
    )

    async def delete_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_support(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Only the Support Team can delete tickets.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ Deleting ticket..."
        )

        await asyncio.sleep(2)

        try:

            await interaction.channel.delete(
                reason="Ticket deleted"
            )

        except Exception:

            pass


# =========================================================
# TICKET PANEL
# =========================================================

class TicketPanel(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.green,
        custom_id="create_ticket"
    )

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="🎫 Create a Ticket",
            description=(
                "## Need help?\n\n"
                "Choose what you need help with.\n\n"
                "💡 **Video Idea**\n"
                "Submit an idea for a video.\n\n"
                "🆘 **Help / Support**\n"
                "Get help with a problem.\n\n"
                "You will then be asked to "
                "describe your idea or problem."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketTypeView(),
            ephemeral=True
        )


# =========================================================
# TICKET PANEL COMMAND
# =========================================================

@bot.tree.command(
    name="ticketpanel",
    description="Create the support ticket panel."
)

async def ticketpanel(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🎫 Sliqad Support",
        description=(
            "## Need help?\n\n"
            "Click **🎫 Create Ticket** below.\n\n"
            "💡 **Video Idea**\n"
            "Submit an idea for a video.\n\n"
            "🆘 **Help / Support**\n"
            "Get help with a problem.\n\n"
            "You will be asked to describe "
            "your idea or problem."
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(
        embed=embed,
        view=TicketPanel()
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    bot.add_view(
        RulesView()
    )

    bot.add_view(
        TicketPanel()
    )

    bot.add_view(
        TicketButtons()
    )

    try:

        guild = discord.Object(
            id=SERVER_ID
        )

        bot.tree.copy_global_to(
            guild=guild
        )

        synced = await bot.tree.sync(
            guild=guild
        )

        print("================================")
        print(f"Bot online: {bot.user}")
        print(f"Bot ID: {bot.user.id}")
        print(f"Commands synced: {len(synced)}")

        for command in synced:

            print(
                f"  /{command.name}"
            )

        print("================================")

    except Exception as error:

        print(
            f"❌ Command sync error: {error}"
        )


# =========================================================
# START
# =========================================================

if not TOKEN:

    print(
        "❌ DISCORD_TOKEN is missing!"
    )

else:

    bot.run(TOKEN)