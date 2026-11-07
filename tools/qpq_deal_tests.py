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
import re
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpq_sim import (Flag, Library, Panel, Run, Story, contract_level, find_vanilla, offered_pairs, kind_names,  # noqa: E402
                     scenario, standard_world)
from qpq_contracts import CONTRACT_GOODS, TERMS, step_points  # noqa: E402

TESTS = []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpq_kinds import KINDS, is_instant  # noqa: E402
AGENT_PROPOSED = {k["key"] for k in KINDS if k["initiator"] != "payer"}


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
        for op in (0, -100):
            p, W = panel(lib, "king", them, opinion=op)
            barter(p, mine=50)
            check(p.ai_accepts(), "%s (opinion %d) refused a gift of 50 gold (total %.1f, %s)" % (
                them, op, total(p), p.failures()))
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


@test
def dislike_raises_the_price(lib, check):
    """Ill will makes them ask more for what they do or give, up to what it is worth."""
    for them in ("duke", "count2"):
        p0, _ = panel(lib, "king", them, opinion=0)
        p1, _ = panel(lib, "king", them, opinion=-100)
        for p in (p0, p1):
            barter(p, 100, 20)
        check(total(p1) < total(p0), "%s: dislike does not make a trade harder (%.1f vs %.1f)" % (
            them, total(p1), total(p0)))
        check(total(p1) >= total(p0) - p0.var("leg_i_a_offers", 0) * 0 - 30, "dislike costs more than its floor")


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


@test
def ill_will_and_trust(lib, check):
    """A deed from someone they loathe is worth less to them: a king who hates a courtier does not hire him for
    a killing on the cheap, though he would from a man he trusts."""
    def world(w, W):
        w.relate(W["king"], "rival", W["count2"])
        w.opinion(W["king"], W["count2"], -80)
    for op, want in ((0, True), (-100, False)):
        p, W = panel(lib, "courtier", "king", opinion=op, setup=world)
        p.deed("i", "quiet_removal")
        picked = [c for c in p.candidates("i") if c is W["count2"]]
        if not picked:
            check(False, "count2 not offered")
            continue
        p.pick("i", picked[0])
        p.deed("t", None)
        p.gold("i", 20)
        check(p.ai_accepts() == want, "opinion %d: the king %s to pay 20 gold to have his rival killed (total %.1f)"
              % (op, "refuses" if want else "agrees", total(p)))


@test
def betrayal_helps_at_war(lib, check):
    """A commander turning his coat against your enemy is worth something to you, whoever you are."""
    p, W = panel(lib, "foe_vassal", "third")
    p.deed("i", "turncoat")
    c = p.candidates("i")
    if c:
        p.pick("i", c[0])
    p.deed("t", None)
    check(p.var("i_a_ask", 0) > 0, "a turncoat against third's enemy is worth nothing to third (%r)" % p.acceptance())


@test
def neutrality_is_no_crime(lib, check):
    """Staying out of a war against a friend weighs against it, but is never refused at any price."""
    def world(w, W):
        w.relate(W["patriarch"], "friend", W["foe"])
        w.opinion(W["patriarch"], W["foe"], 80)
    p, W = panel(lib, "third", "patriarch", setup=world)
    p.deed("t", "stay_out")
    picked = [c for c in p.candidates("t") if c is W["foe"]]
    if picked:
        p.pick("t", picked[0])
    check(not p.refusals(), "staying out of a war against a friend is refused outright: %s" % p.refusals())
    check(p.var("t_a_goal", 0) < 0, "staying out against a friend's enemy is not weighed against (%r)" % p.acceptance())


@test
def stated_tiers(lib, check):
    """The tier a deed's own text states is the tier the script gives it."""
    def tier(me, them, leg, kind, setup=None, pick=None, extra=None):
        p, W = panel(lib, me, them, setup=setup)
        p.deed(leg, kind)
        cands = p.candidates(leg) + p.me.var_lists.get("qpq_ui_%s_title_candidates" % leg, [])
        if pick:
            cands = [c for c in cands if c.name == pick] or cands
        if cands:
            p.pick(leg, cands[0])
        if extra:
            p.click("qpq_ui_extra_%s_%s" % (leg, extra)) if ("qpq_ui_extra_%s_%s" % (leg, extra)) in lib.guis else None
        return p.var(leg + "_agent_tier"), p.var(leg + "_payer_tier")
    a, pt = tier("duke", "duke2", "t", "mutual_defense_league")
    check((a, pt) == (3, 3), "Mutual Defense: text says Tier III, script gives agent %s payer %s" % (a, pt))
    a, pt = tier("duke", "duke2", "t", "title_swap")
    check(a == 3, "Transfer a County (hidden): text says Tier III, script gives %s" % a)
    a, pt = tier("king", "foe", "t", "title_swap")
    check((a, pt) == (1, 1), "Transfer a County as a foreign dowry: text says Tier I, script gives agent %s payer %s" % (a, pt))
    a, pt = tier("king", "foe", "t", "secret_alliance")
    check(a == 1, "Secret Alliance between independent rulers: text says Tier I, script gives %s" % a)
    def kin(w, W):
        W["count"].liege = W["duke"]
        W["count"].father = W["duke"]
        W["count"].imprisoned_by = W["duke"]
    a, pt = tier("king", "duke", "t", "extradition", setup=kin, pick="count")
    check(a == 3, "Extradition of a vassal's own kin: text says Tier III, script gives %s" % a)
    a, pt = tier("king", "foe", "t", "extradition")
    check(a == 3, "Extradition from a foreign ruler: text says Tier III, script gives %s" % a)


@test
def fear_does_not_cancel_dislike(lib, check):
    """On a plain trade of goods, dread of you neither pays for their goods nor makes up for their dislike."""
    got = []
    for dread in (0, 2):
        def world(w, W, dread=dread):
            if dread:
                w.dread[(W["duke"], W["king"])] = dread
        p, W = panel(lib, "king", "duke", opinion=-100, setup=world)
        barter(p, 60, 30)
        got.append(total(p))
    check(abs(got[0] - got[1]) < 1e-6, "dread changes a plain trade with a lord who dislikes you: %r" % got)


@test
def a_blessing_for_oneself(lib, check):
    """Good omens read for the one who pays are a favour to them, not harm: their priest's friendship with them
    is no reason to refuse, and they want it."""
    def world(w, W):
        w.relate(W["godi"], "friend", W["jarl"])
        w.opinion(W["godi"], W["jarl"], 80)
    p, W = panel(lib, "jarl", "godi", setup=world)
    p.deed("t", "favourable_omens")
    me = [c for c in p.candidates("t") if c is W["jarl"]]
    check(me, "the jarl cannot pick himself")
    if me:
        p.pick("t", me[0])
        check(not p.refusals(), "omens for the jarl himself are refused: %s" % p.refusals())
    p, W = panel(lib, "godi", "jarl")
    p.deed("i", "favourable_omens")
    me = [c for c in p.candidates("i") if c is W["jarl"]]
    if me:
        p.pick("i", me[0])
        check(p.var("i_a_goal", 0) > 0, "good omens for himself are worth nothing to the jarl (%r)" % p.acceptance())


