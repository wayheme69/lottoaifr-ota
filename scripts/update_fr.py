#!/usr/bin/env python3
"""Robot résultats LOTTO AI (France).

Télécharge les archives OFFICIELLES de la FDJ (Loto + EuroMillions), qui
contiennent les numéros ET les vrais gains de chaque rang, et écrit
fr_results.json (30 derniers tirages par jeu). L'app lit ce fichier sur
raw.githubusercontent.com ; fdj.fr est bloqué depuis certains pays mais pas
depuis les serveurs GitHub.
"""
import csv, io, json, sys, zipfile, urllib.request
from datetime import datetime, timezone

BASE = "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66"
LOTO_ID, EM_ID = "afp6", "afe6"          # archives « en cours » (Loto depuis nov. 2019, EM depuis 2020)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"
KEEP = 30

# Rangs officiels → « bons numéros + bonus »
LOTO_RANKS = {1: "5+1", 2: "5+0", 3: "4+1", 4: "4+0", 5: "3+1", 6: "3+0", 7: "2+1", 8: "2+0", 9: "x+1"}
EM_RANKS = {1: "5+2", 2: "5+1", 3: "5+0", 4: "4+2", 5: "4+1", 6: "3+2", 7: "4+0",
            8: "2+2", 9: "3+1", 10: "3+0", 11: "1+2", 12: "2+1", 13: "2+0"}

def rows(code):
    req = urllib.request.Request(BASE + code, headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=60).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    raw = z.read(z.namelist()[0])
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: text = raw.decode("latin-1")
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))

def money(s):
    s = (s or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    try: return round(float(s), 2)
    except ValueError: return None

def day(s):
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y%m%d"):
        try: return datetime.strptime(s, fmt).date()
        except ValueError: pass
    raise ValueError(s)

def col(r, *names):
    for n in names:
        if n in r and r[n] not in (None, ""): return r[n]
    return ""

def loto():
    out = []
    for r in rows(LOTO_ID):
        main = [int(r[f"boule_{i}"]) for i in range(1, 6)]
        chance = int(r["numero_chance"])
        assert all(1 <= n <= 49 for n in main) and len(set(main)) == 5 and 1 <= chance <= 10, r
        pay = {LOTO_RANKS[k]: money(r.get(f"rapport_du_rang{k}")) for k in LOTO_RANKS}
        win = {LOTO_RANKS[k]: int(money(r.get(f"nombre_de_gagnant_au_rang{k}")) or 0) for k in LOTO_RANKS}
        out.append({"date": day(r["date_de_tirage"]).isoformat(), "numbers": main, "bonus": [chance],
                    "payouts": pay, "winners": win})
    return out

def euromillions():
    out = []
    for r in rows(EM_ID):
        main = [int(r[f"boule_{i}"]) for i in range(1, 6)]
        stars = [int(r["etoile_1"]), int(r["etoile_2"])]
        assert all(1 <= n <= 50 for n in main) and len(set(main)) == 5 and all(1 <= s <= 12 for s in stars), r
        pay, win = {}, {}
        for k, key in EM_RANKS.items():
            pay[key] = money(col(r, f"rapport_du_rang{k}_Euro_Millions", f"rapport_du_rang{k}"))
            win[key] = int(money(col(r, f"nombre_de_gagnant_au_rang{k}_Euro_Millions_en_france",
                                      f"nombre_de_gagnant_au_rang{k}_en_france")) or 0)
        out.append({"date": day(r["date_de_tirage"]).isoformat(), "numbers": main, "bonus": stars,
                    "payouts": pay, "winners": win})
    return out

def main():
    l, e = loto(), euromillions()
    l.sort(key=lambda d: d["date"], reverse=True); e.sort(key=lambda d: d["date"], reverse=True)
    for name, d in (("Loto", l), ("EuroMillions", e)):
        age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(d[0]["date"]).date()).days
        print(f"{name}: dernier tirage {d[0]['date']} ({age} j) — {d[0]['numbers']} + {d[0]['bonus']}")
        if age > 6: sys.exit(f"{name}: archive FDJ périmée ({age} jours)")
    out = {"source": "FDJ — archives officielles", "loto": l[:KEEP], "euromillions": e[:KEEP]}
    with open("fr_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()
