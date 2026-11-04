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
from qpq_sim import Library, Panel, Run, find_vanilla, offered_pairs, kind_names, scenario, standard_world  # noqa: E402

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
    check(a == 3, "Title Swap (hidden): text says Tier III, script gives %s" % a)
    a, pt = tier("king", "foe", "t", "secret_alliance")
    check(a == 1, "Secret Alliance between independent rulers: text says Tier I, script gives %s" % a)
    def kin(w, W):
        W["count"].liege = W["duke"]
        W["count"].father = W["duke"]
        W["count"].imprisoned_by = W["duke"]
    a, pt = tier("king", "duke", "t", "hand_over", setup=kin, pick="count")
    check(a == 3, "Hand-Over of their own kin: text says Tier III, script gives %s" % a)


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
def a_county_given_away(lib, check):
    """A county handed over in a dowry is a loss to the giver, about what land is worth."""
    p, W = panel(lib, "king", "foe")
    p.deed("t", "secret_clause")
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