@test
def contract_weights_match_vanilla(lib, check):
    """The contract goods are priced from vanilla's own numbers: if a patch changes them, the prices must follow."""
    if not lib.vanilla:
        return
    def block_after(text, start):
        depth, i = 1, start
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        return text[start:i - 1]
    def field(body, name, default):
        m = re.search(r"^\t\t\t%s\s*=\s*(\{|[-@\w.]+)" % name, body, re.M)
        if not m:
            return default
        if m.group(1) == "{":
            return float(re.search(r"value\s*=\s*(-?[\d.]+)", body[m.end():]).group(1))
        v = m.group(1)
        return float(CONST[v]) if v.startswith("@") else float(v)
    text = ""
    folder = os.path.join(lib.vanilla, "common", "subject_contracts", "contracts")
    for fn in ("feudal.txt", "special_contracts.txt"):
        with open(os.path.join(folder, fn), encoding="utf-8-sig") as f:
            text += re.sub(r"#.*", "", f.read()) + "\n"
    CONST = dict(re.findall(r"^(@\w+)\s*=\s*(-?[\d.]+)", text, re.M))
    for term, want in TERMS.items():
        m = re.search(r"^%s\s*=\s*\{" % term, text, re.M)
        check(m, "vanilla has no contract term %s" % term)
        if not m:
            continue
        lv = re.search(r"obligation_levels\s*=\s*\{", block_after(text, m.end()))
        body = block_after(text, m.end() + lv.end())
        levels = []
        for lm in re.finditer(r"^\t\t(\w+)\s*=\s*\{", body, re.M):
            levels.append(block_after(body, lm.end()).replace("\n\t\t\t", "\n\t\t\t"))
        got = dict(score=[field("\n" + b, "score", i) for i, b in enumerate(levels)],
                   liege=[field("\n" + b, "ai_liege_desire", None) for b in levels],
                   subject=[field("\n" + b, "ai_subject_desire", None) for b in levels])
        for which in ("score", "liege", "subject"):
            check(got[which] == [float(x) for x in want[which]],
                  "%s %s: the mod copies %s, vanilla says %s" % (term, which, want[which], got[which]))


def contract_panel(lib, me, them, setup=None):
    def both(w, W):
        W[me].culture.innovations = W[them].culture.innovations = ("innovation_battlements", "innovation_currency_02")
        if setup:
            setup(w, W)
    return panel(lib, me, them, setup=both)


@test
def contract_goods_follow_the_anchor(lib, check):
    """What a contract good is worth to the one who gets it is vanilla's score step times the anchor, and it never
    costs the giver less than that. Loss aversion is the same 1.25 as on every other good."""
    for g in CONTRACT_GOODS:
        me, them = ("duke", "king") if g["step"] == "up" else ("king", "duke")
        frm, to = (2, 3) if g["step"] == "up" else (2, 1) if g["step"] == "down" else (0, 1)
        gain, cost = step_points(g, frm, to)
        check(cost >= gain, "%s costs less to give (%s) than it is worth to get (%s)" % (g["key"], cost, gain))
        if g["key"] == "ct_faith":
            continue
        p, W = contract_panel(lib, me, them)
        p.deed("t", None)
        base = total(p)
        check(p.shown("qpq_ui_offer_t_" + g["key"]), "%s is not on offer from %s to %s" % (g["key"], me, them))
        p.offer("t", g["key"])
        check(abs(total(p) - base - gain) < 0.01, "%s gives %s: worth %s, expected %s" % (g["key"], them, total(p) - base, gain))
        p, W = contract_panel(lib, them, me)
        p.deed("i", None)
        base = total(p)
        p.offer("i", g["key"])
        check(abs(base - total(p) - cost * 1.25) < 0.01, "%s from %s: costs %s, expected %s" % (g["key"], me, base - total(p), cost * 1.25))


@test
def contract_goods_only_where_they_can_apply(lib, check):
    """A contract term is on offer only between liege and vassal, and only if it can still move."""
    def on_offer(me, them, good, setup=None):
        p, W = contract_panel(lib, me, them, setup)
        return p.shown("qpq_ui_offer_t_" + good)
    check(on_offer("king", "duke", "ct_tax_down"), "a liege cannot lower a vassal's taxes")
    check(not on_offer("duke", "king", "ct_tax_down"), "a vassal can lower its liege's taxes")
    check(on_offer("duke", "king", "ct_tax_up"), "a vassal cannot offer its liege higher taxes")
    check(not on_offer("king", "foe", "ct_tax_down"), "taxes lowered for a foreign ruler")
    def exempt(w, W):
        W["duke"].obligations = {"feudal_government_taxes": 0}
    check(not on_offer("king", "duke", "ct_tax_down", exempt), "taxes lowered below exempt")
    def maxed(w, W):
        W["duke"].obligations = {"feudal_government_taxes": 4}
    check(not on_offer("duke", "king", "ct_tax_up", maxed), "taxes raised above extortionate")
    def granted(w, W):
        W["duke"].obligations = {"title_revocation_rights": 1}
    check(not on_offer("king", "duke", "ct_revocation", granted), "a right granted twice")
    p, W = panel(lib, "king", "duke")
    check(not p.shown("qpq_ui_offer_t_ct_fort"), "fortification rights without vanilla's innovation")
    check(not on_offer("king", "duke", "ct_faith"), "religious protection for a vassal of the liege's own faith")
    def other_faith(w, W):
        W["duke"].faith = W["foe"].faith
    check(on_offer("king", "duke", "ct_faith", other_faith), "no religious protection for a vassal of another faith")


@test
def contract_goods_change_the_contract(lib, check):
    """On delivery the vassal's real contract moves one step, in the right direction, and only while they are bound."""
    def deliver(good, payer, agent, setup=None):
        w, W = standard_world(player="king")
        if setup:
            setup(W)
        s = Story("deal")
        s.vars["qpq_offer_" + good] = True
        r = Run(lib, w, W["king"], {"qpq_payer": W[payer], "qpq_agent": W[agent]})
        r.eff(lib.effects["qpq_contract_goods_deliver_effect"], (s, None))
        return W
    W = deliver("ct_tax_down", "king", "duke")
    check(contract_level(W["duke"], "feudal_government_taxes") == 1, "lower taxes left the level at %s" % W["duke"].obligations)
    W = deliver("ct_levy_up", "duke", "king")
    check(contract_level(W["duke"], "feudal_government_levies") == 3, "higher levies left the level at %s" % W["duke"].obligations)
    W = deliver("ct_revocation", "king", "duke")
    check(contract_level(W["duke"], "title_revocation_rights") == 1, "revocation protection not granted: %s" % W["duke"].obligations)
    W = deliver("ct_tax_down", "king", "foe")
    check(contract_level(W["foe"], "feudal_government_taxes") == 2, "a contract changed between strangers")


