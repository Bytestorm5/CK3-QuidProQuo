"""What the one who decides wants.

An Ask is judged by the character deciding (D: scope:recipient, the proposer being P: scope:actor) on what it does
and what they want: a war on T is attractive to a rival of T who borders T and is stronger, repellent to T's ally or
kin; a killing is wanted by an enemy, never by a friend. Each Ask is given the archetypes that apply, and each
archetype adds points (the goal value) and may refuse outright. Written for the normal orientation. Swapped (the
AI is the proposer and decides as scope:actor), only D and P change places: the orientation effect has already put
the right characters in scope:actor and scope:recipient, so T, which the Ask itself derives (the agent's liege,
the payer's suzerain), keeps the very text the Ask gives it.

Everything about T is judged only once T exists: before a target is picked in the panel, there is none.

Two views. The doer's (an AI asked to do the deed: goal_body, WAR_SIDE): what doing it costs them, what they
would like about it. The beneficiary's (an AI that would get the deed done, by you, in the panel's other leg:
benefit_body, WAR_BENEFIT): what they want from it. A deed against someone they have no quarrel with is worth
nothing to them; a title or a treasure handed to them is a gain, not a loss.
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
    # tribute
    "accept_the_yoke": ["pact"], "cast_off_the_yoke": ["harm"],
    # in time of war: judged on the war itself (see WAR_SIDE)
    "join_war": ["war_side"], "stay_out": ["harm", "war_side"],
}

# What one gives up weighs this much more than what one gets: an even swap is refused
LOSS_AVERSION = 1.25

# The wartime deeds are judged on the war in question, found from the deed's parties: D (deciding), P (proposer)
# and T (the war leader of the other side, the deed's target).
#   war:      (whose war, against whom) that names it
#   side:     whose side D would be fighting on, in it
#   motive:   who D would be fighting
#   add_self: D is not in the war yet, and would add their strength to that side
#   sign, weight: how wanting to fight and expecting to win count. Joining: for. Staying out, making peace,
#             yielding or leaving: against (what giving up the fight costs them).
WAR_SIDE = {
    "join_war":   dict(war=("P", "T"), side="P", motive="T", add_self=True,  sign=1,  weight=1.0),
    "stay_out":   dict(war=("P", "T"), side="T", motive="P", add_self=True,  sign=-1, weight=0.6),
}

# The same deeds seen by the one who would pay for them (D, scope:actor in the swapped view; P does the deed):
#   war: the war D's side is measured in, its own (help in it, or the enemy's friend kept out of it).
# Deals do not end wars or take anyone out of one: that is the business of war, not of a bargain.
WAR_BENEFIT = {
    "join_war":   dict(war=("D", "T"), side="D"),
    "stay_out":   dict(war=("D", "T"), side="D"),
}

# Deeds whose target may be the payer themself (a blessing for oneself, or a curse on a rival)
SELF_TARGET = {"buy_a_bull", "favourable_omens"}

# Deeds that weaken T's side in a war (or one to come): the payer weighs them on the war they help win
WAR_HELP_KINDS = {"turncoat", "faithless_ally"}

# Deeds that do T harm only by withholding help: weighed against, never refused outright
HARM_NO_REFUSAL = {"stay_out"}

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
        # a title is a loss, greater with rank: given outright (in a dowry), four times what it is in a swap,
        # where a county comes back, or in giving up a claim
        s += ("\tadd = {\n\t\tvalue = 0\n\t\tscope:target = {\n\t\t\tif = {\n\t\t\t\tlimit = { tier >= tier_kingdom }\n\t\t\t\tadd = -30\n\t\t\t}\n"
              "\t\t\telse_if = {\n\t\t\t\tlimit = { tier = tier_duchy }\n\t\t\t\tadd = -18\n\t\t\t}\n"
              "\t\t\telse = {\n\t\t\t\tadd = -8\n\t\t\t}\n\t\t}\n\t\tmultiply = %s\n\t}\n") % ("@LOSS_SCALE@",)
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


def _roles(k, swapped):
    T = third_party(k)
    D, P = ("scope:actor", "scope:recipient") if swapped else ("scope:recipient", "scope:actor")
    return D, P, T


def _war_name(k, swapped, part):
    return "qpq_%s_goal%s_%s_value" % (k["key"], "_sw" if swapped else "", part)


def _in_war(who, foe, inner):
    """Script value text: run `inner` inside the war that `who` fights against `foe`."""
    return ("\t%s = {\n\t\tevery_character_war = {\n\t\t\tlimit = { qpq_war_foe_trigger = { WHO = %s FOE = %s } }\n%s"
            "\t\t}\n\t}\n") % (who, who, foe, inner)


def _side_strength(of, mine):
    """Inside a war: add up the current strength of the side `of` is on (mine) or of the other side."""
    a, b = ("every_war_attacker", "every_war_defender") if mine else ("every_war_defender", "every_war_attacker")
    return ("\t\t\tif = {\n\t\t\t\tlimit = { is_attacker = %s }\n\t\t\t\t%s = { add = current_military_strength }\n\t\t\t}\n"
            "\t\t\telse = {\n\t\t\t\t%s = { add = current_military_strength }\n\t\t\t}\n") % (of, a, b)


def goal_helpers(k, swapped=False):
    """[(part, script value body)]: the strength of D's side and of the other side, in the war of a wartime deed."""
    cfg = (WAR_BENEFIT if swapped else WAR_SIDE).get(k["key"])
    if not cfg:
        return []
    D, P, T = _roles(k, swapped)
    m = {"D": D, "P": P, "T": T}
    who, foe, side = m[cfg["war"][0]], m[cfg["war"][1]], m[cfg["side"]]
    def guarded(inner):
        return "\tif = {\n\t\tlimit = { exists = %s }\n%s\t}\n" % (T, _indent(inner)) if T else inner
    ours = "\tvalue = 0\n" + guarded(_in_war(who, foe, _side_strength(side, True)))
    if cfg.get("add_self"):
        ours += "\tadd = %s.current_military_strength\n" % D
    ours += "\tmin = 1\n"
    theirs = "\tvalue = 0\n" + guarded(_in_war(who, foe, _side_strength(side, False)))
    return [("ours", ours), ("theirs", theirs)]


