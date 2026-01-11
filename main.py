"""
TODO: fix stupid csvs

also actually get hackatime logging sob
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


async def scan_hackatime_user(session, username, raw_file):
    user_trust = await get_hackatime_user_trust_factor(session, username)
    trust_level = user_trust.get("trust_level", "?")
    line = f"{username},{trust_level}\n"
    print(username, trust_level)
    raw_file.write(line)
    raw_file.flush()
    return {"username": username, "trust_level": trust_level}


async def main():

    # stupid csv stuff
    with open("results_raw.csv", "w") as raw_file:
        raw_file.write("username,trust_level\n")

        async with aiohttp.ClientSession() as session:
            tasks = []
            max_user = 10000
            for number in range(1, max_user):
                tasks.append(
                    asyncio.ensure_future(
                        scan_hackatime_user(session, number, raw_file)
                    )
                )

            users_data = await asyncio.gather(*tasks)

    sorted_by_username = sorted(users_data, key=lambda x: x["username"])

    trust_order = {"red": 0, "green": 1, "blue": 2, "?": 3}
    sorted_by_trust = sorted(
        users_data, key=lambda x: (trust_order.get(x["trust_level"], 99), x["username"])
    )

    with open("results_by_username.csv", "w") as f:
        f.write("username,trust_level\n")
        for user in sorted_by_username:
            f.write(f"{user['username']},{user['trust_level']}\n")

    with open("results_by_trust.csv", "w") as f:
        f.write("username,trust_level\n")
        for user in sorted_by_trust:
            f.write(f"{user['username']},{user['trust_level']}\n")


asyncio.run(main())
print("--- %s seconds ---" % (time.time() - start_time))

# for user in users_data:
# print(user["trust_level"])
# print(user)
# print(users_data[0])
# for user in users_data:
#     error = user.get("error")
#     if error is None:
#         print(
#             (
#                 user.get("trust_factor", {}).get("trust_value", "?")
#                 if user.get("trust_factor")
#                 else "?"
#             ),
#             user["data"]["username"],
#             user["data"]["user_id"],
#             "HRT: ",
#             user["data"]["human_readable_total"],
#             "HRDA: ",
#             user["data"]["human_readable_daily_average"],
#         )
#     elif error == "user has disabled public stats":
#         print("User disabled public stats")
#     else:
#         print(error)
# except Exception as error:
#     print("Failed on user ", user, " ", user)
