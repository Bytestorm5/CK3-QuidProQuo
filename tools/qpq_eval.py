#!/usr/bin/env python3
"""Quid Pro Quo - deals at scale, for judging by reading.

    python3 tools/qpq_eval.py [--vanilla DIR] --n 320 --seed 1 --batch 40 --out DIR

Composes many varied deals in the Backroom Deal panel (tools/qpq_sim.py runs the mod's own script), each in a
world with its own small changes (opinion, traits, dread, rivalries, wealth), and writes each one out as a
short brief: who the two are, what is on the table, what the AI answers and the breakdown it shows. The briefs
are meant to be read by a judge (a person, or a model) who says which answers do not make sense.

Deterministic for a given seed. Writes DIR/cases.jsonl and DIR/batch_NN.md.
"""
import argparse
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpq_kinds import KINDS, is_instant  # noqa: E402
from qpq_sim import (Library, Loc, Refused, SimError, find_vanilla, kind_names, offered_pairs,  # noqa: E402
                     scenario)

LOC = Loc()

KIND = {k["key"]: k for k in KINDS}
TIER = {0: "none", 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}
TRAIT_POOL = ["honest", "just", "deceitful", "schemer", "greedy", "generous", "ambitious", "content", "craven",
              "brave", "compassionate", "callous", "paranoid", "trusting", "zealous", "vengeful"]
GOODS_POOL = ["land", "artifact", "office", "my_word", "ct_tax_down", "ct_levy_down", "ct_revocation", "ct_council", "ct_war",
              "ct_tax_up", "ct_levy_up", "arms", "restraint", "release_hook", "hook",
              "clemency", "succession", "church", "secret"]


def plain(text):
    """Game text without markup: [vassal|E] -> vassal, [x.GetName] -> the target."""
    text = re.sub(r"\[([a-z_]+)\|E\]", lambda m: m.group(1).replace("_", " "), text)
    text = re.sub(r"\[[^\]]*\]", "the target", text)
    return re.sub(r"#\w+ ?|#!", "", text)


def describe_char(c, W, me, p=None):
    w = W["world"]
    rank = {0: "unlanded", 1: "baron", 2: "count", 3: "duke", 4: "king", 5: "emperor"}[
        max((t.tier for t in c.titles), default=0)]
    bits = ["%s (%s%s)" % (c.name, rank, ", clergy" if c.clergy else "")]
    if c.liege is not None:
        bits.append("%s of %s" % ("vassal" if c.is_landed else "courtier", c.liege.name))
    else:
        bits.append("independent")
    bits.append("faith %s" % c.faith.name)
    if c.suzerain is not None:
        bits.append("tributary of %s" % c.suzerain.name)
    bits.append("gold %d, income %d a month" % (c.gold, c.income))
    if p is not None:
        bits.append("weighs gold against a stake of %d a month (income, at least 8, times rank)" % p.value("qpq_stake_value", c))
    if c.max_strength:
        bits.append("army %d" % c.max_strength)
    if c.traits:
        bits.append("traits: " + ", ".join(sorted(c.traits)))
    if c is not me:
        bits.append("opinion of %s: %+d" % (me.name, w.opinion_of(c, me)))
        d = w.dread.get((c, me), 0)
        if d:
            bits.append("dread of %s: %s" % (me.name, {1: "intimidated", 2: "cowed"}[d]))
    for kind in ("rival", "friend", "lover"):
        if c.rel(kind):
            bits.append("%s of %s" % (kind, ", ".join(sorted(x.name for x in c.rel(kind)))))
    if w.wars_of(c):
        for war in w.wars_of(c):
            side = "attacking" if c in war.attackers else "defending"
            foes = war.defenders if c in war.attackers else war.attackers
            bits.append("at war (%s) against %s, war score %+d for the attackers" % (
                side, ", ".join(x.name for x in foes), war.attacker_war_score))
    return "; ".join(bits)


def ask_text(k, names):
    """The deed's own ask, with names in place of the game's text functions."""
    t = k.get("ask", "")
    for key, name in names.items():
        t = re.sub(r"\[%s\.[A-Za-z]+\]" % key, name, t)
    return plain(t)