def _war_side_body(k, swapped):
    """Does D want this fight, and would their side win it? Signed and weighted per deed (WAR_SIDE)."""
    cfg = WAR_SIDE[k["key"]]
    D, P, T = _roles(k, swapped)
    m = {"D": D, "P": P, "T": T}
    who, foe, side, M = m[cfg["war"][0]], m[cfg["war"][1]], m[cfg["side"]], m[cfg["motive"]]
    ours, theirs = _war_name(k, swapped, "ours"), _war_name(k, swapped, "theirs")
    t = ""
    # --- Motivation: do they want to fight M?
    t += _enmity(D, P, M)
    t += "\tif = {\n\t\tlimit = { %s = { any_claim = { holder ?= %s } } }\n\t\tadd = 12\n\t}\n" % (D, M)
    t += ("\tif = {\n\t\tlimit = {\n\t\t\t%s.faith = {\n\t\t\t\tfaith_hostility_level = {\n\t\t\t\t\ttarget = %s.faith\n"
          "\t\t\t\t\tvalue >= faith_hostile_level\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t\tadd = 8\n\t}\n") % (D, M)
    t += ("\t%s = {\n\t\tadd = {\n\t\t\tvalue = ai_boldness\n\t\t\tmultiply = 0.1\n\t\t}\n"
          "\t\tadd = {\n\t\t\tvalue = ai_energy\n\t\t\tmultiply = 0.05\n\t\t}\n"
          "\t\tadd = {\n\t\t\tvalue = ai_compassion\n\t\t\tmultiply = -0.05\n\t\t}\n\t}\n") % D
    t += _traits(D, [("ambitious", 6), ("brave", 4), ("wrathful", 4), ("arrogant", 3)],
                 [("content", 6), ("craven", 10), ("calm", 2)])
    if cfg["add_self"]:
        # already fighting elsewhere: little appetite for another war
        t += "\tif = {\n\t\tlimit = { %s = { is_at_war = yes } }\n\t\tadd = -8\n\t}\n" % D
    else:
        # a long war wears down the will to go on
        t += _in_war(who, foe, "\t\t\tif = {\n\t\t\t\tlimit = { war_days >= 1095 }\n\t\t\t\tadd = -8\n\t\t\t}\n")
    # --- Prospects: would their side win? Strength now, and how the war is going
    t += ("\tif = {\n\t\tlimit = { %s >= { value = %s multiply = 2 } }\n\t\tadd = 20\n\t}\n"
          "\telse_if = {\n\t\tlimit = { %s >= { value = %s multiply = 1.25 } }\n\t\tadd = 10\n\t}\n"
          "\telse_if = {\n\t\tlimit = { %s < { value = %s multiply = 0.5 } }\n\t\tadd = -30\n\t}\n"
          "\telse_if = {\n\t\tlimit = { %s < { value = %s multiply = 0.8 } }\n\t\tadd = -15\n\t}\n") % (
        ours, theirs, ours, theirs, ours, theirs, ours, theirs)
    t += _in_war(who, foe, (
        "\t\t\tif = {\n\t\t\t\tlimit = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = 40 } }\n\t\t\t\tadd = 12\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = 15 } }\n\t\t\t\tadd = 6\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { NOT = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = -40 } } }\n\t\t\t\tadd = -12\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { NOT = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = -15 } } }\n\t\t\t\tadd = -6\n\t\t\t}\n") % {"s": side})
    inner = "".join("\t" + line + "\n" for line in t.rstrip("\n").split("\n"))
    return "\tadd = {\n\t\tvalue = 0\n%s\t\tmultiply = %s\n\t}\n" % (inner, cfg["sign"] * cfg["weight"])