def good_with_deed(lib, me, them, leg, good, years):
    """What ticking GOOD adds to the AI's answer, on a deed of YEARS. Goods that last need a deed to last for."""
    p, W = contract_panel(lib, me, them)
    p.deed(leg, "marcher_charge")
    cands = p.candidates(leg)
    if cands:
        p.pick(leg, cands[0])
    p.me.vars["qpq_ui_%s_years" % leg] = float(years)
    p.click("qpq_ui_refresh")
    base = total(p)
    p.offer(leg, good)
    return total(p) - base


@test
def goods_last_as_long_as_the_deal(lib, check):
    """Lending men, a seat or a promise for twenty years is not the price of one year, at either end of the deal."""
    for good in ("arms", "office", "restraint"):
        gets = [good_with_deed(lib, "king", "duke", "t", good, y) for y in (1, 5, 20)]
        gives = [-good_with_deed(lib, "duke", "king", "i", good, y) for y in (1, 5, 20)]
        check(gets[0] < gets[1] <= gets[2], "%s is worth %s to the one who gets it at 1, 5 and 20 years" % (good, gets))
        check(gives[0] < gives[1] <= gives[2], "%s costs %s to the one who gives it at 1, 5 and 20 years" % (good, gives))
    a = good_with_deed(lib, "duke", "king", "i", "arms", 5)
    check(abs(a + 15 * 1.25) < 0.01, "five years of Arms should cost what it did: %s" % a)
    a = good_with_deed(lib, "duke", "king", "i", "arms", 20)
    check(abs(a + 15 * 2.5 * 1.25) < 0.01, "twenty years of Arms should cost 2.5 times as much: %s" % a)


@test
def permanent_outweighs_promised(lib, check):
    """The anchor's first rule: however long the term, a good that lapses at the deadline is worth no more, and costs
    no more, than the same thing written into the contract for good."""
    for temporary, permanent in (("restraint", "ct_revocation"), ("office", "ct_council")):
        for years in (1, 5, 10, 20):
            a, b = good_with_deed(lib, "king", "duke", "t", temporary, years), good_with_deed(lib, "king", "duke", "t", permanent, years)
            check(a <= b, "%s for %d years is worth %s, %s for good %s" % (temporary, years, a, permanent, b))
            a, b = good_with_deed(lib, "duke", "king", "i", temporary, years), good_with_deed(lib, "duke", "king", "i", permanent, years)
            check(a >= b, "%s for %d years costs %s, %s for good %s" % (temporary, years, -a, permanent, -b))
    # even for one who fears most what it guards against, and is strongest against
    def fearful(w, W):
        W["duke"].traits = set(W["duke"].traits) | {"paranoid", "ambitious"}
        W["duke"].diplomacy = W["duke"].martial = W["duke"].stewardship = W["duke"].intrigue = 30
    for temporary, cap in (("restraint", 15), ("office", 45)):
        p, W = contract_panel(lib, "king", "duke", fearful)
        p.deed("t", "marcher_charge")
        c = p.candidates("t")
        if c:
            p.pick("t", c[0])
        p.me.vars["qpq_ui_t_years"] = 20.0
        p.click("qpq_ui_refresh")
        base = total(p)
        p.offer("t", temporary)
        check(total(p) - base <= cap, "%s for twenty years to the keenest vassal: %s, above %s" % (temporary, total(p) - base, cap))


@test
def goods_that_last_give_a_deadline(lib, check):
    """500 gold for troops has no deed in it, but the troops are not an instant transfer: a deadline is in play.
    The leg gets a term to set and stays open until then. What is handed over at once has none."""
    def gold_for(good):
        p, W = contract_panel(lib, "duke", "king")
        p.deed("t", None)
        p.gold("t", 500)
        p.deed("i", None)
        p.offer("i", good)
        return p
    for good in ("arms", "office", "restraint"):
        p = gold_for(good)
        check(("qpq_ui_i_o_" + good) in p.me.vars, "%s cannot be had with no deed" % good)
        check(p.shown("qpq_ui_term_shown_i"), "%s with no deed has no term to set" % good)
        check(p.shown("qpq_ui_goods_term_i"), "%s with no deed has no row to set the term from" % good)
        check(p.var("i_term") == 60, "%s with no deed runs %s months by default, not five years" % (good, p.var("i_term")))
        check(not p.shown("qpq_ui_term_shown_t"), "the gold paid for %s has a term of its own" % good)
        check(p.var("t_term") == 1, "the gold paid for %s does not change hands at once" % good)
        at_five = total(p)
        check(p.shown("qpq_ui_term_up_i_5"), "%s: the term cannot be raised" % good)
        p.me.vars["qpq_ui_i_years"] = 20.0
        p.click("qpq_ui_refresh")
        check(p.var("i_term") == 240, "%s: a term of twenty years is %s months" % (good, p.var("i_term")))
        check(total(p) <= at_five, "%s for twenty years costs the giver less than for five: %s, %s" % (good, total(p), at_five))
        # it weighs the same as on a deed of that length
        a = good_with_deed(lib, "king", "duke", "t", good, 20)
        p2, W = contract_panel(lib, "king", "duke")
        p2.deed("t", None)
        base = total(p2)
        p2.offer("t", good)
        p2.me.vars["qpq_ui_t_years"] = 20.0
        p2.click("qpq_ui_refresh")
        check(abs(total(p2) - base - a) < 0.01, "%s for twenty years: %s with no deed, %s with one" % (good, total(p2) - base, a))
        # take it back off and the leg is instant again
        p.offer("i", good)
        check(not p.shown("qpq_ui_term_shown_i"), "%s removed, and the leg still has a term" % good)
    # nothing that lasts: no term, done at the next check
    p, W = contract_panel(lib, "king", "duke")
    p.deed("t", None)
    p.offer("t", "ct_revocation")
    check(not p.shown("qpq_ui_term_shown_t"), "a right granted for good has a term to set")
    check(p.var("t_term") == 1, "goods with nothing that lasts do not change hands at once")
    # a deed's term is not doubled up among the goods
    p, W = contract_panel(lib, "king", "duke")
    p.deed("t", "marcher_charge")
    p.offer("t", "arms")
    check(p.shown("qpq_ui_term_shown_t") and not p.shown("qpq_ui_goods_term_t"), "a deed's term shown twice")


