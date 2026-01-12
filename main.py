"""
TODO: proper error handling for hackatime api requests. timeouts, retries, blablaba
TODO: figure out whats actualy the good format for modularization
also figure out max users instead of just trying to hit 30k

mindblown 30k requests in 80 seconds = 375 requests a second
"""

import aiohttp
import asyncio
import time
import csv
import os
import shutil
import random
# from hackatime_api import (
#     scan_hackatime_user,
#     get_hackatime_user,
#     get_hackatime_user_trust_factor,
# )
# from trust_utils import trust_human, get_trust_changes, make_change_message

import os
from dotenv import load_dotenv
from slack_bolt import App
load_dotenv()
SLACKBOT_TOKEN = os.environ["SLACKBOT_TOKEN"]
LOG_CHANNEL =  os.environ["LOG_CHANNEL"]
slackbot = App(token=SLACKBOT_TOKEN)


from pathlib import Path

start_time = time.time()


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
            "username": user,
            "old_trust": old_csv_dict[user]["trust_value"],
            "new_trust": new_csv_dict[user]["trust_value"],
        }
        for user in new_csv_dict
        if user in old_csv_dict and new_csv_dict[user] != old_csv_dict[user]
    ]

    # print(changed)
    return changed


trust_human = {"0": "blue", "1": "red", "2": "green", "?": "Not Found/Unknown"}


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
            "2": ["simply what, from banned to banner.", "?? go ban people now? promotion! or what lol"],
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
    semaphore = asyncio.Semaphore(5)  # only 5
    
  
    async def rate_limited_scan(session, username):
        async with semaphore:
            return await scan_hackatime_user(session, username)


    async with aiohttp.ClientSession() as session:
        # dynamically calculate max user if 100 not found users are in a row
        max_user = 20
        
        users_data = []

        batch_size = 5
        for i in range(0, max_user, batch_size):
            batch_end = min(i + batch_size, max_user)
            tasks = [rate_limited_scan(session, user_id) for user_id in range(i, batch_end)]
            batch_results = await asyncio.gather(*tasks)
            users_data.extend(batch_results) # do analytics here too, process batch? idk
            await asyncio.sleep(0.5)  # bweeep
        print(len(users_data))

        # silly path
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)

        csv_path = data_dir / "userslist.csv"
        old_csv_path = data_dir / "old_userslist.csv"  # + csv_path
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
                # print(user_info)
                error = user_info.get("error")
                if error is None:
                    old_trust = changed_user["old_trust"]
                    new_trust = changed_user["new_trust"]
                    
                    change_message = random.choice(
                        make_change_message(
                            old_trust, new_trust
                        ),
                    )
                    print(
                        # (
                        #     user_info.get("trust_factor", {}).get("trust_value", "?")
                        #     if user_info.get("trust_factor")
                        #     else "?"
                        # ),
                        f"{old_trust} -> {new_trust}",
                        user_info["data"]["username"],
                        user_info["data"]["user_id"],
                        change_message,
                        # "HRT: ", # yes
                        # user_info["data"]["human_readable_total"],
                        # "HRDA: ",
                        # user_info["data"]["human_readable_daily_average"],
                    )

                    message = f"""
                    `{user_info["data"]["username"]}`(`{username}`) had a trust level change! \n
                    *{trust_human[old_trust]}(`{old_trust}`) -> {trust_human[new_trust]}(`{new_trust}`)* \n
                    > __{change_message}__
                    """
                    # text=message,
                    slackbot.client.chat_postMessage(channel=LOG_CHANNEL, text = message,  mrkdwn=True)#, markdown_text=message)




                elif error == "user has disabled public stats":
                    print("User disabled public stats")
                else:
                    print(error)


asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))
