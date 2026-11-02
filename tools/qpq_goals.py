"""What the one who decides wants.

An Ask is judged by the character deciding (D: scope:recipient, the proposer being P: scope:actor) on what it does
and what they want: a war on T is attractive to a rival of T who borders T and is stronger, repellent to T's ally or
kin; a killing is wanted by an enemy, never by a friend. Each Ask is given the archetypes that apply, and each
archetype adds points (the goal value) and may refuse outright. Written for the normal orientation; the swapped
text (D: scope:actor) is made by qpq_ui_gen.sw().
"""

# Who is the third party, per target type
def third_party(k):
    if k["target"] == "char":
        return "scope:secondary_recipient"
    if k["target"] == "derived":
        return k["derive"]
    if k["target"] == "title":
        return "scope:target.holder"
    return None


KIND_GOALS = {
    # war on the third party
    "chartered_conquest": ["war"], "sanctioned_conquest": ["war"], "marcher_charge": ["war"],
    "licensed_feud": ["war"], "proxy_war": ["war"], "partition_pact": ["war"], "steer_the_holy_war": ["war"],
    "holy_warrant": ["war"],
    # harm to the third party
    "quiet_removal": ["harm"], "heir_question": ["harm"], "snatch": ["harm"], "dispossession": ["harm"],
    "hire_the_hashashin": ["harm"], "dossier": ["harm"], "coup_pact": ["harm"], "hand_over": ["harm"],
    "extradition": ["harm"], "excommunication_for_hire": ["harm"], "fatwa_for_hire": ["harm"],
    "blessing_for_a_feud": ["harm"], "buy_a_councillor": ["harm"], "buy_a_bull": ["harm"],
    "crowning_the_usurper": ["harm"], "favourable_omens": ["harm"], "temple_patronage": ["harm"],
    "bought_claim": ["harm"], "faithless_ally": ["harm"], "turncoat": ["harm"], "fund_the_dawa": ["harm", "faith"],
    "the_cloister": ["harm"],
    # good done to the third party
    "electoral_purchase": ["favour"], "electoral_capitulation": ["favour"], "conclave_votes": ["favour"],
    "purchase_a_mitre": ["favour"], "dispensation_for_gold": ["favour"],
    # giving up something
    "title_swap": ["loss_title"], "secret_clause": ["loss_title"], "renunciation": ["loss_title"],
    "hand_over_artifact": ["loss_artifact"],
    # binding oneself to the proposer
    "mutual_defense_league": ["pact"], "faction_pledge": ["pact"], "secret_alliance": ["pact"],
    "stay_home": ["pact"], "defection_pact": ["pact"], "price_of_loyalty": ["pact"], "seed_the_separatists": ["pact"],
    "bought_truce": ["pact"],
    # matters of faith
    "holy_sponsorship": ["faith"], "caliphal_investiture": ["faith"], "pliant_patriarch": ["faith"],
    "consecration_rites": ["faith"], "council_lobbying": ["faith"], "name_in_the_khutba": ["faith"],
    "absolution_by_concession": ["faith"],
}

# Wars where the proposer fights alongside, and wars waged by the faith
JOINT_WARS = {"partition_pact"}
HOLY_WARS = {"steer_the_holy_war", "holy_warrant"}
STRONGER = "max_military_strength > { value = %s.max_military_strength multiply = %s }"


def _enmity(D, P, T):
    """Points for how much D dislikes T (positive: wants them hurt), and the loyalties that pull the other way."""
    s = ""
    s += "\tif = {\n\t\tlimit = { %s = { has_relation_rival = %s } }\n\t\tadd = 18\n\t}\n" % (D, T)
    s += "\tif = {\n\t\tlimit = { %s = { has_relation_nemesis = %s } }\n\t\tadd = 10\n\t}\n" % (D, T)
    s += "\tadd = {\n\t\tvalue = \"%s.opinion(%s)\"\n\t\tmultiply = -0.2\n\t\tmin = -15\n\t\tmax = 15\n\t}\n" % (D, T)
    s += "\tif = {\n\t\tlimit = { %s = { is_allied_to = %s } }\n\t\tadd = -25\n\t}\n" % (D, T)
    s += "\tif = {\n\t\tlimit = { %s = { is_close_family_of = %s } }\n\t\tadd = -25\n\t}\n" % (D, T)
    s += "\tif = {\n\t\tlimit = {\n\t\t\tOR = {\n\t\t\t\t%s = { has_relation_friend = %s }\n\t\t\t\t%s = { has_relation_lover = %s }\n\t\t\t\t%s = { has_relation_best_friend = %s }\n\t\t\t}\n\t\t}\n\t\tadd = -20\n\t}\n" % (D, T, D, T, D, T)
    s += "\tif = {\n\t\tlimit = { %s = { has_relation_victim = %s } }\n\t\tadd = 6\n\t}\n" % (D, T)
    return s