@test
def a_lasting_exchange_holds_until_the_deadline(lib, check):
    """Run through the real monthly tick: an exchange with something that lasts stays open for its whole term and is
    then fulfilled, not breached. One with nothing that lasts is done at the first check."""
    def months_until_closed(term, **lasting):
        w, W = standard_world(player="nobody")
        s = Story("deal")
        s.owner = W["duke"]
        s.vars.update(qpq_kind=Flag("barter"), qpq_payer=W["duke"], qpq_agent=W["king"], qpq_months_left=float(term),
                      qpq_term=float(term), qpq_payer_tier=0.0, qpq_agent_tier=0.0)
        s.vars.update(lasting)
        for month in range(1, term + 3):
            r = Run(lib, w, W["duke"], {})
            r.eff(lib.effects["qpq_story_tick_effect"], (s, None))
            check(not r.errors, "month %d of an exchange: %s" % (month, r.errors[:2]))
            if s.vars.get("qpq_closed") is not None:
                return month, s.vars["qpq_closed"].name
        return None, None
    check(months_until_closed(60) == (1, "delivered"), "nothing lasting: closed %s" % (months_until_closed(60),))
    for var in ("qpq_gave_arms", "qpq_offer_restraint"):
        got = months_until_closed(24, **{var: True})
        check(got == (24, "delivered"), "%s for 24 months: closed %s" % (var, got))


@test
def becoming_a_tributary_weighs_as_vanilla(lib, check):
    """demand_tributary_interaction's numbers, on the same scale: base -60, -200 with no casus belli, rank, rivalry."""
    def circ(setup=None, me="king", them="third"):
        p, W = panel(lib, me, them, setup=setup)
        p.deed("t", "accept_the_yoke")
        check(not p.errors, "script errors: %s" % p.errors[:2])
        return p.var("t_a_ask"), p.var("t_a_circ"), p
    ask, base, _ = circ()
    check(ask == -60, "the base ask should be vanilla's -60: %s" % ask)
    def with_cb(w, W):
        W["king"].cbs_on = (W["third"],)
    _, cb, _ = circ(with_cb)
    check(abs(cb - base - 200) < 0.01, "a casus belli should lift vanilla's -200: %s against %s" % (cb, base))
    def rival(w, W):
        w.relate(W["third"], "rival", W["king"])
    _, r, _ = circ(rival)
    check(abs(r - base + 100) < 0.01, "a rival should cost vanilla's -100: %s against %s" % (r, base))
    def empire(w, W):
        W["third"].titles[0].tier = 5
    _, e, _ = circ(empire)
    check(abs(e - base + 100) < 0.01, "an emperor should cost -200 where a king costs -100: %s against %s" % (e, base))


@test
def payment_stands_in_for_a_casus_belli(lib, check):
    """The one change from vanilla: goods paid also take 2 a point off the -200 for no casus belli, down to -50."""
    def paid(amount, setup=None):
        p, W = panel(lib, "king", "third", setup=setup)
        p.deed("t", "accept_the_yoke")
        unpaid = p.var("t_a_circ")
        if amount:
            p.gold("t", amount)
        check(not p.errors, "script errors: %s" % p.errors[:2])
        return p.var("t_a_circ") - unpaid, p.var("t_a_offers"), p.var("acc_total", 0)
    # it grows with the payment: a token sum cannot lift the penalty
    relief, points, _ = paid(10)
    check(points > 0 and abs(relief - 2 * points) < 0.01, "10 gold, %s points, should lift twice that: %s" % (points, relief))
    check(relief < 10, "a token sum lifted %s of the penalty" % relief)
    # and it stops at -50, so a casus belli is still worth having
    relief, points, total_paid = paid(100000)
    check(abs(relief - 150) < 0.01, "the penalty should stop at -50: lifted %s" % relief)
    check(total_paid <= 0, "gold alone bought a king's freedom: %s" % total_paid)
    def with_cb(w, W):
        W["king"].cbs_on = (W["third"],)
    check(paid(100000, with_cb)[0] == 0, "there is no penalty to lift with a casus belli: %s" % paid(100000, with_cb)[0])
    # a lesser ruler can be bought, at a price
    def lesser(w, W):
        W["third"].titles[0].tier = 3
        W["third"].current_strength = W["third"].max_strength = 800
    check(paid(0, lesser)[2] <= 0, "a lesser ruler gave in for nothing: %s" % paid(0, lesser)[2])
    check(paid(10, lesser)[2] <= 0, "a lesser ruler gave in for 10 gold: %s" % paid(10, lesser)[2])
    check(paid(100000, lesser)[2] > 0, "a lesser ruler could not be bought: %s" % paid(100000, lesser)[2])


@test
def what_you_do_in_return_is_payment_too(lib, check):
    """A deed you do for them softens the same penalty, by what it is worth to them; goods handed back take it away."""
    def relief(i_deed=None, mine=0, theirs=0, setup=None):
        p, W = panel(lib, "king", "third", setup=setup, king=dict(gold=100000), third=dict(gold=100000))
        p.deed("t", "accept_the_yoke")
        unpaid = p.var("t_a_circ")
        if mine:
            p.gold("t", mine)
        if i_deed:
            p.deed("i", i_deed)
        elif theirs:
            p.deed("i", None)
        if theirs:
            p.gold("i", theirs)
        check(not p.errors, "script errors: %s" % p.errors[:2])
        return p.var("t_a_circ") - unpaid, p
    # worth 39 to them, on the numbers in the standard world: an alliance they want, less their risk
    r, p = relief("secret_alliance")
    net = p.var("i_a_ask") + p.var("i_a_goal") + p.var("i_a_char") + p.var("i_a_risk") + p.var("i_a_circ")
    check(net > 0 and abs(r - 2 * net) < 0.01, "a deed worth %s to them should lift twice that: %s" % (net, r))
    # a deed that is nothing but a risk to them lifts nothing, and adds nothing to the penalty
    check(relief("proxy_war")[0] == 0, "a deed worth nothing to them moved the penalty: %s" % relief("proxy_war")[0])
    # with goods it adds up, and still stops at -50
    both = relief("secret_alliance", mine=100)[0]
    check(both > r, "goods on top of a deed should lift more: %s against %s" % (both, r))
    check(relief("secret_alliance", mine=100000)[0] == 150, "the penalty should stop at -50: %s" % relief("secret_alliance", mine=100000)[0])
    # with a casus belli there is nothing to lift
    def with_cb(w, W):
        W["king"].cbs_on = (W["third"],)
    check(relief("secret_alliance", setup=with_cb)[0] == 0, "a deed lifted a penalty that does not apply: %s" % relief("secret_alliance", setup=with_cb)[0])
    # gold paid and handed straight back is no payment
    check(relief(mine=1000, theirs=1000)[0] == 0, "gold swapped both ways softened the penalty: %s" % relief(mine=1000, theirs=1000)[0])
    check(relief(mine=1000, theirs=500)[0] < relief(mine=1000)[0], "goods handed back should reduce it: %s" % relief(mine=1000, theirs=500)[0])