def _losing_body(ours, theirs, who, foe, side, scale):
    """Points for how badly D's side is doing (positive: losing), times scale: strength, then war score."""
    t = ("\tif = {\n\t\tlimit = { %(o)s < { value = %(t)s multiply = 0.5 } }\n\t\tadd = 20\n\t}\n"
         "\telse_if = {\n\t\tlimit = { %(o)s < { value = %(t)s multiply = 0.8 } }\n\t\tadd = 10\n\t}\n"
         "\telse_if = {\n\t\tlimit = { %(o)s >= { value = %(t)s multiply = 2 } }\n\t\tadd = -20\n\t}\n"
         "\telse_if = {\n\t\tlimit = { %(o)s >= { value = %(t)s multiply = 1.25 } }\n\t\tadd = -10\n\t}\n") % {"o": ours, "t": theirs}
    t += _in_war(who, foe, (
        "\t\t\tif = {\n\t\t\t\tlimit = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = 40 } }\n\t\t\t\tadd = -12\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = 15 } }\n\t\t\t\tadd = -6\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { NOT = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = -40 } } }\n\t\t\t\tadd = 12\n\t\t\t}\n"
        "\t\t\telse_if = {\n\t\t\t\tlimit = { NOT = { qpq_war_side_winning_trigger = { WHO = %(s)s SCORE = -15 } } }\n\t\t\t\tadd = 6\n\t\t\t}\n") % {"s": side})
    return "\tadd = {\n\t\tvalue = 0\n%s\t\tmultiply = %s\n\t}\n" % (_indent(t), scale)


def _war_benefit_body(k):
    """What D (the payer) gets from P doing a wartime deed: help in its own war, or an enemy's friend kept home."""
    key = k["key"]
    cfg = WAR_BENEFIT[key]
    D, P, T = _roles(k, True)
    m = {"D": D, "P": P, "T": T}
    who, foe, side = m[cfg["war"][0]], m[cfg["war"][1]], m[cfg["side"]]
    ours, theirs = _war_name(k, True, "ours"), _war_name(k, True, "theirs")
    t = ""
    if key == "join_war":
        # help is worth most to a side that is losing, and in proportion to the help
        t += "\tadd = 8\n"
        t += _losing_body(ours, theirs, who, foe, side, 1)
        t += ("\tif = {\n\t\tlimit = { %s.current_military_strength >= { value = %s multiply = 0.25 } }\n\t\tadd = 8\n\t}\n") % (P, theirs)
    elif key == "stay_out":
        # worth most if they would otherwise come in on the enemy's side
        t += "\tadd = 6\n"
        t += "\tif = {\n\t\tlimit = { %s = { is_allied_to = %s } }\n\t\tadd = 15\n\t}\n" % (P, T)
        t += ("\tif = {\n\t\tlimit = { %(P)s = { has_relation_rival = %(D)s } }\n\t\tadd = 10\n\t}\n"
              "\telse_if = {\n\t\tlimit = { %(P)s = { opinion = { target = %(D)s value <= -20 } } }\n\t\tadd = 6\n\t}\n") % {"P": P, "D": D}
        t += _losing_body(ours, theirs, who, foe, side, 0.3)
    return t


