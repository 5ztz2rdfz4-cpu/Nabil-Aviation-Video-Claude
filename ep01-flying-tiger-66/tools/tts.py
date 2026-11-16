import asyncio, ssl, sys, json
import edge_tts, edge_tts.communicate as c
c._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
voice, rate, pitch, lines, outdir = sys.argv[1:6]
async def one(i, t):
    com = edge_tts.Communicate(t, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(f"{outdir}/{i}.mp3", "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] in ("WordBoundary","SentenceBoundary"):
                words.append([ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]])
    json.dump(words, open(f"{outdir}/{i}.json","w"), ensure_ascii=False)
async def main():
    for ln in open(lines, encoding="utf-8"):
        if "|" in ln:
            i, t = ln.rstrip("\n").split("|", 1); await one(i, t)
asyncio.run(main())
