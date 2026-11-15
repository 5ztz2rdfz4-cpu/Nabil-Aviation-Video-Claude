"""Generate the Bahasa Melayu narration line by line with edge-tts (ms-MY-OsmanNeural).

Each entry: (key, subtitle_text, tts_text, pause_after_seconds)
The subtitle text is what appears on screen; tts_text is spelled for correct
pronunciation (e.g. "747" -> "tujuh empat tujuh").
Output: build/vo/<key>.mp3 and build/vo/timeline.json
"""
import asyncio, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "vo")
VOICE = "ms-MY-OsmanNeural"
RATE = "+9%"
PITCH = "-7Hz"

# section, key, subtitle, tts, pause after
LINES = [
    # [00:00 - 00:20] HOOK  (starts after ~2.6 s logo sting)
    ("hook", "h1", "Bayangkan… dua buah Boeing 747.", "Bayangkan... dua buah Boeing, tujuh empat tujuh.", 0.41),
    ("hook", "h2", "Dua pesawat penumpang terbesar pada zaman itu.", "Dua pesawat penumpang terbesar pada zaman itu.", 0.34),
    ("hook", "h3", "Kedua-duanya berada di landasan yang sama.", "Kedua-duanya berada di landasan yang sama.", 0.41),
    ("hook", "h4", "Tetapi dalam beberapa saat sahaja, dunia penerbangan bakal menyaksikan tragedi paling dahsyat dalam sejarah penerbangan awam.",
     "Tetapi dalam beberapa saat sahaja, dunia penerbangan bakal menyaksikan tragedi paling dahsyat, dalam sejarah penerbangan awam.", 0.45),
    ("hook", "h5", "Inilah kisah Tenerife Airport Disaster, 27 Mac 1977.", "Inilah kisah, Tenerife Airport Disaster. Dua puluh tujuh Mac, sembilan belas tujuh puluh tujuh.", 0.90),
    # [00:20 - 00:50] WHAT HAPPENED
    ("what", "w1", "Semuanya bermula apabila sebuah letupan bom berlaku di Lapangan Terbang Gran Canaria, Sepanyol.",
     "Semuanya bermula apabila sebuah letupan bom berlaku di Lapangan Terbang Gran Canaria, Sepanyol.", 0.34),
    ("what", "w2", "Akibat kejadian itu, beberapa penerbangan terpaksa dialihkan ke Lapangan Terbang Los Rodeos di Tenerife.",
     "Akibat kejadian itu, beberapa penerbangan terpaksa dialihkan ke Lapangan Terbang Los Rodeos, di Tenerife.", 0.38),
    ("what", "w3", "Antaranya ialah KLM Flight 4805 dari Belanda dan Pan Am Flight 1736 dari Amerika Syarikat.",
     "Antaranya ialah K L M, Flight empat lapan kosong lima, dari Belanda. Dan Pan Am, Flight satu tujuh tiga enam, dari Amerika Syarikat.", 0.34),
    ("what", "w4", "Kedua-duanya menggunakan pesawat ikonik Boeing 747.", "Kedua-duanya menggunakan pesawat ikonik, Boeing tujuh empat tujuh.", 0.41),
    ("what", "w5", "Lapangan terbang yang kecil itu mula sesak dengan pesawat.", "Lapangan terbang yang kecil itu, mula sesak dengan pesawat.", 0.30),
    ("what", "w6", "Dan keadaan bakal menjadi lebih buruk apabila kabus tebal mula menyelubungi kawasan lapangan terbang.",
     "Dan keadaan bakal menjadi lebih buruk, apabila kabus tebal mula menyelubungi kawasan lapangan terbang.", 0.68),
    # [00:50 - 01:25] THE CRITICAL MOMENT
    ("crit", "c1", "Apabila Lapangan Terbang Gran Canaria dibuka semula, pesawat-pesawat mula bersedia untuk berlepas.",
     "Apabila Lapangan Terbang Gran Canaria dibuka semula, pesawat-pesawat mula bersedia untuk berlepas.", 0.34),
    ("crit", "c2", "KLM 4805 berada di hadapan, manakala Pan Am 1736 sedang mengikuti laluan taxi yang sama.",
     "K L M empat lapan kosong lima berada di hadapan. Manakala Pan Am satu tujuh tiga enam, sedang mengikuti laluan teksi yang sama.", 0.34),
    ("crit", "c3", "Disebabkan kesesakan, kedua-dua pesawat terpaksa menggunakan landasan aktif untuk bergerak ke kedudukan masing-masing.",
     "Disebabkan kesesakan, kedua-dua pesawat terpaksa menggunakan landasan aktif, untuk bergerak ke kedudukan masing-masing.", 0.34),
    ("crit", "c4", "Pan Am diarahkan keluar melalui satu taxiway, tetapi pesawat itu tidak berjaya mengambil simpang yang diarahkan.",
     "Pan Am diarahkan keluar melalui satu taxiway. Tetapi pesawat itu, tidak berjaya mengambil simpang yang diarahkan.", 0.34),
    ("crit", "c5", "Pada masa yang sama, jarak penglihatan semakin terhad akibat kabus.", "Pada masa yang sama, jarak penglihatan semakin terhad akibat kabus.", 0.38),
    ("crit", "c6", "Kedua-dua pesawat kini berada di landasan yang sama… tanpa dapat melihat antara satu sama lain.",
     "Kedua-dua pesawat kini berada di landasan yang sama... tanpa dapat melihat antara satu sama lain.", 0.75),
    # [01:25 - 02:05] THE FATAL MISCOMMUNICATION
    ("comm", "m1", "Di dalam kokpit KLM, kapten Jacob van Zanten menyangka pesawatnya sudah mendapat kebenaran untuk berlepas.",
     "Di dalam kokpit K L M, kapten Jacob van Zanten, menyangka pesawatnya sudah mendapat kebenaran untuk berlepas.", 0.34),
    ("comm", "m2", "Tetapi sebenarnya, menara kawalan hanya memberikan arahan laluan selepas berlepas, bukannya take-off clearance.",
     "Tetapi sebenarnya, menara kawalan hanya memberikan arahan laluan selepas berlepas. Bukannya, take-off clearance.", 0.38),
    ("comm", "m3", "Penggunaan frasa komunikasi yang tidak jelas, ditambah pula dengan dua transmisi radio yang bertindih, menyebabkan mesej penting tidak diterima dengan sempurna.",
     "Penggunaan frasa komunikasi yang tidak jelas, ditambah pula dengan dua transmisi radio yang bertindih, menyebabkan mesej penting, tidak diterima dengan sempurna.", 0.38),
    ("comm", "m4", "Pan Am pula sempat memberi amaran bahawa mereka masih berada di landasan.",
     "Pan Am pula, sempat memberi amaran bahawa mereka masih berada di landasan.", 0.34),
    ("comm", "m5", "Malah, jurutera penerbangan KLM sendiri mempersoalkan sama ada Pan Am sudah keluar dari landasan.",
     "Malah, jurutera penerbangan K L M sendiri, mempersoalkan sama ada Pan Am sudah keluar dari landasan.", 0.41),
    ("comm", "m6", "Namun, pesawat KLM terus memecut untuk berlepas.", "Namun... pesawat K L M, terus memecut untuk berlepas.", 0.68),
    # [02:05 - 02:30] THE COLLISION
    ("coll", "x1", "Dalam kabus tebal itu, kru Pan Am akhirnya ternampak sebuah Boeing 747 KLM muncul di hadapan mereka.",
     "Dalam kabus tebal itu, kru Pan Am akhirnya ternampak, sebuah Boeing tujuh empat tujuh K L M, muncul di hadapan mereka.", 0.26),
    ("coll", "x2", "Mereka cuba mengelak.", "Mereka cuba mengelak.", 0.26),
    ("coll", "x3", "Tetapi sudah terlambat.", "Tetapi... sudah terlambat.", 0.45),
    ("coll", "x4", "Pada sekitar jam 5:06 petang, kedua-dua pesawat bertembung dengan dahsyat.",
     "Pada sekitar jam lima, enam minit petang, kedua-dua pesawat bertembung dengan dahsyat.", 2.6),  # dramatic silence
    ("coll", "x5", "Tragedi itu meragut 583 nyawa.", "Tragedi itu, meragut lima ratus lapan puluh tiga nyawa.", 0.52),
    ("coll", "x6", "Kesemua 248 orang di dalam pesawat KLM terkorban, manakala 335 orang di dalam Pan Am turut terkorban.",
     "Kesemua dua ratus empat puluh lapan orang di dalam pesawat K L M terkorban. Manakala tiga ratus tiga puluh lima orang di dalam Pan Am, turut terkorban.", 0.38),
    ("coll", "x7", "Hanya 61 orang terselamat dari pesawat Pan Am.", "Hanya enam puluh satu orang, terselamat dari pesawat Pan Am.", 0.98),
    # [02:30 - 03:00] LESSON & CONCLUSION
    ("less", "l1", "Tenerife bukan sekadar sebuah nahas pesawat.", "Tenerife, bukan sekadar sebuah nahas pesawat.", 0.30),
    ("less", "l2", "Ia menjadi titik perubahan besar dalam sejarah keselamatan penerbangan.", "Ia menjadi titik perubahan besar, dalam sejarah keselamatan penerbangan.", 0.38),
    ("less", "l3", "Industri penerbangan memperkukuhkan prosedur komunikasi antara juruterbang dan menara kawalan, penggunaan frasa standard serta latihan Crew Resource Management.",
     "Industri penerbangan memperkukuhkan prosedur komunikasi antara juruterbang dan menara kawalan, penggunaan frasa standard, serta latihan Crew Resource Management.", 0.41),
    ("less", "l4", "Tragedi ini mengingatkan kita bahawa dalam dunia penerbangan, setiap arahan, setiap pengesahan dan setiap keputusan mempunyai makna yang sangat besar.",
     "Tragedi ini mengingatkan kita, bahawa dalam dunia penerbangan, setiap arahan, setiap pengesahan, dan setiap keputusan, mempunyai makna yang sangat besar.", 0.45),
    ("less", "l5", "Kerana dalam penerbangan…", "Kerana dalam penerbangan...", 0.38),
    ("less", "l6", "One misunderstood message can change everything.", "One misunderstood message, can change everything.", 0.68),
    ("less", "l7", "This is Nabil Aviation.", "This is Nabil Aviation.", 0.26),
    ("less", "l8", "Exploring aviation history, one story at a time.", "Exploring aviation history, one story at a time.", 0.00),
]

