import aiohttp


# import aiohappyeyeballs what on earth autoprompt
async def get_hackatime_user(session, username):
    url = f"https://hackatime.hackclub.com/api/v1/users/{username}/stats"
    async with session.get(url) as resp:
        response = await resp.json()
        return response


async def get_hackatime_user_trust_factor(session, username):

    url = f"https://hackatime.hackclub.com/api/v1/users/{username}/trust_factor"
    async with session.get(url) as resp:
        response = await resp.json()
        return response


async def scan_hackatime_user(session, username):
    user_trust = await get_hackatime_user_trust_factor(session, username)

    trust_level = user_trust.get("trust_level", "?")
    trust_value = user_trust.get("trust_value", "?")
    line = f"{username},{trust_level}\n"
    print(username, trust_value, trust_level)
    return {
        "username": username,
        "trust_value": str(user_trust.get("trust_value", "?")),
    }  # , "trust_level": trust_level}