@test
def getting_a_tributary_weighs_as_vanilla(lib, check):
    """become_tributary_interaction's numbers, to the one who would be suzerain: base +50, so it is welcome for free
    unless they are a nemesis."""
    def total_for(setup=None):
        p, W = panel(lib, "third", "king", setup=setup)
        p.deed("i", "accept_the_yoke")
        check(not p.errors, "script errors: %s" % p.errors[:2])
        return total(p)
    base = total_for()
    check(base > 0, "an AI turns down a free tributary: %s" % base)
    def nemesis(w, W):
        w.relate(W["king"], "nemesis", W["third"])
    check(total_for(nemesis) < base - 90, "a nemesis should be refused: %s against %s" % (total_for(nemesis), base))


@test
def rejecting_a_suzerain_weighs_as_vanilla(lib, check):
    """cease_paying_tribute_interaction's ai_will_do: base -25, and fear of the suzerain counts double."""
    def parts(setup=None):
        p, W = panel(lib, "foe", "chief", setup=setup)
        p.deed("t", "cast_off_the_yoke")
        check(not p.errors, "script errors: %s" % p.errors[:2])
        return p.var("t_a_ask"), p.var("t_a_circ"), p.var("t_a_goal", 0)
    ask, circ, goal = parts()
    check(ask == -25, "the base should be vanilla's -25: %s" % ask)
    check(not goal, "the tributary's own wishes are counted twice: goal %s" % goal)
    # chief 700 against king 6000: (700 / 6000 - 1) * -50 = +44.2, times -2
    check(abs(circ + 88.33) < 0.5, "a tributary of 700 under a suzerain of 6000 should be -88.3: %s" % circ)
    def rival(w, W):
        w.relate(W["chief"], "rival", W["king"])
    check(abs(parts(rival)[1] - circ - 30) < 0.01, "a rival suzerain should give vanilla's +30: %s" % parts(rival)[1])
    def strong(w, W):
        W["chief"].current_strength = 12000
        W["chief"].max_strength = 12000
    check(parts(strong)[1] > 0, "a tributary far stronger than its suzerain is still afraid: %s" % parts(strong)[1])


@test
def deeds_done_at_sealing_have_no_term(lib, check):
    """A tribute deed takes effect when sealed: no term to set, and a long one is no discount."""
    for me, them, kind in (("king", "third", "accept_the_yoke"), ("foe", "chief", "cast_off_the_yoke")):
        p, W = panel(lib, me, them)
        p.deed("t", kind)
        check(not p.shown("qpq_ui_term_shown_t"), "%s has a term to set" % kind)
        base = p.var("t_a_ask")
        p.me.vars["qpq_ui_t_years"] = 20.0
        p.click("qpq_ui_refresh")
        check(p.var("t_a_ask") == base, "%s asks %s at twenty years, %s usually" % (kind, p.var("t_a_ask"), base))


@test
def absolution_only_from_faiths_with_it(lib, check):
    """Which heads of faith can give absolution follows vanilla's doctrines, not every head of a faith."""
    def has(me, them):
        p, W = panel(lib, me, them)
        p.deed("i", None)
        return p.shown("qpq_ui_offer_i_church")
    check(has("duke2", "pope"), "the Pope cannot give absolution")
    check(not has("foe", "caliph"), "a caliph can give absolution")


@test
def abdication_outweighs_a_county(lib, check):
    """Giving up every title is a bigger ask than ceding one county."""
    p, W = panel(lib, "king", "duke")
    p.deed("t", "the_cloister")
    abdicate = total(p)
    p, W = panel(lib, "duke", "duke2")
    p.deed("t", "title_swap")
    cands = p.me.var_lists.get("qpq_ui_t_title_candidates", [])
    if cands:
        p.pick("t", cands[0])
    check(abdicate < total(p), "abdicating asks %s, one county asks %s" % (abdicate, total(p)))


@test
def one_proxy_war_three_ways(lib, check):
    """Proxy War is one deed asked of different people: each way keeps its own target rules, tiers and terms."""
    def deal(me, them, target):
        p, W = panel(lib, me, them)
        p.deed("t", "proxy_war")
        names = [c.name for c in p.candidates("t")]
        if target not in names:
            return None, names, p
        p.pick("t", W[target])
        return (p.var("t_agent_tier"), p.var("t_payer_tier")), names, p
    abroad, names, _ = deal("king", "duke", "foe")
    check(abroad is not None, "a vassal cannot be sent against a foreign neighbour: %s" % names)
    feud, names, _ = deal("king", "duke", "duke2")
    check(feud is not None, "a vassal cannot be sent against a fellow vassal: %s" % names)
    if abroad and feud:
        check(feud[0] >= abroad[0] + 2 and feud[1] >= abroad[1] + 2, "a feud is no worse than a war abroad: %s, %s" % (feud, abroad))
    hired, names, _ = deal("king", "foe", "third")
    check(hired is not None, "a foreign ruler cannot be hired: %s" % names)
    _, names, _ = deal("king", "foe", "duke")
    check("duke" not in names, "a foreign ruler offered your own vassal as a target: %s" % names)
    # the tiers the three deeds had apart: abroad is a tier lower here for the foe's hostile faith
    check(abroad == (1, 0), "a vassal sent abroad: agent and payer tiers %s, expected (1, 0)" % (abroad,))
    check(hired == (1, 2), "a foreign ruler hired: agent and payer tiers %s, expected (1, 2)" % (hired,))
    # only a feud inside the realm hands the vassal a hook on the liege
    def seal(agent, target):
        w, W = standard_world(player="king")
        r = Run(lib, w, W["king"], {"qpq_payer": W["king"], "qpq_agent": W[agent], "qpq_target": W[target]})
        r.eff(lib.effects["qpq_k_proxy_war_on_seal_effect"], (Story("deal"), None))
        return (W[agent], W["king"]) in w.hooks
    check(seal("duke", "duke2"), "a feud gave the vassal no hook on the liege")
    check(not seal("duke", "foe"), "a war abroad gave the vassal a hook on the liege")
    check(not seal("foe", "third"), "a foreign ruler gained a hook on the payer")


@test
def an_elector_can_sell_a_vote(lib, check):
    """The vote is one deed: a liege can buy it, and an elector can offer it, through the same panel."""
    p, W = panel(lib, "king", "duke")
    check(p.shown("qpq_ui_kind_t_electoral_purchase"), "a liege cannot buy an elector's vote")
    p, W = panel(lib, "duke", "king")
    check(p.shown("qpq_ui_kind_i_electoral_purchase"), "an elector cannot offer their vote")
    p, W = panel(lib, "king", "foe")
    check(not p.shown("qpq_ui_kind_t_electoral_purchase"), "a vote bought from someone who has none")


@test
def a_county_given_away(lib, check):
    """A county handed over in a dowry is a loss to the giver, about what land is worth."""
    p, W = panel(lib, "king", "foe")
    p.deed("t", "title_swap")
    titles = p.me.var_lists.get("qpq_ui_t_title_candidates", [])
    county = [t for t in titles if t.tier == 2]
    check(county, "no county offered for the dowry")
    if county:
        p.pick("t", county[0])
        check(p.var("t_a_goal", 0) <= -30, "giving away a county costs foe only %s" % p.var("t_a_goal"))