def _traits(D, pos, neg):
    s = ""
    for tr, v in pos:
        s += "\tif = {\n\t\tlimit = { %s = { has_trait = %s } }\n\t\tadd = %d\n\t}\n" % (D, tr, v)
    for tr, v in neg:
        s += "\tif = {\n\t\tlimit = { %s = { has_trait = %s } }\n\t\tadd = %d\n\t}\n" % (D, tr, -v)
    return s


def goal_body(arch, D, P, T):
    """The inside of a script value (after value = 0)."""
    s = ""
    if arch == "war":
        s += _enmity(D, P, T)
        # the war is worth more against a neighbour, over a claim, against someone weaker
        s += ("\tif = {\n\t\tlimit = {\n\t\t\t%s = { top_liege = { any_neighboring_and_across_water_top_liege_realm_owner = { this = %s.top_liege } } }\n\t\t}\n"
              "\t\tadd = 10\n\t}\n") % (D, T)
        s += "\tif = {\n\t\tlimit = { %s = { any_claim = { holder ?= %s } } }\n\t\tadd = 12\n\t}\n" % (D, T)
        s += "\tif = {\n\t\tlimit = { %s = { %s } }\n\t\tadd = -20\n\t}\n" % (T, STRONGER % (D, "1.3"))
        s += "\tif = {\n\t\tlimit = { %s = { %s } }\n\t\tadd = -25\n\t}\n" % (T, STRONGER % (D, "1.8"))
        s += "\tif = {\n\t\tlimit = { %s = { max_military_strength < { value = %s.max_military_strength multiply = 0.6 } } }\n\t\tadd = 8\n\t}\n" % (T, D)
        s += "\tif = {\n\t\tlimit = { %s = { is_at_war = yes } }\n\t\tadd = -8\n\t}\n" % D
        s += _traits(D, [("ambitious", 6), ("brave", 4), ("wrathful", 4)], [("content", 6), ("craven", 10), ("compassionate", 3)])
    elif arch == "harm":
        s += _enmity(D, P, T)
        s += "\tif = {\n\t\tlimit = { %s = { is_liege_or_above_of = %s } }\n\t\tadd = -6\n\t}\n" % (T, D)
        s += _traits(D, [("sadistic", 8), ("vengeful", 6), ("callous", 5), ("deceitful", 3)],
                     [("compassionate", 8), ("forgiving", 6), ("honest", 4)])
    elif arch == "favour":
        # the reverse of enmity: wants good for those they like
        s += "\tadd = {\n\t\tvalue = \"%s.opinion(%s)\"\n\t\tmultiply = 0.2\n\t\tmin = -15\n\t\tmax = 15\n\t}\n" % (D, T)
        s += "\tif = {\n\t\tlimit = {\n\t\t\tOR = {\n\t\t\t\t%s = { has_relation_rival = %s }\n\t\t\t\t%s = { has_relation_nemesis = %s }\n\t\t\t}\n\t\t}\n\t\tadd = -25\n\t}\n" % (D, T, D, T)
        s += "\tif = {\n\t\tlimit = { %s = { is_allied_to = %s } }\n\t\tadd = 10\n\t}\n" % (D, T)
        s += "\tif = {\n\t\tlimit = { %s = { is_close_family_of = %s } }\n\t\tadd = 12\n\t}\n" % (D, T)
    elif arch == "loss_title":
        # a title is a loss, greater with rank and with the development of its land
        s += ("\tadd = {\n\t\tvalue = 0\n\t\tscope:target = {\n\t\t\tif = {\n\t\t\t\tlimit = { tier >= tier_kingdom }\n\t\t\t\tadd = -30\n\t\t\t}\n"
              "\t\t\telse_if = {\n\t\t\t\tlimit = { tier = tier_duchy }\n\t\t\t\tadd = -18\n\t\t\t}\n"
              "\t\t\telse = {\n\t\t\t\tadd = -8\n\t\t\t}\n\t\t}\n\t}\n")
        s += _traits(D, [("generous", 5)], [("greedy", 8), ("ambitious", 5)])
    elif arch == "loss_artifact":
        s += "\tadd = {\n\t\tvalue = 0\n\t\tscope:target = { add = qpq_gift_artifact_cost_value }\n\t\tmultiply = -1\n\t}\n"
        s += _traits(D, [("generous", 5)], [("greedy", 8)])
    elif arch == "pact":
        # what an alliance with P is worth to D: protection when P is strong or D is at war, little when P is weak
        s += "\tif = {\n\t\tlimit = { %s = { %s } }\n\t\tadd = 10\n\t}\n" % (P, STRONGER % (D, "1.2"))
        s += "\tif = {\n\t\tlimit = { %s = { max_military_strength < { value = %s.max_military_strength multiply = 0.5 } } }\n\t\tadd = -10\n\t}\n" % (P, D)
        s += "\tif = {\n\t\tlimit = { %s = { is_at_war = yes } }\n\t\tadd = 8\n\t}\n" % D
        s += "\tif = {\n\t\tlimit = { %s.faith = %s.faith }\n\t\tadd = 6\n\t}\n" % (D, P)
        s += "\tif = {\n\t\tlimit = { %s.culture = %s.culture }\n\t\tadd = 4\n\t}\n" % (D, P)
        s += "\tif = {\n\t\tlimit = { %s = { has_relation_rival = %s } }\n\t\tadd = -30\n\t}\n" % (D, P)
        s += _traits(D, [("trusting", 4)], [("paranoid", 8)])
    elif arch == "faith":
        s += "\tif = {\n\t\tlimit = { %s.faith = %s.faith }\n\t\tadd = 8\n\t}\n" % (D, P)
        s += "\tif = {\n\t\tlimit = { NOT = { %s.faith = %s.faith } }\n\t\tadd = -12\n\t}\n" % (D, P)
        s += "\tif = {\n\t\tlimit = { %s = { has_trait = excommunicated } }\n\t\tadd = -15\n\t}\n" % P
        s += "\tif = {\n\t\tlimit = { %s = { piety_level >= 3 } }\n\t\tadd = 6\n\t}\n" % P
        s += _traits(D, [("zealous", 4)], [])
    return s


