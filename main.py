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
    #  [{'username': '14', 'old_trust': '2', 'new_trust': '0'}]
    # ^^ example
    # username should hopefully always be numeric lol ig
    # this is stupid jank and probably very inefficient but i htink it gives me what i wanht
    old_csv_file = open(old_csv_path, "r")
    old_csv = list(csv.DictReader(old_csv_file))
    old_csv_dict = {user["username"]: user for user in old_csv}
    # print(old_csv[1])

    new_csv_file = open(new_csv_path, "r")
    new_csv = list(csv.DictReader(new_csv_file))
    new_csv_dict = {user["username"]: user for user in new_csv}

    changed = [
        # new_csv_dict[user]
        {
            "username": int(user),
            "old_trust": old_csv_dict[user]["trust_value"],
            "new_trust": new_csv_dict[user]["trust_value"],
        }
        for user in new_csv_dict
        if user in old_csv_dict and new_csv_dict[user] != old_csv_dict[user]
    ]

    # print(changed)
    return changed


trust_human = {0: "blue", 1: "red", 2: "green", "?": "Not Found/Unknown"}


def make_change_message(old_trust, new_trust):
    trust_changes = {
        "0": {
            "?": ["nuked a normal user"],
            "0": None,  # ["[nochange] why am I talking about this? ts nothing changed"],
            "1": [
                "bye banned person",
                "banned, hope there won't or will be meta posts",
                "^^ Be good kids-enslaved-to-hackatime, this one didn't work hard enough",
            ],
            "2": [
                "promotion! trusted",
                "Be good kids... ^^ banned!... No, unfortunately they got a promotion so no drama.",
                "Promotion! now go release the fraud squad files and the fraud list",
            ],
        },
        "1": {
            "?": ["Yes, legally obligated to follow your GDPR requests. Or something"],
            "0": [
                "no longer guilty...",
                "free to fraud, live to fraud another day? who knows",
                "Fraud Squad holds children's accounts in jail for indefinite period only to release them or smt - some meta",
            ],
            "1": [
                None
                # "[nochange] already banned, why am I talking about this? ts nothing changed. fraudster's meta posts don't do anything"
            ],
            "2": ["simply what, from banned to banner.", "promotion! or what lol"],
        },
        "2": {
            "?": ["someone nuked someone - amongus?"],
            "0": ["someone got demoted, watch this channel in case there's a ban"],
            "1": [
                "ooh fell from the sky, this will have drama",
                "Fraud Squad... does fraud",
            ],
            "2": None,
            # "2": [
            #     "[nochange] nothing changed why am I sending this",
            #     "[nochange] same boring fraud squad position, wait for other drama.",
            # ],
        },
        "?": {
            "?": None,
            "0": None,  # nothing of interest
            "1": ["banned from the start??"],
            "2": ["instatrust"],
        },
    }
    return trust_changes[old_trust][new_trust]


async def main():

    async with aiohttp.ClientSession() as session:
        tasks = []
        # dynamically calculate max user if 100 not found users are in a row
        max_user = 3000
        for user_info in range(max_user):
            tasks.append(asyncio.ensure_future(scan_hackatime_user(session, user_info)))
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
            print("Not first run, scanning users")
            changed = get_trust_changes(csv_path, old_csv_path)
            print(len(changed))
            for changed_user in changed:
                username = changed_user["username"]
                user_info = await get_hackatime_user(session, username)
                print(user_info)
                error = user_info.get("error")
                if error is None:
                    print(
                        # (
                        #     user_info.get("trust_factor", {}).get("trust_value", "?")
                        #     if user_info.get("trust_factor")
                        #     else "?"
                        # ),
                        f"{changed_user['old_trust']} -> {changed_user['new_trust']}",
                        user_info["data"]["username"],
                        user_info["data"]["user_id"],
                        make_change_message(
                            changed_user["old_trust"], changed_user["new_trust"]
                        ),
                        # "HRT: ", # yes
                        # user_info["data"]["human_readable_total"],
                        # "HRDA: ",
                        # user_info["data"]["human_readable_daily_average"],
                    )

                elif error == "user has disabled public stats":
                    print("User disabled public stats")
                else:
                    print(error)
        # should we implement batches. each batch end update files.
        # for batch in range(int(max_user/batch_size) + 1):
        #     for number in range(batch_size):
        #         tasks.append(asyncio.ensure_future(scan_hackatime_user(session, number)))
        #     users_data = await asyncio.gather(*tasks)


asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))
