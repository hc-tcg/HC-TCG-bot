"""Commands to help manage forums."""

from __future__ import annotations

from asyncio import sleep
from collections import defaultdict
from json import dump, load
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import (
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Extension,
    GuildForumPost,
    SlashContext,
    StringSelectMenu,
    StringSelectOption,
    component_callback,
    events,
    listen,
    slash_command,
    spread_to_rows,
)

from bot.util import DataGenerator, Server, ServerManager


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
        _generator: DataGenerator,
    ) -> None:
        """Commands to help manage forums.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        _generator (DataGenerator): Card data generator
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
        if not self.manager.discord_links[str(ctx.guild_id)].authorize_user(ctx.member):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        for parent, threads in self.to_close.items():
            parent_channel = await self.client.fetch_channel(parent)
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
        if not self.manager.discord_links[str(ctx.guild_id)].authorize_user(ctx.member):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        await ctx.send("Creating message", ephemeral=True)

        await self.new_post(self, DummyPost(ctx))

    @listen("new_thread_create")
    async def new_post(self: ForumExt, event: events.NewThreadCreate) -> None:
        """Track a new thread when posted."""
        thread: GuildForumPost = event.thread
        if str(thread.guild.id) not in self.manager.discord_links.keys():
            return
        server: Server = self.manager.discord_links[str(thread.guild.id)]
        if str(thread.parent_id) not in server.tracked_forums.keys():
            return
        await sleep(1)
        await thread.join()
        final_tags = [
            tag
            for tag in thread.applied_tags
            if tag.name in server.tracked_forums[str(thread.parent_id)]
        ]
        open_tag = thread.parent_channel.get_tag("open", case_insensitive=True)
        if open_tag:
            final_tags.append(open_tag)
        await thread.edit(applied_tags=final_tags)
        select_option = []
        for tag in thread.parent_channel.available_tags:
            if not (
                tag.name in server.tracked_forums[str(thread.parent_id)]
                or tag.name.lower() in ["open", "closed"]
            ):
                select_option.append(
                    StringSelectOption(label=tag.name, value=tag.id, emoji=tag.emoji_name)
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
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send("Couldn't find an online server for this discord!", ephemeral=True)
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]
        if not (
            server.authorize_user(ctx.author)
            or (ctx.channel.initial_post and ctx.author == ctx.channel.initial_post.author)
        ):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        post: GuildForumPost = ctx.channel
        selected_tag = post.parent_channel.get_tag(ctx.values[0])
        final_tags = [
            tag
            for tag in post.applied_tags
            if tag.name in server.tracked_forums[str(post.parent_id)]
            or tag.name in ["open", "closed"]
        ]
        if selected_tag in final_tags:
            final_tags.remove(selected_tag)
            await ctx.send("Removed tag", ephemeral=True)
        else:
            final_tags.append(selected_tag)
            await ctx.send("Added tag", ephemeral=True)
        await post.edit(applied_tags=final_tags)

    @component_callback("close_thread")
    async def close_thread(self: ForumExt, ctx: ComponentContext) -> None:
        """Close a thread."""
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send("Couldn't find an online server for this discord!", ephemeral=True)
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]
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
    generator: DataGenerator,
) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord bot client
    manager (ServerManager): The server connection manager
    scheduler (AsyncIOScheduler): Event scheduler
    generator (DataGenerator): Card data generator
    """
    return ForumExt(client, manager, scheduler, generator)
