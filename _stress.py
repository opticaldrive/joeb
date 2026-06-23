import aiohttp, asyncio, time, ssl, certifi
from collections import Counter

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
BASE = "https://hackatime.hackclub.com/api/v1/users/{}/trust_factor"

async def one(session, sem, uid, codes, lat):
    async with sem:
        t = time.time()
        try:
            async with session.get(BASE.1(uid)) as r:
                await r.read()
                codes[r.status] += 1
        except Exception as e:
            codes[type(e).__name__] += 1
        lat.append(time.time() - t)

async def run_level(concurrency, n_requests):
    sem = asyncio.Semaphore(concurrency)
    codes = Counter()
    lat = []
    conn = aiohttp.TCPConnector(limit=concurrency, ssl=SSL_CTX)
    async with aiohttp.ClientSession(connector=conn) as session:
        start = time.time()
        # cycle through real-ish ids 1..n_requests
        tasks = [one(session, sem, (i % 2000) + 1, codes, lat) for i in range(n_requests)]
        await asyncio.gather(*tasks)
        wall = time.time() - start
    ok = codes.get(200, 0)
    rps = n_requests / wall
    ok_rps = ok / wall
    avg_lat = sum(lat) / len(lat) if lat else 0
    print(f"conc={concurrency:>4}  reqs={n_requests}  wall={wall:6.2f}s  "
          f"rps={rps:7.1f}  ok_rps={ok_rps:7.1f}  avg_lat={avg_lat:5.2f}s  "
          f"codes={dict(codes)}")
    return ok, n_requests

async def main():
    print("ramping concurrency (1000 reqs each level)...")
    for c in [100, 200, 300, 500, 800]:
        await run_level(c, 1000)
        await asyncio.sleep(5)  # cooldown between levels

asyncio.run(main())