@test
def judged_by_their_own_lights(lib, check):
    """An AI weighs what it gets and gives, never the other party: changing only the player's purse, income or
    standing, or what a deed would cost the player, changes nothing in the AI's answer, part by part."""
    def parts(p):
        a = p.acceptance()
        return {k: v for k, v in a.items() if not k.startswith("leg_")}, \
            {L: {k: v for k, v in a.get("leg_" + L, {}).items() if k not in ("payer_tier", "agent_tier")
                 or (L == "t" and k == "agent_tier") or (L == "i" and k == "payer_tier")} for L in "ti"}
    players = [dict(gold=5000, income=2, prestige_level=0), dict(gold=5000, income=200, prestige_level=5)]

    def run(me, them, setup_deal, me_fields, world=None):
        p, W = panel(lib, me, them, setup=world, **{me: me_fields})
        setup_deal(p, W)
        return parts(p)
    # a plain trade of gold
    def barter_deal(p, W):
        barter(p, 60, 30)
    a, b = (run("king", "duke", barter_deal, f) for f in players)
    check(a == b, "a plain trade changes with the player's wealth: %r vs %r" % (a, b))
    # a deed they do, paid in gold
    def deed_t(p, W):
        p.deed("t", "development_charter")
        c = p.me.var_lists.get("qpq_ui_t_title_candidates", [])
        if c:
            p.pick("t", c[0])
        p.gold("t", 80)
    a, b = (run("king", "duke", deed_t, f) for f in players)
    check(a == b, "a deed they do changes with the player's wealth: %r vs %r" % (a, b))
    # a deed you do for them, and its suggested price: neither the player's purse nor what it costs the player
    def rival(w, W):
        w.relate(W["king"], "rival", W["count2"])
        w.opinion(W["king"], W["count2"], -80)
    def kin_rival(w, W):
        rival(w, W)
        W["courtier"].father = W["count2"]      # the doer's own kin: the deed is far worse for the doer
    def deed_i(p, W):
        p.deed("i", "quiet_removal")
        for c in p.candidates("i"):
            if c is W["count2"]:
                p.pick("i", c)
        p.deed("t", None)
        p.gold("i")
    a = run("courtier", "king", deed_i, players[0], rival)
    b = run("courtier", "king", deed_i, players[1], rival)
    c = run("courtier", "king", deed_i, players[0], kin_rival)
    check(a == b, "a deed done for them changes with the player's wealth: %r vs %r" % (a, b))
    check(a[0] == c[0] and a[1]["i"] == c[1]["i"], "a deed done for them changes with what it costs the doer: %r vs %r" % (a, c))
    # every deed: what it is worth to the AI paying for it is the same whoever offers to do it (a betrayal in war
    # excepted: that is worth the strength the doer takes off the enemy; and a tributary, where who it is is the deed,
    # as become_tributary_interaction weighs it)
    w, W = standard_world(player="nobody")
    doers = [W[n] for n in ("duke", "count", "courtier", "foe", "pope")]
    for name in sorted(v for v in lib.values if v.startswith("qpq_") and v.endswith("_worth_value")):
        if name[4:-12] in ("turncoat", "faithless_ally", "accept_the_yoke"):
            continue
        # the deed's own orientation: its proposer is scope:actor (the payer, or for an agent-proposed deed the doer)
        agent_init = name[4:-12] in AGENT_PROPOSED
        seen = set()
        for d in doers:
            actor, recipient = (d, W["king"]) if agent_init else (W["king"], d)
            r = Run(lib, w, W["king"], {"actor": actor, "recipient": recipient, "secondary_recipient": W["count2"],
                                       "target": W["c_county2"]})
            seen.add(round(r.value(name, (W["king"], None)), 3))
        check(len(seen) == 1, "%s depends on who would do the deed: %s" % (name, sorted(seen)))


# --------------------------------------------------------------------------- AI proposals
def ai_propose(lib, who, kind, setup=None, player="nobody"):
    """An AI proposes KIND (qpq_ai_propose_kind_effect, as the AI broker runs it). Sealing is the pact engine's
    own business, outside what the simulator runs: it is recorded instead. Returns (run, sealed?, world)."""
    stubs = {k for k in lib.effects if k.endswith("_seal_from_scopes_effect")} | {"qpq_ai_command_seal_effect"}
    lib.stubs |= stubs
    try:
        w, W = standard_world(player=player)
        if setup:
            setup(w, W)
        r = Run(lib, w, W[who], {})
        r.eff(lib.expand("effect", "qpq_ai_propose_kind_effect", {"KIND": kind}), (W[who], None))
        sealed = any(e[0] == "stub" and e[1].endswith("_seal_from_scopes_effect") for e in r.events)
        return r, sealed, W
    finally:
        lib.stubs -= stubs


@test
def ai_at_war_deals(lib, check):
    """An AI at war hires a neighbour to join it; nobody is paid to end a war or walk out of one."""
    def third_losing(w, W):
        W["war"].attacker_war_score = 40
    r, sealed, W = ai_propose(lib, "third", "join_war", third_losing)
    rec = r.scopes.get("recipient")
    check(rec is not None and rec not in W["war"].attackers + W["war"].defenders,
          "a losing third finds nobody outside the war to hire (%r)" % rec)
    check(r.scopes.get("secondary_recipient") is W["foe"], "the war third hires for is not its war with foe")
    check(not r.errors, "script errors: %s" % r.errors[:3])
    for gone in ("make_peace", "yield_war", "leave_war"):
        check(("qpq_ui_kind_t_%s" % gone) not in lib.guis, "a deal can still %s" % gone)
    # a truce keeps a peace, it does not end a war; an ally already fighting you cannot sell its absence
    p, W = panel(lib, "third", "foe")
    p.deed("t", "bought_truce")
    check("qpq_valid_at_peace" in p.explain(), "third buys a truce from foe in the middle of their war (%s)" % p.explain())
    def foe_ally(w, W):
        w.ally(W["foe"], W["emir"])
    p, W = panel(lib, "third", "foe", setup=foe_ally)
    if p.valid("qpq_ui_kind_t_faithless_ally"):
        p.deed("t", "faithless_ally")
        c = p.candidates("t")
        if c:
            p.pick("t", c[0])
        check("qpq_valid_not_fighting_you" in p.explain(),
              "an enemy already at war with third sells its absence from that war (%s)" % p.explain())


