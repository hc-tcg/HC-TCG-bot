from typing import Any
from interactions import (
    Extension,
    Member,
    Client,
    Button,
    StringSelectMenu,
    StringSelectOption,
    GuildForumPost,
    ComponentContext,
    ButtonStyle,
    spread_to_rows,
    SlashContext,
    component_callback,
    slash_command,
    listen,
    events,
)
from collections import defaultdict
from json import load, dump
from asyncio import sleep

from util import validate_user


class dummyPost:
    def __init__(self, ctx: SlashContext) -> None:
        self.thread = ctx.channel
        self.author = ctx.author
        self.channel = ctx.channel


class forumExt(Extension):
    def __init__(self, client: Client, config: dict):
        self.client = client
        self.forumData = config["forum_data"]
        self.permissions = config["permissions"]
        self.fp = config["files"]["forums"]
        try:
            with open(self.fp, "r") as f:
                self.to_close = defaultdict(lambda: [], load(f))
        except FileNotFoundError:
            self.to_close = defaultdict(lambda: [])

    @listen()
    async def disconnect(self, event):
        with open(self.fp, "w") as f:
            dump(self.to_close, f)

    @slash_command()
    async def forum(self, ctx: SlashContext):
        """Commands to help manage forums"""

    @forum.subcommand()
    async def close_done(self, ctx: SlashContext):
        """Closes all forums that are complete for the next update"""
        if not validate_user(ctx.author, ctx.guild, self.permissions):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        for parent, threads in self.to_close.items():
            parentChannel = await self.client.fetch_channel(parent)
            for threadId in threads:
                thread = await parentChannel.fetch_post(threadId)
                if thread:
                    await thread.archive(True)
        self.to_close = defaultdict(lambda: [])
        await ctx.send("Closed all posts", ephemeral=True)

    @forum.subcommand()
    async def manual(self, ctx: SlashContext):
        if not validate_user(ctx.author, ctx.guild, self.permissions):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        await ctx.send("Creating message", ephemeral=True)

        await self.new_post(self, dummyPost(ctx))

    @listen("new_thread_create")
    async def new_post(self, event: events.NewThreadCreate):
        thread: GuildForumPost = event.thread
        if not str(thread.parent_id) in self.forumData.keys():
            return
        await sleep(1)
        await thread.join()
        final_tags = [
            tag
            for tag in thread.applied_tags
            if tag.name in self.forumData[str(thread.parent_id)]
        ]
        open_tag = thread.parent_channel.get_tag("open", case_insensitive=True)
        if open_tag:
            final_tags.append(open_tag)
        await thread.edit(applied_tags=final_tags)
        selectOptions = []
        for tag in thread.parent_channel.available_tags:
            if not (
                tag.name in self.forumData[str(thread.parent_id)]
                or tag.name.lower() in ["open", "closed"]
            ):
                selectOptions.append(
                    StringSelectOption(
                        label=tag.name, value=tag.id, emoji=tag.emoji_name
                    )
                )
        await thread.send(
            "Thanks for submitting a post",
            components=spread_to_rows(
                StringSelectMenu(*selectOptions, custom_id="post_tagged"),
                Button(
                    style=ButtonStyle.DANGER,
                    label="Close thread",
                    emoji=":wastebasket:",
                    custom_id="close_thread",
                ),
            ),
        )

    @component_callback("post_tagged")
    async def change_tags(self, ctx: ComponentContext):
        if not (
            validate_user(ctx.author, ctx.guild, self.permissions)
            or (
                ctx.channel.initial_post
                and ctx.author == ctx.channel.initial_post.author
            )
        ):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        post: GuildForumPost = ctx.channel
        selected_tag = post.parent_channel.get_tag(ctx.values[0])
        final_tags = [
            tag
            for tag in post.applied_tags
            if tag.name in self.forumData[str(post.parent_id)]
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
    async def close_thread(self, ctx: ComponentContext):
        if not (
            validate_user(ctx.author, ctx.guild, self.permissions)
            or (
                ctx.channel.initial_post
                and ctx.author == ctx.channel.initial_post.author
            )
        ):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        final_tags = [
            tag
            for tag in ctx.channel.applied_tags
            if not tag.name in ["open", "closed"]
        ]
        closed_tag = ctx.channel.parent_channel.get_tag("closed", case_insensitive=True)
        if closed_tag:
            final_tags.append(closed_tag)
        await ctx.send("Closed post")
        await ctx.channel.edit(locked=True, applied_tags=final_tags)
        self.to_close[ctx.channel.parent_id].append(ctx.channel_id)


def setup(client, **kwargs):
    return forumExt(client, **kwargs)