def benefit_body(arch, D, P, T):
    """The inside of a script value: what D, who would pay for the deed, gets from it (the beneficiary's view)."""
    s = ""
    if arch == "war":
        s += _enmity(D, P, T)
        s += "\tif = {\n\t\tlimit = { %s = { any_claim = { holder ?= %s } } }\n\t\tadd = 12\n\t}\n" % (D, T)
        s += _traits(D, [("ambitious", 6), ("wrathful", 4)], [("compassionate", 3), ("content", 4)])
    elif arch == "harm":
        s += _enmity(D, P, T)
        s += _traits(D, [("sadistic", 8), ("vengeful", 6), ("callous", 5)],
                     [("compassionate", 8), ("forgiving", 6), ("honest", 4)])
    elif arch == "war_help":
        # T's side weakened (an ally kept home, a vassal turned): worth the war it makes winnable, above all one
        # for land D has a claim on
        s += _enmity(D, P, T)
        s += "\tif = {\n\t\tlimit = { %s = { any_claim = { holder ?= %s } } }\n\t\tadd = 25\n\t}\n" % (D, T)
        s += _traits(D, [("ambitious", 6), ("wrathful", 4)], [("content", 4)])
    elif arch == "loss_title":
        # the title (or claim) given up comes to them: a gain, greater with rank
        s += ("\tadd = {\n\t\tvalue = 0\n\t\tscope:target = {\n\t\t\tif = {\n\t\t\t\tlimit = { tier >= tier_kingdom }\n\t\t\t\tadd = 60\n\t\t\t}\n"
              "\t\t\telse_if = {\n\t\t\t\tlimit = { tier = tier_duchy }\n\t\t\t\tadd = 40\n\t\t\t}\n"
              "\t\t\telse = {\n\t\t\t\tadd = 25\n\t\t\t}\n\t\t}\n\t}\n")
        s += _traits(D, [("greedy", 8), ("ambitious", 5)], [])
    elif arch == "loss_artifact":
        s += "\tscope:target = { add = qpq_gift_artifact_cost_value }\n"
        s += _traits(D, [("greedy", 8)], [("generous", 3)])
    else:
        # favour, pact, faith: the same whichever side of the deed one is on
        s += goal_body(arch, D, P, T)
    return s


import re


def sw(text):
    return re.sub(r"scope:(actor|recipient)(?![A-Za-z0-9_])",
                  lambda m: "scope:" + ("recipient" if m.group(1) == "actor" else "actor"), text)


# How much more a title given away outright costs than one swapped (see goal_body, loss_title)
# (Title Swap too: in the panel the county that comes back is a good of its own, priced as land)
LOSS_SCALE = {"secret_clause": 4, "title_swap": 4}


def goal_value(k, swapped=False):
    """Script value text for the Ask's goals, or None."""
    archs = KIND_GOALS.get(k["key"])
    if not archs:
        return None
    T = third_party(k)
    if T is None and any(a in ("war", "harm", "favour") for a in archs):
        return None
    D, P = ("scope:actor", "scope:recipient") if swapped else ("scope:recipient", "scope:actor")
    body = ""
    for a in archs:
        if a == "war_side":
            body += _war_benefit_body(k) if swapped else _war_side_body(k, swapped)
        elif swapped:
            # deeds that weaken the payer's enemy in war are judged by the payer on the war they help win
            body += benefit_body("war_help" if (a == "harm" and k["key"] in WAR_HELP_KINDS) else a, D, P, T)
        else:
            body += goal_body(a, D, P, T)
    body = body.replace("@LOSS_SCALE@", str(LOSS_SCALE.get(k["key"], 1)))
    if k["key"] in SELF_TARGET and T:
        # the payer picked themself: no harm to judge. Done for you, it is nothing to them either way; for
        # themself, it is the favour they wanted
        body = "\tif = {\n\t\tlimit = { NOT = { %s = scope:actor } }\n%s\t}\n" % (T, _indent(body))
        if swapped:
            body += "\telse = {\n\t\tadd = 15\n\t}\n"
    G = T or ("scope:target" if k["target"] == "artifact" else None)
    if G:
        body = "\tif = {\n\t\tlimit = { exists = %s }\n%s\t}\n" % (G, _indent(body))
    return "\tvalue = 0\n" + body


def _indent(text):
    return "".join("\t" + line + "\n" for line in text.rstrip("\n").split("\n"))


# The reasons an AI will not do a deed at any price, whatever the deed (qpq_ai_refuses_<why>_trigger) and the
# arguments each takes. Dislike is never one of them: opinion counts for or against, but never refuses outright.
REFUSE_GENERIC = [("rival", "APT"), ("virtue", "AT"), ("damnable", "APT"), ("no_leverage", "APT")]


def refuse_args(args, agent, payer, tier):
    parts = []
    if "A" in args:
        parts.append("AGENT = %s" % agent)
    if "P" in args:
        parts.append("PAYER = %s" % payer)
    if "T" in args:
        parts.append("TIER = %s" % tier)
    return " ".join(parts)


