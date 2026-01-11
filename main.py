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
import csv
import os
import shutil

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
    return {
        "username": username,
        "trust_value": user_trust.get("trust_value", "?"),
    }  # , "trust_level": trust_level}


def get_trust_changes(new_csv_path, old_csv_path):
    # yk what can even eliminate csvs entirely for the new one - store it in memory sob
    old_csv_file = open(old_csv_path, "r")
    old_csv = list(csv.DictReader(old_csv_file))
    old_csv_dict = {user["username"]: user for user in old_csv}
    print(old_csv[1])

    new_csv_file = open(new_csv_path, "r")
    new_csv = list(csv.DictReader(new_csv_file))
    new_csv_dict = {user["username"]: user for user in new_csv}

    changed = [
        new_csv_dict[user]
        for user in new_csv_dict
        if user in old_csv_dict and new_csv_dict[user] != old_csv_dict[user]
    ]
    print(changed)


async def main():

    async with aiohttp.ClientSession() as session:
        tasks = []
        # dynamically calculate max user if 100 not found users are in a row
        max_user = 3000
        for user in range(max_user):
            tasks.append(asyncio.ensure_future(scan_hackatime_user(session, user)))
        users_data = await asyncio.gather(*tasks)
        print(len(users_data))

        # silly nodir path
        csv_path = "userslist.csv"
        old_csv_path = "old_" + csv_path
        not_first_run = False
        if os.path.exists(csv_path):
            shutil.copy(csv_path, old_csv_path)
            not_first_run = True
        with open(csv_path, "w", newline="") as list_file:
            writer = csv.DictWriter(list_file, fieldnames=["username", "trust_value"])
            writer.writeheader()
            writer.writerows(users_data)

        if not_first_run:
            get_trust_changes(csv_path, old_csv_path)

        # should we implement batches. each batch end update files.
        # for batch in range(int(max_user/batch_size) + 1):
        #     for number in range(batch_size):
        #         tasks.append(asyncio.ensure_future(scan_hackatime_user(session, number)))
        #     users_data = await asyncio.gather(*tasks)


asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))
