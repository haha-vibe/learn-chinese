#!/usr/bin/env python3
"""
Build the two dictionary JSON files consumed by learnchinese.html:
  - tps-dictionary.json   : the TPS Frequency Dictionary (2500 chars), parsed + cleaned
  - cedict-supplement.json: WORDS chars missing from TPS, sourced from CC-CEDICT

Both share one schema, keyed by simplified character:
  { "rank": int|null, "source": "tps"|"cedict",
    "readings": [ { "pinyin": str, "defs": [str], "adultDefs"?: [str], "cl"?: [str] } ],
    "examples": [ { "word": str, "level"?: int, "readings": [ <reading> ] } ] }

Adult/mature senses are pre-marked here (moved out of "defs" into "adultDefs") so the
HTML needs no content-filter regex at render time.

Inputs (same folder):
  progressive-dictionary.txt          (TPS, from monkeywalk.com)
  cedict_1_0_ts_utf-8_mdbg.txt        (CC-CEDICT, from mdbg.net)
  learnchinese.html                   (only to read the WORDS index)
"""
import re, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
def path(p): return os.path.join(HERE, p)

# ───────────────────────── adult / mature content filter ─────────────────────────
# Match word STEMS so one term covers all inflections (e.g. "\bsex" → sex, sexual,
# sexuality, sexology, sex worker). Leading \b avoids false positives (analysis≠anal).
ADULT_TERMS = [
    r'\(vulgar\)', r'\(taboo\)', r'\(obscene\)', r'\(profanity\)', r'\(slang for sex',
    r'\bsex', r'\bhomosex', r'\bbisex', r'\btranssex', r'\bintersex',
    r'\bpenis\b', r'\bvagina', r'\bvulva\b', r'\bclitoris\b', r'\bphallus\b', r'\bphallic\b',
    r'\bgenital', r'\btesticle', r'\bscrotum\b', r'\banus\b', r'\banal sex\b',
    r'\bfuck', r'\bmasturbat', r'\bejaculat', r'\borgasm', r'\bcopulat', r'\bfornicat',
    r'\bcoitus\b', r'\bintercourse\b', r'\bsodom', r'\bbuggery\b', r'\bcunnilingus\b',
    r'\bfellatio\b', r'\borgy\b', r'\borgies\b', r'\bincest', r'\bbestiality\b',
    r'\bpornograph', r'\bporn\b', r'\bprostitut', r'\bbrothel\b', r'\bwhore', r'\bhooker\b',
    r'\bgigolo\b', r'\bstripper\b', r'\bstriptease\b',
    r'\blewd\b', r'\blicentious\b', r'\blascivious\b', r'\bsalacious\b', r'\bribald\b',
    r'\bobscene\b', r'\bobscenity\b', r'\bwanton\b', r'\bdepraved\b', r'\bdepravity\b', r'\bdissolute\b',
    r'\bdebauch', r'\bbawdy\b', r'\berotic', r'\blust(?:ful)?\b', r'\blibido\b', r'\blewdness\b',
    r'\baphrodisiac\b', r'\blecher', r'\bhorny\b', r'\bfetish', r'\bfrigidity\b',
    r'\bpromiscu', r'\bnymphomania', r'\baroused\b', r'\barousal\b',
    r'\brape\b', r'\braping\b', r'\brapist\b', r'\bmolest', r'\bpedophil', r'\bpaedophil',
    r'\bcondom\b', r'\bcontracepti',
]
ADULT_RE = re.compile('|'.join(ADULT_TERMS), re.I)
def is_adult(s): return bool(ADULT_RE.search(s))

# ───────────────────────── pinyin numeric → tone marks (for CEDICT) ─────────────────────────
TBL = {'a':'āáǎà','e':'ēéěè','i':'īíǐì','o':'ōóǒò','u':'ūúǔù','ü':'ǖǘǚǜ'}
def tone_syl(syl):
    syl = syl.replace('u:','ü').replace('U:','Ü')
    m = re.search(r'[1-5]$', syl)
    if not m: return syl.replace('5','')
    t = int(m.group()); base = syl[:-1]
    if t == 5: return base
    low = base.lower()
    def mark(ch):
        l = ch.lower()
        if l in TBL:
            mk = TBL[l][t-1]; return mk.upper() if ch.isupper() else mk
        return ch
    for v in ('a','e'):
        i = low.find(v)
        if i >= 0: return base[:i]+mark(base[i])+base[i+1:]
    i = low.find('ou')
    if i >= 0: return base[:i]+mark(base[i])+base[i+1:]
    for i in range(len(base)-1,-1,-1):
        if base[i].lower() in TBL: return base[:i]+mark(base[i])+base[i+1:]
    return base
def tone_marks(raw): return ''.join(tone_syl(s) for s in raw.split())

# ───────────────────────── reading builder (CL extraction + adult split) ─────────────────────────
def split_cl(defs):
    cls, rest = [], []
    for d in defs:
        m = re.search(r'CL:(.*)$', d)
        if m:
            for part in m.group(1).split(','):
                ch = part.split('[')[0].strip()
                if '|' in ch: ch = ch.split('|')[-1]
                if ch: cls.append(ch)
            d = d[:m.start()].strip().rstrip(',;').strip()
        if d: rest.append(d)
    return rest, cls

def mk_reading(pinyin, defs):
    rest, cls = split_cl(defs)
    clean = [d for d in rest if not is_adult(d)]
    adult = [d for d in rest if is_adult(d)]
    r = {"pinyin": pinyin, "defs": clean}
    if adult: r["adultDefs"] = adult
    if cls:   r["cl"] = cls
    return r

