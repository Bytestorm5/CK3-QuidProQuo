"""Quid Pro Quo - contract terms as goods, priced from vanilla's own contract weights.

Each good moves one vassal contract obligation one step. Its price comes from the numbers vanilla gives each
obligation level in common/subject_contracts/contracts: `score` (who a change favours, and by how much: vanilla's
own measure of an even trade) and `ai_liege_desire` / `ai_subject_desire` (how much each side wants the level).
TERMS copies them; the contract_weights_match_vanilla deal test fails if a game patch changes them.

The anchor for every other good in the mod is POINTS_PER_SCORE: acceptance points per point of vanilla score.
    gain (what the one who gets it counts) = POINTS_PER_SCORE * score step
    cost (what the one who gives it counts) = POINTS_PER_SCORE * (score step + how much more the giver wants to keep
                                              this level than the other wants the change, if at all)
"""

POINTS_PER_SCORE = 15

# Levels low to high, as vanilla lists them. Where vanilla leaves out `score` it defaults to the level's order.
# Where a desire is a script value, this is its unconditional base.
_TAX_LEVELS = dict(score=[2, 1, 0, -2, -3], liege=[1, 2, 3, 5, 6], subject=[5, 4, 3, 2, 1])
_LEVY_LEVELS = dict(score=[2, 1, 0, -1, -2], liege=[1, 2, 3, 4, 5], subject=[5, 4, 3, 2, 1])
TERMS = {
    "feudal_government_taxes": _TAX_LEVELS,
    "feudal_government_levies": _LEVY_LEVELS,
    "title_revocation_rights": dict(score=[0, 1], liege=[1, 0], subject=[0, 1]),
    "council_rights": dict(score=[0, 3], liege=[2, 0], subject=[0, 1]),
    "war_declaration_rights": dict(score=[0, 1], liege=[2, 0], subject=[0, 1]),
    "fortification_rights": dict(score=[0, 1], liege=[2, 0], subject=[0, 1]),
    "coinage_rights": dict(score=[0, 1], liege=[2, 0], subject=[0, 1]),
    "religious_rights": dict(score=[0, 3], liege=[2, 0], subject=[0, 10]),
}

_FEUDAL = "OR = { government_has_flag = government_is_feudal government_has_flag = government_is_japan_feudal }"
_FEUDAL_OR_CLAN = ("OR = { government_has_flag = government_is_feudal government_has_flag = government_is_japan_feudal "
                   "government_has_flag = government_is_clan }")

