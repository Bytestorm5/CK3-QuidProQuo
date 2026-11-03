#!/usr/bin/env python3
"""Quid Pro Quo - what an AI will and will not agree to, tested on the mod's own script.

    python3 tools/qpq_deal_tests.py [--vanilla /path/to/ck3/game] [-k NAME]

Every test composes a deal in the Backroom Deal panel through its own buttons (tools/qpq_sim.py runs the
script as written) and checks the answer against a rule of good sense:

  no free lunch     with no deed on either side, an AI agrees only to come out ahead on the goods, valued
                    at its own purse, and what it gives up weighs more than what it gets
  goodwill          liking, dread and Command make a deed cheaper for the one who does it; they never pay
                    for goods handed over, and dislike is never a refusal on its own
  worth             a deed done for an AI is worth what that AI wants from it, not what it costs the doer
  monotony          paying more never hurts; asking more never helps
  reasons           whenever an AI will not agree at any price, the panel says why
  clean             no scenario logs a script error

Deterministic: the same files give the same results. Exit code 1 if any test fails.
"""
import argparse
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpq_sim import Library, Panel, find_vanilla, offered_pairs, kind_names, scenario, standard_world  # noqa: E402

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


class Check:
    def __init__(self):
        self.failures = []
        self.count = 0

    def __call__(self, ok, msg):
        self.count += 1
        if not ok:
            self.failures.append(msg)


def panel(lib, me, them, opinion=None, setup=None, **world_changes):
    w, W = standard_world(player=me)
    if opinion is not None:
        w.opinion(W[them], W[me], opinion)
    for name, fields in world_changes.items():
        for k, v in fields.items():
            setattr(W[name], k, v)
    if setup:
        setup(w, W)
    return Panel(lib, w, W[me], W[them]), W


def barter(p, mine=None, theirs=None):
    """Goods only: MINE gold from me (leg t), THEIRS gold from them (leg i)."""
    if mine:
        p.deed("t", None)
        p.gold("t", mine)
    if theirs:
        p.deed("i", None)
        p.gold("i", theirs)


def total(p):
    return p.var("acc_total", 0.0)