# ───────────────────────── 1. TPS dictionary ─────────────────────────
TPS_LEVELS = {'①':1,'②':2,'③':3,'④':4,'⑤':5}
HDR = re.compile(r'^(\d+)\.\s+(\S+)$')
ENTRY = re.compile(r'^(\S+)\s+(?:([①②③④⑤])\s+)?(\[.*)$')

def parse_entry(line):
    m = ENTRY.match(line)
    if not m: return None
    word, lv, rest = m.group(1), m.group(2), m.group(3)
    level = TPS_LEVELS.get(lv) if lv else None
    readings = []
    for chunk in rest.split('◆'):
        rm = re.match(r'^\[([^\]]+)\]\s*(.*)$', chunk.strip())
        if not rm: continue
        defs = [s.strip() for s in rm.group(2).split(';') if s.strip()]
        if defs: readings.append((rm.group(1).strip(), defs))
    return (word, level, readings) if readings else None

def build_tps():
    tps, cur = {}, None
    for ln in open(path('progressive-dictionary.txt'), encoding='utf-8'):
        line = ln.rstrip('\r\n').strip()
        if not line: continue
        h = HDR.match(line)
        if h:
            cur = {"char": h.group(2), "rank": int(h.group(1)), "readings": [], "ex": {}}
            tps[h.group(2)] = cur
            continue
        if not cur: continue
        p = parse_entry(line)
        if not p: continue
        word, level, readings = p
        if word == cur["char"]:
            for pin, defs in readings: cur["readings"].append(mk_reading(pin, defs))
        else:
            ex = cur["ex"].setdefault(word, {"word": word, "level": level, "readings": []})
            for pin, defs in readings: ex["readings"].append(mk_reading(pin, defs))
            if level and (ex["level"] is None or level < ex["level"]): ex["level"] = level
    out = {}
    for ch, sec in tps.items():
        rec = {"rank": sec["rank"], "source": "tps", "readings": sec["readings"], "examples": []}
        for ex in sec["ex"].values():
            e = {"word": ex["word"], "readings": ex["readings"]}
            if ex["level"] is not None: e["level"] = ex["level"]
            rec["examples"].append(e)
        out[ch] = rec
    return out

# ───────────────────────── 2. CEDICT supplement ─────────────────────────
def load_words():
    html = open(path('learnchinese.html'), encoding='utf-8').read()
    src = re.search(r'const WORDS = (\{.*?\n\});', html, re.S).group(1)
    src = src.replace('simp:', '"simp":').replace('trad:', '"trad":')
    src = re.sub(r'(\bL\d+):', r'"\1":', src)
    src = re.sub(r',\s*([\]}])', r'\1', src)
    return json.loads(src)

CED = re.compile(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$')
XREF = re.compile(r'^(see|see also|also pr\.?|also written|also pronounced|cf\.|old variant of|variant of|Japanese variant of)\b', re.I)
def clean_ced(defstr):
    out = []
    for d in defstr.split('/'):
        d = re.sub(r'\s*\[[^\]]*\]', '', d)
        d = re.sub(r'\s+', ' ', d).strip().rstrip(',;').strip()
        if not d or XREF.match(d): continue
        out.append(d)
    return out

def build_supplement(tps_out, max_phrases=16):
    WORDS = load_words()
    seen, order = set(), []
    for k in WORDS:
        for w in WORDS[k]:
            if w['simp'] not in seen: seen.add(w['simp']); order.append(w['simp'])
    missing = [c for c in order if c not in tps_out]
    mset = set(missing)
    char_map = {c: [] for c in missing}; phrase_map = {c: [] for c in missing}
    for ln in open(path('cedict_1_0_ts_utf-8_mdbg.txt'), encoding='utf-8'):
        if not ln or ln[0] == '#': continue
        m = CED.match(ln.strip())
        if not m: continue
        trad, simp, pin, defstr = m.groups(); cps = list(simp); L = len(cps)
        d1 = defstr.split('/')[0].strip()
        if L == 1 and simp in mset:
            if re.match(r'^(variant|old variant|Japanese variant|archaic variant) of', d1, re.I): continue
            if re.match(r'^\(archaic\)', d1, re.I): continue
            if any(r[0] == pin for r in char_map[simp]): continue
            char_map[simp].append((pin, defstr))
        elif 2 <= L <= 4 and cps[0] in mset:
            if re.match(r'^\(archaic\)', d1, re.I): continue
            if len(phrase_map[cps[0]]) < max_phrases: phrase_map[cps[0]].append((simp, pin, defstr))
    supp = {}
    for c in missing:
        readings = []
        for pin, defstr in char_map[c]:
            defs = clean_ced(defstr)
            if defs: readings.append(mk_reading(tone_marks(pin), defs))
        examples = []
        for word, pin, defstr in phrase_map[c]:
            defs = clean_ced(defstr)
            if defs: examples.append({"word": word, "readings": [mk_reading(tone_marks(pin), defs)]})
        supp[c] = {"rank": None, "source": "cedict", "readings": readings, "examples": examples}
    return supp, missing

if __name__ == '__main__':
    tps = build_tps()
    json.dump(tps, open(path('tps-dictionary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    supp, missing = build_supplement(tps)
    json.dump(supp, open(path('cedict-supplement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    merged = {**tps, **supp}
    has = lambda v: bool(v["readings"] or v["examples"])
    empty = [k for k, v in merged.items() if not has(v)]
    ad = sum(1 for v in merged.values() for r in v["readings"] if r.get("adultDefs"))
    print(f"tps-dictionary.json    : {len(tps)} chars")
    print(f"cedict-supplement.json : {len(supp)} chars (filled {len(missing)} TPS gaps)")
    print(f"merged coverage        : {sum(1 for v in merged.values() if has(v))}/{len(merged)}  (empty: {empty})")
    print(f"readings w/ adult senses marked: {ad}")
