"""
TODO: proper error handling for hackatime api requests. timeouts, retries, blablaba

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
from hackatime_api import (
    scan_hackatime_user,
    get_hackatime_user,
    get_hackatime_user_trust_factor,
)
from trust_utils import trust_human, get_trust_changes, make_change_message
from pathlib import Path

start_time = time.time()


async def main():

    async with aiohttp.ClientSession() as session:
        tasks = []
        # dynamically calculate max user if 100 not found users are in a row
        max_user = 3000
        for user_info in range(max_user):
            tasks.append(asyncio.ensure_future(scan_hackatime_user(session, user_info)))
        users_data = await asyncio.gather(*tasks)
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
                    change_message = random.choice(
                        make_change_message(
                            changed_user["old_trust"], changed_user["new_trust"]
                        ),
                    )
                    print(
                        # (
                        #     user_info.get("trust_factor", {}).get("trust_value", "?")
                        #     if user_info.get("trust_factor")
                        #     else "?"
                        # ),
                        f"{changed_user['old_trust']} -> {changed_user['new_trust']}",
                        user_info["data"]["username"],
                        user_info["data"]["user_id"],
                        change_message,
                        # "HRT: ", # yes
                        # user_info["data"]["human_readable_total"],
                        # "HRDA: ",
                        # user_info["data"]["human_readable_daily_average"],
                    )

                elif error == "user has disabled public stats":
                    print("User disabled public stats")
                else:
                    print(error)


asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))