# --------------------------------------------------------------------------- no free lunch
@test
def gold_for_gold(lib, check):
    """A swap of gold for gold: accepted only for clearly more than they give."""
    for them, purse in (("duke", 200), ("count2", 80), ("foe", 400), ("emir", 180)):
        for theirs in (20, purse // 2, purse):
            for ratio in (0.3, 1.0, 1.1):
                mine = max(1, int(theirs * ratio))
                p, W = panel(lib, "king", them, king=dict(gold=5000))
                barter(p, mine, theirs)
                check(not p.ai_accepts(), "%s accepted %d gold for their %d (total %.1f)" % (
                    them, mine, theirs, total(p)))
            p, W = panel(lib, "king", them, king=dict(gold=5000))
            barter(p, theirs * 2, theirs)
            check(p.ai_accepts(), "%s refused %d gold for their %d (total %.1f, fails %s)" % (
                them, theirs * 2, theirs, total(p), p.failures()))


@test
def the_reported_case(lib, check):
    """30 gold for 90 gold (reported from play), for every AI the king can deal with."""
    w, W = standard_world()
    for c in w.chars:
        if c is W["king"] or c.gold < 90:
            continue
        p, W2 = panel(lib, "king", c.name)
        barter(p, 30, 90)
        check(not p.ai_accepts(), "%s accepted 30 gold for 90 (total %.1f)" % (c.name, total(p)))


@test
def gifts_and_demands(lib, check):
    """Something for nothing: a gift is taken, a bare demand is not, however they feel about you."""
    for them in ("duke", "count2", "foe"):
        p, W = panel(lib, "king", them)
        barter(p, mine=50)
        check(p.ai_accepts(), "%s refused a gift of 50 gold (%s)" % (them, p.failures()))
        for op in (0, 100):
            p, W = panel(lib, "king", them, opinion=op)
            barter(p, theirs=40)
            check(not p.ai_accepts(), "%s (opinion %d) handed over 40 gold for nothing (total %.1f)" % (
                them, op, total(p)))


@test
def command_cannot_buy_goods(lib, check):
    """Command leans on a subordinate to do a deed; it does not make them pay."""
    for them in ("duke", "count2"):
        p, W = panel(lib, "king", them, opinion=50)
        barter(p, 30, 90)
        for tier in (3, 2, 1):
            if p.valid("qpq_ui_command_%d" % tier):
                p.command(tier)
                break
        check(p.var("command", 0) > 0, "no Command tier open on %s" % them)
        check(not p.ai_accepts(), "%s, commanded at tier %s, gave 90 gold for 30 (total %.1f)" % (
            them, p.var("command"), total(p)))


@test
def wealth_matters(lib, check):
    """The same gold is worth more to a poorer lord."""
    got = {}
    for them in ("count2", "duke"):
        p, W = panel(lib, "king", them)
        barter(p, mine=40)
        got[them] = p.var("acc_offers", 0.0)
    check(got["count2"] > got["duke"], "40 gold counts no more to a count than to a duke: %r" % got)


# --------------------------------------------------------------------------- goodwill
@test
def dislike_is_not_a_refusal(lib, check):
    """However much they dislike you, opinion alone never makes them refuse at any price."""
    for them in ("duke", "count2", "foe"):
        p, W = panel(lib, "king", them, opinion=-100)
        barter(p, mine=50)
        check(p.var("acc_other", 0) > -500, "%s at -100 opinion will not take a gift at any price" % them)
        check("hatred" not in p.refusals(), "hatred is still a refusal reason for %s" % them)


@test
def goodwill_discounts_deeds(lib, check):
    """A friend does a deed for less, never for nothing."""
    p0, _ = panel(lib, "king", "duke", opinion=0)
    p1, _ = panel(lib, "king", "duke", opinion=100)
    for p in (p0, p1):
        p.deed("t", "marcher_charge")
        p.gold("t", 30)
    check(total(p1) > total(p0), "liking does not make marcher charge cheaper (%.1f vs %.1f)" % (
        total(p1), total(p0)))
    p, _ = panel(lib, "king", "duke", opinion=100)
    p.deed("t", "marcher_charge")
    check(not p.ai_accepts(), "a friendly duke keeps his levies raised for nothing (total %.1f)" % total(p))


# --------------------------------------------------------------------------- worth
@test
def deeds_they_do_not_want(lib, check):
    """Doing them a 'favour' they do not care about is worth little: no paying for an unwanted killing.
    (The player is the duke; the AI is his liege the king, who would pay for the deed.)"""
    for kind in ("quiet_removal", "dossier", "snatch"):
        p, W = panel(lib, "duke", "king")
        p.deed("i", kind)
        picked = [c for c in p.candidates("i") if c.name == "count2"]
        check(picked, "%s: count2 is not offered as a target (%r)" % (kind, p.candidates("i")))
        if not picked:
            continue
        p.pick("i", picked[0])
        p.deed("t", None)
        p.gold("i", 60)
        check(not p.ai_accepts(), "%s: the king pays 60 gold to have a count he has no quarrel with dealt with "
              "(total %.1f)" % (kind, total(p)))


@test
def deeds_they_want(lib, check):
    """... but a deed against their rival is worth paying for."""
    def world(w, W):
        w.relate(W["king"], "rival", W["count2"])
        w.opinion(W["king"], W["count2"], -80)
    for kind in ("quiet_removal", "dossier"):
        p, W = panel(lib, "duke", "king", setup=world)
        p.deed("i", kind)
        picked = [c for c in p.candidates("i") if c is W["count2"]]
        if not picked:
            check(False, "%s: count2 not offered" % kind)
            continue
        p.pick("i", picked[0])
        p.deed("t", None)
        p.gold("i", 20)
        check(p.var("i_a_goal", 0) > 15, "%s: a rival's ruin is worth little to the king (%r)" % (
            kind, p.acceptance()))
        check(p.ai_accepts(), "%s: the king will not pay 20 gold to see his rival dealt with (total %.1f, %s)" % (
            kind, total(p), p.failures()))


@test
def fair_price_is_fair(lib, check):
    """The price the panel suggests covers what the deed asks of them, wherever gold can (twenty months of
    their stake, less for a dirtier deed, is the most any sum is worth)."""
    for kind in kind_names(lib, "t"):
        for me, them in offered_pairs(lib, "t", kind)[:2]:
            def setup(p, W):
                W[me].gold = 10 ** 6
                p.deed("t", kind)
                c = p.candidates("t")
                if c:
                    p.pick("t", c[0])
                p.gold("t")
            p, W = scenario(lib, me, them, setup)
            leg = p.acceptance().get("leg_t", {})
            ask, offers, tier = leg.get("a_ask", 0), leg.get("a_offers", 0), leg.get("agent_tier", 0)
            most = 100 * max(0.5, 1 - 0.1 * tier)
            if -ask <= most * 0.95:
                check(offers >= -ask, "%s %s->%s: the fair price (%s) is worth %.1f against an ask of %.1f" % (
                    kind, me, them, leg.get("fair"), offers, ask))


# --------------------------------------------------------------------------- monotony
@test
def more_gold_never_hurts(lib, check):
    """For each deed they would do (leg t), paying more never lowers their acceptance."""
    for kind in kind_names(lib, "t"):
        pairs = offered_pairs(lib, "t", kind, player_names=["king"])[:1]
        for me, them in pairs:
            prev = None
            for amount in (10, 50, 150, 400):
                def setup(p, W, amount=amount):
                    p.deed("t", kind)
                    c = p.candidates("t")
                    if c:
                        p.pick("t", c[0])
                    p.gold("t", amount)
                p, W = scenario(lib, me, them, setup)
                t = total(p)
                if prev is not None:
                    check(t >= prev - 1e-6, "%s: paying %d gives %.1f, less than %.1f" % (kind, amount, t, prev))
                prev = t


@test
def asking_more_never_helps(lib, check):
    """For each deed done for them (leg i), asking more of their gold never raises acceptance."""
    for kind in kind_names(lib, "i"):
        pairs = offered_pairs(lib, "i", kind, player_names=["king"])[:1]
        for me, them in pairs:
            prev = None
            for amount in (10, 40, 120):
                def setup(p, W, amount=amount):
                    p.deed("i", kind)
                    c = p.candidates("i")
                    if c:
                        p.pick("i", c[0])
                    p.gold("i", amount)
                p, W = scenario(lib, me, them, setup)
                t = total(p)
                if prev is not None:
                    check(t <= prev + 1e-6, "%s: asking %d gives %.1f, more than %.1f" % (kind, amount, t, prev))
                prev = t


# --------------------------------------------------------------------------- reasons, clean
@test
def refusals_explained(lib, check):
    """Every deed, both legs: if they will not at any price, a reason is shown; no script errors."""
    for leg in ("t", "i"):
        for kind in kind_names(lib, leg):
            for me, them in offered_pairs(lib, leg, kind)[:6]:
                def setup(p, W):
                    p.deed(leg, kind)
                    c = p.candidates(leg)
                    if c:
                        p.pick(leg, c[0])
                p, W = scenario(lib, me, them, setup)
                if p.var("acc_other", 0) <= -500:
                    check(p.refusals(), "%s %s %s->%s: refused at any price with no reason shown" % (
                        leg, kind, me, them))
                check(not p.errors, "%s %s %s->%s: script errors %s" % (leg, kind, me, them, p.errors[:3]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vanilla", default="")
    ap.add_argument("-k", default="", help="run only tests whose name contains this")
    args = ap.parse_args()
    lib = Library(find_vanilla(args.vanilla))
    bad = 0
    for fn in TESTS:
        if args.k and args.k not in fn.__name__:
            continue
        check = Check()
        try:
            fn(lib, check)
        except Exception:  # noqa: BLE001 - report and go on
            check.failures.append("CRASH\n" + traceback.format_exc())
        status = "ok  " if not check.failures else "FAIL"
        print("%s %-28s %d checks%s" % (status, fn.__name__, check.count,
                                         "" if not check.failures else ", %d failed" % len(check.failures)))
        for f in check.failures[:8]:
            print("       " + f)
        if len(check.failures) > 8:
            print("       ... and %d more" % (len(check.failures) - 8))
        bad += bool(check.failures)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
