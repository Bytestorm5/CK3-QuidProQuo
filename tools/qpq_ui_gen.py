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
UI_OFFERS = ["gold", "land", "claim", "office", "marriage", "release_hook", "my_word", "secret", "contract",
             "succession", "clemency", "arms", "artifact", "church", "restraint", "hook"]
TIMINGS = ["up_front", "on_delivery", "split", "stipend"]
CANDIDATE_CAP = 120

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
        ["qpq_o_charter"] + list(extras())


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
            if k["group"].startswith("church_"):
                shown = dlc + rel
            else:
                shown = dlc if k.get("dlc") else "\t\talways = yes\n"
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
        out += ("qpq_ui_land_clear_%s = {\n\tscope = character\n\teffect = {\n\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_ui_%s_land }\n"
                "\t\t\tclear_variable_list = qpq_ui_%s_land\n\t\t}\n\t\tif = {\n\t\t\tlimit = { has_variable = qpq_ui_%s_o_land }\n"
                "\t\t\tremove_variable = qpq_ui_%s_o_land\n\t\t}\n\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % ((L,) * 5)
        # Does the chosen deed have anything to configure (a target or terms)?
        out += ("qpq_ui_config_%s = {\n\tscope = character\n\tis_shown = {\n\t\tOR = {\n\t\t\tqpq_ui_leg_%s_needs_char_trigger = yes\n"
                "\t\t\tqpq_ui_leg_%s_needs_title_trigger = yes\n\t\t\tqpq_ui_leg_%s_needs_artifact_trigger = yes\n") % (L, L, L, L)
        for flag in extras():
            out += "\t\t\tqpq_ui_leg_%s_has_extra_%s_trigger = yes\n" % (L, flag)
        out += "\t\t}\n\t}\n}\n\n"
        # Group headings (deed list)
        # Land is given as chosen titles: picking one adds it to (or takes it off) the list, and the box is
        # ticked while the list is not empty
        out += ("qpq_ui_land_toggle_%s = {\n\tscope = character\n\tsaved_scopes = { qpq_pick }\n\teffect = {\n"
                "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable_list = qpq_ui_%s_land\n"
                "\t\t\t\tis_target_in_variable_list = { name = qpq_ui_%s_land target = scope:qpq_pick }\n\t\t\t}\n"
                "\t\t\tremove_list_variable = { name = qpq_ui_%s_land target = scope:qpq_pick }\n\t\t}\n"
                "\t\telse = {\n\t\t\tadd_to_variable_list = { name = qpq_ui_%s_land target = scope:qpq_pick }\n\t\t}\n"
                "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\thas_variable_list = qpq_ui_%s_land\n"
                "\t\t\t\tvariable_list_size = { name = qpq_ui_%s_land value > 0 }\n\t\t\t}\n\t\t\tset_variable = qpq_ui_%s_o_land\n\t\t}\n"
                "\t\telse = {\n\t\t\tif = {\n\t\t\t\tlimit = { has_variable = qpq_ui_%s_o_land }\n\t\t\t\tremove_variable = qpq_ui_%s_o_land\n\t\t\t}\n\t\t}\n"
                "\t\tqpq_ui_refresh_effect = yes\n\t}\n}\n\n") % ((L,) * 10)
        # Group headings
        for g, _name in GROUPS:
            kinds = [k for k in DEEDS if k["group"] == g]
            if not kinds:
                continue
            if g.startswith("church_"):
                gs = "\t\tOR = {\n"
                for k in kinds:
                    gs += "\t\t\tAND = {\n%s%s\t\t\t}\n" % (block(oriented(k, L, k.get("dlc") or ""), 4),
                                                          block(oriented(k, L, k["rel"]), 4))
                gs += "\t\t}\n"
            else:
                gs = "\t\talways = yes\n"
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
    s += "\t\t\tset_variable = { name = qpq_ui_%s_price value = scope:qpq_price }\n" % L
    # How the recipient of the deal (the other character) sees this leg
    if proposer_me(k, L):
        # You put it to them: their view is exactly the pact's own acceptance
        s += "\t\t\tset_variable = { name = qpq_ui_%s_a_ask value = qpq_%s_ask_value }\n" % (L, key)
        s += "\t\t\tset_variable = { name = qpq_ui_%s_a_offers value = qpq_%s_offer_points_value }\n" % (L, key)
        s += ("\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_other\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_ai_acceptance_value\n"
              "\t\t\t\t\tsubtract = qpq_%s_ask_value\n\t\t\t\t\tsubtract = qpq_%s_offer_points_value\n"
              "\t\t\t\t\tsubtract = {\n\t\t\t\t\t\tvalue = \"scope:recipient.opinion(scope:actor)\"\n\t\t\t\t\t\tmultiply = 0.5\n\t\t\t\t\t}\n"
              "\t\t\t\t}\n\t\t\t}\n") % (L, key, key, key)
    elif k["initiator"] == "payer":
        # They are the payer: they gain the deed and pay the goods
        s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_ask\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_demand_value\n\t\t\t\t\tmultiply = -0.6\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
        s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_offers\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_offer_points_value\n\t\t\t\t\tmultiply = -0.8\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
        s += "\t\t\tset_variable = { name = qpq_ui_%s_a_other value = 0 }\n" % L
    else:
        # They do the deed and are paid
        s += "\t\t\tset_variable = { name = qpq_ui_%s_a_ask value = qpq_%s_demand_value }\n" % (L, key)
        s += "\t\t\tset_variable = {\n\t\t\t\tname = qpq_ui_%s_a_offers\n\t\t\t\tvalue = {\n\t\t\t\t\tvalue = qpq_%s_offer_points_value\n\t\t\t\t\tmultiply = -1\n\t\t\t\t}\n\t\t\t}\n" % (L, key)
        s += "\t\t\tset_variable = { name = qpq_ui_%s_a_other value = 0 }\n" % L
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

    leg_vars = ["ekind", "target", "target_ok", "payer_tier", "agent_tier", "price", "term", "a_ask", "a_offers",
                "a_other"] + ["fail_%d" % i for i in range(max_valid())]
    lists = ["candidates", "title_candidates", "artifact_candidates", "land_candidates"]

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
        eff += ("\tif = {\n\t\tlimit = {\n\t\t\tNOT = { has_variable = qpq_ui_%s_o_land }\n\t\t\thas_variable_list = qpq_ui_%s_land\n\t\t}\n"
                "\t\tclear_variable_list = qpq_ui_%s_land\n\t}\n") % (L, L, L)
        eff += ("\tif = {\n\t\tlimit = { NOT = { has_variable = qpq_ui_%s_o_gold } }\n"
                "\t\tset_variable = { name = qpq_ui_%s_timing value = flag:up_front }\n\t}\n") % (L, L)
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

        # A different deed was picked: the old target and its terms go
        eff += "qpq_ui_clear_leg_%s_effect = {\n" % L
        for v in ["qpq_ui_%s_pick_char" % L, "qpq_ui_%s_target_title" % L, "qpq_ui_%s_target_artifact" % L] + \
                 ["qpq_ui_%s_%s" % (L, f) for f in extras()]:
            eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
        eff += "}\n\n"

        # The whole leg: which Ask carries it, candidates for its target, tiers, price and acceptance
        eff += "qpq_ui_leg_%s_refresh_effect = {\n\tqpq_ui_prune_goods_%s_effect = yes\n" % (L, L)
        eff += "\tif = {\n\t\tlimit = { qpq_ui_leg_%s_allows_land_trigger = yes }\n\t\tqpq_ui_fill_land_%s_effect = yes\n\t}\n" % (L, L)
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
    eff += "\tset_variable = { name = qpq_ui_acc_other value = 0 }\n"
    for L in LEGS:
        eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_%s_ekind }\n" % L
        eff += "\t\tset_variable = qpq_ui_deal_active\n"
        eff += "\t\tchange_variable = { name = qpq_ui_acc_ask add = var:qpq_ui_%s_a_ask }\n" % L
        eff += "\t\tchange_variable = { name = qpq_ui_acc_offers add = var:qpq_ui_%s_a_offers }\n" % L
        eff += "\t\tchange_variable = { name = qpq_ui_acc_other add = var:qpq_ui_%s_a_other }\n\t}\n" % L
    eff += "\tchange_variable = { name = qpq_ui_acc_other add = qpq_ui_deal_opinion_value }\n"
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
            "\t\t\t\tchange_variable = { name = qpq_ui_acc_other add = { value = var:qpq_ui_their_tier multiply = -8 } }\n\t\t\t}\n\t\t}\n")
    eff += ("\t\telse = {\n\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_my_tier < 1 }\n\t\t\t\tset_variable = { name = qpq_ui_my_tier value = 1 }\n\t\t\t}\n"
            "\t\t\tif = {\n\t\t\t\tlimit = { var:qpq_ui_their_tier < 1 }\n\t\t\t\tset_variable = { name = qpq_ui_their_tier value = 1 }\n\t\t\t}\n\t\t}\n")
    eff += "\t}\n"
    eff += ("\tif = {\n\t\tlimit = { has_variable = qpq_ui_deal_active }\n"
            "\t\tset_variable = {\n\t\t\tname = qpq_ui_acc_total\n\t\t\tvalue = {\n\t\t\t\tvalue = var:qpq_ui_acc_ask\n"
            "\t\t\t\tadd = var:qpq_ui_acc_offers\n\t\t\t\tadd = var:qpq_ui_acc_other\n\t\t\t}\n\t\t}\n\t}\n}\n\n")

    # Clear everything the compute steps derive
    eff += "qpq_ui_clear_derived_effect = {\n"
    gv = ["qpq_ui_deal_active", "qpq_ui_my_tier", "qpq_ui_their_tier", "qpq_ui_acc_ask",
          "qpq_ui_acc_offers", "qpq_ui_acc_other", "qpq_ui_acc_total"]
    for L in LEGS:
        gv += ["qpq_ui_%s_%s" % (L, v) for v in leg_vars]
    for v in gv:
        eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
    for L in LEGS:
        for lst in lists:
            eff += ("\tif = {\n\t\tlimit = { has_variable_list = qpq_ui_%s_%s }\n\t\tclear_variable_list = qpq_ui_%s_%s\n\t}\n") % (L, lst, L, lst)
    eff += "}\n\n"

    # Clear the player's choices (on opening and closing)
    eff += "qpq_ui_clear_choices_effect = {\n"
    vs = ["qpq_ui_charter"]
    for L in LEGS:
        vs += ["qpq_ui_%s_pick_char" % L, "qpq_ui_%s_target_title" % L, "qpq_ui_%s_target_artifact" % L] + \
              ["qpq_ui_%s_o_%s" % (L, o) for o in UI_OFFERS] + ["qpq_ui_%s_%s" % (L, f) for f in extras()]
    for v in vs:
        eff += "\tif = {\n\t\tlimit = { has_variable = %s }\n\t\tremove_variable = %s\n\t}\n" % (v, v)
    for L in LEGS:
        eff += "\tif = {\n\t\tlimit = { has_variable_list = qpq_ui_%s_land }\n\t\tclear_variable_list = qpq_ui_%s_land\n\t}\n" % (L, L)
        eff += "\tset_variable = { name = qpq_ui_%s_kind value = flag:none }\n" % L
        eff += "\tset_variable = { name = qpq_ui_%s_timing value = flag:up_front }\n" % L
    eff += "}\n\n"

    # Save the deal as scope values and scopes: for the proposal event and for sealing
    eff += "qpq_ui_save_deal_effect = {\n"
    eff += "\tif = {\n\t\tlimit = { has_variable = qpq_ui_charter }\n\t\tsave_scope_value_as = { name = qpq_deal_charter value = yes }\n\t}\n"
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
        eff += "\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_deal_land_%s }\n\t\t\tclear_variable_list = qpq_deal_land_%s\n\t\t}\n" % (L, L)
        eff += ("\t\tif = {\n\t\t\tlimit = { has_variable_list = qpq_ui_%s_land }\n\t\t\tevery_in_list = {\n\t\t\t\tvariable = qpq_ui_%s_land\n"
                "\t\t\t\tscope:qpq_deal_me = { add_to_variable_list = { name = qpq_deal_land_%s target = prev } }\n\t\t\t}\n\t\t}\n") % (L, L, L)
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
                    "\t\t\t\tgold >= var:qpq_ui_t_price\n\t\t\t}\n\t\t\ttrigger_else_if = {\n\t\t\t\tlimit = {\n"
                    "\t\t\t\t\thas_variable = qpq_ui_t_o_gold\n\t\t\t\t\tvar:qpq_ui_t_timing = flag:split\n\t\t\t\t}\n"
                    "\t\t\t\tgold >= { value = var:qpq_ui_t_price divide = 2 }\n\t\t\t}\n\t\t\ttrigger_else = {\n\t\t\t\talways = yes\n\t\t\t}\n\t\t}\n")
        else:
            trg += ("\t\tcustom_description = {\n\t\t\ttext = QPQ_UI_FAIL_GOLD_THEM\n\t\t\ttrigger_if = {\n\t\t\t\tlimit = {\n"
                    "\t\t\t\t\thas_variable = qpq_ui_i_o_gold\n\t\t\t\t\tvar:qpq_ui_i_timing = flag:up_front\n\t\t\t\t}\n"
                    "\t\t\t\tscope:recipient = { gold >= scope:actor.var:qpq_ui_i_price }\n\t\t\t}\n\t\t\ttrigger_else_if = {\n\t\t\t\tlimit = {\n"
                    "\t\t\t\t\thas_variable = qpq_ui_i_o_gold\n\t\t\t\t\tvar:qpq_ui_i_timing = flag:split\n\t\t\t\t}\n"
                    "\t\t\t\tscope:recipient = { gold >= { value = scope:actor.var:qpq_ui_i_price divide = 2 } }\n"
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
                "\t\t\tNOT = { scope:qpq_deal_%s_o_stipend ?= yes }\n\t\t}\n\t\ttrigger_if = {\n\t\t\tlimit = { scope:qpq_deal_%s_o_split ?= yes }\n"
                "\t\t\t%s = { gold >= { value = scope:qpq_deal_%s_price divide = 2 } }\n\t\t}\n\t\ttrigger_else = {\n"
                "\t\t\t%s = { gold >= scope:qpq_deal_%s_price }\n\t\t}\n\t}\n") % (L, L, L, L, payer, L, payer, L)
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
        out += cl("QpqUiKindDesc_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), "qpq_%s_interaction_desc" % k["key"]) for k in DEEDS], "QPQ_UI_NO_DEED_DESC_%s" % L.upper())
        out += cl("QpqUiKindAsk_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), "qpq_%s_ask_ui_%s" % (k["key"], L)) for k in DEEDS], "qpq_empty")
        hint = {"condition": "QPQ_UI_HINT_CONDITION", "perform": "QPQ_UI_HINT_PERFORM", "restraint": "QPQ_UI_HINT_RESTRAINT"}
        out += cl("QpqUiKindHint_%s" % L, [("var:qpq_ui_%s_kind ?= flag:%s" % (L, k["key"]), hint[k["mode"]]) for k in DEEDS], "qpq_empty")
        out += cl("QpqUiGoldLine_%s" % L, [
            ("NOT = { has_variable = qpq_ui_%s_o_gold }" % L, "qpq_empty"),
            ("var:qpq_ui_%s_timing ?= flag:on_delivery" % L, "QPQ_UI_GOLD_ON_DELIVERY_%s" % L.upper()),
            ("var:qpq_ui_%s_timing ?= flag:split" % L, "QPQ_UI_GOLD_SPLIT_%s" % L.upper()),
            ("var:qpq_ui_%s_timing ?= flag:stipend" % L, "QPQ_UI_GOLD_STIPEND_%s" % L.upper()),
        ], "QPQ_UI_GOLD_UP_FRONT_%s" % L.upper())
    for who in ("my", "their"):
        out += cl("QpqUi%sTier" % who.capitalize(), [("var:qpq_ui_%s_tier ?= %d" % (who, t), "qpq_tier_%d" % t) for t in range(6)], "qpq_empty")
    for who in ("my", "their"):
        out += cl("QpqUiConseq%s" % who.capitalize(),
                  [("has_variable = qpq_ui_charter var:qpq_ui_%s_tier > 0" % who, "QPQ_UI_CONSEQ_PUBLIC_%s" % who.upper())] +
                  [("var:qpq_ui_%s_tier ?= %d" % (who, t), "QPQ_UI_CONSEQ_%d" % t) for t in range(6)], "qpq_empty")
    out += cl("QpqUiSecrecyNote", [("has_variable = qpq_ui_charter", "QPQ_UI_SECRECY_PUBLIC")], "QPQ_UI_SECRECY_SECRET")
    out += cl("QpqUiAcceptance", [
        ("NOT = { exists = var:qpq_ui_acc_total }", "QPQ_UI_ACC_NONE"),
        ("var:qpq_ui_recipient = { is_ai = no }", "QPQ_UI_ACC_PLAYER"),
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
        for t, txt in (("UP_FRONT", "paid when sealed"), ("ON_DELIVERY", "paid on delivery"),
                       ("SPLIT", "half now and half on delivery"), ("STIPEND", "in yearly installments")):
            L_.append(' QPQ_UI_GOLD_%s_%s:0 "#P •#! [GetPlayer.MakeScope.Var(\'qpq_ui_%s_price\').GetValue|0] gold, %s"' % (t, L.upper(), L, txt))
        L_.append(' qpq_deal.1.gold_%s:0 "\\n #P •#! [qpq_deal_%s_price|0] gold"' % (L, L))
    write("localization/english/qpq_ui_kinds_l_english.yml", "\n".join(L_) + "\n")


# ------------------------------------------------------------------ the deal event (a human recipient)
HUB50_TERMS = ["on_delivery", "split", "stipend", "land", "claim", "office", "marriage", "release_hook",
               "my_word", "secret", "contract", "succession", "clemency", "arms", "artifact", "church",
               "restraint", "hook"]
HUB50_EXTRAS = ["qpq_x_armed", "qpq_x_consent", "qpq_x_armies"]


def gen_deal_events(write):
    out = "# GENERATED by tools/qpq_gen.py (tools/qpq_ui_gen.py) - a deal put to a person.\n\nnamespace = qpq_deal\n\n"
    out += "qpq_deal.1 = {\n\ttype = character_event\n\ttitle = qpq_deal.1.t\n\tdesc = {\n\t\tdesc = qpq_deal.1.intro\n"

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
    out += "\t\tdesc = qpq_deal.1.price\n\t}\n"
    out += "\ttheme = intrigue\n\tleft_portrait = root\n\tright_portrait = scope:actor\n\n"
    ok = "qpq_deal_valid_trigger = yes"
    out += ("\toption = {\n\t\tname = qpq_hub.50.a\n\t\ttrigger = { %s }\n\t\tremove_character_flag = qpq_considering_proposal\n"
            "\t\tqpq_seal_deal_effect = yes\n\t}\n") % ok
    out += ("\toption = {\n\t\tname = qpq_hub.50.c\n\t\ttrigger = { NOT = { %s } }\n\t\tcustom_tooltip = qpq_hub.50.c_tt\n"
            "\t\tremove_character_flag = qpq_considering_proposal\n\t\tscope:actor = {\n\t\t\tsend_interface_toast = {\n"
            "\t\t\t\ttype = event_toast_effect_neutral\n\t\t\t\ttitle = qpq_msg_proposal_lapsed_title\n\t\t\t\tleft_icon = root\n"
            "\t\t\t\tcustom_tooltip = qpq_msg_proposal_lapsed_tt\n\t\t\t}\n\t\t}\n\t}\n") % ok
    out += ("\toption = {\n\t\tname = qpq_hub.50.b\n\t\tremove_character_flag = qpq_considering_proposal\n\t\tscope:actor = {\n"
            "\t\t\tadd_opinion = { target = root modifier = qpq_declined_pact_opinion }\n\t\t\tsend_interface_toast = {\n"
            "\t\t\t\ttype = event_toast_effect_neutral\n\t\t\t\ttitle = qpq_msg_proposal_declined_title\n\t\t\t\tleft_icon = root\n"
            "\t\t\t\tcustom_tooltip = qpq_msg_proposal_declined_tt\n\t\t\t}\n\t\t}\n\t}\n}\n")
    write("events/qpq_deal_events.txt", out)


def gen_all(block, fmt_shown, OFFER_DEFS, write):
    import qpq_gui_gen
    gen_scripted_guis(block, fmt_shown, OFFER_DEFS, write)
    gen_ui_script(block, fmt_shown, OFFER_DEFS, write)
    gen_ui_custom_loc(write)
    gen_ui_loc(write)
    gen_deal_events(write)
    qpq_gui_gen.gen_gui(write)