def leg_text(p, L, me, them):
    a = p.acceptance().get("leg_" + L)
    if not a:
        return None
    kind = a["kind"]
    doer, payer = (them, me) if L == "t" else (me, them)
    goods = sorted(k[len("qpq_ui_%s_o_" % L):] for k in p.me.vars if k.startswith("qpq_ui_%s_o_" % L))
    gold = p.var(L + "_amount")
    if "gold" in goods:
        goods.remove("gold")
        goods.insert(0, "%d gold" % (gold if gold is not None else p.var(L + "_price", 0)))
    tgt = p.var(L + "_target")
    title = p.var(L + "_target_title")
    if kind == "barter":
        deed = "no deed"
    else:
        k = KIND[kind]
        names = {"qpq_payer": payer.name, "qpq_agent": doer.name, "qpq_target": tgt.name if tgt is not None else "the target",
                 "qpq_target_title": title.name if title is not None else "the title"}
        yrs, usual = p.years(L), max(1, round(k["term"] / 12))
        term = "Done the moment it is sealed." if is_instant(k) else "%s %d year%s (the usual term for this deed is %d year%s)." % (
            "A promise kept for" if k["mode"] == "restraint" else "To be done within", yrs, "" if yrs == 1 else "s",
            usual, "" if usual == 1 else "s")
        deed = "%s, that is: %s %s. (%s In this text, 'you' is %s.)%s %s Scandal tier for %s: %s, for %s: %s" % (
            k["name"], doer.name, ask_text(k, names), plain(k["desc"]), payer.name,
            (" Target: %s%s." % (tgt.name, (" (holder of %s)" % title.name) if title is not None else "")) if tgt is not None else "",
            term, doer.name, TIER[int(a.get("agent_tier", 0))], payer.name, TIER[int(a.get("payer_tier", 0))])
    return "%s does: %s\n  %s gives: %s" % (doer.name, deed, payer.name, ", ".join(goods) or "nothing")


_PAIRS = {}


def pairs_for(lib, leg, kind):
    if (leg, kind) not in _PAIRS:
        _PAIRS[(leg, kind)] = offered_pairs(lib, leg, kind)
    return _PAIRS[(leg, kind)]