import re


def sw(text):
    return re.sub(r"scope:(actor|recipient)(?![A-Za-z0-9_])",
                  lambda m: "scope:" + ("recipient" if m.group(1) == "actor" else "actor"), text)


def goal_value(k, swapped=False):
    """Script value text for the Ask's goals, or None."""
    archs = KIND_GOALS.get(k["key"])
    if not archs:
        return None
    T = third_party(k)
    if T is None and any(a in ("war", "harm", "favour") for a in archs):
        return None
    D, P = ("scope:actor", "scope:recipient") if swapped else ("scope:recipient", "scope:actor")
    if swapped and T:
        T = sw(T)
    body = ""
    for a in archs:
        body += goal_body(a, D, P, T)
    return "\tvalue = 0\n" + body


def goal_refusal(k, swapped=False):
    """Trigger text: D will not, for any price. Only an AI refuses; None if the Ask has no such rule."""
    archs = KIND_GOALS.get(k["key"]) or []
    T = third_party(k)
    D, P = ("scope:actor", "scope:recipient") if swapped else ("scope:recipient", "scope:actor")
    if swapped and T:
        T = sw(T)
    parts = []
    if "war" in archs and T:
        parts.append("%s = { is_allied_to = %s }" % (D, T))
        parts.append("%s = { is_close_family_of = %s }" % (D, T))
        # Nobody fights a realm that outweighs them hopelessly, however loyal or well paid. The faith's own armies
        # are not the decider's, and a partner who joins the war is counted in.
        if k["key"] in JOINT_WARS:
            parts.append("%s = { max_military_strength > { value = %s.max_military_strength add = %s.max_military_strength multiply = 2 } }" % (T, D, P))
        elif k["key"] not in HOLY_WARS:
            parts.append("%s = { %s }" % (T, STRONGER % (D, "2")))
    if "harm" in archs and T:
        parts.append("%s = { is_close_family_of = %s }" % (D, T))
        parts.append("AND = {\n\t\t%s = { is_allied_to = %s }\n\t\t%s = { opinion = { target = %s value >= 30 } }\n\t}" % (D, T, D, T))
        parts.append("OR = {\n\t\t%s = { has_relation_friend = %s }\n\t\t%s = { has_relation_lover = %s }\n\t\t%s = { has_relation_best_friend = %s }\n\t}" % (D, T, D, T, D, T))
    if "favour" in archs and T:
        parts.append("OR = {\n\t\t%s = { has_relation_rival = %s }\n\t\t%s = { has_relation_nemesis = %s }\n\t}" % (D, T, D, T))
    if "pact" in archs:
        parts.append("%s = { has_relation_rival = %s }" % (D, P))
    parts = [p for p in parts if p]
    if not parts:
        return None
    out = "\tOR = {\n"
    for p in parts:
        out += "\t\t" + p.replace("\n", "\n\t") + "\n"
    out += "\t}\n"
    return out