START = 2.6  # logo sting before first line


async def synth(key, text):
    import edge_tts
    path = os.path.join(OUT, key + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    proxy = os.environ.get("HTTPS_PROXY")
    for attempt in range(4):
        try:
            c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, proxy=proxy)
            await c.save(path)
            return path
        except Exception as e:  # network hiccup
            print("retry", key, e)
            await asyncio.sleep(2 + attempt * 2)
    raise RuntimeError(key)


def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    async def run():
        for sec, key, sub, tts, pause in LINES:
            await synth(key, tts)
    asyncio.run(run())
    t = START
    tl = []
    for sec, key, sub, tts, pause in LINES:
        p = os.path.join(OUT, key + ".mp3")
        # trim leading/trailing silence for tight timing
        w = os.path.join(OUT, key + ".wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p, "-af",
                        "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                        "-ar", "48000", "-ac", "1", w], check=True)
        d = dur(w)
        tl.append(dict(section=sec, key=key, text=sub, start=round(t, 3), end=round(t + d, 3), wav=w))
        t += d + pause
    json.dump(dict(lines=tl, total=round(t, 3)), open(os.path.join(OUT, "timeline.json"), "w"), indent=1, ensure_ascii=False)
    for l in tl:
        print(f"{l['start']:7.2f} {l['end']:7.2f} {l['section']} {l['text'][:60]}")
    print("total", t)


if __name__ == "__main__":
    main()