# step: down / up move the obligation one level towards 0 / towards the last level; grant sets a right.
# has: the vanilla flag a granted right sets, where it has one. allow: vanilla's own conditions for the level,
# with {S} the subject and {L} the liege.
CONTRACT_GOODS = [
    dict(key="ct_tax_down", term="feudal_government_taxes", step="down", gov=_FEUDAL, money=True, name="Lower Taxes",
         desc="Lower the [tax|E] they owe you by one level in their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand lower taxes", demand_desc="Your [tax|E] to them falls by one level in your [vassal_contract|E], when you deliver.",
         term_text="their taxes lowered one level", owe="Lower [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName]'s taxes by one level",
         owed="Your taxes to [Story.MakeScope.Var('qpq_payer').Char.GetShortUIName] fall by one level"),
    dict(key="ct_levy_down", term="feudal_government_levies", step="down", gov=_FEUDAL, name="Lower Levies",
         desc="Lower the [levies|E] they owe you by one level in their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand lower levies", demand_desc="Your [levies|E] to them fall by one level in your [vassal_contract|E], when you deliver.",
         term_text="their levies lowered one level", owe="Lower [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName]'s levies by one level",
         owed="Your levies to [Story.MakeScope.Var('qpq_payer').Char.GetShortUIName] fall by one level"),
    dict(key="ct_revocation", term="title_revocation_rights", step="grant", gov=_FEUDAL_OR_CLAN, has="vassal_contract_cannot_revoke_titles",
         allow="OR = { {S}.faith = {L}.faith {L}.faith = { NOT = { has_doctrine_parameter = unlock_jizya_contract } } }",
         name="Revocation Protection",
         desc="Write into their [vassal_contract|E] that you can never [revoke|E] their titles, when the deal is done. Permanent.",
         demand="Demand revocation protection", demand_desc="They can never [revoke|E] your titles: written into your [vassal_contract|E] when you deliver.",
         term_text="their titles protected from revocation", owe="Protect [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName]'s titles from revocation, by contract",
         owed="Your titles protected from revocation, by contract"),
    dict(key="ct_council", term="council_rights", step="grant", gov=_FEUDAL_OR_CLAN, has="can_demand_council_seat",
         name="Council Guarantee",
         desc="Give them the right in their [vassal_contract|E] to demand a seat on your [council|E], when the deal is done. Permanent, unlike a seat given as Office, which lasts only the term.",
         demand="Demand a council guarantee", demand_desc="The right to demand a seat on their [council|E], written into your [vassal_contract|E] when you deliver.",
         term_text="the right to a council seat", owe="Guarantee [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] the right to a council seat",
         owed="The right to a seat on [Story.MakeScope.Var('qpq_payer').Char.GetShortUIName]'s council"),
    dict(key="ct_war", term="war_declaration_rights", step="grant", gov=_FEUDAL_OR_CLAN, has="vassal_contract_war_override",
         name="War Declaration Rights",
         desc="Let them declare war freely, whatever your [crown_authority|E], through their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand war declaration rights", demand_desc="The right to declare war freely, written into your [vassal_contract|E] when you deliver.",
         term_text="the right to declare war freely", owe="Grant [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] the right to declare war",
         owed="The right to declare war freely"),
    dict(key="ct_fort", term="fortification_rights", step="grant", gov=_FEUDAL,
         allow="{L}.culture = { has_innovation = innovation_battlements }", name="Fortification Rights",
         desc="Grant fortification rights in their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand fortification rights", demand_desc="Fortification rights, written into your [vassal_contract|E] when you deliver.",
         term_text="fortification rights", owe="Grant [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] fortification rights",
         owed="Fortification rights"),
    dict(key="ct_coinage", term="coinage_rights", step="grant", gov=_FEUDAL,
         allow="{L}.culture = { has_innovation = innovation_currency_02 }", name="Coinage Rights",
         desc="Grant coinage rights in their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand coinage rights", demand_desc="Coinage rights, written into your [vassal_contract|E] when you deliver.",
         term_text="coinage rights", owe="Grant [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] coinage rights",
         owed="Coinage rights"),
    dict(key="ct_faith", term="religious_rights", step="grant", gov=_FEUDAL_OR_CLAN, has="religiously_protected",
         allow="NOT = { {S}.faith = {L}.faith } {L} = { NOT = { rite = { rite_has_tenet = tenet_tax_nonbelievers } } NOT = { faith = { has_doctrine = special_doctrine_jizya } } }",
         name="Religious Protection",
         desc="Protect them from being pressed over their different [faith|E], in their [vassal_contract|E], when the deal is done. Permanent.",
         demand="Demand religious protection", demand_desc="Protection for your [faith|E], written into your [vassal_contract|E] when you deliver.",
         term_text="protection for their faith", owe="Protect [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName]'s faith, by contract",
         owed="Your faith protected, by contract"),
    dict(key="ct_tax_up", term="feudal_government_taxes", step="up", gov=_FEUDAL, money=True, name="Higher Taxes",
         desc="Raise the [tax|E] you owe them by one level in your [vassal_contract|E], when the deal is done. Permanent.",
         term_text="your taxes raised one level", owe="Your taxes to [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] rise by one level",
         owed="[Story.MakeScope.Var('qpq_payer').Char.GetShortUIName]'s taxes to you rise by one level"),
    dict(key="ct_levy_up", term="feudal_government_levies", step="up", gov=_FEUDAL, name="Higher Levies",
         desc="Raise the [levies|E] you owe them by one level in your [vassal_contract|E], when the deal is done. Permanent.",
         term_text="your levies raised one level", owe="Your levies to [Story.MakeScope.Var('qpq_agent').Char.GetShortUIName] rise by one level",
         owed="[Story.MakeScope.Var('qpq_payer').Char.GetShortUIName]'s levies to you rise by one level"),
]
CONTRACT_KEYS = [g["key"] for g in CONTRACT_GOODS]
# What a vassal can demand of its liege in a deal the vassal proposes
CONTRACT_DEMANDS = [g["key"] for g in CONTRACT_GOODS if g["step"] != "up"]


def _steps(g):
    """(current level, level after) for each level the good can move an obligation from."""
    n = len(TERMS[g["term"]]["score"])
    if g["step"] == "grant":
        return [(0, 1)]
    if g["step"] == "down":
        return [(lv, lv - 1) for lv in range(1, n)]
    return [(lv, lv + 1) for lv in range(0, n - 1)]


