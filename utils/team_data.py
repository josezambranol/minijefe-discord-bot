"""
Módulo de Gestión del Equipo (Squad MiniJefe)
Define los 5 integrantes oficiales con sus Discord User IDs exactos
para garantizar menciones directas (@Usuario) 100% efectivas y sin @everyone.
"""

from typing import List, Dict, Any, Optional
import discord

# Lista oficial de los 5 integrantes del equipo con sus IDs reales de Discord
TEAM_MEMBERS: List[Dict[str, Any]] = [
    {
        "id_alias": "jote",
        "discord_id": 644124012871548958,
        "name": "jotelito",
        "display_name": "Jote",
        "role": "Líder / Usuario",
        "emoji": "👑",
        "search_patterns": ["jotelito", "jote", "jose", "josed", "𝓙𝓸𝓽𝓮"]
    },
    {
        "id_alias": "jordy",
        "discord_id": 710931815271235645,
        "name": "kennenint",
        "display_name": "Jordy",
        "role": "Desarrollador",
        "emoji": "💻",
        "search_patterns": ["kennenint", "jordy", "jordydev", "jordy006281", "jordyint_51899"]
    },
    {
        "id_alias": "rafxzz",
        "discord_id": 1186725307475042395,
        "name": "raxszz_56977",
        "display_name": 'Rafxzz"',
        "role": "Miembro",
        "emoji": "⚡",
        "search_patterns": ["raxszz_56977", "rafxzz", "raxszz", "rafxzz\"", "rafa"]
    },
    {
        "id_alias": "ByLogan",
        "discord_id": 740298769857380435,
        "name": "logan7596",
        "display_name": "ByLogan",
        "role": "Miembro",
        "emoji": "🔥",
        "search_patterns": ["logan7596", "bylogan", "bylogan2", "logan", "charles"]
    },
    {
        "id_alias": "SEVINHO",
        "discord_id": 753613232870260846,
        "name": "gucci_1510",
        "display_name": "SEVINHO",
        "role": "Miembro",
        "emoji": "🎯",
        "search_patterns": ["gucci_1510", "sevinho", "sebas", "sevin", "sebastian"]
    }
]

def find_guild_member_for_team_entry(team_entry: Dict[str, Any], guild: Optional[discord.Guild]) -> Optional[discord.Member]:
    """Busca en el servidor al miembro de Discord por ID directo o por nombre/patrón."""
    if not guild:
        return None

    # 1. Búsqueda directa por Discord ID (la más rápida y exacta)
    if "discord_id" in team_entry and team_entry["discord_id"]:
        member = guild.get_member(team_entry["discord_id"])
        if member:
            return member

    # 2. Búsqueda en caché por patrones
    patterns = [p.lower() for p in team_entry.get("search_patterns", [])]
    patterns.extend([team_entry["name"].lower(), team_entry["display_name"].lower()])

    for member in guild.members:
        if member.id == team_entry.get("discord_id"):
            return member
        username = member.name.lower()
        display_name = member.display_name.lower()
        global_name = (member.global_name or "").lower()
        nick = (member.nick or "").lower()

        for pat in patterns:
            if (pat == username or pat in username or
                pat == display_name or pat in display_name or
                pat == global_name or pat in global_name or
                pat == nick or pat in nick):
                return member
    return None

def get_team_mentions(guild: Optional[discord.Guild] = None) -> str:
    """
    Retorna las menciones directas oficiales (<@id>) de los 5 integrantes del equipo.
    Al tener sus Discord IDs registrados, siempre genera menciones válidas y clickeables.
    NUNCA usa @everyone ni @here.
    """
    mentions = []
    for member_info in TEAM_MEMBERS:
        # Si tiene discord_id registrado, usar mención directa siempre
        d_id = member_info.get("discord_id")
        if d_id:
            mentions.append(f"<@{d_id}>")
        else:
            found = find_guild_member_for_team_entry(member_info, guild)
            if found:
                mentions.append(found.mention)
            else:
                mentions.append(f"**@{member_info['display_name']}**")

    return " ".join(mentions)

def get_team_directory_info(guild: Optional[discord.Guild]) -> List[Dict[str, Any]]:
    """Retorna la lista de los 5 miembros con su estado en el servidor."""
    result = []
    for info in TEAM_MEMBERS:
        found = find_guild_member_for_team_entry(info, guild)
        d_id = info.get("discord_id")
        mention_str = f"<@{d_id}>" if d_id else (found.mention if found else f"@{info['display_name']}")
        result.append({
            "info": info,
            "member": found,
            "mention": mention_str,
            "display": found.display_name if found else info["display_name"],
            "avatar_url": found.display_avatar.url if found else None
        })
    return result
