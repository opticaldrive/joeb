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

import ssl
import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

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

trust_human = {"0": "blue", "1": "red", "2": "green", "?": "Not Found/Unknown"}

min_interval = 12 * 60 # half hr
# import aiohappyeyeballs what on earth autoprompt
async def get_hackatime_user(session, username):
    url = f"https://hackatime.hackclub.com/api/v1/users/{username}/stats"
    async with session.get(url) as resp:
        response = await resp.json()
        return response


async def get_hackatime_user_trust_factor(session, username):

    url = f"https://hackatime.hackclub.com/api/v1/users/{username}/trust_factor"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()
            return resp.status, data
    except Exception:
        # timeout / connection reset / non-json body (rate limit) -> unknown, not "?"
        return None, {}


async def scan_hackatime_user(session, username):
    status, user_trust = await get_hackatime_user_trust_factor(session, username)

    trust_value = user_trust.get("trust_value")
    # 200 with a value = real reading. 404 = genuinely no such user ("?").
    # anything else (429 rate limit / 5xx / timeout) = transient failure: we DON'T
    # know the value, so flag it (ok=False) and let the caller keep the old one
    # instead of recording a fake "?" that flaps real users.
    if status == 200 and trust_value is not None:
        ok = True
    elif status == 404:
        ok = True
    else:
        ok = False

    print(username, trust_value, user_trust.get("trust_level", "?"), "ok" if ok else "FAIL")
    return {
        # str so it matches csv-loaded keys (DictReader gives strings); otherwise
        # int ids never match old_csv_dict and every user looks brand-new (?->x).
        "username": str(username),
        "trust_value": str(trust_value) if trust_value is not None else "?",
        "ok": ok,
    }


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


async def scanny_all_users(session, semaphore):
    async def rate_limited_scan(session, username):
        async with semaphore:
            return await scan_hackatime_user(session, username)



    # dynamically calculate max user if 100 not found users are in a row
    miss_limit = 15000 #  THIS IS INTENTIONALLY BIG
    batch_size = 50          # small batches -> smooth pacing
    users_data = []

    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    
    csv_path = data_dir / "userslist.csv"
    old_csv_path = data_dir / "old_userslist.csv"  # + csv_path

    if os.path.exists(csv_path):
        shutil.copy(csv_path, old_csv_path)  # snapshot previous run as baseline
    old_csv_file = open(old_csv_path, "r")
    old_csv = list(csv.DictReader(old_csv_file))
    old_csv_dict = {user["username"]: user for user in old_csv}

    # pace to the minimum rps needed to finish one full scan within min_interval.
    # last run scanned ids 0..N contiguously, so len(old_csv) ~= ids to scan again.
    est_ids = max(len(old_csv), 1000)          # first-run fallback if no baseline
    target_rps = est_ids / min_interval
    per_batch_secs = batch_size / target_rps   # how long each batch should take
    print(f"pacing: ~{est_ids} ids, target {target_rps:.3f} rps, {per_batch_secs:.1f}s/batch")

    consecutive_misses = 0
    i = 0
    done = False

    while not done:
        batch_start = time.time()
        batch_end = i + batch_size
        tasks = [rate_limited_scan(session, user_id) for user_id in range(i, batch_end)]
        batch_results = await asyncio.gather(*tasks)

        # a transient API failure (rate limit/timeout) gives us no value, so keep the
        # last known one instead of writing a fake "?" that would flap real users.
        # also drop the internal "ok" flag so it doesn't leak into the csv.
        for r in batch_results:
            if not r.pop("ok", True):
                prev = old_csv_dict.get(r["username"])
                r["trust_value"] = prev["trust_value"] if prev else "?"

        users_data.extend(batch_results) # do analytics here too, process batch? idk

        # save overall list (first batch overwrites + writes header, rest append)
        mode = "w" if i == 0 else "a"
        with open(csv_path, mode, newline="") as list_file:
            writer = csv.DictWriter(list_file, fieldnames=["username", "trust_value"])
            if i == 0:
                writer.writeheader()
            writer.writerows(batch_results)

        users_dict = {user["username"]: user for user in batch_results}

        changed = []
        for user in users_dict:
            # existing logged user
            if user in old_csv_dict:
                if users_dict[user] != old_csv_dict[user]:
                    changed.append({
                        "username": user,
                        "old_trust": old_csv_dict[user]["trust_value"],
                        "new_trust": users_dict[user]["trust_value"]
                    })
            else: # we want to also include existing lols
                changed.append({
                        "username": user,
                        "old_trust":"?",
                        "new_trust": users_dict[user]["trust_value"]
                })
        print("Changed:", len(changed))

        for changed_user in changed:
            username = changed_user["username"]
            old_trust = changed_user["old_trust"]
            new_trust = changed_user["new_trust"]

            # only log meaningful changes. make_change_message returns None for the
            # boring/noisy ones (?->?, ?->0, etc.), so new not-found users and plain
            # blue new users get dropped -> we only log red/green outcomes.
            # gate BEFORE the get_hackatime_user call so we don't waste a request.
            flavors = [m for m in (make_change_message(old_trust, new_trust) or []) if m]
            if not flavors:
                continue

            user_info = await get_hackatime_user(session, username)
            error = user_info.get("error")
            if error is None:
                textname = user_info["data"]["username"]
            elif "user has disabled public stats" in error:
                textname = "Unknown(disabled public stats)"
            else:
                textname = "Unknown(error occurred)"

            message = f"""
            `{textname}`(`{username}`) had a trust level change! \n*{trust_human[old_trust]}(`{old_trust}`) -> {trust_human[new_trust]}(`{new_trust}`)* 
            """
            slackbot.client.chat_postMessage(channel=LOG_CHANNEL, text = message,  mrkdwn=True)
            print(message)

        for r in batch_results:
            if r["trust_value"] == "?":
                consecutive_misses += 1
                if consecutive_misses >=miss_limit:
                    done = True
                    break
            else:
                consecutive_misses = 0   # a real user resets the streak

        i = batch_end

        # pace: sleep the remainder so this batch fills its target time slot
        if not done:
            elapsed = time.time() - batch_start
            await asyncio.sleep(max(0, per_batch_secs - elapsed))
            
         



async def main():
    print("app startup!")
    semaphore = asyncio.Semaphore(1000)  # only 5
    
    while True:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CTX)) as session:
            start = time.time()
            try:
                await scanny_all_users(session, semaphore)
            except Exception as e:
                print("scan failed:", repr(e))   # don't let one run kill the daemon
            elapsed = time.time() - start
            sleep_for = max(0, min_interval - elapsed)
            print(f"scan took {elapsed:.0f}s, sleeping {sleep_for:.0f}s")
            await asyncio.sleep(sleep_for)

    


asyncio.run(main())