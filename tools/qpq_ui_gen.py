"""Generate the custom Backroom Deal panel: scripted GUIs, UI effects/triggers, custom loc, loc, the deal
event and the .gui window.

A deal is two legs, each of them an ordinary pact of the engine:
    leg "t"  They do the deed, you give the goods.   payer = you,  agent = them.
    leg "i"  You do the deed, they give the goods.   payer = them, agent = you.
Either side may be empty. A leg with goods but no deed is carried by the "barter" kind. Which character is
scope:actor (the proposer) when a kind's own snippets run depends on the kind: see proposer_me().

Panel state lives in variables on the player (qpq_ui_*, and qpq_ui_t_* / qpq_ui_i_* per leg), so it is synced
in multiplayer; the open tab is UI-only state in the GUI variable system (qpq_tab).

Hand-written companions:
    common/scripted_effects/qpq_ui_effects.txt   open / close / refresh / propose / seal the deal
    common/scripted_triggers/qpq_ui_triggers.txt can the deal be proposed
    common/scripted_guis/qpq_ui.txt               close, refresh, propose
    localization/english/qpq_l_english.yml        QPQ_UI_* strings
"""
import os
import re
from qpq_kinds import KINDS, GROUPS
import qpq_goals as goals

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEGS = ("t", "i")


def deal_words(t):
    for a, b in (("Pacts", "Deals"), ("pacts", "deals"), ("Pact", "Deal"), ("pact", "deal")):
        t = re.sub(r"(?<![\w])%s(?![\w])" % a, b, t)
    return t


# GuiScope with the player as root, actor = the player and recipient = the character the panel was opened on.
# AddScope needs a real object scope (X.MakeScope, as vanilla does); a raw .Var('x') is not one.
GS = ("GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'actor', GetPlayer.MakeScope )"
      ".AddScope( 'recipient', GetPlayer.MakeScope.Var('qpq_ui_recipient').Char.MakeScope ).End")
GS_ROOT = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
# Charter is a property of the whole deal, not of one leg's goods
UI_OFFERS = ["gold", "land", "claim", "office", "release_hook", "my_word", "secret", "contract",
             "succession", "clemency", "arms", "artifact", "church", "restraint", "hook"]
TIMINGS = ["up_front", "on_delivery"]
GOLD_STEPS = [10, 100, 1000]
CANDIDATE_CAP = 120
# Goods that are named, not waved at: each is chosen item by item from what the payer has. (good, list name, kind)
PICKED = [("land", "land", "title"), ("artifact", "gift_artifact", "artifact"), ("secret", "gift_secret", "char")]

TITLE_SOURCES = {
    "realm_counties": "every_realm_county",
    "domain_titles": "every_held_title",
    "claimed_titles": "every_claim",
}

DEEDS = [k for k in KINDS if not k.get("carrier")]
BARTER = [k for k in KINDS if k.get("carrier")][0]
DEMAND_KEYS = {"gold", "on_delivery", "split", "stipend", "land", "office", "contract", "release_hook",
               "my_word", "clemency", "artifact", "church"}


# ------------------------------------------------------------------ orientation helpers
def sw(text):
    """Swap scope:actor and scope:recipient in a snippet written from the proposer's point of view."""
    if not text:
        return text
    return re.sub(r"scope:(actor|recipient)(?![A-Za-z0-9_])",
                  lambda m: "scope:" + ("recipient" if m.group(1) == "actor" else "actor"), text)


def proposer_me(k, L):
    """Is the player the proposer (scope:actor) when kind k runs in leg L?"""
    return (k["initiator"] == "payer") == (L == "t")


def oriented(k, L, text):
    return text if proposer_me(k, L) else sw(text)


def orient_effect(k, L):
    return "qpq_deal_orient_%s_effect = yes" % ("normal" if proposer_me(k, L) else "swapped")


def leg_pa(L):
    """(payer, agent) as scope names in the panel's scripted GUIs (actor = you, recipient = them)."""
    return ("scope:actor", "scope:recipient") if L == "t" else ("scope:recipient", "scope:actor")


def retarget(text, k, L):
    """A snippet that reads the target as scope:secondary_recipient / scope:target, for the deal event, where
    the targets are saved per leg."""
    if not text:
        return text
    text = re.sub(r"scope:secondary_recipient(?![A-Za-z0-9_])", "scope:qpq_deal_%s_char" % L, text)
    tgt = "scope:qpq_deal_%s_%s" % (L, "artifact" if k["target"] == "artifact" else "title")
    return re.sub(r"scope:target(?![A-Za-z0-9_])", tgt, text)


def ask_ui(k, L):
    """Panel text for an Ask in leg L: the story/secret ask text with the panel's variables standing in."""
    me, them = "GetPlayer", "GetPlayer.MakeScope.Var('qpq_ui_recipient').Char"
    payer, agent = (me, them) if L == "t" else (them, me)
    return (k["ask"]
            .replace("[qpq_target_title.", "[GetPlayer.MakeScope.Var('qpq_ui_%s_target_title').Title." % L)
            .replace("[qpq_target_artifact.", "[GetPlayer.MakeScope.Var('qpq_ui_%s_target_artifact').Artifact." % L)
            .replace("[qpq_target.", "[GetPlayer.MakeScope.Var('qpq_ui_%s_target').Char." % L)
            .replace("[qpq_payer.", "[%s." % payer)
            .replace("[qpq_agent.", "[%s." % agent))


def ask_ev(k, L):
    """The same Ask in the proposal event (root: the recipient; actor = the proposer)."""
    payer, agent = ("actor", "recipient") if L == "t" else ("recipient", "actor")
    return (k["ask"]
            .replace("[qpq_target_title.", "[qpq_deal_%s_title." % L)
            .replace("[qpq_target_artifact.", "[qpq_deal_%s_artifact." % L)
            .replace("[qpq_target.", "[qpq_deal_%s_target." % L)
            .replace("[qpq_payer.", "[%s." % payer)
            .replace("[qpq_agent.", "[%s." % agent))


def vkind(L, k):
    return "var:qpq_ui_%s_kind = flag:%s" % (L, k["key"])


def vekind(L, k):
    return "var:qpq_ui_%s_ekind = flag:%s" % (L, k["key"])


def extras():
    seen = {}
    for k in DEEDS:
        for x in k.get("extra_options", []):
            seen.setdefault(x["flag"], (x, []))[1].append(k)
    return seen


def max_valid():
    return max(len(k.get("valid", [])) for k in KINDS)


def offer_shown(block, fmt_shown, OFFER_DEFS, o, L, level):
    """The good's availability: the payer of leg L must be able to give it to the agent."""
    p, a = leg_pa(L)
    return block(fmt_shown(OFFER_DEFS[o]["shown"], p, a), level)


def seal_scope_names():
    """Every saved scope the pact-sealing chain creates: cleared between the two legs of a deal."""
    names = set()
    pats = (r"save_(?:temporary_)?scope_as\s*=\s*([A-Za-z0-9_$]+)",
            r"save_(?:temporary_)?scope_value_as\s*=\s*\{\s*name\s*=\s*([A-Za-z0-9_$]+)")
    texts = []
    with open(os.path.join(ROOT, "common/scripted_effects/qpq_core_effects.txt"), encoding="utf-8-sig") as f:
        texts.append(f.read())
    for k in KINDS:
        texts.append(k.get("on_seal") or "")
    for t in texts:
        for p in pats:
            names.update(re.findall(p, t))
    names.update(["qpq_payer", "qpq_agent", "qpq_target", "qpq_target_title", "qpq_target_artifact", "qpq_price",
                  "qpq_payer_tier", "qpq_agent_tier", "qpq_floor_zero", "qpq_term_months", "qpq_story",
                  "qpq_mirror", "qpq_payer_secret", "qpq_agent_secret", "qpq_is_charter", "secondary_recipient",
                  "target"])
    return sorted(n for n in names if "$" not in n and not n.startswith("qpq_deal_") and n not in
                  ("actor", "recipient", "qpq_exposer", "qpq_exposed_half"))


def all_flag_scopes():
    """The scope values a leg's goods are loaded into for the engine (qpq_o_*, extras, charter)."""
    return ["qpq_o_%s" % o for o in UI_OFFERS] + ["qpq_o_%s" % t for t in TIMINGS[1:]] + \
        ["qpq_o_charter", "qpq_gift_payer", "qpq_gift_artifact_points", "qpq_gift_secret_points", "qpq_gift_artifact_cost"] + list(extras())


