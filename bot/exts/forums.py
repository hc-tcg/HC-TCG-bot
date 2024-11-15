"""Commands to help manage forums."""

from __future__ import annotations

from asyncio import sleep
from collections import defaultdict
from json import dump, load

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import (
    TYPE_THREAD_CHANNEL,
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Extension,
    GuildForum,
    GuildForumPost,
    GuildText,
    SlashContext,
    Snowflake_Type,
    StringSelectMenu,
    StringSelectOption,
    ThreadTag,
    component_callback,
    events,
    listen,
    slash_command,
    spread_to_rows,
)

from bot.util import Server, ServerManager


class DummyPost:
    """A fake post."""

    def __init__(self: DummyPost, ctx: SlashContext) -> None:
        """Fake post for manually tracking a forum post."""
        self.thread = ctx.channel
        self.author = ctx.author
        self.channel = ctx.channel


class ForumExt(Extension):
    """Commands to help manage forums."""

    def __init__(
        self: ForumExt,
        client: Client,
        manager: ServerManager,
        _scheduler: AsyncIOScheduler,
    ) -> None:
        """Commands to help manage forums.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        """
        self.client: Client = client
        self.manager: ServerManager = manager

        self.to_close: defaultdict[str, list] = defaultdict(list)
        with open("forums.json") as f:
            self.to_close.update(load(f))

    @listen()
    async def disconnect(self: ForumExt, _: str) -> None:
        """Handle bot disconnection."""
        with open("forums.json", "w") as f:
            dump(self.to_close, f)

    @slash_command()
    async def forum(self: ForumExt, _: SlashContext) -> None:
        """Commands to help manage forums."""

    @forum.subcommand()
    async def close_done(self: ForumExt, ctx: SlashContext) -> None:
        """Close all forums that are complete for the next update."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if not self.manager.get_server(ctx.guild_id).authorize_user(ctx.member):
            await ctx.send("You can't do that!", ephemeral=True)
            return

        for parent, threads in self.to_close.items():
            parent_channel = await self.client.fetch_channel(parent)
            if not isinstance(parent_channel, GuildForum):
                continue
            for thread_id in threads:
                thread = await parent_channel.fetch_post(thread_id)
                if thread:
                    await thread.archive(locked=True)
        self.to_close = defaultdict(list)
        await ctx.send("Closed all posts", ephemeral=True)

    @forum.subcommand()
    async def manual(self: ForumExt, ctx: SlashContext) -> None:
        """Manually add a forum to be tracked."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        authed = self.manager.get_server(ctx.guild_id).authorize_user(ctx.member)
        if not authed:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        await ctx.send("Creating message", ephemeral=True)

        await self.new_post(self, DummyPost(ctx))

    @listen("new_thread_create")
    async def new_post(self: ForumExt, event: events.NewThreadCreate) -> None:
        """Track a new thread when posted."""
        thread: TYPE_THREAD_CHANNEL = event.thread
        if not isinstance(thread, GuildForumPost): # Must be a forum post
            return

        server: Server = self.manager.get_server(thread.guild.id)
        if str(thread.parent_id) not in server.tracked_forums.keys(): # Ensure this forum is tracked
            return

        forum: GuildText | GuildForum = thread.parent_channel
        if isinstance(forum, GuildText): # This should never happen since we know it's a forum post
            return

        await sleep(1)
        await thread.join()

        final_tags: list[Snowflake_Type | ThreadTag] = [
            tag
            for tag in thread.applied_tags
            if tag.name in server.tracked_forums[str(thread.parent_id)]
        ]
        open_tag = forum.get_tag("open", case_insensitive=True)
        if open_tag:
            final_tags.append(open_tag)
        await thread.edit(applied_tags=final_tags)

        select_option = []
        for tag in forum.available_tags:
            if not (
                tag.name in server.tracked_forums[str(thread.parent_id)]
                or tag.name.lower() in ["open", "closed"]
            ):
                select_option.append(
                    StringSelectOption(label=tag.name, value=str(tag.id), emoji=tag.emoji_name)
                )
        await thread.send(
            "Thanks for submitting a post",
            components=spread_to_rows(
                StringSelectMenu(*select_option, custom_id="post_tagged"),
                Button(
                    style=ButtonStyle.DANGER,
                    label="Close thread",
                    emoji=":wastebasket:",
                    custom_id="close_thread",
                ),
            ),
        )

    @component_callback("post_tagged")
    async def change_tags(self: ForumExt, ctx: ComponentContext) -> None:
        """Change the status tag on a post."""
        server: Server = self.manager.get_server(ctx.guild_id)
        if not (
            server.authorize_user(ctx.author)
            or (ctx.channel.initial_post and ctx.author == ctx.channel.initial_post.author)
        ):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        post: GuildForumPost = ctx.channel
        parent: GuildForum | GuildText = post.parent_channel
        if isinstance(parent, GuildText): # This will never happen (type checking is fun I swear)
            return
        selected_tag = parent.get_tag(ctx.values[0])
        final_tags: list[Snowflake_Type | ThreadTag] = [
            tag
            for tag in post.applied_tags
            if tag.name in server.tracked_forums[str(post.parent_id)]
            or tag.name in ["open", "closed"]
        ]
        if selected_tag in final_tags:
            final_tags.remove(selected_tag)
            await ctx.send("Removed tag", ephemeral=True)
        elif selected_tag:
            final_tags.append(selected_tag)
            await ctx.send("Added tag", ephemeral=True)
        else:
            await ctx.send("Couldn't find tag!")
        await post.edit(applied_tags=final_tags)

    @component_callback("close_thread")
    async def close_thread(self: ForumExt, ctx: ComponentContext) -> None:
        """Close a thread."""
        server: Server = self.manager.get_server(ctx.guild_id)
        if not (
            server.authorize_user(ctx.author)
            or (ctx.channel.initial_post and ctx.author == ctx.channel.initial_post.author)
        ):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        final_tags = [tag for tag in ctx.channel.applied_tags if tag.name not in ["open", "closed"]]
        closed_tag = ctx.channel.parent_channel.get_tag("closed", case_insensitive=True)
        if closed_tag:
            final_tags.append(closed_tag)
        await ctx.send("Closed post")
        await ctx.channel.edit(locked=True, applied_tags=final_tags)
        self.to_close[ctx.channel.parent_id].append(ctx.channel_id)


def setup(
    client: Client,
    manager: ServerManager,
    scheduler: AsyncIOScheduler,
) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord bot client
    manager (ServerManager): The server connection manager
    scheduler (AsyncIOScheduler): Event scheduler
    """
    return ForumExt(client, manager, scheduler)