# Why an AI will not do an Ask at any price: one label per rule, shown to the player as a reason
REFUSAL_LABELS = ["ally", "kin", "stronger", "liked_ally", "friend", "rival_target", "rival_you"]


def goal_refusal_parts(k, swapped=False):
    """[(label, trigger text)]: each rule under which D will not, for any price. Only an AI refuses."""
    archs = KIND_GOALS.get(k["key"]) or []
    T = third_party(k)
    D, P = ("scope:actor", "scope:recipient") if swapped else ("scope:recipient", "scope:actor")
    parts = []
    if swapped:
        # Who would pay for it will not pay to see their own ally, kin or friend hurt, nor deal with a rival
        if ("war" in archs or "harm" in archs) and T:
            parts.append(("ally", "%s = { is_allied_to = %s }" % (D, T)))
            parts.append(("kin", "%s = { is_close_family_of = %s }" % (D, T)))
        if "harm" in archs and T and k["key"] not in HARM_NO_REFUSAL:
            parts.append(("friend", "OR = {\n\t\t%s = { has_relation_friend = %s }\n\t\t%s = { has_relation_lover = %s }\n\t\t%s = { has_relation_best_friend = %s }\n\t}" % (D, T, D, T, D, T)))
        if "favour" in archs and T:
            parts.append(("rival_target", "OR = {\n\t\t%s = { has_relation_rival = %s }\n\t\t%s = { has_relation_nemesis = %s }\n\t}" % (D, T, D, T)))
        if "pact" in archs:
            parts.append(("rival_you", "%s = { has_relation_rival = %s }" % (D, P)))
        archs = []
    if "war" in archs and T:
        parts.append(("ally", "%s = { is_allied_to = %s }" % (D, T)))
        parts.append(("kin", "%s = { is_close_family_of = %s }" % (D, T)))
        # Nobody fights a realm that outweighs them hopelessly, however loyal or well paid. The faith's own armies
        # are not the decider's, and a partner who joins the war is counted in.
        if k["key"] in JOINT_WARS:
            parts.append(("stronger", "%s = { max_military_strength > { value = %s.max_military_strength add = %s.max_military_strength multiply = 2 } }" % (T, D, P)))
        elif k["key"] not in HOLY_WARS:
            parts.append(("stronger", "%s = { %s }" % (T, STRONGER % (D, "2"))))
    if "war_side" in archs and T and k["key"] == "join_war":
        parts.append(("ally", "%s = { is_allied_to = %s }" % (D, T)))
        parts.append(("kin", "%s = { is_close_family_of = %s }" % (D, T)))
        parts.append(("stronger", "%s > { value = %s multiply = 2 }" % (_war_name(k, swapped, "theirs"), _war_name(k, swapped, "ours"))))
    if "harm" in archs and T and k["key"] not in HARM_NO_REFUSAL:
        parts.append(("kin", "%s = { is_close_family_of = %s }" % (D, T)))
        parts.append(("liked_ally", "AND = {\n\t\t%s = { is_allied_to = %s }\n\t\t%s = { opinion = { target = %s value >= 30 } }\n\t}" % (D, T, D, T)))
        parts.append(("friend", "OR = {\n\t\t%s = { has_relation_friend = %s }\n\t\t%s = { has_relation_lover = %s }\n\t\t%s = { has_relation_best_friend = %s }\n\t}" % (D, T, D, T, D, T)))
    if "favour" in archs and T:
        parts.append(("rival_target", "OR = {\n\t\t%s = { has_relation_rival = %s }\n\t\t%s = { has_relation_nemesis = %s }\n\t}" % (D, T, D, T)))
    if "pact" in archs:
        parts.append(("rival_you", "%s = { has_relation_rival = %s }" % (D, P)))
    seen, out = set(), []
    for label, text in parts:
        if label not in seen:
            seen.add(label)
            if T and T in text:
                self_ok = "\tNOT = { %s = scope:actor }\n" % T if k["key"] in SELF_TARGET else ""
                text = "AND = {\n\texists = %s\n%s\t%s\n}" % (T, self_ok, text.replace("\n", "\n\t"))
            out.append((label, text))
    return out


def goal_refusal(k, swapped=False):
    """Trigger text: D will not, for any price. Only an AI refuses; None if the Ask has no such rule."""
    parts = [t for _l, t in goal_refusal_parts(k, swapped)]
    if not parts:
        return None
    out = "\tOR = {\n"
    for p in parts:
        out += "\t\t" + p.replace("\n", "\n\t") + "\n"
    out += "\t}\n"
    return out