# ------------------------------------------------------------------ scripted GUIs
def gen_scripted_guis(block, fmt_shown, OFFER_DEFS, write):
    out = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - Backroom Deal panel buttons.\n\n"
    for L in LEGS:
        # One button per deed
        for k in DEEDS:
            out += "qpq_ui_kind_%s_%s = {\n\tscope = character\n\tsaved_scopes = { actor recipient }\n" % (L, k["key"])
            rel = block(oriented(k, L, k["rel"]), 2)
            dlc = block(oriented(k, L, k.get("dlc") or ""), 2)
            # Church deeds that cannot apply between these two (no church, wrong faith, not a head of faith)
            # are not listed at all; every other deed is listed and greyed out with its reasons.
            shown = dlc + rel + block(oriented(k, L, k.get("avail") or ""), 2)
            out += "\tis_shown = {\n%s\t}\n" % shown
            out += "\tis_valid = {\n%s\t}\n" % rel
            out += "\teffect = {\n"
            # Picking a deed selects it; it is taken out again from the side's summary
            out += "\t\tif = {\n\t\t\tlimit = { NOT = { %s } }\n\t\t\tqpq_ui_clear_leg_%s_effect = yes\n\t\t}\n" % (vkind(L, k), L)
            out += "\t\tset_variable = { name = qpq_ui_%s_kind value = flag:%s }\n" % (L, k["key"])
            out += "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n"
        out += "qpq_ui_nodeed_%s = {\n\tscope = character\n\teffect = {\n\t\tset_variable = { name = qpq_ui_%s_kind value = flag:none }\n" % (L, L)
        out += "\t\tqpq_ui_clear_leg_%s_effect = yes\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n" % L
        # Gold: picking it adds it (its amount and timing are set in its window); it is removed from the summary
        out += ("qpq_ui_gold_add_%s = {\n\tscope = character\n\teffect = {\n\t\tset_variable = qpq_ui_%s_o_gold\n"
                "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (L, L)
        # Gold: the amount is the player's to set (the fair price is only where it starts)
        for sign, name in ((1, "up"), (-1, "down")):
            for n in GOLD_STEPS:
                out += ("qpq_ui_gold_%s_%s_%d = {\n\tscope = character\n\teffect = {\n"
                        "\t\tif = {\n\t\t\tlimit = { NOT = { has_variable = qpq_ui_%s_amount } }\n"
                        "\t\t\tset_variable = { name = qpq_ui_%s_amount value = var:qpq_ui_%s_fair }\n\t\t}\n"
                        "\t\tchange_variable = { name = qpq_ui_%s_amount add = %d }\n"
                        "\t\tif = {\n\t\t\tlimit = { var:qpq_ui_%s_amount < 1 }\n\t\t\tset_variable = { name = qpq_ui_%s_amount value = 1 }\n\t\t}\n"
                        "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (name, L, n, L, L, L, L, sign * n, L, L)
        out += ("qpq_ui_gold_fair_%s = {\n\tscope = character\n\tis_shown = { has_variable = qpq_ui_%s_amount }\n"
                "\teffect = {\n\t\tremove_variable = qpq_ui_%s_amount\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (L, L, L)
        for good, lst, _kind in PICKED:
            out += ("qpq_ui_%s_clear_%s = {\n\tscope = character\n\teffect = {\n\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_ui_%s_%s }\n"
                    "\t\t\tclear_variable_list = qpq_ui_%s_%s\n\t\t}\n\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_o_%s }\n"
                    "\t\t\tremove_variable = qpq_ui_%s_o_%s\n\t\t}\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (
                good, L, L, lst, L, lst, L, good, L, good)
        # Does the chosen deed have anything to configure (a target or terms)?
        out += ("qpq_ui_config_%s = {\n\tscope = character\n\tis_shown = {\n\t\tOR = {\n\t\t\tqpq_ui_leg_%s_needs_char_trigger = yes\n"
                "\t\t\tqpq_ui_leg_%s_needs_title_trigger = yes\n\t\t\tqpq_ui_leg_%s_needs_artifact_trigger = yes\n") % (L, L, L, L)
        for flag in extras():
            out += "\t\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n" % (L, flag)
        out += "\t\t}\n\t}\n}\n\n"
        # Group headings (deed list)
        # Land is given as chosen titles: picking one adds it to (or takes it off) the list, and the box is
        # ticked while the list is not empty
        for good, lst, _kind in PICKED:
            v = "qpq_ui_%s_%s" % (L, lst)
            out += ("qpq_ui_%s_toggle_%s = {\n\tscope = character\n\tsaved_scopes = { qpq_pick }\n\teffect = {\n"
                    "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable_list = %s\n"
                    "\t\t\t\tis_target_in_variable_list = { name = %s target = scope:qpq_pick }\n\t\t\t}\n"
                    "\t\t\tremove_list_variable = { name = %s target = scope:qpq_pick }\n\t\t}\n"
                    "\t\telse = {\n\t\t\tadd_to_variable_list = { name = %s target = scope:qpq_pick }\n\t\t}\n"
                    "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable_list = %s\n"
                    "\t\t\t\tvariable_list_size = { name = %s value > 0 }\n\t\t\t}\n\t\t\tset_variable = qpq_ui_%s_o_%s\n\t\t}\n"
                    "\t\telse = {\n\t\t\tif = {\n\t\t\t\tlimit = { has_variable = qpq_ui_%s_o_%s }\n\t\t\t\tremove_variable = qpq_ui_%s_o_%s\n\t\t\t}\n\t\t}\n"
                    "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (good, L, v, v, v, v, v, v, L, good, L, good, L, good)
        # Group headings
        for g, _name in GROUPS:
            kinds = [k for k in DEEDS if k["group"] == g]
            if not kinds:
                continue
            gs = "\t\tOR = {\n"
            for k in kinds:
                gs += "\t\t\tAND = {\n%s%s%s\t\t\t}\n" % (block(oriented(k, L, k.get("dlc") or ""), 4),
                                                         block(oriented(k, L, k["rel"]), 4),
                                                         block(oriented(k, L, k.get("avail") or ""), 4))
            gs += "\t\t}\n"
            out += "qpq_ui_group_%s_%s = {\n\tscope = character\n\tsaved_scopes = { actor recipient }\n\tis_shown = {\n%s\t}\n}\n\n" % (L, g, gs)
        # Goods. A ticked box always stays visible so it can be unticked.
        for o in UI_OFFERS:
            out += "qpq_ui_offer_%s_%s = {\n\tscope = character\n\tsaved_scopes = { actor recipient }\n\tis_shown = {\n" % (L, o)
            out += "\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n" % (L, o)
            out += "\t\tOR = {\n\t\t\thas_variable = qpq_ui_%s_o_%s\n\t\t\tAND = {\n" % (L, o)
            out += offer_shown(block, fmt_shown, OFFER_DEFS, o, L, 4)
            out += "\t\t\t}\n\t\t}\n\t}\n"
            out += "\teffect = {\n\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_o_%s }\n\t\t\tremove_variable = qpq_ui_%s_o_%s\n\t\t}\n" % (L, o, L, o)
            out += "\t\telse = {\n\t\t\tset_variable = qpq_ui_%s_o_%s\n\t\t}\n" % (L, o)
            out += "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n"
        # Payment timing (only with gold)
        for t in TIMINGS:
            out += "qpq_ui_timing_%s_%s = {\n\tscope = character\n\tis_shown = {\n\t\thas_variable = qpq_ui_%s_o_gold\n" % (L, t, L)
            if t != "up_front":
                out += "\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n" % (L, t)
            out += "\t}\n\teffect = {\n\t\tset_variable = { name = qpq_ui_%s_timing value = flag:%s }\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n" % (L, t)
        # Ask-specific extra terms
        for flag, (x, kinds) in extras().items():
            out += "qpq_ui_extra_%s_%s = {\n\tscope = character\n\tis_shown = {\n\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n\t}\n" % (L, flag, L, flag)
            out += "\teffect = {\n\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_%s }\n\t\t\tremove_variable = qpq_ui_%s_%s\n\t\t}\n" % (L, flag, L, flag)
            out += "\t\telse = {\n\t\t\tset_variable = qpq_ui_%s_%s\n\t\t}\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n" % (L, flag)
        out += "qpq_ui_has_extras_%s = {\n\tscope = character\n\tis_shown = {\n\t\tOR = {\n" % L
        for flag in extras():
            out += "\t\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n" % (L, flag)
        out += "\t\t}\n\t}\n}\n\n"
        for t in ("char", "title", "artifact"):
            out += "qpq_ui_needs_%s_target_%s = {\n\tscope = character\n\tis_shown = {\n\t\tqpq_ui_leg_%s_needs_%s_trigger = yes\n\t}\n}\n\n" % (t, L, L, t)
        out += ("qpq_ui_needs_any_target_%s = {\n\tscope = character\n\tis_shown = {\n\t\tOR = {\n"
                "\t\t\tqpq_ui_leg_%s_needs_char_trigger = yes\n\t\t\tqpq_ui_leg_%s_needs_title_trigger = yes\n"
                "\t\t\tqpq_ui_leg_%s_needs_artifact_trigger = yes\n\t\t}\n\t}\n}\n\n") % (L, L, L, L)
        # Picking a target from the lists
        for what, var in (("char", "qpq_ui_%s_pick_char"), ("title", "qpq_ui_%s_target_title"),
                          ("artifact", "qpq_ui_%s_target_artifact")):
            out += ("qpq_ui_pick_%s_%s = {\n\tscope = character\n\tsaved_scopes = { qpq_pick }\n\teffect = {\n"
                    "\t\tset_variable = { name = %s value = scope:qpq_pick }\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % (
                what, L, var % L)
    # Side summaries: "You will" is your deed (leg i) and your goods (leg t); "They will" the reverse
    out += ("qpq_ui_me_empty = {\n\tscope = character\n\tis_shown = {\n\t\tvar:qpq_ui_i_kind = flag:none\n"
            "\t\tNOT = { qpq_ui_leg_t_has_goods_trigger = yes }\n\t}\n}\n\n")
    out += ("qpq_ui_them_empty = {\n\tscope = character\n\tis_shown = {\n\t\tvar:qpq_ui_t_kind = flag:none\n"
            "\t\tNOT = { qpq_ui_leg_i_has_goods_trigger = yes }\n\t}\n}\n\n")
    # Secrecy: public (a Charter, no secret, the fallout lands now) or secret (exposure risk, full fallout)
    out += ("qpq_ui_secrecy_public = {\n\tscope = character\n\teffect = {\n\t\tset_variable = qpq_ui_charter\n"
            "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n")
    out += ("qpq_ui_secrecy_secret = {\n\tscope = character\n\teffect = {\n\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_charter }\n"
            "\t\t\tremove_variable = qpq_ui_charter\n\t\t}\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n")
    write("common/scripted_guis/qpq_ui_kinds.txt", out)


# ------------------------------------------------------------------ UI effects and triggers
def fill_pickers(k, L, block):
    """Candidates for the Ask's target, capped, best first. Runs with the kind's orientation in place."""
    me = "scope:qpq_deal_me"
    if k["target"] == "char":
        pick = k["pick"].replace("add_to_list = characters", "add_to_list = qpq_ui_chars_%s" % L)
        s = block(pick, 3)
        s += ("\t\t\tevery_in_list = {\n\t\t\t\tlist = qpq_ui_chars_%s\n\t\t\t\tsave_temporary_scope_as = secondary_recipient\n"
              "\t\t\t\tif = {\n\t\t\t\t\tlimit = {\n%s\t\t\t\t\t}\n\t\t\t\t\tadd_to_list = qpq_ui_pool_char_%s\n\t\t\t\t}\n\t\t\t}\n") % (
            L, block(k.get("target_valid") or "always = yes", 6), L)
        s += ("\t\t\tordered_in_list = {\n\t\t\t\tlist = qpq_ui_pool_char_%s\n\t\t\t\torder_by = qpq_ui_candidate_order_value\n"
              "\t\t\t\tmax = %d\n\t\t\t\tcheck_range_bounds = no\n"
              "\t\t\t\t%s = { add_to_variable_list = { name = qpq_ui_%s_candidates target = prev } }\n\t\t\t}\n") % (L, CANDIDATE_CAP, me, L)
        return s
    pk = k["pick"]
    src = {"actor": "scope:actor", "recipient": "scope:recipient"}[pk["source"]]
    if k["target"] == "artifact":
        it, lst, order, pool = "every_character_artifact", "qpq_ui_%s_artifact_candidates" % L, "artifact_rarity", "qpq_ui_pool_artifact_%s" % L
    else:
        it, lst, order, pool = TITLE_SOURCES[pk["filter"]], "qpq_ui_%s_title_candidates" % L, "qpq_ui_title_order_value", "qpq_ui_pool_title_%s" % L
    s = "\t\t\t%s = {\n\t\t\t\t%s = {\n\t\t\t\t\tsave_temporary_scope_as = target\n" % (src, it)
    s += "\t\t\t\t\tif = {\n\t\t\t\t\t\tlimit = {\n%s%s\t\t\t\t\t\t}\n\t\t\t\t\t\tadd_to_list = %s\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n" % (
        block(pk["can_pick"], 7), block(k.get("target_valid") or "always = yes", 7), pool)
    s += ("\t\t\tordered_in_list = {\n\t\t\t\tlist = %s\n\t\t\t\torder_by = %s\n\t\t\t\tmax = %d\n"
          "\t\t\t\tcheck_range_bounds = no\n"
          "\t\t\t\t%s = { add_to_variable_list = { name = %s target = prev } }\n\t\t\t}\n") % (pool, order, CANDIDATE_CAP, me, lst)
    return s


def keep_pick(k, L):
    """A pick stays while it is still eligible (it is in the full, uncapped pool), and is kept visible even if
    it falls outside the capped list; then the real pick is loaded as the scope the engine reads."""
    t = k["target"]
    me = "scope:qpq_deal_me"
    if t == "char":
        v, lst, pool = "qpq_ui_%s_pick_char" % L, "qpq_ui_%s_candidates" % L, "qpq_ui_pool_char_%s" % L
        s = ("\t\t\tif = {\n\t\t\t\tlimit = { exists = var:%s }\n\t\t\t\tif = {\n\t\t\t\t\tlimit = { var:%s = { is_in_list = %s } }\n"
             "\t\t\t\t\tif = {\n\t\t\t\t\t\tlimit = {\n\t\t\t\t\t\t\tNOT = { is_target_in_variable_list = { name = %s target = var:%s } }\n\t\t\t\t\t\t}\n"
             "\t\t\t\t\t\tadd_to_variable_list = { name = %s target = var:%s }\n\t\t\t\t\t}\n\t\t\t\t}\n"
             "\t\t\t\telse = {\n\t\t\t\t\tremove_variable = %s\n\t\t\t\t}\n\t\t\t}\n") % (v, v, pool, lst, v, lst, v, v)
        s += "\t\t\tif = {\n\t\t\t\tlimit = { exists = var:%s }\n\t\t\t\tvar:%s = { save_scope_as = secondary_recipient }\n\t\t\t}\n" % (v, v)
        return s
    if t in ("title", "artifact"):
        v = "qpq_ui_%s_target_%s" % (L, t)
        lst = "qpq_ui_%s_%s_candidates" % (L, t)
        pool = "qpq_ui_pool_%s_%s" % (t, L)
        s = ("\t\t\tif = {\n\t\t\t\tlimit = { exists = var:%s }\n\t\t\t\tif = {\n\t\t\t\t\tlimit = { var:%s = { is_in_list = %s } }\n"
             "\t\t\t\t\tif = {\n\t\t\t\t\t\tlimit = {\n\t\t\t\t\t\t\tNOT = { is_target_in_variable_list = { name = %s target = var:%s } }\n\t\t\t\t\t\t}\n"
             "\t\t\t\t\t\tadd_to_variable_list = { name = %s target = var:%s }\n\t\t\t\t\t}\n\t\t\t\t}\n"
             "\t\t\t\telse = {\n\t\t\t\t\tremove_variable = %s\n\t\t\t\t}\n\t\t\t}\n") % (v, v, pool, lst, v, lst, v, v)
        s += "\t\t\tif = {\n\t\t\t\tlimit = { exists = var:%s }\n\t\t\t\tvar:%s = { save_scope_as = target }\n\t\t\t}\n" % (v, v)
        return s
    return ""


REFUSE_WHYS = [w for w, _a in goals.REFUSE_GENERIC if w != "hatred"] + goals.REFUSAL_LABELS
# On your side (leg i) you do the deed and they only pay for it: only what they want for others can stop them
WHYS = {"t": REFUSE_WHYS, "i": list(goals.REFUSAL_LABELS)}


def refusal_flags(k, L, block):
    """Flags for each reason the AI deciding this leg will not do it at any price. Mirrors where the -1000 is
    applied: the pact's own acceptance when you put it to them, the swapped goals and refusals otherwise. Hatred is
    judged once for the whole deal (qpq_ui_ref_hatred)."""
    def flag(why, trig):
        return "\t\t\tif = {\n\t\t\t\tlimit = {\n%s\t\t\t\t}\n\t\t\t\tset_variable = qpq_ui_ref_%s_%s\n\t\t\t}\n" % (
            block(trig, 5), L, why)
    tier = "qpq_%s_agent_tier_value" % k["key"]
    s = ""
    if proposer_me(k, L):
        if k["initiator"] == "payer":
            for why, args in goals.REFUSE_GENERIC:
                if why != "hatred":
                    s += flag(why, "qpq_ai_refuses_%s_trigger = { %s }" % (why, goals.refuse_args(args, "scope:recipient", "scope:actor", tier)))
        if goals.goal_value(k):
            for why, trig in goals.goal_refusal_parts(k):
                s += flag(why, trig)
    else:
        if goals.goal_value(k, True):
            for why, trig in goals.goal_refusal_parts(k, True):
                s += flag(why, trig)
        if k["initiator"] != "payer":
            for why, args in goals.REFUSE_GENERIC:
                if why != "hatred":
                    s += flag(why, "qpq_ai_refuses_%s_trigger = { %s }" % (why, goals.refuse_args(args, "scope:actor", "scope:recipient", tier)))
    return s


def target_exists(k):
    """Trigger text: the Ask's target is in place (always, for an Ask without one)."""
    T = goals.third_party(k)
    if k["target"] == "artifact":
        return "exists = scope:target"
    return ("exists = %s" % T) if T else "always = yes"


def circ_guarded(k, L, text):
    """Their circumstances often turn on the target: count them once it is in place (0 until then)."""
    if target_exists(k) == "always = yes":
        return text
    return ("\t\t\tset_variable = { name = qpq_ui_%s_a_circ value = 0 }\n"
            "\t\t\tif = {\n\t\t\t\tlimit = { %s }\n%s\t\t\t}\n") % (
        L, target_exists(k), "".join("\t" + x + "\n" for x in text.rstrip("\n").split("\n")))


def compute_kind(k, L, block):
    key = k["key"]
    s = ""
    # the target shown in the Ask text
    if k["target"] == "char":
        s += "\t\t\tif = {\n\t\t\t\tlimit = { exists = scope:secondary_recipient }\n"
        s += "\t\t\t\tset_variable = { name = qpq_ui_%s_target value = scope:secondary_recipient }\n\t\t\t}\n" % L
    elif k["target"] == "derived":
        s += "\t\t\tif = {\n\t\t\t\tlimit = { exists = %s }\n\t\t\t\t%s = { save_scope_as = secondary_recipient }\n" % (k["derive"], k["derive"])
        s += "\t\t\t\tset_variable = { name = qpq_ui_%s_target value = scope:secondary_recipient }\n\t\t\t}\n" % L
    elif k["target"] == "title":
        s += "\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\texists = scope:target\n\t\t\t\t\tscope:target = { exists = holder }\n\t\t\t\t}\n"
        s += "\t\t\t\tset_variable = { name = qpq_ui_%s_target value = scope:target.holder }\n\t\t\t}\n" % L
    s += "\t\t\tset_variable = { name = qpq_ui_%s_term value = %d }\n" % (L, k["term"])
    s += "\t\t\tset_variable = { name = qpq_ui_%s_payer_tier value = qpq_%s_payer_tier_value }\n" % (L, key)
    s += "\t\t\tset_variable = { name = qpq_ui_%s_agent_tier value = qpq_%s_agent_tier_value }\n" % (L, key)
    s += "\t\t\tsave_scope_value_as = { name = qpq_price value = qpq_%s_price_value }\n" % key
    s += "\t\t\tset_variable = { name = qpq_ui_%s_fair value = scope:qpq_price }\n" % L
    s += ("\t\t\tif = {\n\t\t\t\tlimit = { has_variable = qpq_ui_%s_amount }\n\t\t\t\tclear_saved_scope = qpq_price\n"
          "\t\t\t\tsave_scope_value_as = { name = qpq_price value = var:qpq_ui_%s_amount }\n\t\t\t}\n") % (L, L)
    s += "\t\t\tset_variable = { name = qpq_ui_%s_price value = scope:qpq_price }\n" % L
    # How the recipient of the deal (the other character) sees this leg, part by part (each a line of the
    # breakdown): the Ask, the goods, their goals, their character, dread, their circumstances, and refusal.
    # Opinion is counted once for the whole deal.
    def setv(part, value):
        return "\t\t\tset_variable = { name = qpq_ui_%s_a_%s value = %s }\n" % (L, part, value)
    gv = goals.goal_value(k, not proposer_me(k, L))
    goal = ("qpq_%s_goal%s_value" % (key, "" if proposer_me(k, L) else "_sw")) if gv else "0"
    if proposer_me(k, L):
        # You put it to them: their view is exactly the pact's own acceptance
        s += setv("ask", "qpq_%s_ask_value" % key)
        s += setv("offers", "qpq_%s_offer_points_value" % key)
        s += setv("char", "qpq_%s_character_value" % key)
        s += setv("dread", "qpq_%s_dread_value" % key)
        s += circ_guarded(k, L, setv("circ", "qpq_%s_circumstance_value" % key))
        s += setv("refuse", "qpq_%s_refusal_value" % key)
    else:
        if k["initiator"] == "payer":
            # They are the payer: they gain the deed and pay the goods
            s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_ask\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_demand_value\n\t\t\t\t\tmultiply = -0.6\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
            s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_offers\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_offer_points_value\n\t\t\t\t\tmultiply = -0.8\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
        else:
            # They do the deed and are paid
            s += setv("ask", "qpq_%s_demand_value" % key)
            s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_offers\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_offer_points_value\n\t\t\t\t\tmultiply = -1\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
        s += setv("char", "0") + setv("dread", "0") + setv("circ", "0") + setv("refuse", "0")
        # Some deeds they will not do at any price
        refuse = []
        if gv and goals.goal_refusal(k, True):
            refuse.append("qpq_%s_goal_sw_refuses_trigger = yes" % key)
        if k["initiator"] != "payer":
            refuse.append("qpq_ai_refuses_trigger = { AGENT = scope:actor PAYER = scope:recipient TIER = qpq_%s_agent_tier_value }" % key)
        if refuse:
            s += ("\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\tOR = {\n%s\t\t\t\t\t}\n\t\t\t\t}\n%s\t\t\t}\n") % (
                "".join("\t\t\t\t\t\t%s\n" % r for r in refuse), "\t" + setv("refuse", "-1000"))
    s += setv("goal", goal)
    s += ("\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%(L)s_a_other\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = var:qpq_ui_%(L)s_a_goal\n"
          "\t\t\t\t\tadd = var:qpq_ui_%(L)s_a_char\n\t\t\t\t\tadd = var:qpq_ui_%(L)s_a_dread\n"
          "\t\t\t\t\tadd = var:qpq_ui_%(L)s_a_circ\n\t\t\t\t\tadd = var:qpq_ui_%(L)s_a_refuse\n\t\t\t\t}\n\t\t\t}\n") % {"L": L}
    s += refusal_flags(k, L, block)
    # Every title beyond the first counts again (land is chosen title by title)
    sign = "1" if proposer_me(k, L) else ("-0.8" if k["initiator"] == "payer" else "-1")
    s += ("\t\t\tif = {\n\t\t\t\tlimit = { has_variable = qpq_ui_%s_o_land }\n\t\t\t\tchange_variable = {\n\t\t\t\t\tname = qpq_ui_%s_a_offers\n"
          "\t\t\t\t\tadd = {\n\t\t\t\t\t\tvalue = qpq_offer_land_points_value\n\t\t\t\t\t\tmultiply = qpq_ui_land_extra_%s_value\n"
          "\t\t\t\t\t\tmultiply = %s\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n") % (L, L, L, sign)
    # Is the target in place?
    if k["target"] == "char":
        need = "exists = scope:secondary_recipient\n" + (k.get("target_valid") or "")
    elif k["target"] in ("title", "artifact"):
        need = "exists = scope:target\n" + (k.get("target_valid") or "")
    elif k["target"] == "derived":
        need = "exists = scope:secondary_recipient"
    else:
        need = "always = yes"
    s += "\t\t\tif = {\n\t\t\t\tlimit = {\n%s\t\t\t\t}\n\t\t\t\tset_variable = qpq_ui_%s_target_ok\n\t\t\t}\n" % (block(need, 5), L)
    # The Ask's own conditions (shown as reasons on the Propose button), once the target is in place
    if k.get("valid"):
        s += "\t\t\tif = {\n\t\t\t\tlimit = { has_variable = qpq_ui_%s_target_ok }\n" % L
        for i, (_loc, trig) in enumerate(k["valid"]):
            s += "\t\t\t\tif = {\n\t\t\t\t\tlimit = {\n\t\t\t\t\t\tNOT = {\n%s\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t\tset_variable = qpq_ui_%s_fail_%d\n\t\t\t\t}\n" % (
                block(trig, 7), L, i)
        s += "\t\t\t}\n"
    return s


def gen_ui_script(block, fmt_shown, OFFER_DEFS, write):
    eff = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - Backroom Deal panel logic, per leg and Ask.\n"
    eff += "# Root: the player. scope:qpq_deal_me / qpq_deal_them are the two characters; actor / recipient are set by\n"
    eff += "# qpq_deal_orient_*_effect to whichever of them is the proposer of the Ask being worked on.\n\n"

    leg_vars = ["ekind", "target", "target_ok", "payer_tier", "agent_tier", "price", "fair", "term", "a_ask", "a_offers",
                "a_other", "a_goal", "a_char", "a_dread", "a_circ", "a_refuse"] + ["fail_%d" % i for i in range(max_valid())]
    lists = ["candidates", "title_candidates", "artifact_candidates", "land_candidates", "gift_artifact_candidates",
             "gift_secret_candidates"]

    # Scope values the engine reads, cleared between the legs and between the kinds of one refresh
    eff += "qpq_ui_clear_scopes_effect = {\n"
    for n in ["secondary_recipient", "target", "qpq_price"] + all_flag_scopes():
        eff += "\tif = {\n\t\tlimit = { exists = scope:%s }\n\t\tclear_saved_scope = %s\n\t}\n" % (n, n)
    eff += "}\n\n"

    for L in LEGS:
        # Load the ticked boxes into the scope values the pact engine and acceptance values read
        eff += "qpq_ui_load_goods_%s_effect = {\n" % L
        for o in UI_OFFERS:
            eff += "\tif = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_ui_%s_o_%s\n\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t}\n" % (L, o, L, o)
            eff += "\t\tsave_scope_value_as = { name = qpq_o_%s value = yes }\n\t}\n" % o
        eff += "\t%s = { save_scope_as = qpq_gift_payer }\n" % ("scope:qpq_deal_me" if L == "t" else "scope:qpq_deal_them")
        for good, lst in (("artifact", "gift_artifact"), ("secret", "gift_secret")):
            eff += ("\tif = {\n\t\tlimit = {\n\t\t\thas_variable_list = qpq_ui_%s_%s\n\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t}\n"
                    "\t\tsave_scope_value_as = { name = qpq_gift_%s_points value = qpq_ui_gift_%s_%s_value }\n") % (L, lst, L, good, good, good, L)
            if good == "artifact":
                eff += "\t\tsave_scope_value_as = { name = qpq_gift_artifact_cost value = qpq_ui_gift_artifact_cost_%s_value }\n" % L
            eff += "\t}\n"
        for t in TIMINGS[1:]:
            eff += "\tif = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_ui_%s_o_gold\n\t\t\tvar:qpq_ui_%s_timing ?= flag:%s\n" % (L, L, t)
            eff += "\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t}\n" % (L, t)
            eff += "\t\tsave_scope_value_as = { name = qpq_o_%s value = yes }\n\t}\n" % t
        for flag in extras():
            eff += "\tif = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_ui_%s_%s\n\t\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n\t\t}\n" % (L, flag, L, flag)
            eff += "\t\tsave_scope_value_as = { name = %s value = yes }\n\t}\n" % flag
        eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_charter }\n\t\tsave_scope_value_as = { name = qpq_o_charter value = yes }\n\t}\n"
        eff += "}\n\n"

        # Goods the chosen deed does not allow are put down again
        eff += "qpq_ui_prune_goods_%s_effect = {\n" % L
        for o in UI_OFFERS:
            eff += ("\tif = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_ui_%s_o_%s\n\t\t\tNOT = { qpq_ui_leg_%s_allows_%s_trigger = yes }\n\t\t}\n"
                    "\t\tremove_variable = qpq_ui_%s_o_%s\n\t}\n") % (L, o, L, o, L, o)
        for good, lst, _kind in PICKED:
            eff += ("\tif = {\n\t\tlimit = {\n\t\t\tNOT = { has_variable = qpq_ui_%s_o_%s }\n\t\t\thas_variable_list = qpq_ui_%s_%s\n\t\t}\n"
                    "\t\tclear_variable_list = qpq_ui_%s_%s\n\t}\n") % (L, good, L, lst, L, lst)
        eff += ("\tif = {\n\t\tlimit = { NOT = { has_variable = qpq_ui_%s_o_gold } }\n"
                "\t\tset_variable = { name = qpq_ui_%s_timing value = flag:up_front }\n"
                "\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_amount }\n\t\t\tremove_variable = qpq_ui_%s_amount\n\t\t}\n\t}\n") % (L, L, L, L)
        for t in TIMINGS[1:]:
            eff += ("\tif = {\n\t\tlimit = {\n\t\t\tvar:qpq_ui_%s_timing = flag:%s\n"
                    "\t\t\tNOT = { qpq_ui_leg_%s_allows_%s_trigger = yes }\n\t\t}\n"
                    "\t\tset_variable = { name = qpq_ui_%s_timing value = flag:up_front }\n\t}\n") % (L, t, L, t, L)
        eff += "}\n\n"

        # Titles the payer of this leg could hand over (never the capital or the primary title), minus those
        # already chosen; the chosen ones are the variable list qpq_ui_<leg>_land
        payer = "scope:qpq_deal_me" if L == "t" else "scope:qpq_deal_them"
        eff += "qpq_ui_fill_land_%s_effect = {\n" % L
        eff += ("\t%s = {\n\t\tevery_held_title = {\n\t\t\tlimit = {\n\t\t\t\ttier >= tier_county\n"
                "\t\t\t\tNOT = { this = %s.capital_county }\n\t\t\t\tNOT = { this = %s.primary_title }\n\t\t\t}\n"
                "\t\t\tadd_to_list = qpq_ui_pool_land_%s\n\t\t}\n\t}\n") % (payer, payer, payer, L)
        eff += ("\tordered_in_list = {\n\t\tlist = qpq_ui_pool_land_%s\n\t\tlimit = {\n\t\t\tNOT = {\n"
                "\t\t\t\tscope:qpq_deal_me = { is_target_in_variable_list = { name = qpq_ui_%s_land target = prev } }\n\t\t\t}\n\t\t}\n"
                "\t\torder_by = qpq_ui_title_order_value\n\t\tmax = %d\n\t\tcheck_range_bounds = no\n"
                "\t\tscope:qpq_deal_me = { add_to_variable_list = { name = qpq_ui_%s_land_candidates target = prev } }\n\t}\n}\n\n") % (
            L, L, CANDIDATE_CAP, L)

        # Artifacts the payer could hand over, best first
        agent = "scope:qpq_deal_them" if L == "t" else "scope:qpq_deal_me"
        eff += "qpq_ui_fill_artifact_%s_effect = {\n" % L
        eff += ("\t%s = {\n\t\tevery_character_artifact = {\n\t\t\tadd_to_list = qpq_ui_pool_gift_artifact_%s\n\t\t}\n\t}\n") % (payer, L)
        eff += ("\tordered_in_list = {\n\t\tlist = qpq_ui_pool_gift_artifact_%s\n\t\tlimit = {\n\t\t\tNOT = {\n"
                "\t\t\t\tscope:qpq_deal_me = { is_target_in_variable_list = { name = qpq_ui_%s_gift_artifact target = prev } }\n\t\t\t}\n\t\t}\n"
                "\t\torder_by = artifact_rarity\n\t\tmax = %d\n\t\tcheck_range_bounds = no\n"
                "\t\tscope:qpq_deal_me = { add_to_variable_list = { name = qpq_ui_%s_gift_artifact_candidates target = prev } }\n\t}\n}\n\n") % (
            L, L, CANDIDATE_CAP, L)
        # People the payer knows a secret about that the other side does not (the secret is named by who it is on)
        eff += "qpq_ui_fill_secret_%s_effect = {\n" % L
        eff += ("\t%s = {\n\t\tevery_known_secret = {\n\t\t\tlimit = {\n\t\t\t\tNOT = { is_known_by = %s }\n"
                "\t\t\t\tNOT = { secret_owner = %s }\n\t\t\t\tNOT = { secret_owner = %s }\n\t\t\t\tsecret_owner = { is_alive = yes }\n\t\t\t}\n"
                "\t\t\tsecret_owner = { add_to_list = qpq_ui_pool_gift_secret_%s }\n\t\t}\n\t}\n") % (payer, agent, agent, payer, L)
        eff += ("\tordered_in_list = {\n\t\tlist = qpq_ui_pool_gift_secret_%s\n\t\tlimit = {\n\t\t\tNOT = {\n"
                "\t\t\t\tscope:qpq_deal_me = { is_target_in_variable_list = { name = qpq_ui_%s_gift_secret target = prev } }\n\t\t\t}\n\t\t}\n"
                "\t\torder_by = qpq_ui_candidate_order_value\n\t\tmax = %d\n\t\tcheck_range_bounds = no\n"
                "\t\tscope:qpq_deal_me = { add_to_variable_list = { name = qpq_ui_%s_gift_secret_candidates target = prev } }\n\t}\n}\n\n") % (
            L, L, CANDIDATE_CAP, L)

        # A different deed was picked: the old target and its terms go
        eff += "qpq_ui_clear_leg_%s_effect = {\n" % L
        for v in ["qpq_ui_%s_pick_char" % L, "qpq_ui_%s_target_title" % L, "qpq_ui_%s_target_artifact" % L,
                  "qpq_ui_%s_amount" % L] + ["qpq_ui_%s_%s" % (L, f) for f in extras()]:
            eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
        eff += "}\n\n"

        # The whole leg: which Ask carries it, candidates for its target, tiers, price and acceptance
        eff += "qpq_ui_leg_%s_refresh_effect = {\n\tqpq_ui_prune_goods_%s_effect = yes\n" % (L, L)
        for good, _lst, _kind in PICKED:
            eff += "\tif = {\n\t\tlimit = { qpq_ui_leg_%s_allows_%s_trigger = yes }\n\t\tqpq_ui_fill_%s_%s_effect = yes\n\t}\n" % (L, good, good, L)
        eff += ("\tif = {\n\t\tlimit = { NOT = { var:qpq_ui_%s_kind = flag:none } }\n"
                "\t\tset_variable = { name = qpq_ui_%s_ekind value = var:qpq_ui_%s_kind }\n\t}\n") % (L, L, L)
        eff += ("\telse_if = {\n\t\tlimit = { qpq_ui_leg_%s_has_goods_trigger = yes }\n"
                "\t\tset_variable = { name = qpq_ui_%s_ekind value = flag:barter }\n\t}\n") % (L, L)
        eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n\t\tqpq_ui_clear_scopes_effect = yes\n" % L
        first = True
        for k in KINDS:
            eff += "\t\t%s = {\n\t\t\tlimit = { %s }\n" % ("if" if first else "else_if", vekind(L, k))
            first = False
            eff += "\t\t\t%s\n" % orient_effect(k, L)
            if k["target"] in ("char", "title", "artifact"):
                eff += fill_pickers(k, L, block)
                # Filling the pickers reuses the target scopes, so the real pick is loaded after it
                for n in ("secondary_recipient", "target"):
                    eff += "\t\t\tif = {\n\t\t\t\tlimit = { exists = scope:%s }\n\t\t\t\tclear_saved_scope = %s\n\t\t\t}\n" % (n, n)
                eff += keep_pick(k, L)
            eff += "\t\t\tqpq_ui_load_goods_%s_effect = yes\n" % L
            eff += compute_kind(k, L, block)
            eff += "\t\t}\n"
        eff += "\t}\n}\n\n"

    # Put the two legs together
    eff += "qpq_ui_deal_finish_effect = {\n\tqpq_deal_orient_normal_effect = yes\n"
    eff += "\tset_variable = { name = qpq_ui_acc_ask value = 0 }\n\tset_variable = { name = qpq_ui_acc_offers value = 0 }\n"
    for part in ("other", "goal", "char", "dread", "circ", "refuse", "opinion", "public"):
        eff += "\tset_variable = { name = qpq_ui_acc_%s value = 0 }\n" % part
    for L in LEGS:
        eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n" % L
        eff += "\t\tset_variable = qpq_ui_deal_active\n"
        eff += "\t\tchange_variable = { name = qpq_ui_acc_ask add = var:qpq_ui_%s_a_ask }\n" % L
        eff += "\t\tchange_variable = { name = qpq_ui_acc_offers add = var:qpq_ui_%s_a_offers }\n" % L
        for part in ("goal", "char", "dread", "circ", "refuse"):
            eff += "\t\tchange_variable = { name = qpq_ui_acc_%s add = var:qpq_ui_%s_a_%s }\n" % (part, L, part)
        eff += "\t}\n"
    # Opinion is counted once for the whole deal
    eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_deal_active }\n\t\tset_variable = { name = qpq_ui_acc_opinion value = qpq_ui_deal_opinion_value }\n\t}\n"
    eff += ("\tif = {\n\t\tlimit = {\n\t\t\tvar:qpq_ui_recipient = { is_ai = yes }\n"
            "\t\t\tvar:qpq_ui_recipient = { opinion = { target = root value <= -60 } }\n\t\t}\n"
            "\t\tchange_variable = { name = qpq_ui_acc_refuse add = -1000 }\n\t\tset_variable = qpq_ui_ref_hatred\n\t}\n")
    # Each side's scandal: the worse of its two halves
    eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_deal_active }\n"
    eff += "\t\tset_variable = { name = qpq_ui_my_tier value = 0 }\n\t\tset_variable = { name = qpq_ui_their_tier value = 0 }\n"
    for L, mine, theirs in (("t", "payer", "agent"), ("i", "agent", "payer")):
        eff += "\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n" % L
        eff += ("\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_%s_%s_tier > var:qpq_ui_my_tier }\n"
                "\t\t\t\tset_variable = { name = qpq_ui_my_tier value = var:qpq_ui_%s_%s_tier }\n\t\t\t}\n") % (L, mine, L, mine)
        eff += ("\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_%s_%s_tier > var:qpq_ui_their_tier }\n"
                "\t\t\t\tset_variable = { name = qpq_ui_their_tier value = var:qpq_ui_%s_%s_tier }\n\t\t\t}\n\t\t}\n") % (L, theirs, L, theirs)
    # Published openly (a Charter), a deal may carry any tier: its fallout lands at once. A secret deal is at
    # least Tier I. Nobody likes to be seen doing what is scandalous: the other side asks more for it.
    eff += ("\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_charter }\n"
            "\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_their_tier > 0 }\n"
            "\t\t\t\tset_variable = { name = qpq_ui_acc_public value = { value = var:qpq_ui_their_tier multiply = -8 } }\n\t\t\t}\n\t\t}\n")
    eff += ("\t\telse = {\n\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_my_tier < 1 }\n\t\t\t\tset_variable = { name = qpq_ui_my_tier value = 1 }\n\t\t\t}\n"
            "\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_their_tier < 1 }\n\t\t\t\tset_variable = { name = qpq_ui_their_tier value = 1 }\n\t\t\t}\n\t\t}\n")
    eff += "\t}\n"
    # Everything but the Ask and the goods, as the panel judges refusal (at -500 or less)
    eff += ("\tset_variable = {\n\t\tname = qpq_ui_acc_other\n\t\tvalue = {\n\t\t\tvalue = var:qpq_ui_acc_goal\n"
            "\t\t\tadd = var:qpq_ui_acc_char\n\t\t\tadd = var:qpq_ui_acc_dread\n\t\t\tadd = var:qpq_ui_acc_circ\n"
            "\t\t\tadd = var:qpq_ui_acc_refuse\n\t\t\tadd = var:qpq_ui_acc_opinion\n\t\t\tadd = var:qpq_ui_acc_public\n\t\t}\n\t}\n")
    # Your authority over a subordinate (Command): what it adds, and what they would have said without it
    eff += "\tqpq_ui_command_compute_effect = yes\n"
    eff += ("\tif = {\n\t\tlimit = { has_variable = qpq_ui_deal_active }\n"
            "\t\tset_variable = {\n\t\t\tname = qpq_ui_acc_before_cmd\n\t\t\tvalue = {\n\t\t\t\tvalue = var:qpq_ui_acc_ask\n"
            "\t\t\t\tadd = var:qpq_ui_acc_offers\n\t\t\t\tadd = var:qpq_ui_acc_other\n\t\t\t}\n\t\t}\n"
            "\t\tset_variable = {\n\t\t\tname = qpq_ui_acc_total\n\t\t\tvalue = {\n\t\t\t\tvalue = var:qpq_ui_acc_before_cmd\n"
            "\t\t\t\tadd = var:qpq_ui_acc_cmd\n\t\t\t}\n\t\t}\n\t}\n}\n\n")

    # Clear everything the compute steps derive
    eff += "qpq_ui_clear_derived_effect = {\n"
    gv = ["qpq_ui_deal_active", "qpq_ui_my_tier", "qpq_ui_their_tier", "qpq_ui_acc_ask",
          "qpq_ui_acc_offers", "qpq_ui_acc_other", "qpq_ui_acc_total", "qpq_ui_ref_hatred",
          "qpq_ui_acc_before_cmd", "qpq_ui_acc_cmd", "qpq_ui_acc_goal", "qpq_ui_acc_char", "qpq_ui_acc_dread", "qpq_ui_acc_circ", "qpq_ui_acc_refuse",
          "qpq_ui_acc_opinion", "qpq_ui_acc_public", "qpq_ui_cmd_ok", "qpq_ui_cmd_level", "qpq_ui_cmd_expect",
          "qpq_ui_cmd_margin"]
    for L in LEGS:
        gv += ["qpq_ui_%s_%s" % (L, v) for v in leg_vars]
        gv += ["qpq_ui_ref_%s_%s" % (L, w) for w in WHYS[L]]
    for v in gv:
        eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
    for L in LEGS:
        for lst in lists:
            eff += ("\tif = {\n\t\tlimit = { has_variable_list = qpq_ui_%s_%s }\n\t\tclear_variable_list = qpq_ui_%s_%s\n\t}\n") % (L, lst, L, lst)
    eff += "}\n\n"

    # Clear the player's choices (on opening and closing)
    eff += "qpq_ui_clear_choices_effect = {\n"
    vs = ["qpq_ui_charter", "qpq_ui_command"]
    for L in LEGS:
        vs += ["qpq_ui_%s_amount" % L, "qpq_ui_%s_pick_char" % L, "qpq_ui_%s_target_title" % L, "qpq_ui_%s_target_artifact" % L] + \
              ["qpq_ui_%s_o_%s" % (L, o) for o in UI_OFFERS] + ["qpq_ui_%s_%s" % (L, f) for f in extras()]
    for v in vs:
        eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
    for L in LEGS:
        for _good, lst, _kind in PICKED:
            eff += "\tif = {\n\t\tlimit = { has_variable_list = qpq_ui_%s_%s }\n\t\tclear_variable_list = qpq_ui_%s_%s\n\t}\n" % (L, lst, L, lst)
        eff += "\tset_variable = { name = qpq_ui_%s_kind value = flag:none }\n" % L
        eff += "\tset_variable = { name = qpq_ui_%s_timing value = flag:up_front }\n" % L
    eff += "}\n\n"

    # Save the deal as scope values and scopes: for the proposal event and for sealing
    eff += "qpq_ui_save_deal_effect = {\n"
    eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_charter }\n\t\tsave_scope_value_as = { name = qpq_deal_charter value = yes }\n\t}\n"
    eff += "\tqpq_ui_command_save_effect = yes\n"
    for L in LEGS:
        eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n" % L
        first = True
        for k in KINDS:
            eff += "\t\t%s = {\n\t\t\tlimit = { %s }\n\t\t\tsave_scope_value_as = { name = qpq_deal_%s_kind value = flag:%s }\n\t\t}\n" % (
                "if" if first else "else_if", vekind(L, k), L, k["key"])
            first = False
        eff += "\t\tsave_scope_value_as = { name = qpq_deal_%s_price value = var:qpq_ui_%s_price }\n" % (L, L)
        for o in UI_OFFERS:
            eff += ("\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable = qpq_ui_%s_o_%s\n\t\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t\t}\n"
                    "\t\t\tsave_scope_value_as = { name = qpq_deal_%s_o_%s value = yes }\n\t\t}\n") % (L, o, L, o, L, o)
        for t in TIMINGS[1:]:
            eff += ("\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable = qpq_ui_%s_o_gold\n\t\t\t\tvar:qpq_ui_%s_timing ?= flag:%s\n"
                    "\t\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t\t}\n"
                    "\t\t\tsave_scope_value_as = { name = qpq_deal_%s_o_%s value = yes }\n\t\t}\n") % (L, L, t, L, t, L, t)
        for flag in extras():
            eff += ("\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable = qpq_ui_%s_%s\n\t\t\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n\t\t\t}\n"
                    "\t\t\tsave_scope_value_as = { name = qpq_deal_%s_%s value = yes }\n\t\t}\n") % (L, flag, L, flag, L, flag)
        for what, v in (("char", "qpq_ui_%s_pick_char"), ("title", "qpq_ui_%s_target_title"),
                        ("artifact", "qpq_ui_%s_target_artifact")):
            eff += "\t\tif = {\n\t\t\tlimit = { exists = var:%s }\n\t\t\tvar:%s = { save_scope_as = qpq_deal_%s_%s }\n\t\t}\n" % (
                v % L, v % L, L, what)
        eff += "\t\tif = {\n\t\t\tlimit = { exists = var:qpq_ui_%s_target }\n\t\t\tvar:qpq_ui_%s_target = { save_scope_as = qpq_deal_%s_target }\n\t\t}\n" % (L, L, L)
        # The titles to hand over wait on the proposer until the deal is sealed
        for _good, lst, _kind in PICKED:
            eff += "\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_deal_%s_%s }\n\t\t\tclear_variable_list = qpq_deal_%s_%s\n\t\t}\n" % (lst, L, lst, L)
            eff += ("\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_ui_%s_%s }\n\t\t\tevery_in_list = {\n\t\t\t\tvariable = qpq_ui_%s_%s\n"
                    "\t\t\t\tscope:qpq_deal_me = { add_to_variable_list = { name = qpq_deal_%s_%s target = prev } }\n\t\t\t}\n\t\t}\n") % (
                L, lst, L, lst, lst, L)
        eff += "\t}\n"
    eff += "}\n\n"

    # Sealing one leg (root and saved scopes: qpq_deal_me / qpq_deal_them, and the qpq_deal_<leg>_* values)
    names = seal_scope_names()
    eff += "qpq_deal_clear_seal_scopes_effect = {\n"
    for n in names + all_flag_scopes():
        eff += "\tif = {\n\t\tlimit = { exists = scope:%s }\n\t\tclear_saved_scope = %s\n\t}\n" % (n, n)
    eff += "}\n\n"
    for L in LEGS:
        eff += "qpq_deal_load_goods_%s_effect = {\n" % L
        for o in UI_OFFERS + TIMINGS[1:]:
            eff += "\tif = {\n\t\tlimit = { scope:qpq_deal_%s_o_%s ?= yes }\n\t\tsave_scope_value_as = { name = qpq_o_%s value = yes }\n\t}\n" % (L, o, o)
        for flag in extras():
            eff += "\tif = {\n\t\tlimit = { scope:qpq_deal_%s_%s ?= yes }\n\t\tsave_scope_value_as = { name = %s value = yes }\n\t}\n" % (L, flag, flag)
        eff += "\tif = {\n\t\tlimit = { scope:qpq_deal_charter ?= yes }\n\t\tsave_scope_value_as = { name = qpq_o_charter value = yes }\n\t}\n"
        eff += "}\n\n"
        eff += "qpq_deal_seal_leg_%s_effect = {\n\tqpq_deal_clear_seal_scopes_effect = yes\n" % L
        # Where the engine finds the titles chosen to be handed over, and which list is this leg's
        for n in ("qpq_deal_land_src", "qpq_land_leg"):
            eff += "\tif = {\n\t\tlimit = { exists = scope:%s }\n\t\tclear_saved_scope = %s\n\t}\n" % (n, n)
        eff += "\tscope:qpq_deal_me = { save_scope_as = qpq_deal_land_src }\n"
        eff += "\tsave_scope_value_as = { name = qpq_land_leg value = flag:%s }\n" % L
        first = True
        for k in KINDS:
            eff += "\t%s = {\n\t\tlimit = { scope:qpq_deal_%s_kind ?= flag:%s }\n" % ("if" if first else "else_if", L, k["key"])
            first = False
            eff += "\t\t%s\n" % orient_effect(k, L)
            if k["target"] == "char":
                eff += "\t\tif = {\n\t\t\tlimit = { exists = scope:qpq_deal_%s_char }\n\t\t\tscope:qpq_deal_%s_char = { save_scope_as = secondary_recipient }\n\t\t}\n" % (L, L)
            elif k["target"] in ("title", "artifact"):
                w = k["target"]
                eff += "\t\tif = {\n\t\t\tlimit = { exists = scope:qpq_deal_%s_%s }\n\t\t\tscope:qpq_deal_%s_%s = { save_scope_as = target }\n\t\t}\n" % (L, w, L, w)
            eff += "\t\tqpq_deal_load_goods_%s_effect = yes\n" % L
            eff += "\t\tsave_scope_value_as = { name = qpq_price value = scope:qpq_deal_%s_price }\n" % L
            eff += "\t\tqpq_k_%s_seal_from_scopes_effect = yes\n" % k["key"]
            eff += "\t}\n"
        eff += "\tscope:qpq_story ?= { save_scope_as = qpq_deal_%s_story }\n}\n\n" % L
    write("common/scripted_effects/qpq_ui_kind_effects.txt", eff)

    # ---------------------------------------------------------------- triggers
    trg = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - Backroom Deal panel conditions (root: the player).\n\n"
    for L in LEGS:
        for o in UI_OFFERS + TIMINGS[1:]:
            trg += "qpq_ui_leg_%s_allows_%s_trigger = {\n\tOR = {\n" % (L, o)
            n = 0
            for k in DEEDS:
                if o in k["offers"]:
                    trg += "\t\t%s\n" % vkind(L, k)
                    n += 1
            if o in BARTER["offers"]:
                trg += "\t\tvar:qpq_ui_%s_kind = flag:none\n" % L
                n += 1
            if not n:
                trg += "\t\talways = no\n"
            trg += "\t}\n}\n\n"
        trg += "qpq_ui_leg_%s_has_goods_trigger = {\n\tOR = {\n" % L
        for o in UI_OFFERS:
            trg += "\t\thas_variable = qpq_ui_%s_o_%s\n" % (L, o)
        trg += "\t}\n}\n\n"
        for flag, (_x, kinds) in extras().items():
            trg += "qpq_ui_leg_%s_has_extra_%s_trigger = {\n\tOR = {\n" % (L, flag)
            for k in kinds:
                trg += "\t\t%s\n" % vkind(L, k)
            trg += "\t}\n}\n\n"
        for t in ("char", "title", "artifact"):
            trg += "qpq_ui_leg_%s_needs_%s_trigger = {\n\tOR = {\n" % (L, t)
            n = 0
            for k in DEEDS:
                if k["target"] == t:
                    trg += "\t\t%s\n" % vkind(L, k)
                    n += 1
            if not n:
                trg += "\t\talways = no\n"
            trg += "\t}\n}\n\n"
        # The Ask's own conditions, as Propose failure reasons
        trg += "qpq_ui_leg_%s_ask_valid_trigger = {\n" % L
        for k in KINDS:
            if not k.get("valid"):
                continue
            trg += "\ttrigger_if = {\n\t\tlimit = { %s }\n" % vekind(L, k)
            for i, (loc, _trig) in enumerate(k["valid"]):
                trg += "\t\tcustom_description = {\n\t\t\ttext = %s\n\t\t\tNOT = { has_variable = qpq_ui_%s_fail_%d }\n\t\t}\n" % (loc, L, i)
            trg += "\t}\n"
        trg += "\talways = yes\n}\n\n"
        # The Ask is still open between these two (things can change while the panel is open)
        trg += "qpq_ui_leg_%s_still_possible_trigger = {\n" % L
        first = True
        for k in KINDS:
            trg += "\t%s = {\n\t\tlimit = { %s }\n%s%s\t}\n" % ("trigger_if" if first else "trigger_else_if", vekind(L, k),
                                                              block(oriented(k, L, k["rel"]), 2),
                                                              block(oriented(k, L, k.get("dlc") or ""), 2))
            first = False
        trg += "\ttrigger_else = {\n\t\talways = no\n\t}\n}\n\n"
        # No second deal of the same Ask between the same two characters
        trg += "qpq_ui_leg_%s_no_same_pact_trigger = {\n" % L
        first = True
        for k in DEEDS:
            trg += "\t%s = {\n\t\tlimit = { %s }\n\t\tNOT = { qpq_has_active_pact_of_kind_with_trigger = { A = scope:actor B = scope:recipient KIND = %s } }\n\t}\n" % (
                "trigger_if" if first else "trigger_else_if", vekind(L, k), k["key"])
            first = False
        trg += "\ttrigger_else = {\n\t\talways = yes\n\t}\n}\n\n"
        # Every ticked good must still be possible (actor, recipient saved)
        trg += "qpq_ui_leg_%s_offers_still_possible_trigger = {\n" % L
        for o in UI_OFFERS:
            trg += "\ttrigger_if = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_ui_%s_o_%s\n\t\t\tqpq_ui_leg_%s_allows_%s_trigger = yes\n\t\t}\n" % (L, o, L, o)
            trg += offer_shown(block, fmt_shown, OFFER_DEFS, o, L, 2)
            trg += "\t}\n"
        trg += "\talways = yes\n}\n\n"
        # One leg of the Propose button's failure reasons
        trg += "qpq_ui_leg_%s_ready_trigger = {\n\ttrigger_if = {\n\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n" % (L, L)
        trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_NOT_POSSIBLE_%s\n\t\t\tqpq_ui_leg_%s_still_possible_trigger = yes\n\t\t}\n") % (L.upper(), L)
        trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_NO_TARGET_%s\n\t\t\thas_variable = qpq_ui_%s_target_ok\n\t\t}\n") % (L.upper(), L)
        trg += "\t\tqpq_ui_leg_%s_ask_valid_trigger = yes\n" % L
        trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_SAME_PACT\n\t\t\tqpq_ui_leg_%s_no_same_pact_trigger = yes\n\t\t}\n") % L
        trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_OFFERS_%s\n\t\t\tqpq_ui_leg_%s_offers_still_possible_trigger = yes\n\t\t}\n") % (L.upper(), L)
        # Gold paid when the deal is sealed must be in the payer's hands
        if L == "t":
            trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_GOLD_YOU\n\t\t\ttrigger_if = {\n\t\t\t\tlimit = {\n"
                    "\t\t\t\t\thas_variable = qpq_ui_t_o_gold\n\t\t\t\t\tvar:qpq_ui_t_timing = flag:up_front\n\t\t\t\t}\n"
                    "\t\t\t\tgold >= var:qpq_ui_t_price\n\t\t\t}\n\t\t\ttrigger_else = {\n\t\t\t\talways = yes\n\t\t\t}\n\t\t}\n")
        else:
            trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_GOLD_THEM\n\t\t\ttrigger_if = {\n\t\t\t\tlimit = {\n"
                    "\t\t\t\t\thas_variable = qpq_ui_i_o_gold\n\t\t\t\t\tvar:qpq_ui_i_timing = flag:up_front\n\t\t\t\t}\n"
                    "\t\t\t\tscope:recipient = { gold >= scope:actor.var:qpq_ui_i_price }\n"
                    "\t\t\t}\n\t\t\ttrigger_else = {\n\t\t\t\talways = yes\n\t\t\t}\n\t\t}\n")
        trg += "\t}\n\ttrigger_else = {\n\t\talways = yes\n\t}\n}\n\n"

    # ---- the deal as sent: is it still sound when it is answered? (event qpq_deal.1; root: the recipient;
    # scope:actor = the proposer, scope:recipient = root, the legs saved as qpq_deal_<leg>_*)
    for L in LEGS:
        trg += "qpq_deal_leg_%s_valid_trigger = {\n\ttrigger_if = {\n\t\tlimit = { exists = scope:qpq_deal_%s_kind }\n" % (L, L)
        first = True
        for k in KINDS:
            body = block(oriented(k, L, k["rel"]), 3) + block(oriented(k, L, k.get("dlc") or ""), 3)
            if k["target"] == "char":
                body += "\t\t\texists = scope:qpq_deal_%s_char\n\t\t\tscope:qpq_deal_%s_char = { is_alive = yes }\n" % (L, L)
                body += block(retarget(oriented(k, L, k.get("target_valid") or ""), k, L), 3)
            elif k["target"] in ("title", "artifact"):
                body += "\t\t\texists = scope:qpq_deal_%s_%s\n" % (L, k["target"])
                body += block(retarget(oriented(k, L, k.get("target_valid") or ""), k, L), 3)
            elif k["target"] == "derived":
                body += block("exists = %s" % oriented(k, L, k["derive"]), 3)
            for loc, trig in k.get("valid", []):
                body += "\t\t\tcustom_description = {\n\t\t\t\ttext = %s\n%s\t\t\t}\n" % (loc, block(retarget(oriented(k, L, trig), k, L), 4))
            if k["key"] != "clemency_bargain":
                body += "\t\t\tscope:actor = { is_imprisoned = no }\n\t\t\tscope:recipient = { is_imprisoned = no }\n"
            if not k.get("carrier"):
                body += "\t\t\tNOT = { qpq_has_active_pact_of_kind_with_trigger = { A = scope:actor B = scope:recipient KIND = %s } }\n" % k["key"]
            trg += "\t\t%s = {\n\t\t\tlimit = { scope:qpq_deal_%s_kind = flag:%s }\n%s\t\t}\n" % (
                "trigger_if" if first else "trigger_else_if", L, k["key"], body)
            first = False
        trg += "\t\ttrigger_else = {\n\t\t\talways = no\n\t\t}\n\t}\n\ttrigger_else = {\n\t\talways = yes\n\t}\n}\n\n"
    # Gold due at sealing is in the payer's hands (leg t: the proposer pays; leg i: the recipient pays)
    trg += "qpq_deal_gold_ok_trigger = {\n"
    for L, payer in (("t", "scope:actor"), ("i", "scope:recipient")):
        trg += ("\ttrigger_if = {\n\t\tlimit = {\n\t\t\tscope:qpq_deal_%s_o_gold ?= yes\n\t\t\tNOT = { scope:qpq_deal_%s_o_on_delivery ?= yes }\n"
                "\t\t}\n\t\t%s = { gold >= scope:qpq_deal_%s_price }\n\t}\n") % (L, L, payer, L)
    trg += "\talways = yes\n}\n\n"
    # Room for the deal's pacts on both sides
    trg += ("qpq_deal_room_trigger = {\n\ttrigger_if = {\n\t\tlimit = {\n\t\t\texists = scope:qpq_deal_t_kind\n\t\t\texists = scope:qpq_deal_i_kind\n\t\t}\n"
            "\t\tscope:actor = {\n\t\t\tOR = {\n\t\t\t\tNOT = { has_variable_list = qpq_pacts }\n"
            "\t\t\t\tvariable_list_size = { name = qpq_pacts value < qpq_pact_cap_minus_one_value }\n\t\t\t}\n\t\t}\n"
            "\t\tscope:recipient = {\n\t\t\tOR = {\n\t\t\t\tNOT = { has_variable_list = qpq_pacts }\n"
            "\t\t\t\tvariable_list_size = { name = qpq_pacts value < qpq_pact_cap_minus_one_value }\n\t\t\t}\n\t\t}\n\t}\n"
            "\ttrigger_else = {\n\t\tqpq_both_have_pact_capacity_trigger = { ACTOR = scope:actor RECIPIENT = scope:recipient }\n\t}\n}\n\n")
    trg += ("qpq_deal_valid_trigger = {\n\tqpq_deal_leg_t_valid_trigger = yes\n\tqpq_deal_leg_i_valid_trigger = yes\n"
            "\tqpq_deal_room_trigger = yes\n\tqpq_deal_gold_ok_trigger = yes\n}\n\n")

    # ---- single-leg proposals made by the AI to a player (event qpq_hub.50) keep their own checks
    trg += "qpq_proposed_kind_is_agent_init_trigger = {\n\tOR = {\n"
    for k in KINDS:
        if k["initiator"] == "agent":
            trg += "\t\tscope:qpq_proposed_kind ?= flag:%s\n" % k["key"]
    trg += "\t}\n}\n\n"
    trg += "qpq_proposed_kind_still_valid_trigger = {\n"
    first = True
    for k in KINDS:
        body = block(k["rel"], 2) + block(k.get("dlc") or "", 2)
        if k["target"] == "char":
            body += "\t\texists = scope:secondary_recipient\n\t\tscope:secondary_recipient = { is_alive = yes }\n"
            body += block(k.get("target_valid") or "", 2)
        elif k["target"] in ("title", "artifact"):
            body += "\t\texists = scope:target\n" + block(k.get("target_valid") or "", 2)
        elif k["target"] == "derived":
            body += "\t\texists = %s\n" % k["derive"]
        for loc, trig in k.get("valid", []):
            body += "\t\tcustom_description = {\n\t\t\ttext = %s\n%s\t\t}\n" % (loc, block(trig, 3))
        if k["key"] != "clemency_bargain":
            body += "\t\tscope:actor = { is_imprisoned = no }\n\t\tscope:recipient = { is_imprisoned = no }\n"
        body += "\t\tNOT = { qpq_has_active_pact_of_kind_with_trigger = { A = scope:actor B = scope:recipient KIND = %s } }\n" % k["key"]
        trg += "\t%s = {\n\t\tlimit = { scope:qpq_proposed_kind = flag:%s }\n%s\t}\n" % (
            "trigger_if" if first else "trigger_else_if", k["key"], body)
        first = False
    trg += "\ttrigger_else = {\n\t\talways = no\n\t}\n}\n"
    write("common/scripted_triggers/qpq_ui_kind_triggers.txt", trg)


# ------------------------------------------------------------------ custom loc for the panel
def gen_ui_custom_loc(write):
    def cl(name, pairs, fallback):
        s = "%s = {\n\ttype = character\n\tlog_loc_errors = no\n" % name
        for trig, key in pairs:
            s += "\ttext = {\n\t\ttrigger = { %s }\n\t\tlocalization_key = %s\n\t}\n" % (trig, key)
        s += "\ttext = {\n\t\tfallback = yes\n\t\tlocalization_key = %s\n\t}\n}\n\n" % fallback
        return s
    out = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - text for the Backroom Deal panel (root: the player).\n\n"
    for L in LEGS:
        out += cl("QpqUiKindName_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), "qpq_%s_name" % k["key"]) for k in DEEDS], "QPQ_UI_NO_DEED")
        # The pitch is spoken by whoever wants the deed done: you (your own words) or them ("might put it like this")
        out += cl("QpqUiKindDesc_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]),
                                            "qpq_%s_%s" % (k["key"], "interaction_desc" if proposer_me(k, L) else "desc_them"))
                                           for k in DEEDS], "QPQ_UI_NO_DEED_DESC_%s" % L.upper())
        out += cl("QpqUiKindAsk_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), "qpq_%s_ask_ui_%s" % (k["key"], L)) for k in DEEDS], "qpq_empty")
        hint = {"condition": "QPQ_UI_HINT_CONDITION", "perform": "QPQ_UI_HINT_PERFORM", "restraint": "QPQ_UI_HINT_RESTRAINT"}
        out += cl("QpqUiKindHint_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), hint[k["mode"]]) for k in DEEDS], "qpq_empty")
        out += cl("QpqUiGoldLine_%s" % L, [
            ("NOT = { has_variable = qpq_ui_%s_o_gold }" % L, "qpq_empty"),
            ("var:qpq_ui_%s_timing ?= flag:on_delivery" % L, "QPQ_UI_GOLD_ON_DELIVERY_%s" % L.upper()),
        ], "QPQ_UI_GOLD_UP_FRONT_%s" % L.upper())
    for who in ("my", "their"):
        out += cl("QpqUi%sTier" % who.capitalize(), [("var:qpq_ui_%s_tier ?= %d" % (who, t), "qpq_tier_%d" % t) for t in range(6)], "qpq_empty")
    for who in ("my", "their"):
        out += cl("QpqUiConseq%s" % who.capitalize(),
                  [("has_variable = qpq_ui_charter var:qpq_ui_%s_tier > 0" % who, "QPQ_UI_CONSEQ_PUBLIC_%s" % who.upper())] +
                  [("var:qpq_ui_%s_tier ?= %d" % (who, t), "QPQ_UI_CONSEQ_%d" % t) for t in range(6)], "qpq_empty")
    out += cl("QpqUiSecrecyNote", [("has_variable = qpq_ui_charter", "QPQ_UI_SECRECY_PUBLIC")], "QPQ_UI_SECRECY_SECRET")
    # Why they will not, at any price: one line per reason that holds
    out += cl("QpqUiRef_hatred", [("has_variable = qpq_ui_ref_hatred", "QPQ_UI_REF_HATRED")], "qpq_empty")
    for L in LEGS:
        for w in WHYS[L]:
            out += cl("QpqUiRef_%s_%s" % (L, w), [("has_variable = qpq_ui_ref_%s_%s" % (L, w), "QPQ_UI_REF_%s_%s" % (w.upper(), L.upper()))], "qpq_empty")
    # The breakdown, one line per part; a part that adds nothing is left out
    for part in ("goal", "char", "dread", "circ", "public", "refuse"):
        out += cl("QpqUiAccLine_%s" % part, [("exists = var:qpq_ui_acc_%s NOT = { var:qpq_ui_acc_%s = 0 }" % (part, part),
                                               "QPQ_UI_ACC_LINE_%s" % part.upper())], "qpq_empty")
    out += cl("QpqUiRefuseBlock", [("exists = var:qpq_ui_acc_other var:qpq_ui_acc_other <= -500", "QPQ_UI_REFUSE_BLOCK")], "qpq_empty")
    out += cl("QpqUiAcceptance", [
        ("NOT = { exists = var:qpq_ui_acc_total }", "QPQ_UI_ACC_NONE"),
        ("var:qpq_ui_recipient = { is_ai = no }", "QPQ_UI_ACC_PLAYER"),
        ("var:qpq_ui_acc_other <= -500", "QPQ_UI_ACC_REFUSE"),
        ("var:qpq_ui_acc_total > 0", "QPQ_UI_ACC_YES"),
    ], "QPQ_UI_ACC_NO")
    write("common/customizable_localization/qpq_ui_custom_loc.txt", out)


def gen_ui_loc(write):
    """Generated loc: the panel's and the event's version of each Ask's text."""
    L_ = ["l_english:"]
    for k in DEEDS:
        for L in LEGS:
            L_.append(' qpq_%s_ask_ui_%s:0 "%s"' % (k["key"], L, deal_words(ask_ui(k, L)).replace('"', '\\"')))
            L_.append(' qpq_%s_ask_ev_%s:0 "%s"' % (k["key"], L, ("\\n #P •#! " + deal_words(ask_ev(k, L))).replace('"', '\\"')))
    for o in UI_OFFERS[1:]:
        L_.append(' QPQ_UI_BULLET_OFFER_%s:0 "#P •#! $qpq_offer_%s$"' % (o, o))
    for L in LEGS:
        for t, txt in (("UP_FRONT", "paid at once"), ("ON_DELIVERY", "paid when the deed is done")):
            L_.append(' QPQ_UI_GOLD_%s_%s:0 "#P •#! [GetPlayer.MakeScope.Var(\'qpq_ui_%s_price\').GetValue|0] gold, %s"' % (t, L.upper(), L, txt))
        L_.append(' qpq_deal.1.gold_%s:0 "\\n #P •#! [qpq_deal_%s_price|0] gold"' % (L, L))
    # Why they will not, at any price (the deed, then the reason)
    them = "[GetPlayer.MakeScope.Var('qpq_ui_recipient').Char.GetShortUIName]"
    them_p = "[GetPlayer.MakeScope.Var('qpq_ui_recipient').Char.GetShortUINamePossessive]"
    for L in LEGS:
        tgt = "[GetPlayer.MakeScope.Var('qpq_ui_%s_target').Char.GetShortUIName]" % L
        tgt_p = "[GetPlayer.MakeScope.Var('qpq_ui_%s_target').Char.GetShortUINamePossessive]" % L
        why = {
            "rival": "%s will risk nothing for a rival (Tier II or worse)" % them,
            "virtue": "%s is too honest, just, zealous or compassionate to commit a crime (Tier IV or worse)" % them,
            "damnable": "it would damn %s (Tier V), and %s is not cowed by you" % (them, them),
            "no_leverage": "a deed this dirty (Tier III or worse), for someone %s dislikes, who holds no strong hook on them and does not frighten them" % them,
            "ally": "%s is allied to %s" % (them, tgt),
            "kin": "%s is %s close family" % (tgt, them_p),
            "stronger": "%s side is more than twice as strong" % tgt_p,
            "liked_ally": "%s is allied to %s, and likes them" % (them, tgt),
            "friend": "%s is %s friend or lover" % (tgt, them_p),
            "rival_target": "%s is %s rival" % (tgt, them_p),
            "rival_you": "you are %s rival" % them_p,
        }
        for w in WHYS[L]:
            L_.append(' QPQ_UI_REF_%s_%s:0 "\\n#N •#! [GetPlayer.Custom(\'QpqUiKindName_%s\')]: %s"' % (w.upper(), L.upper(), L, why[w]))
    L_.append(' QPQ_UI_REF_HATRED:0 "\\n#N •#! %s despises you (opinion of -60 or worse)"' % them)
    lines = "[GetPlayer.Custom('QpqUiRef_hatred')]" + "".join(
        "[GetPlayer.Custom('QpqUiRef_%s_%s')]" % (L, w) for L in LEGS for w in WHYS[L])
    L_.append(' QPQ_UI_REFUSE_LINES:0 "%s"' % lines)
    L_.append(' QPQ_UI_REFUSE_BLOCK:0 "#T Why %s will not, at any price#!$QPQ_UI_REFUSE_LINES$\\n\\n"' % them)
    for k in DEEDS:
        L_.append(' qpq_%s_desc_them:0 "#weak [GetPlayer.MakeScope.Var(\'qpq_ui_recipient\').Char.GetShortUIName] might put it like this:#!\\n#F $qpq_%s_flavor$#!\\n\\n$qpq_%s_rules$"' % (k["key"], k["key"], k["key"]))
        L_.append(' qpq_%s_pitch_ev:0 "\\n\\n#F $qpq_%s_flavor$#!"' % (k["key"], k["key"]))
    write("localization/english/qpq_ui_kinds_l_english.yml", "\n".join(L_) + "\n")


# ------------------------------------------------------------------ the deal event (a human recipient)
HUB50_TERMS = ["on_delivery", "land", "claim", "office", "release_hook",
               "my_word", "secret", "contract", "succession", "clemency", "arms", "artifact", "church",
               "restraint", "hook"]
HUB50_EXTRAS = ["qpq_x_armed", "qpq_x_consent", "qpq_x_armies"]


def gen_deal_events(write):
    out = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - a deal put to a person.\n\nnamespace = qpq_deal\n\n"
    # Title: the deed asked of the reader, else the one offered, else a plain offer
    out += "qpq_deal.1 = {\n\ttype = character_event\n\ttitle = {\n\t\tfirst_valid = {\n"
    for L in ("t", "i"):
        for k in DEEDS:
            out += "\t\t\ttriggered_desc = {\n\t\t\t\ttrigger = { scope:qpq_deal_%s_kind ?= flag:%s }\n\t\t\t\tdesc = qpq_%s_name\n\t\t\t}\n" % (L, k["key"], k["key"])
    out += "\t\t\tdesc = qpq_deal.1.t\n\t\t}\n\t}\n\tdesc = {\n\t\tdesc = qpq_deal.1.intro\n"
    # The proposer's pitch, for a deed they would naturally be the one to ask for
    out += "\t\tfirst_valid = {\n"
    for L in ("t", "i"):
        for k in DEEDS:
            if proposer_me(k, L):
                out += "\t\t\ttriggered_desc = {\n\t\t\t\ttrigger = { scope:qpq_deal_%s_kind ?= flag:%s }\n\t\t\t\tdesc = qpq_%s_pitch_ev\n\t\t\t}\n" % (L, k["key"], k["key"])
    out += "\t\t\tdesc = qpq_empty\n\t\t}\n"
    # A liege who commands it rather than asks
    out += "\t\tfirst_valid = {\n"
    for t in (3, 2, 1):
        out += "\t\t\ttriggered_desc = {\n\t\t\t\ttrigger = { scope:qpq_deal_command ?= %d }\n\t\t\t\tdesc = qpq_deal.1.command_%d\n\t\t\t}\n" % (t, t)
    out += "\t\t\tdesc = qpq_empty\n\t\t}\n"

    def side(deed_leg, goods_leg, header, nothing_trig):
        s = "\t\ttriggered_desc = {\n\t\t\ttrigger = { always = yes }\n\t\t\tdesc = %s\n\t\t}\n" % header
        s += "\t\tfirst_valid = {\n"
        for k in DEEDS:
            s += "\t\t\ttriggered_desc = {\n\t\t\t\ttrigger = { scope:qpq_deal_%s_kind ?= flag:%s }\n\t\t\t\tdesc = qpq_%s_ask_ev_%s\n\t\t\t}\n" % (deed_leg, k["key"], k["key"], deed_leg)
        s += "\t\t\tdesc = qpq_empty\n\t\t}\n"
        s += "\t\ttriggered_desc = {\n\t\t\ttrigger = { scope:qpq_deal_%s_o_gold ?= yes }\n\t\t\tdesc = qpq_deal.1.gold_%s\n\t\t}\n" % (goods_leg, goods_leg)
        for o in HUB50_TERMS:
            s += "\t\ttriggered_desc = {\n\t\t\ttrigger = { scope:qpq_deal_%s_o_%s ?= yes }\n\t\t\tdesc = qpq_hub.50.term_%s\n\t\t}\n" % (goods_leg, o, o)
        for x in HUB50_EXTRAS:
            s += "\t\ttriggered_desc = {\n\t\t\ttrigger = { scope:qpq_deal_%s_%s ?= yes }\n\t\t\tdesc = qpq_hub.50.term_%s\n\t\t}\n" % (deed_leg, x, x)
        s += "\t\ttriggered_desc = {\n\t\t\ttrigger = {\n\t\t\t\tNOT = { exists = scope:qpq_deal_%s_kind }\n\t\t\t\tNOT = { scope:qpq_deal_%s_o_gold ?= yes }\n" % (deed_leg, goods_leg)
        for o in HUB50_TERMS:
            s += "\t\t\t\tNOT = { scope:qpq_deal_%s_o_%s ?= yes }\n" % (goods_leg, o)
        s += "\t\t\t}\n\t\t\tdesc = qpq_deal.1.nothing\n\t\t}\n"
        return s

    # What the proposer will do: their deed is leg i's, their goods are leg t's
    out += side("i", "t", "qpq_deal.1.they_will", None)
    out += side("t", "i", "qpq_deal.1.you_will", None)
    out += ("\t\ttriggered_desc = {\n\t\t\ttrigger = { scope:qpq_deal_charter ?= yes }\n\t\t\tdesc = qpq_hub.50.term_charter\n\t\t}\n")
    out += ("\t\tfirst_valid = {\n\t\t\ttriggered_desc = {\n\t\t\t\ttrigger = { scope:qpq_deal_charter ?= yes }\n"
            "\t\t\t\tdesc = qpq_deal.1.stakes_charter\n\t\t\t}\n\t\t\tdesc = qpq_deal.1.stakes_secret\n\t\t}\n\t}\n")
    out += "\ttheme = intrigue\n\tleft_portrait = root\n\tright_portrait = scope:actor\n\n"
    ok = "qpq_deal_valid_trigger = yes"
    out += ("\toption = {\n\t\tname = qpq_hub.50.a\n\t\ttrigger = { %s }\n\t\tremove_character_flag = qpq_considering_proposal\n"
            "\t\tqpq_seal_deal_effect = yes\n\t}\n") % ok
    out += ("\toption = {\n\t\tname = qpq_hub.50.c\n\t\ttrigger = { NOT = { %s } }\n\t\tcustom_tooltip = qpq_hub.50.c_tt\n"
            "\t\tremove_character_flag = qpq_considering_proposal\n\t\tscope:actor = {\n\t\t\tsend_interface_toast = {\n"
            "\t\t\t\ttype = event_toast_effect_neutral\n\t\t\t\ttitle = qpq_msg_proposal_lapsed_title\n\t\t\t\tleft_icon = root\n"
            "\t\t\t\tcustom_tooltip = qpq_msg_proposal_lapsed_tt\n\t\t\t}\n\t\t}\n\t}\n") % ok
    out += ("\toption = {\n\t\tname = qpq_hub.50.b\n\t\tremove_character_flag = qpq_considering_proposal\n"
            "\t\tqpq_command_defied_effect = yes\n\t\tscope:actor = {\n"
            "\t\t\tadd_opinion = { target = root modifier = qpq_declined_pact_opinion }\n\t\t\tsend_interface_toast = {\n"
            "\t\t\t\ttype = event_toast_effect_neutral\n\t\t\t\ttitle = qpq_msg_proposal_declined_title\n\t\t\t\tleft_icon = root\n"
            "\t\t\t\tcustom_tooltip = qpq_msg_proposal_declined_tt\n\t\t\t}\n\t\t}\n\t}\n}\n")
    write("events/qpq_deal_events.txt", out)


# What an artifact does, by the vanilla modifiers it can carry (tools/artifact_modifiers.txt lists every vanilla one)
ARTIFACT_FAMILIES = {
    "prestige": r"prestige",
    "piety": r"piety|clergy|zealot",
    "gold": r"income|tax|gold_cost|hire_cost|maintenance|development_growth",
    "war": r"prowess|knight|casualty|raid|levy|advantage|pursue|retreat|controlled_province|men_at_arms|damage|siege|"
           r"screen|counter|skirmish|supply|toughness|duel",
    "scheme": r"scheme|secrecy",
    "standing": r"opinion|legitimacy|influence|merit|vassal_limit|dread|tyranny|grandeur",
}


def gen_artifact_triggers(write):
    path = os.path.join(ROOT, "tools/artifact_modifiers.txt")
    with open(path, encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip()]
    out = ("# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - what an artifact does, from the modifiers it carries.\n"
           "# Root: the artifact.\n\n")
    for fam, rx in ARTIFACT_FAMILIES.items():
        out += "qpq_artifact_grants_%s_trigger = {\n\tOR = {\n" % fam
        for n in names:
            if re.search(rx, n):
                out += "\t\thas_artifact_modifier = %s\n" % n
        out += "\t}\n}\n\n"
    write("common/scripted_triggers/qpq_artifact_triggers.txt", out)


def gen_all(block, fmt_shown, OFFER_DEFS, write):
    import qpq_gui_gen
    gen_artifact_triggers(write)
    gen_scripted_guis(block, fmt_shown, OFFER_DEFS, write)
    gen_ui_script(block, fmt_shown, OFFER_DEFS, write)
    gen_ui_custom_loc(write)
    gen_ui_loc(write)
    gen_deal_events(write)
    qpq_gui_gen.gen_gui(write)
