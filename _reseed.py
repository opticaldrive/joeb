import aiohttp, asyncio, time, csv, ssl, certifi
from pathlib import Path

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
URL = "https://hackatime.hackclub.com/api/v1/users/{}/trust_factor"

CONCURRENCY = 100
BATCH = 500
MISS_LIMIT = 250

async def scan(session, sem, uid):
    async with sem:
        try:
            async with session.get(URL.format(uid)) as r:
                d = await r.json()
        except Exception:
            d = {}
        return {"username": str(uid), "trust_value": str(d.get("trust_value", "?"))}

async def main():
    data_dir = Path(__file__).parent / "data"
    out = data_dir / "userslist.csv"
    sem = asyncio.Semaphore(CONCURRENCY)
    conn = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=SSL_CTX)

    start = time.time()
    consecutive_misses = 0
    i = 0
    total_hits = 0
    async with aiohttp.ClientSession(connector=conn) as session:
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["username", "trust_value"])
            w.writeheader()
            done = False
            while not done:
                results = await asyncio.gather(*[scan(session, sem, uid)
                                                 for uid in range(i, i + BATCH)])
                w.writerows(results)
                f.flush()
                for r in results:
                    if r["trust_value"] == "?":
                        consecutive_misses += 1
                        if consecutive_misses >= MISS_LIMIT:
                            done = True
                            break
                    else:
                        consecutive_misses = 0
                        total_hits += 1
                i += BATCH
                print(f"scanned up to id {i}, hits so far {total_hits}, "
                      f"streak {consecutive_misses}")
    print(f"DONE: {total_hits} real users, last id ~{i}, "
          f"took {time.time()-start:.1f}s -> {out}")

asyncio.run(main())