def make_case(lib, rng, kinds_t, kinds_i, idx):
    shape = rng.choices(["barter", "deed_t", "deed_i", "both", "gift", "demand"], [18, 34, 24, 12, 6, 6])[0]
    leg = "t" if shape in ("deed_t", "gift") else "i" if shape in ("deed_i", "demand") else rng.choice("ti")
    kind = None
    if shape in ("deed_t", "deed_i", "both"):
        kind = rng.choice(kinds_t if leg == "t" else kinds_i)
        pairs = pairs_for(lib, leg, kind)
    else:
        pairs = [("king", x) for x in ("duke", "duke2", "count", "count2", "foe", "third", "emir", "jarl", "chief")]
    if not pairs:
        return None
    me_name, them_name = rng.choice(pairs)
    other_kind = None
    if shape == "both":
        ol = "i" if leg == "t" else "t"
        cands = [k for k in (kinds_i if ol == "i" else kinds_t)
                 if (me_name, them_name) in pairs_for(lib, ol, k)]
        other_kind = rng.choice(cands) if cands else None
    tweaks = {
        "opinion": rng.choice([0, 0, 0, 25, 60, 100, -30, -70, -100]),
        "traits": rng.sample(TRAIT_POOL, rng.choice([0, 0, 1, 1, 2])),
        "dread": rng.choice([0, 0, 0, 0, 1, 2]),
        "rival_me": rng.random() < 0.06,
        "friend_me": rng.random() < 0.08,
        "target_rel": rng.choice([None, None, None, "rival", "friend"]),
        "their_gold_mult": rng.choice([0.2, 1, 1, 3]),
        "command": rng.random() < 0.25,
        "charter": rng.random() < 0.1,
    }
    record = {"id": idx, "shape": shape, "me": me_name, "them": them_name, "kind": kind, "other_kind": other_kind,
              "tweaks": tweaks}
    goods_done = []

    def setup(p, W):
        w = W["world"]
        me, them = W[me_name], W[them_name]
        me.gold = max(me.gold, 3000)
        them.gold = int(them.gold * tweaks["their_gold_mult"])
        op = tweaks["opinion"]
        if tweaks["friend_me"]:
            op = max(op, 50)
        if tweaks["rival_me"]:
            op = min(op, -50)
        w.opinion(them, me, op)
        them.traits |= set(tweaks["traits"])
        if tweaks["dread"] and me.is_landed:
            w.dread[(them, me)] = tweaks["dread"]
        if tweaks["rival_me"]:
            w.relate(them, "rival", me)
        elif tweaks["friend_me"]:
            w.relate(them, "friend", me)
        p.refresh()
        legs = []
        if shape == "barter":
            p.deed("t", None)
            p.gold("t", rng.choice([10, 30, 60, 100, 200]))
            p.deed("i", None)
            p.gold("i", min(them.gold, rng.choice([10, 30, 60, 90, 150])) or 1)
            if rng.random() < 0.4:
                g = rng.choice(GOODS_POOL)
                try:
                    p.offer(rng.choice("ti"), g)
                    goods_done.append(g)
                except Refused:
                    pass
        elif shape == "gift":
            p.deed("t", None)
            p.gold("t", rng.choice([20, 50, 150]))
        elif shape == "demand":
            p.deed("i", None)
            p.gold("i", min(them.gold, rng.choice([20, 50, 150])) or 1)
        else:
            legs = [(leg, kind)] + ([("i" if leg == "t" else "t", other_kind)] if other_kind else [])
            for L, k in legs:
                p.deed(L, k)
                cands = p.candidates(L) + [x for lst in ("title_candidates", "artifact_candidates")
                                           for x in p.me.var_lists.get("qpq_ui_%s_%s" % (L, lst), [])]
                ok = []
                for c in cands[:12]:
                    p.pick(L, c)
                    if p.var(L + "_target_ok"):
                        ok.append(c)
                if not ok and KIND[k]["target"] in ("char", "title", "artifact"):
                    raise Refused("no valid target")
                if ok:
                    target = rng.choice(ok)
                    p.pick(L, target)
                    if tweaks["target_rel"] and hasattr(target, "relations") and target is not them:
                        w.relate(them, tweaks["target_rel"], target)
                        w.opinion(them, target, -70 if tweaks["target_rel"] == "rival" else 70)
                # the term: often the usual one, otherwise anything from a year to twenty
                if rng.random() < 0.4 and not is_instant(KIND[k]):
                    p.term(L, rng.choice([1, 2, 3, 5, 10, 15, 20]))
            # payment: the leg that is paid in gold is the other side's goods
            paid = [L for L, _k in legs]
            if not other_kind:
                p.deed("i" if leg == "t" else "t", None)
            for L in paid:
                if rng.random() < 0.85:
                    p.gold(L)
                    fair = p.var(L + "_fair", 50)
                    frac = rng.choice([0.0, 0.25, 0.5, 1.0, 1.0, 1.5, 3.0])
                    amount = max(1, int(fair * frac))
                    if L == "i":
                        amount = min(amount, max(1, them.gold))
                    p.gold(L, amount)
                if rng.random() < 0.25:
                    g = rng.choice(GOODS_POOL)
                    try:
                        p.offer(L, g)
                        goods_done.append(g)
                    except Refused:
                        pass
        if tweaks["charter"]:
            p.public(True)
        if tweaks["command"]:
            for tier in (3, 2, 1):
                if p.shown("qpq_ui_command_shown") and p.valid("qpq_ui_command_%d" % tier):
                    p.command(tier)
                    break
        p.refresh()
    try:
        p, W = scenario(lib, me_name, them_name, setup)
    except (Refused, SimError) as e:
        return None
    me, them = W[me_name], W[them_name]
    acc = p.acceptance()
    names = {"qpq_ui_recipient": them.name}
    for L in ("t", "i"):
        tgt = p.var(L + "_target")
        if tgt is not None:
            names["qpq_ui_%s_target" % L] = tgt.name
        ek = p.var(L + "_ekind")
        if ek is not None:
            names["QpqUiKindName_%s" % L] = KIND[ek.name]["name"] if ek.name in KIND else ek.name
    reasons = [LOC.plain("QPQ_UI_REF_%s_%s" % (f[2:].upper(), f[0].upper()), names) for f in p.refusals()]
    unmet = [LOC.plain(k, names) for k in p.explain() if k not in ("QPQ_UI_FAIL_REFUSE", "QPQ_UI_FAIL_WONT")]
    record.update({
        "me_desc": describe_char(me, W, me, p), "them_desc": describe_char(them, W, me, p),
        "leg_t": leg_text(p, "t", me, them), "leg_i": leg_text(p, "i", me, them),
        "acceptance": acc, "accepts": p.ai_accepts(), "failures": p.failures(), "refusals": p.refusals(),
        "reasons": reasons, "unmet": unmet,
        "command": p.var("command", 0), "charter": "qpq_ui_charter" in me.vars, "errors": p.errors,
    })
    return record