@test
def ai_prepares_for_war(lib, check):
    """Before falling on a neighbour it could beat alone, an AI buys the absence of the ally who would tip the
    war: from a lukewarm ally it can; a loyal one will not sell; with no such ally it does not try."""
    def base(w, W):
        w.wars.clear()
        W["king"].claims.append(W["c_foe_seat"])
        w.ally(W["foe"], W["emir"])
        W["emir"].max_strength = W["emir"].current_strength = 2500
    def lukewarm(w, W):
        base(w, W)
        w.opinion(W["emir"], W["foe"], -40)
        W["emir"].traits |= {"greedy", "deceitful"}
    def loyal(w, W):
        base(w, W)
        w.opinion(W["emir"], W["foe"], 60)
    def unallied(w, W):
        w.wars.clear()
        W["king"].claims.append(W["c_foe_seat"])
    r, sealed, W = ai_propose(lib, "king", "faithless_ally", lukewarm)
    check(r.scopes.get("recipient") is W["emir"] and r.scopes.get("secondary_recipient") is W["foe"],
          "the king does not go to foe's ally the emir (%r, %r)" % (r.scopes.get("recipient"), r.scopes.get("secondary_recipient")))
    check(sealed, "a lukewarm, greedy ally does not sell its absence")
    check(not r.errors, "script errors: %s" % r.errors[:3])
    r, sealed, W = ai_propose(lib, "king", "faithless_ally", loyal)
    check(not sealed, "a loyal ally sells out its friend")
    w, W = standard_world(player="nobody")
    unallied(w, W)
    check(not Run(lib, w, W["king"], {}).trig(lib.triggers["qpq_k_faithless_ally_ai_valid_trigger"], (W["king"], None)),
          "the king looks for an ally to buy off where there is none")


@test
def ai_picks_its_targets(lib, check):
    """AI finders aim where the AI wants: the rival it hates and can beat, by the vassal best able to do it."""
    def rivals(w, W):
        w.relate(W["king"], "rival", W["jarl"])
        w.opinion(W["king"], W["jarl"], -80)
        w.relate(W["king"], "rival", W["emperor"])
        w.opinion(W["king"], W["emperor"], -80)
    r, sealed, W = ai_propose(lib, "king", "chartered_conquest", rivals)
    check(r.scopes.get("secondary_recipient") is W["jarl"],
          "the king's conquest is not aimed at the rival a vassal can beat (%r)" % r.scopes.get("secondary_recipient"))
    check(r.scopes.get("recipient") is W["duke"], "the conquest is not given to the strongest vassal (%r)" % r.scopes.get("recipient"))
    check(sealed, "the duke will not take a conquest of a weak rival")


@test
def ai_hires_wars_three_ways(lib, check):
    """The AI's one Proxy War still has its three ways: a vassal sent abroad, a foreign hand, a feud between vassals."""
    def world(pick):
        def setup(w, W):
            w.random_list_pick = pick
            w.relate(W["king"], "rival", W["foe"])
            w.opinion(W["king"], W["foe"], -80)
            w.relate(W["duke"], "rival", W["duke2"])
        return setup
    r, sealed, W = ai_propose(lib, "king", "proxy_war", world(0))
    check(r.scopes.get("recipient") in (W["duke"], W["duke2"]), "no vassal sent abroad (%r)" % r.scopes.get("recipient"))
    target = r.scopes.get("secondary_recipient")
    check(target is not None and r.w.top_liege(target) is not W["king"], "the war abroad is aimed at home (%r)" % target)
    r, sealed, W = ai_propose(lib, "king", "proxy_war", world(1))
    check(r.scopes.get("secondary_recipient") is W["foe"], "the foreign rival is not the target (%r)" % r.scopes.get("secondary_recipient"))
    hired = r.scopes.get("recipient")
    check(hired is None or hired.liege is None, "the hired hand is someone's vassal (%r)" % hired)
    r, sealed, W = ai_propose(lib, "king", "proxy_war", world(2))
    check(r.scopes.get("recipient") is W["duke"], "the feud does not go to the vassal with the rival (%r)" % r.scopes.get("recipient"))
    check(r.scopes.get("secondary_recipient") is W["duke2"], "the feud is not aimed at the rival (%r)" % r.scopes.get("secondary_recipient"))
    check(not r.errors, "script errors: %s" % r.errors[:3])


@test
def ai_buys_votes_for_its_heir(lib, check):
    """An AI liege who has reason to worry buys an elector's vote for the heir, not for anyone else."""
    def setup(w, W):
        W["king"].primary_heir = W["count"]
        W["king"].traits = set(W["king"].traits) | {"ambitious"}
    r, sealed, W = ai_propose(lib, "king", "electoral_purchase", setup)
    check(r.scopes.get("secondary_recipient") is W["count"], "the vote is not for the heir (%r)" % r.scopes.get("secondary_recipient"))
    check(r.scopes.get("recipient") in (W["duke"], W["duke2"]), "the vote is not bought from an elector (%r)" % r.scopes.get("recipient"))
    check(not r.errors, "script errors: %s" % r.errors[:3])
    w, W = standard_world(player="nobody")
    W["king"].primary_heir = W["count"]
    r = Run(lib, w, W["king"], {})
    check(not r.trig(lib.triggers["qpq_k_electoral_purchase_ai_valid_trigger"], (W["king"], None)),
          "a liege with no reason to worry buys votes")
    W["king"].traits = set(W["king"].traits) | {"ambitious"}
    check(r.trig(lib.triggers["qpq_k_electoral_purchase_ai_valid_trigger"], (W["king"], None)),
          "an ambitious liege with electors does not think of buying votes")


@test
def ai_commands_its_vassals(lib, check):
    """An AI liege a vassal would refuse leans on its authority: the lightest tier that would do, only when its
    standing allows, never when timid, and never past what goodwill can do."""
    def trial(price, legit=5, bold=0):
        w, W = standard_world(player="nobody")
        W["king"].legitimacy_level, W["king"].boldness = legit, bold
        sc = {"actor": W["king"], "recipient": W["duke"], "secondary_recipient": W["jarl"], "qpq_o_gold": True,
              "qpq_price": float(price), "qpq_o_on_delivery": True}
        r = Run(lib, w, W["king"], sc)
        before = r.value("qpq_marcher_charge_ai_acceptance_value", (W["king"], None))
        r.eff(lib.expand("effect", "qpq_ai_try_command_effect", {"KIND": "marcher_charge"}), (W["king"], None))
        after = r.value("qpq_marcher_charge_ai_acceptance_value", (W["king"], None))
        return before, r.scopes.get("qpq_deal_command"), after, r.errors
    before, tier, after, errs = trial(40)
    check(before <= 0 and tier == 1 and after > 0, "a reminder of duty does not tip a near deal (%s, %s, %s)" % (before, tier, after))
    check(not errs, "script errors: %s" % errs[:3])
    before, tier, after, errs = trial(1)
    check(tier is None, "Command is used where even full goodwill cannot cover the deed (%s -> %s)" % (before, after))
    check(trial(40, legit=1)[1] is None, "a liege without the standing for it commands anyway")
    check(trial(40, bold=-80)[1] is None, "a timid liege commands anyway")


# --------------------------------------------------------------------------- time
def with_term(lib, me, them, L, kind, years, setup=None):
    """KIND in leg L at a term of YEARS (None: the usual one), nothing on the other side."""
    def compose(p, W):
        W[me].gold = 10 ** 6
        p.deed(L, kind)
        c = p.candidates(L)
        if c:
            p.pick(L, c[0])
        p.term(L, years)
    return scenario(lib, me, them, compose)[0]