def step_points(g, frm, to):
    """(gain, cost) of moving this good's obligation from level frm to level to."""
    t = TERMS[g["term"]]
    score = abs(t["score"][to] - t["score"][frm])
    # a good that eases the vassal is given by the liege; one that burdens the vassal is given by the vassal
    giver, getter = ("subject", "liege") if g["step"] == "up" else ("liege", "subject")
    giver_loses = abs(t[giver][to] - t[giver][frm])
    getter_gains = abs(t[getter][to] - t[getter][frm])
    gain = POINTS_PER_SCORE * score
    return gain, gain + POINTS_PER_SCORE * max(0, giver_loses - getter_gains)


def demand_cost(key):
    """What a liege gives up when a vassal's own proposal demands this good, for the common first step."""
    g = next(x for x in CONTRACT_GOODS if x["key"] == key)
    frm, to = (2, 1) if g["step"] == "down" else _steps(g)[0]
    return -step_points(g, frm, to)[1]


def subject_scope(g, P, A):
    """Whose contract the good changes: the one who gives a burden on themselves, else the one who gets the ease."""
    return P if g["step"] == "up" else A


def liege_scope(g, P, A):
    return A if g["step"] == "up" else P


def _level_link(term):
    return "vassal_contract_obligation_level:%s" % term


def shown(g):
    """The good's availability, in the {P} {A} convention of qpq_gen.OFFER_DEFS."""
    S, L = subject_scope(g, "{P}", "{A}"), liege_scope(g, "{P}", "{A}")
    last = len(TERMS[g["term"]]["score"]) - 1
    if g["step"] == "down":
        level = "%s > 0" % _level_link(g["term"])
    elif g["step"] == "up":
        level = "%s < %d" % (_level_link(g["term"]), last)
    elif g.get("has"):
        level = "NOT = { vassal_contract_has_flag = %s }" % g["has"]
    else:
        level = "%s = 0" % _level_link(g["term"])
    s = ("%s = {\n    liege ?= %s\n    is_ruler = yes\n    is_tributary = no\n    %s\n"
         "    vassal_contract_has_modifiable_obligations = yes\n    subject_contract_is_blocked_from_modification = no\n"
         "    %s\n}\n" % (S, L, g["gov"], level))
    if g.get("allow"):
        s += g["allow"].replace("{S}", S).replace("{L}", L) + "\n"
    return s


def gen_values():
    """Script values, root the subject: what the next step of each good is worth, from TERMS."""
    out = ("# Generated by tools/qpq_contracts.py from vanilla's contract weights: %d points per point of `score`.\n"
           "# Root: the subject of the contract. gain = what the one who gets it counts, cost = what the giver counts.\n\n" % POINTS_PER_SCORE)
    for g in CONTRACT_GOODS:
        for which, idx in (("gain", 0), ("cost", 1)):
            out += "qpq_%s_%s_value = {\n\tvalue = 0\n" % (g["key"], which)
            for frm, to in _steps(g):
                pts = step_points(g, frm, to)[idx]
                if g["step"] == "grant":
                    out += "\tadd = %d\n" % pts
                else:
                    out += "\tif = {\n\t\tlimit = { %s = %d }\n\t\tadd = %d\n\t}\n" % (_level_link(g["term"]), frm, pts)
            out += "}\n\n"
        G = "scope:actor"
        R = "scope:recipient"
        S = subject_scope(g, G, R)
        out += "qpq_offer_%s_points_value = {\n\tvalue = %s.qpq_%s_gain_value\n" % (g["key"], S, g["key"])
        if g.get("money"):
            out += "\tif = {\n\t\tlimit = { %s = { has_trait = greedy } }\n\t\tmultiply = 1.25\n\t}\n" % R
        out += "}\n\n"
    return out


def cost_body(key, G, R):
    """The line of qpq_gen.goods_cost_body for this good: what handing it over costs G, who gives it to R."""
    g = next(x for x in CONTRACT_GOODS if x["key"] == key)
    s = "\t\tadd = {\n\t\t\tvalue = %s.qpq_%s_cost_value\n" % (subject_scope(g, G, R), key)
    if g.get("money"):
        s += "\t\t\tif = {\n\t\t\t\tlimit = { %s = { has_trait = greedy } }\n\t\t\t\tmultiply = 1.25\n\t\t\t}\n" % G
    return s + "\t\t}\n"