def brief(r):
    acc = r["acceptance"]
    parts = ", ".join("%s %+.1f" % (k, v) for k, v in acc.items()
                      if not k.startswith("leg_") and k not in ("other", "before_cmd", "total", "offers") and v)
    goods = []
    for L, what in (("t", "goods they get"), ("i", "goods they give")):
        v = acc.get("leg_" + L, {}).get("a_offers")
        if v:
            goods.append("%s %+.1f" % (what, v))
    parts = ", ".join(goods + ([parts] if parts else []))
    lines = ["### Case %d" % r["id"],
             "- You (the player): %s" % r["me_desc"],
             "- They (an AI deciding): %s" % r["them_desc"]]
    for L in ("t", "i"):
        if r["leg_" + L]:
            lines.append("- " + r["leg_" + L].replace("\n  ", "\n- "))
    if r["command"]:
        lines.append("- You lean on your authority over them: Command tier %d" % r["command"])
    if r["charter"]:
        lines.append("- Proclaimed openly as a Charter")
    own = "ACCEPTS" if acc.get("total", 0) > 0 and not r["reasons"] else "REFUSES"
    if r["unmet"]:
        lines.append("- **The deal cannot be proposed as it stands**: %s. (Their own answer would be: %s, total %+.1f.)" % (
            "; ".join(r["unmet"]), own, acc.get("total", 0)))
    else:
        lines.append("- **Answer: %s**, total %+.1f (an AI agrees above 0)" % (own, acc.get("total", 0)))
    for x in r["reasons"]:
        lines.append("  - will not at any price: %s" % x)
    lines.append("- Breakdown: %s" % (parts or "nothing"))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vanilla", default="")
    ap.add_argument("--n", type=int, default=320)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    lib = Library(find_vanilla(args.vanilla))
    rng = random.Random(args.seed)
    kinds_t = [k for k in kind_names(lib, "t") if k != "barter"]
    kinds_i = [k for k in kind_names(lib, "i") if k != "barter"]
    os.makedirs(args.out, exist_ok=True)
    cases, idx = [], 0
    while len(cases) < args.n:
        idx += 1
        r = make_case(lib, rng, kinds_t, kinds_i, idx)
        if r is not None:
            r["id"] = len(cases) + 1
            cases.append(r)
    with open(os.path.join(args.out, "cases.jsonl"), "w") as f:
        for r in cases:
            f.write(json.dumps(r, default=str) + "\n")
    for b in range(0, len(cases), args.batch):
        with open(os.path.join(args.out, "batch_%02d.md" % (b // args.batch + 1)), "w") as f:
            f.write("".join(brief(r) + "\n" for r in cases[b:b + args.batch]))
    errs = sum(1 for r in cases if r["errors"])
    print("%d cases, %d accepted, %d with script errors -> %s" % (
        len(cases), sum(r["accepts"] for r in cases), errs, args.out))


if __name__ == "__main__":
    main()
