from interactions import Member, Guild


def validate_user(user: Member, guild: Guild, valid_ids: list):
    in_list = user.id in valid_ids
    has_role = any([True for role in user.roles if role.id in valid_ids])
    in_guild = guild.id in valid_ids
    return in_list or has_role or in_guild