def gen_effects():
    """Sealing and delivery. Scopes: the pact story, with scope:qpq_payer (gives) and scope:qpq_agent (gets)."""
    out = "# Generated by tools/qpq_contracts.py.\n\n# Called while the goods are written onto the story\nqpq_contract_goods_seal_effect = {\n"
    for k in CONTRACT_KEYS:
        out += "\tif = {\n\t\tlimit = { scope:qpq_o_%s ?= yes }\n\t\tset_variable = qpq_offer_%s\n\t}\n" % (k, k)
    out += "}\n\n# Root: the mirror story; prev: the main story\nqpq_contract_goods_mirror_effect = {\n"
    for k in CONTRACT_KEYS:
        out += "\tqpq_mirror_copy_var_effect = { VAR = qpq_offer_%s }\n" % k
    out += "}\n\n# On delivery: the contract itself changes, if they are still liege and vassal and the term can still move\nqpq_contract_goods_deliver_effect = {\n"
    for g in CONTRACT_GOODS:
        S = subject_scope(g, "scope:qpq_payer", "scope:qpq_agent")
        L = liege_scope(g, "scope:qpq_payer", "scope:qpq_agent")
        out += "\tif = {\n\t\tlimit = {\n\t\t\thas_variable = qpq_offer_%s\n\t\t\t%s = { liege ?= %s }\n\t\t}\n\t\t%s = {\n" % (g["key"], S, L, S)
        for i, (frm, to) in enumerate(_steps(g)):
            set_level = "vassal_contract_set_obligation_level = { type = %s level = %d }" % (g["term"], to)
            if g["step"] == "grant":
                out += "\t\t\t%s\n" % set_level
            else:
                out += "\t\t\t%sif = {\n\t\t\t\tlimit = { %s = %d }\n\t\t\t\t%s\n\t\t\t}\n" % (
                    "else_" if i else "", _level_link(g["term"]), frm, set_level)
        out += "\t\t}\n\t}\n"
    return out + "}\n"


def gen_triggers():
    out = "# Generated by tools/qpq_contracts.py.\n\n# Root: a pact story. Does it carry a contract term still to be delivered?\nqpq_story_has_contract_terms_trigger = {\n\tOR = {\n"
    for k in CONTRACT_KEYS:
        out += "\t\texists = var:qpq_offer_%s\n" % k
    return out + "\t}\n}\n"


def gen_custom_loc():
    out = "# Generated by tools/qpq_contracts.py: one story line per contract term.\n\n"
    for k in CONTRACT_KEYS:
        out += ("QpqStory_%s = {\n\ttype = all\n\tlog_loc_errors = no\n"
                "\ttext = {\n\t\ttrigger = {\n\t\t\texists = var:qpq_main\n\t\t\texists = var:qpq_offer_%s\n\t\t}\n\t\tlocalization_key = qpq_sl_owed_%s\n\t}\n"
                "\ttext = {\n\t\ttrigger = {\n\t\t\tNOT = { exists = var:qpq_main }\n\t\t\texists = var:qpq_offer_%s\n\t\t}\n\t\tlocalization_key = qpq_sl_owe_%s\n\t}\n"
                "\ttext = {\n\t\tfallback = yes\n\t\tlocalization_key = qpq_empty\n\t}\n}\n\n") % (k, k, k, k, k)
    return out


def gen_loc():
    L = ["l_english:", " qpq_sl_contract_block:0 \"%s\"" % "".join("[Story.Custom('QpqStory_%s')]" % k for k in CONTRACT_KEYS),
         ' QPQ_UI_LIST_CONTRACT:0 "Contract terms"']
    for g in CONTRACT_GOODS:
        k = g["key"]
        L.append(' qpq_offer_%s:0 "%s"' % (k, g["name"]))
        L.append(' qpq_offer_%s_desc:0 "%s"' % (k, g["desc"]))
        L.append(' QPQ_REASON_OFFER_%s:0 "%s"' % (k.upper(), g["name"]))
        L.append(' qpq_hub.50.term_%s:0 "\\n #P •#! %s, on delivery"' % (k, g["term_text"]))
        L.append(' qpq_sl_owe_%s:0 "\\n#N •#! %s, when they deliver"' % (k, g["owe"]))
        L.append(' qpq_sl_owed_%s:0 "\\n• %s, when you deliver"' % (k, g["owed"]))
        if "demand" in g:
            L.append(' qpq_demand_%s:0 "%s"' % (k, g["demand"]))
            L.append(' qpq_demand_%s_desc:0 "%s"' % (k, g["demand_desc"]))
            L.append(' QPQ_REASON_DEMAND_%s:0 "%s"' % (k.upper(), g["demand"]))
    return "\n".join(L) + "\n"
