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
from qpq_sim import (Library, Panel, Run, Story, contract_level, find_vanilla, offered_pairs, kind_names,  # noqa: E402
                     scenario, standard_world)
from qpq_contracts import CONTRACT_GOODS, TERMS, step_points  # noqa: E402

TESTS = []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpq_kinds import KINDS  # noqa: E402
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
    check((a, pt) == (3, 3), "Mutual Defense League: text says Tier III, script gives agent %s payer %s" % (a, pt))
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


@test
def permanent_outweighs_promised(lib, check):
    """The anchor's first rule: a promise that lapses at the deadline is worth no more than the same protection
    written into the contract for good."""
    p, W = contract_panel(lib, "king", "duke")
    p.deed("t", None)
    base = total(p)
    p.offer("t", "restraint")
    promise = total(p) - base
    p, W = contract_panel(lib, "king", "duke")
    p.deed("t", None)
    base = total(p)
    p.offer("t", "ct_revocation")
    permanent = total(p) - base
    check(promise <= permanent, "Promise of Safety is worth %s, permanent Revocation Protection %s" % (promise, permanent))


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
    # excepted: that is worth the strength the doer takes off the enemy)
    w, W = standard_world(player="nobody")
    doers = [W[n] for n in ("duke", "count", "courtier", "foe", "pope")]
    for name in sorted(v for v in lib.values if v.startswith("qpq_") and v.endswith("_worth_value")):
        if name[4:-12] in ("turncoat", "faithless_ally"):
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
