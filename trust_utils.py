import csv
import random


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
