"""
TODO: fix stupid csvs

also actually get hackatime logging sob

also actually get it to be sane and not like weird csv annoying rubbish

also figure out max users

mindblown 30k requests in 80 seconds = 375 requests a second
"""

import aiohttp
import asyncio
import time

start_time = time.time()


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

    
    return {"username": username, "trust value":  user_trust.get("trust_value", "?")}#, "trust_level": trust_level}



async def main():

    async with aiohttp.ClientSession() as session:
        tasks = []
        max_user = 300
        for user in range(max_user):
            tasks.append(asyncio.ensure_future(scan_hackatime_user(session, user)))
        users_data = await asyncio.gather(*tasks)
        print(len(users_data))

        # should we implement batches. each batch end update files. 
        # for batch in range(int(max_user/batch_size) + 1):
        #     for number in range(batch_size):
        #         tasks.append(asyncio.ensure_future(scan_hackatime_user(session, number)))
        #     users_data = await asyncio.gather(*tasks)



asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))