@test
def time_weighs_on_deeds(lib, check):
    """The term weighs on what a deed asks of the one who does it. Something to bring about by a deadline (a war
    won, a rival ruined) is harder in less time: a year asks more than ten. A promise is dearer the longer it
    binds. The usual term sits in between."""
    for kind in kind_names(lib, "t"):
        mode = next(k["mode"] for k in KINDS if k["key"] == kind)
        if is_instant(next(k for k in KINDS if k["key"] == kind)):
            continue
        for me, them in offered_pairs(lib, "t", kind)[:1]:
            ask = {y: with_term(lib, me, them, "t", kind, y).var("t_a_ask") for y in (1, None, 10, 20)}
            line = "%s %s->%s (%s): %r" % (kind, me, them, mode, ask)
            if mode == "restraint":
                check(ask[1] >= ask[None] >= ask[10] >= ask[20] and ask[1] > ask[20],
                      "a promise is not dearer the longer it binds: " + line)
            else:
                check(ask[1] <= ask[None] <= ask[10] <= ask[20] and ask[1] < ask[10],
                      "a deed is not harder in less time: " + line)


@test
def a_war_in_a_year(lib, check):
    """A war in one year is harder to pull off than a war in ten: the duke takes the king's gold to conquer his
    rival in ten years, but the same sum will not buy it in one."""
    def rivals(w, W):
        w.relate(W["king"], "rival", W["jarl"])
        w.opinion(W["king"], W["jarl"], -80)

    def conquest(years, gold=None):
        p, W = panel(lib, "king", "duke", setup=rivals, king=dict(gold=5000))
        p.deed("t", "chartered_conquest")
        p.pick("t", W["jarl"])
        p.term("t", years)
        p.gold("t", gold)
        return p
    fair = {y: conquest(y).var("t_fair") for y in (1, None, 10)}
    check(fair[1] > fair[None] >= fair[10], "the fair price of a conquest does not fall with time: %r" % fair)
    p = conquest(10, fair[10])
    check(p.ai_accepts(), "the duke will not conquer his liege's rival in ten years for %s gold (total %.1f, %s)" % (
        fair[10], total(p), p.failures()))
    p = conquest(1, fair[10])
    check(not p.ai_accepts(), "the duke conquers in one year for what ten years would cost (%s gold, total %.1f)" % (
        fair[10], total(p)))


@test
def sooner_is_better(lib, check):
    """To the one who pays, a deed done for them is worth more the sooner it is done, and a promise made to them
    more the longer it holds."""
    def world(w, W):
        w.relate(W["king"], "rival", W["count2"])
        w.opinion(W["king"], W["count2"], -80)
    for kind in ("quiet_removal", "dossier"):
        fair = {}
        for y in (1, None, 10):
            p, W = panel(lib, "duke", "king", setup=world)
            p.deed("i", kind)
            p.pick("i", W["count2"])
            p.term("i", y)
            p.deed("t", None)
            p.gold("i")
            fair[y] = p.var("i_fair")
        check(fair[1] > fair[None] > fair[10], "%s: the king does not pay more to have it done sooner: %r" % (kind, fair))
    for kind in kind_names(lib, "i"):
        k = next(k for k in KINDS if k["key"] == kind)
        if k["mode"] != "restraint":
            continue
        for me, them in offered_pairs(lib, "i", kind)[:1]:
            worth = {y: with_term(lib, me, them, "i", kind, y) for y in (1, None, 20)}
            worth = {y: p.var("i_a_ask", 0) + p.var("i_a_goal", 0) for y, p in worth.items()}
            if worth[None] > 0:
                check(worth[1] < worth[None] < worth[20], "%s %s->%s: a promise held longer is not worth more to them: %r" % (
                    kind, me, them, worth))


@test
def the_term_is_kept(lib, check):
    """The term runs from one year to twenty, a year or five at a time; the deal is sealed with the term chosen,
    each leg its own; and a goods-only leg has none to set."""
    p, W = panel(lib, "king", "duke")
    p.deed("t", "marcher_charge")
    usual = p.years("t")
    check(usual == 5, "marcher charge's usual term is not five years (%r)" % usual)
    check(not p.shown("qpq_ui_term_usual_t"), "'back to the usual term' shown on the usual term")
    p.term("t", 1)
    check(not p.valid("qpq_ui_term_down_t_1") and not p.valid("qpq_ui_term_down_t_5"), "the term goes below a year")
    p.term("t", 3)
    p.click("qpq_ui_term_down_t_5")
    check(p.years("t") == 1, "five years off three leaves %r, not one" % p.years("t"))
    p.term("t", 20)
    check(not p.valid("qpq_ui_term_up_t_1") and not p.valid("qpq_ui_term_up_t_5"), "the term goes past twenty years")
    p.term("t", 18)
    p.click("qpq_ui_term_up_t_5")
    check(p.years("t") == 20, "five years on eighteen leaves %r, not twenty" % p.years("t"))
    check(p.var("t_term") == 240, "twenty years is not 240 months (%r)" % p.var("t_term"))
    p.term("t", None)
    check(p.years("t") == usual, "'back to the usual term' leaves %r years" % p.years("t"))
    p.deed("t", "chartered_conquest")
    check(p.years("t") == 8, "a new deed keeps the old one's term (%r)" % p.years("t"))
    p.deed("t", None)
    check(not p.shown("qpq_ui_term_shown_t"), "a goods-only leg has a term to set")

    # sealed with the terms chosen: the pact engine (which the simulator does not run) is handed each leg's own
    def world(w, W):
        w.relate(W["king"], "rival", W["count2"])
        w.opinion(W["king"], W["count2"], -80)
    lib.stubs.add("qpq_seal_pact_effect")
    try:
        p, W = panel(lib, "duke", "king", setup=world, duke=dict(gold=5000))
        p.deed("i", "dossier")
        p.pick("i", W["count2"])
        p.term("i", 3)
        p.deed("t", "blessing_for_a_feud")
        p.pick("t", W["count2"])
        p.term("t", 2)
        p.gold("t", 1000)
        check(p.ai_accepts(), "the test deal is refused (%s, total %.1f)" % (p.failures(), total(p)))
        r = p.click("qpq_ui_propose")
        terms = [e[3].get("qpq_term_months") for e in r.events if e[0] == "stub" and e[1] == "qpq_seal_pact_effect"]
        check(terms == [24, 36], "the legs are sealed with terms %r, not 24 and 36 months" % terms)
        check(not r.errors, "script errors: %s" % r.errors[:3])
    finally:
        lib.stubs.discard("qpq_seal_pact_effect")


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
                else:
                    check(not p.refusals(), "%s %s %s->%s: a reason to refuse at any price is shown (%s), "
                          "but they do not refuse" % (leg, kind, me, them, p.refusals()))
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
