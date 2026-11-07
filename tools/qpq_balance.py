#!/usr/bin/env python3
"""Quid Pro Quo - every good and deed in one currency, for rebalancing.

    python3 tools/qpq_balance.py [--vanilla DIR]

The anchor is the vassal contract: one point of vanilla's own contract `score` is POINTS_PER_SCORE acceptance points
(tools/qpq_contracts.py). This prints what each good is worth to the AI who gets it and what it costs the AI who gives
it, and what each deed asks of the AI who does it, in acceptance points and in contract score points, read from the
mod's own script through the Backroom Deal panel. Read it after changing a weight: permanent should outweigh
temporary, and nothing should sit far from what it is comparable to. It judges nothing itself.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from qpq_contracts import POINTS_PER_SCORE  # noqa: E402
from qpq_kinds import DURATION_GOODS, KINDS  # noqa: E402
from qpq_sim import Library, Panel, SimError, find_vanilla, offered_pairs, standard_world  # noqa: E402
from qpq_ui_gen import UI_OFFERS  # noqa: E402

TERMS = (1, 2, 5, 10, 20)
# Lord pairs to try, most typical first: the first where the good is on offer is the one reported
PAIRS = [("king", "duke"), ("duke", "king"), ("duke", "count"), ("king", "foe"), ("duke", "duke2"),
         ("pope", "king"), ("king", "pope"), ("pope", "duke2"), ("duke2", "pope")]


def prepared(me, them):
    """The standard world, with what a good needs to be on offer: hooks both ways, kin in prison, a child to name
    heir, and the innovations behind contract rights. Same-faith pairs are left as they are."""
    w, W = standard_world(player=me)
    a, b = W[me], W[them]
    w.hooks[(a, b)] = w.hooks[(b, a)] = "weak"
    for c in (a, b):
        c.culture.innovations = ("innovation_battlements", "innovation_currency_02")
    if b.liege is a:
        b.father = a
    if a.liege is b:
        a.father = b
    if me == "king" and them == "duke":
        W["count"].father = b
        W["count"].imprisoned_by = a
    return Panel(LIB, w, W[me], W[them]), W


def good_value(good, leg):
    """Acceptance points for ticking GOOD in LEG with no deed in play (t: I give, i: they give), and who the AI is."""
    for me, them in PAIRS:
        p, W = prepared(me, them)
        p.deed(leg, None)
        if not p.shown("qpq_ui_offer_%s_%s" % (leg, good)):
            continue
        base = p.var("acc_total", 0.0)
        try:
            p.offer(leg, good)
        except SimError:
            continue
        return p.var("acc_total", 0.0) - base, them
    return None, None


def over_term(good, leg, years):
    """A good that lasts until the deadline: its worth over a term of YEARS, with no deed in play."""
    me, them = ("king", "duke") if leg == "t" else ("duke", "king")
    p, W = prepared(me, them)
    p.deed(leg, None)
    base = p.var("acc_total", 0.0)
    p.offer(leg, good)
    p.me.vars["qpq_ui_%s_years" % leg] = float(years)
    p.click("qpq_ui_refresh")
    return p.var("acc_total", 0.0) - base, them


def units(pts):
    return "%+7.1f  %+5.1f" % (pts, pts / POINTS_PER_SCORE)


def main():
    global LIB
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vanilla", default="")
    args = ap.parse_args()
    LIB = Library(find_vanilla(args.vanilla))

    print("Anchor: 1 contract score point = %d acceptance points\n" % POINTS_PER_SCORE)
    print("GOODS                 AI gets it: points  score   | AI gives it: points  score")
    for good in UI_OFFERS[1:]:
        if good in DURATION_GOODS:
            continue
        gets, a = good_value(good, "t")
        gives, b = good_value(good, "i")
        left = "%s (%s)" % (units(gets), a) if gets is not None else "not on offer"
        right = "%s (%s)" % (units(gives), b) if gives is not None else "not on offer"
        print("%-20s  %-28s | %s" % (good, left, right))

    print("\nGOODS THAT LAST UNTIL THE DEADLINE, by the term")
    print("                      " + "".join("%14s" % ("%d yr" % y) for y in TERMS))
    for good in DURATION_GOODS:
        print("%-20s  gets it %s" % (good, "".join("%14s" % units(over_term(good, "t", y)[0]).split()[0] for y in TERMS)))
        print("%-20s gives it %s" % ("", "".join("%14s" % units(over_term(good, "i", y)[0]).split()[0] for y in TERMS)))

    print("\nDEEDS (what the AI asks to do it, before goods)   points  score  tier  (who)")
    rows = []
    for k in KINDS:
        if k.get("carrier"):
            continue
        pairs = offered_pairs(LIB, "t", k["key"])
        if not pairs:
            rows.append((0, k["name"], "not on offer in the standard world"))
            continue
        me, them = next((x for x in PAIRS if x in pairs), pairs[0])
        p, W = prepared(me, them)
        p.deed("t", k["key"])
        cands = p.candidates("t") + p.me.var_lists.get("qpq_ui_t_title_candidates", [])
        if cands:
            p.pick("t", cands[0])
        # the deed's whole cost to them, leaving out only a refusal at any price
        ask = (p.var("acc_before_cmd", 0.0) or 0.0) - (p.var("acc_refuse", 0.0) or 0.0)
        rows.append((ask, k["name"], "%s  %s  (%s for %s)" % (units(ask), p.var("t_agent_tier"), them, me)))
    for ask, name, text in sorted(rows, key=lambda r: r[0]):
        print("%-30s %s" % (name, text))


if __name__ == "__main__":
    main()
