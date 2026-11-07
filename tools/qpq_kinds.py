"""Quid Pro Quo - the pact catalogue.

Every Ask in the design doc (catalogues A-D) is one entry here. tools/qpq_gen.py turns this table into
interactions, secret types, per-kind triggers/effects/values, the proposal hub events and localization.

Snippet conventions
-------------------
Interaction context (rel, avail, pick, target_valid, valid, payer_adj, agent_adj, demand, extra option triggers):
    scope:actor               the proposer
    scope:recipient           the other party
    scope:secondary_recipient the target character (target == 'char')
    scope:target              the target title / artifact (target == 'title' / 'artifact')
  For initiator == 'payer' the actor pays and the recipient acts. For initiator == 'agent' it is reversed.

Story context (deliver, breach, invalid, can_perform, perform, attempt, tick, on_deliver, on_end):
    root = the pact story (var:qpq_* available)
    scope:qpq_payer, scope:qpq_agent, scope:qpq_target, scope:qpq_target_title,
    scope:qpq_target_artifact, scope:qpq_story

on_seal: scopes as above plus scope values from the interaction (scope:qpq_o_* flags).
exposed: root = the exposed secret; scope:qpq_payer, scope:qpq_agent, scope:qpq_target,
    scope:qpq_target_title, scope:qpq_exposer, scope:qpq_f_tier (worst tier) available.
ai.find: root = the AI proposer. Must save scope:recipient and (if needed) scope:secondary_recipient / scope:target.
    For initiator == 'payer' the proposer is the payer (scope:actor).
"""

from qpq_contracts import CONTRACT_DEMANDS, CONTRACT_KEYS

# ---------------------------------------------------------------- relationships
REL_VASSAL = """
scope:recipient = {
    liege ?= scope:actor
    is_landed = yes
}
"""
REL_VASSAL_OR_COURTIER = """
scope:recipient = {
    OR = {
        liege ?= scope:actor
        is_courtier_of = scope:actor
    }
    is_adult = yes
    NOT = { this = scope:actor }
}
"""
REL_LIEGE = """
scope:actor = {
    liege ?= scope:recipient
    is_landed = yes
}
"""
REL_PEER_VASSAL = """
scope:actor = { is_landed = yes }
scope:recipient = {
    is_landed = yes
    NOT = { this = scope:actor }
}
exists = scope:actor.liege
scope:actor.liege = scope:recipient.liege
"""
REL_FOREIGN = """
NOT = { scope:recipient.top_liege = scope:actor.top_liege }
"""
REL_FOREIGN_RULER = REL_FOREIGN + """
scope:actor = { is_landed = yes }
scope:recipient = {
    is_independent_ruler = yes
    is_landed = yes
}
"""
REL_FOREIGN_VASSAL = REL_FOREIGN + """
scope:actor = { is_landed = yes }
scope:recipient = {
    is_landed = yes
    is_independent_ruler = no
    exists = liege
}
"""
REL_HOF = """
scope:recipient = {
    qpq_is_head_of_faith_trigger = yes
    NOT = { this = scope:actor }
}
scope:actor.faith = scope:recipient.faith
"""

# ---------------------------------------------------------------- pickers
PICK_NEIGHBOUR_RULERS_OF_RECIPIENT = """
scope:recipient = {
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            NOT = { this = scope:actor }
            NOT = { this = scope:actor.top_liege }
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
}
"""
PICK_NEIGHBOUR_RULERS_OF_ACTOR = """
scope:actor = {
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            NOT = { this = scope:recipient }
            NOT = { this = scope:actor }
        }
        add_to_list = characters
    }
}
"""
PICK_FELLOW_VASSALS = """
scope:actor = {
    every_vassal = {
        limit = {
            is_landed = yes
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
}
"""
PICK_PEER_VASSALS = """
scope:actor.liege = {
    every_vassal = {
        limit = {
            is_landed = yes
            NOT = { this = scope:recipient }
            NOT = { this = scope:actor }
        }
        add_to_list = characters
    }
}
"""
PICK_VICTIMS = """
scope:actor = {
    every_vassal = {
        limit = { NOT = { this = scope:recipient } }
        add_to_list = characters
    }
    every_courtier = {
        limit = {
            is_adult = yes
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = { NOT = { this = scope:recipient } }
        add_to_list = characters
    }
    every_relation = {
        type = rival
        limit = { NOT = { this = scope:recipient } }
        add_to_list = characters
    }
}
"""
PICK_RIVALS = """
scope:actor = {
    every_relation = {
        type = rival
        limit = { NOT = { this = scope:recipient } }
        add_to_list = characters
    }
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = { NOT = { this = scope:recipient } }
        add_to_list = characters
    }
    every_vassal = {
        limit = {
            is_landed = yes
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
}
"""
PICK_SAME_FAITH_RIVALS = """
scope:actor = {
    every_relation = {
        type = rival
        limit = {
            faith = scope:recipient.faith
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            faith = scope:recipient.faith
            NOT = { this = scope:recipient }
        }
        add_to_list = characters
    }
    every_vassal = {
        limit = {
            is_landed = yes
            faith = scope:recipient.faith
        }
        add_to_list = characters
    }
}
"""
PICK_SELF_OR_RIVALS = """
scope:actor = { add_to_list = characters }
""" + PICK_RIVALS

# ---------------------------------------------------------------- story helpers
# Exposure of a war paid for against someone the payer was bound to by truce or tribute:
# a truce-breaker by proxy (a suzerain setting a war on its own tributary counts the same)
TRUCE_BREAKER = """
if = {
    limit = {
        exists = scope:qpq_target
        qpq_bound_by_peace_trigger = { A = scope:qpq_payer B = scope:qpq_target }
    }
    scope:qpq_payer = { add_prestige = major_prestige_loss }
}
"""

AGENT_BEAT_TARGET = "qpq_beat_trigger = { LIST = qpq_agent_beat WHO = scope:qpq_target }"
PAYER_BEAT_TARGET = "qpq_beat_trigger = { LIST = qpq_payer_beat WHO = scope:qpq_target }"
TARGET_DEAD = "scope:qpq_target = { is_alive = no }"
TARGET_GONE_INVALID = "NOT = { exists = scope:qpq_target }"

GRANT_LICENCE = "qpq_grant_war_licence_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }"
REVOKE_LICENCE = """
if = {
    limit = { exists = scope:qpq_target }
    qpq_revoke_war_licence_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }
}
"""
AI_PACT_WAR = """
if = {
    limit = {
        scope:qpq_agent = { is_at_war = no }
        scope:qpq_target = { is_alive = yes }
    }
    random = {
        chance = 20
        qpq_ai_declare_pact_war_effect = { ATTACKER = scope:qpq_agent DEFENDER = scope:qpq_target }
    }
}
"""

VICTIM_HOUSE_HOSTILE = """
if = {
    limit = { exists = scope:qpq_target.house.house_head }
    scope:qpq_target.house.house_head = {
        if = {
            limit = {
                is_alive = yes
                NOT = { this = scope:qpq_payer }
            }
            add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_my_house_opinion }
        }
    }
}
"""

ALL_OFFERS = (["gold", "on_delivery", "split", "stipend", "land", "claim", "office",
               "release_hook", "my_word", "hook", "secret", "succession", "clemency", "arms",
               "artifact", "church"] + CONTRACT_KEYS + ["restraint", "charter"])
NO_CLAIM = [o for o in ALL_OFFERS if o != "claim"]
AGENT_DEMANDS = (["gold", "on_delivery", "split", "stipend", "land", "office", "release_hook",
                  "my_word", "clemency", "artifact", "church"] + CONTRACT_DEMANDS)

# Goods that last until the deadline, and so weigh by the term (qpq_goods_term_mult_value). With no deed in the
# leg they still give it a deadline: LASTING_TERM unless the panel sets another.
DURATION_GOODS = ["office", "arms", "restraint"]
LASTING_TERM = 60

KINDS = []


def is_instant(k):
    """A deed done the moment it is sealed: it has no deadline, so no term to set or to weigh."""
    return str(k.get("deliver", "")).strip() == "always = yes"


def K(**kw):
    kw.setdefault("initiator", "payer")
    kw.setdefault("target", "char")
    kw.setdefault("mode", "condition")
    kw.setdefault("term", 60)
    kw.setdefault("agent_ctx", kw.get("cat") in ("A", "B"))
    kw.setdefault("payer_ctx", True)
    kw.setdefault("offers", NO_CLAIM if not kw.get("claim_ok") else ALL_OFFERS)
    kw.setdefault("victors", False)
    kw.setdefault("effort", 0)
    kw.setdefault("icategory", "interaction_category_diplomacy")
    KINDS.append(kw)
    return kw


###############################################################################
# CATALOGUE A: liege to vassal
###############################################################################

K(key="chartered_conquest", licence=True, cat="A", group="war", secret="conquest", icon="declare_war_interaction",
  name="Chartered Conquest",
  ask="conquer land held by [qpq_target.GetTitledFirstName] under a published charter",
  desc="Publicly charter a [vassal|E] to take land from a named neighbour. They may use the Crown Mandate [casus_belli|E], borrowing your [de_jure|E] right where they have no [claim|E] of their own.",
  echo="Frontier lordships granted to whoever could take them, as on the Iberian frontier.",
  payer_base=0, agent_base=0, claim_ok=True, term=96, effort=20,
  rel=REL_VASSAL, pick=PICK_NEIGHBOUR_RULERS_OF_RECIPIENT,
  target_valid="""
scope:secondary_recipient = {
    is_landed = yes
    NOT = { top_liege = scope:actor.top_liege }
}
""",
  demand=[("10", "scope:recipient = { has_trait = ambitious }", "QPQ_REASON_AMBITIOUS_CONQUEST"),
          ("-15", "scope:recipient = { has_trait = craven }", "QPQ_REASON_CRAVEN_WAR"),
          ("10", "scope:qpq_o_charter ?= yes", "QPQ_REASON_HONOURABLE_CHARTER")],
  deliver=AGENT_BEAT_TARGET,
  invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE + """
if = {
    limit = { exists = scope:qpq_is_charter }
    scope:qpq_agent = { add_to_variable_list = { name = qpq_mandate_against target = scope:qpq_target } }
    scope:qpq_target = {
        every_realm_county = {
            limit = {
                any_this_title_or_de_jure_above = { holder ?= scope:qpq_payer }
            }
            scope:qpq_agent = { add_to_variable_list = { name = qpq_mandate_titles target = prev } }
        }
    }
}
""",
  attempt=AI_PACT_WAR,
  on_end=REVOKE_LICENCE + """
scope:qpq_agent = {
    if = {
        limit = { has_variable_list = qpq_mandate_titles }
        clear_variable_list = qpq_mandate_titles
    }
    if = {
        limit = { has_variable_list = qpq_mandate_against }
        clear_variable_list = qpq_mandate_against
    }
    # Other Charters of the same vassal keep their Crown Mandate
    every_in_list = {
        variable = qpq_pacts
        limit = {
            qpq_story_is_active_trigger = yes
            NOT = { this = scope:qpq_story }
            var:qpq_kind = flag:chartered_conquest
            has_variable = qpq_charter
            exists = var:qpq_target
        }
        var:qpq_target = { save_scope_as = qpq_other_mandate_target }
        scope:qpq_agent = { add_to_variable_list = { name = qpq_mandate_against target = scope:qpq_other_mandate_target } }
        var:qpq_payer = { save_scope_as = qpq_other_mandate_payer }
        scope:qpq_other_mandate_target = {
            every_realm_county = {
                limit = {
                    any_this_title_or_de_jure_above = { holder ?= scope:qpq_other_mandate_payer }
                }
                scope:qpq_agent = { add_to_variable_list = { name = qpq_mandate_titles target = prev } }
            }
        }
    }
}
""",
  exposed="",
  ai=dict(weight=6, valid="""
is_landed = yes
any_vassal = { is_landed = yes is_ai = yes }
""", find="""
# the strongest vassal free to fight, against the neighbour root most wants brought low and they can beat
ordered_vassal = {
    limit = {
        is_landed = yes
        is_ai = yes
        is_at_war = no
        any_neighboring_and_across_water_top_liege_realm_owner = {
            NOT = { top_liege = root.top_liege }
        }
    }
    order_by = max_military_strength
    save_scope_as = recipient
}
scope:recipient ?= {
    save_scope_as = qpq_ai_fighter
    ordered_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            NOT = { top_liege = root.top_liege }
            NOT = { this = root }
        }
        order_by = qpq_ai_war_target_value
        save_scope_as = secondary_recipient
    }
}
"""))

K(key="marcher_charge", cat="A", group="war", secret="conquest", icon="icon_combat",
  name="Marcher Charge",
  ask="hold the border against [qpq_target.GetTitledFirstName]",
  desc="A [vassal|E] keeps [levies|E] raised and defends a named border for the whole term. Failing is a breach of the pact, not a scandal.",
  echo="Marcher lords across Europe.",
  payer_base=0, agent_base=0, mode="restraint", term=60, effort=5,
  rel=REL_VASSAL, pick=PICK_NEIGHBOUR_RULERS_OF_RECIPIENT,
  target_valid="scope:secondary_recipient = { is_landed = yes NOT = { top_liege = scope:actor.top_liege } }",
  on_seal="""
scope:qpq_agent = {
    every_held_title = {
        limit = { tier = tier_county }
        scope:qpq_story ?= { add_to_variable_list = { name = qpq_charge_counties target = prev } }
    }
    add_character_modifier = { modifier = qpq_marcher_charge_modifier months = qpq_term_months_value }
}
""",
  breach="""
has_variable_list = qpq_charge_counties
any_in_list = {
    variable = qpq_charge_counties
    holder ?= {
        OR = {
            this = scope:qpq_target
            top_liege = scope:qpq_target.top_liege
        }
    }
}
""",
  on_end="""
scope:qpq_agent = {
    if = {
        limit = { has_character_modifier = qpq_marcher_charge_modifier }
        remove_character_modifier = qpq_marcher_charge_modifier
    }
}
""",
  ai=dict(weight=5, valid="""is_landed = yes any_vassal = { is_landed = yes is_ai = yes }""", find="""
# the neighbour root most fears and dislikes, held off by the strongest vassal on that border
ordered_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        NOT = { top_liege = root.top_liege }
        OR = {
            has_relation_rival = root
            faith = { faith_hostility_level = { target = root.faith value >= faith_hostile_level } }
        }
    }
    order_by = qpq_ai_enmity_value
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    ordered_vassal = {
        limit = {
            is_landed = yes
            any_neighboring_and_across_water_top_liege_realm_owner = { this = scope:secondary_recipient }
        }
        order_by = max_military_strength
        save_scope_as = recipient
    }
}
"""))

K(key="holy_sponsorship", cat="A", group="favours", secret="conquest", icon="religious",
  name="Holy Sponsorship",
  ask="convert [qpq_target_title.GetName] to [qpq_payer.GetFaith.GetName]",
  desc="Sponsor a [vassal|E] to bring a named [county|E] into your [faith|E]. Bought piety looks bad if it comes out.",
  payer_base=0, agent_base=0, target="title", term=96, effort=5,
  rel=REL_VASSAL,
  pick=dict(source="recipient", filter="realm_counties", can_pick="""
scope:target = {
    tier = tier_county
    NOT = { faith = scope:actor.faith }
}
"""),
  target_valid="scope:target = { NOT = { faith = scope:actor.faith } }",
  valid=[("qpq_valid_agent_same_faith", "scope:recipient.faith = scope:actor.faith")],
  deliver="scope:qpq_target_title.faith = scope:qpq_payer.faith",
  invalid="NOT = { scope:qpq_target_title.holder.top_liege ?= scope:qpq_agent.top_liege }",
  attempt="""
random = {
    chance = {
        value = 1
        add = { value = scope:qpq_agent.learning divide = 8 }
    }
    scope:qpq_target_title = { set_county_faith = scope:qpq_payer.faith }
}
""",
  exposed="scope:qpq_agent = { add_piety = minor_piety_loss }")

K(key="development_charter", cat="A", group="favours", secret="bribery", icon="icon_transfer_county",
  name="Development Charter",
  ask="raise the development of [qpq_target_title.GetName]",
  desc="Pay a [vassal|E] to raise one of their [counties|E] by five levels of [county_development|E] within the term.",
  payer_base=0, agent_base=0, target="title", term=120, effort=0,
  rel=REL_VASSAL,
  pick=dict(source="recipient", filter="domain_titles", can_pick="scope:target = { tier = tier_county }"),
  target_valid="scope:target = { tier = tier_county }",
  on_seal="""
scope:qpq_story ?= {
    set_variable = {
        name = qpq_dev_goal
        value = { value = scope:qpq_target_title.development_level add = 5 }
    }
}
""",
  deliver="scope:qpq_target_title.development_level >= var:qpq_dev_goal",
  invalid="NOT = { scope:qpq_target_title.holder ?= scope:qpq_agent }",
  attempt="""
random = {
    chance = 40
    scope:qpq_target_title = { change_development_progress_with_overflow = 10 }
}
""",
  exposed="")

K(key="electoral_purchase", cat="A", group="family", secret="bribery", icon="heir",
  name="Electoral Purchase",
  ask="vote for [qpq_target.GetTitledFirstName] in the next election",
  desc="Buy an [elector|E]'s vote for your chosen [heir|E]. If it comes out, the vote stands, but the other electors remember it was bought.",
  echo="The 1257 double election, where both candidates spent heavily on the electors.",
  payer_base=2, agent_base=2, term=120, mode="restraint", effort=0,
  rel="""
exists = scope:actor.primary_title
scope:actor.primary_title = { any_elector = { this = scope:recipient } }
NOT = { scope:actor = scope:recipient }
""",
  pick="""
scope:actor = {
    add_to_list = characters
    every_close_family_member = {
        limit = { is_adult = yes }
        add_to_list = characters
    }
    every_courtier = {
        limit = { is_adult = yes }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { this = scope:recipient } }",
  on_seal="""
scope:qpq_agent = {
    add_opinion = {
        target = scope:qpq_target
        modifier = qpq_bought_vote_opinion
    }
    recalculate_succession_election_vote = yes
}
""",
  deliver="scope:qpq_target = { has_title = scope:qpq_payer.primary_title }",
  invalid="scope:qpq_target = { is_alive = no }",
  exposed="""
if = {
    limit = { exists = scope:qpq_payer.primary_title }
    scope:qpq_payer.primary_title = {
        every_elector = {
            limit = {
                NOT = { this = scope:qpq_agent }
                NOT = { this = scope:qpq_payer }
            }
            add_opinion = { target = scope:qpq_payer modifier = qpq_bought_election_opinion }
        }
    }
}
""",
  ai=dict(weight=3, valid="""
is_landed = yes
exists = primary_title
exists = primary_heir
primary_title = {
    any_elector = {
        is_ai = yes
        NOT = { this = root }
        NOT = { this = root.primary_heir }
    }
}
OR = { has_trait = ambitious has_trait = paranoid }
""", find="""
primary_heir = { save_scope_as = secondary_recipient }
primary_title = {
    ordered_elector = {
        limit = {
            is_ai = yes
            NOT = { this = root }
            NOT = { this = root.primary_heir }
        }
        order_by = max_military_strength
        save_scope_as = recipient
    }
}
"""))

K(key="loyal_mole", cat="A", group="shadows", secret="faction", icon="faction",
  name="The Loyal Mole",
  ask="join a faction against [qpq_payer.GetShortUIName] and sabotage it",
  desc="A [vassal|E] joins a [faction|E] against you, then sabotages it or walks out at the critical moment.",
  payer_base=3, agent_base=3, target="none", term=72, effort=10,
  rel=REL_VASSAL,
  tick="""
qpq_record_faction_members_effect = yes
if = {
    limit = { has_variable = qpq_agent_in_faction }
    set_variable = qpq_mole_joined
    scope:qpq_agent.joined_faction ?= {
        if = {
            limit = { faction_discontent > 0 }
            add_faction_discontent = -2
        }
    }
}
""",
  deliver="""
has_variable = qpq_mole_joined
scope:qpq_agent = {
    NOT = {
        joined_faction ?= { faction_target = scope:qpq_payer }
    }
}
""",
  attempt="""
if = {
    limit = { NOT = { has_variable = qpq_mole_joined } }
    random = {
        chance = 15
        qpq_ai_join_faction_against_payer_effect = yes
    }
}
else = {
    random = {
        chance = 8
        scope:qpq_agent = {
            if = {
                limit = { exists = joined_faction }
                joined_faction = { add_faction_discontent = -20 }
                leave_faction = joined_faction
            }
        }
    }
}
""",
  exposed="""
# Faction members turn on the mole, and stop trusting each other
scope:qpq_payer = {
    every_targeting_faction = {
        every_faction_member = {
            limit = { NOT = { this = scope:qpq_agent } }
            add_opinion = { target = scope:qpq_agent modifier = qpq_betrayer_opinion }
        }
        every_faction_member = {
            save_temporary_scope_as = qpq_mistrusting
            prev = {
                every_faction_member = {
                    limit = { NOT = { this = scope:qpq_mistrusting } }
                    add_opinion = { target = scope:qpq_mistrusting modifier = qpq_faction_mistrust_opinion }
                }
            }
        }
    }
}
""")

K(key="agent_provocateur", cat="A", group="shadows", secret="faction", icon="faction",
  name="Agent Provocateur",
  ask="start a revolt against [qpq_payer.GetShortUIName] so it can be crushed",
  desc="A [vassal|E] starts a revolt on purpose, so you can crush it and [revoke|E] from everyone who joins.",
  payer_base=4, agent_base=4, target="none", term=96, effort=25,
  rel=REL_VASSAL,
  tick="qpq_record_faction_members_effect = yes",
  deliver="""
has_variable = qpq_agent_in_faction
OR = {
    is_target_in_variable_list = { name = qpq_payer_beat target = scope:qpq_agent }
    any_in_list = {
        variable = qpq_entrapped
        save_temporary_scope_as = qpq_trapped
        scope:qpq_story = { is_target_in_variable_list = { name = qpq_payer_beat target = scope:qpq_trapped } }
    }
}
""",
  attempt="""
if = {
    limit = { NOT = { has_variable = qpq_agent_in_faction } }
    random = {
        chance = 12
        qpq_ai_join_faction_against_payer_effect = yes
    }
}
else_if = {
    limit = {
        scope:qpq_agent = {
            is_a_faction_leader = yes
            joined_faction = { faction_is_at_war = no }
        }
    }
    random = {
        chance = 10
        scope:qpq_agent.joined_faction = { faction_start_war = {} }
    }
}
""",
  on_deliver="""
# Crush and revoke everyone who joined
if = {
    limit = { has_variable_list = qpq_entrapped }
    every_in_list = {
        variable = qpq_entrapped
        limit = { is_alive = yes }
        scope:qpq_payer = {
            add_opinion = { target = prev modifier = qpq_conspirator_opinion }
        }
    }
}
""",
  exposed="""
qpq_entrapped_turn_on_payer_effect = yes
scope:qpq_payer = {
    add_tyranny = 30
    every_vassal = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_plays_favourites_opinion opinion = -10 }
    }
}
""")

K(key="dossier", cat="A", group="shadows", secret="espionage", icon="secret",
  name="Dossier",
  ask="find or plant dirt on [qpq_target.GetTitledFirstName]",
  desc="Find or plant [secrets|E] on a rival and hand them over. If it comes out, the target's [opinion|E] of you collapses and the spy is branded an informer.",
  payer_base=2, agent_base=2, term=48, effort=5,
  rel=REL_VASSAL_OR_COURTIER, pick=PICK_FELLOW_VASSALS,
  target_valid="scope:secondary_recipient = { NOT = { this = scope:actor } }",
  demand=[("{ value = scope:recipient.intrigue multiply = 1 max = 20 }", "always = yes", "QPQ_REASON_INTRIGUE_SKILL")],
  deliver="""
OR = {
    scope:qpq_target = {
        any_secret = { is_known_by = scope:qpq_payer }
    }
    scope:qpq_payer = { has_hook = scope:qpq_target }
}
""",
  invalid=TARGET_GONE_INVALID,
  attempt="""
random = {
    chance = {
        value = 3
        add = { value = scope:qpq_agent.intrigue divide = 3 }
    }
    if = {
        limit = {
            scope:qpq_target = {
                any_secret = { NOT = { is_known_by = scope:qpq_payer } }
            }
        }
        scope:qpq_target = {
            random_secret = {
                limit = { NOT = { is_known_by = scope:qpq_payer } }
                reveal_to = scope:qpq_payer
            }
        }
    }
    else = {
        scope:qpq_payer = { add_hook = { type = fabrication_hook target = scope:qpq_target } }
    }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -40 }
        add_opinion = { target = scope:qpq_agent modifier = qpq_informer_opinion }
    }
}
scope:qpq_agent = { add_character_modifier = { modifier = qpq_informer_modifier years = 10 } }
""",
  ai=dict(weight=6, valid="""is_landed = yes any_vassal = { count >= 2 }""", find="""
ordered_relation = {
    type = rival
    limit = { liege ?= root }
    order_by = qpq_ai_enmity_value
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    if = {
        limit = { exists = cp:councillor_spymaster }
        cp:councillor_spymaster = { save_scope_as = recipient }
    }
}
"""))

K(key="quiet_removal", cat="A", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="Quiet Removal",
  ask="see that [qpq_target.GetTitledFirstName] does not live out the term",
  desc="Kill a rival [vassal|E], [courtier|E] or foreign figure. If it comes out, both of you carry the murder, and the victim's [house|E] turns hostile.",
  echo="Henry II and Becket, 1170: an angry word, a dead archbishop, a public penance.",
  payer_base=4, agent_base=4, term=60, effort=25,
  rel=REL_VASSAL_OR_COURTIER, pick=PICK_VICTIMS,
  target_valid="""
scope:secondary_recipient = {
    NOT = { this = scope:actor }
    NOT = { this = scope:recipient }
    NOT = { is_child_of = scope:actor }
}
""",
  demand=[("20", "scope:recipient = { has_relation_rival = scope:secondary_recipient }", "QPQ_REASON_HATES_TARGET"),
          ("-40", "scope:recipient = { is_close_family_of = scope:secondary_recipient }", "QPQ_REASON_TARGET_IS_KIN"),
          ("10", "scope:recipient = { OR = { has_trait = sadistic has_trait = callous } }", "QPQ_REASON_RUTHLESS")],
  deliver=TARGET_DEAD,
  attempt="""
random = {
    chance = 25
    qpq_ai_start_murder_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target.killer ?= scope:qpq_agent }
    scope:qpq_agent = { add_trait = murderer }
}
""" + VICTIM_HOUSE_HOSTILE + """
if = {
    limit = { scope:qpq_target.liege ?= scope:qpq_payer }
    scope:qpq_payer = { add_tyranny = 20 }
}
""",
  ai=dict(weight=4, valid="""is_landed = yes any_relation = { type = rival } OR = { has_trait = deceitful has_trait = callous has_trait = sadistic has_trait = vengeful has_trait = schemer }""", find="""
# the rival root hates most, by the subtlest of root's vassals
ordered_relation = {
    type = rival
    limit = { is_alive = yes }
    order_by = qpq_ai_enmity_value
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    ordered_vassal = {
        limit = {
            is_ai = yes
            intrigue >= 10
            NOT = { this = scope:secondary_recipient }
            NOT = { is_close_family_of = scope:secondary_recipient }
        }
        order_by = intrigue
        save_scope_as = recipient
    }
}
"""))

K(key="heir_question", cat="A", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="The Heir Question",
  ask="remove [qpq_target.GetTitledFirstName], [qpq_payer.GetShortUINamePossessive] own heir",
  desc="Remove your [heir|E] or a disfavoured child. If it comes out: [kinslaying|E], a realm-wide [opinion|E] penalty, and your next heir turns against you.",
  payer_base=5, agent_base=5, term=60, effort=30,
  rel=REL_VASSAL_OR_COURTIER,
  pick="""
scope:actor = {
    every_child = {
        limit = { is_alive = yes }
        add_to_list = characters
    }
    if = {
        limit = { exists = primary_heir }
        primary_heir = { add_to_list = characters }
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { this = scope:recipient } }",
  demand=[("-30", "scope:recipient = { is_close_family_of = scope:secondary_recipient }", "QPQ_REASON_TARGET_IS_KIN")],
  deliver=TARGET_DEAD,
  attempt="""
random = {
    chance = 20
    qpq_ai_start_murder_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }
}
""",
  exposed="""
scope:qpq_payer = {
    every_vassal = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -15 }
    }
    if = {
        limit = { exists = primary_heir }
        primary_heir = {
            add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -80 }
        }
    }
}
""" + VICTIM_HOUSE_HOSTILE)

K(key="snatch", cat="A", group="blood", secret="abduction", icon="prison",
  icategory="interaction_category_hostile",
  name="Snatch",
  ask="kidnap [qpq_target.GetTitledFirstName] and deliver them to [qpq_payer.GetShortUIName]",
  desc="Kidnap a named character, such as a rival's child, to hold as a [hostage|E] or [ward|E].",
  payer_base=4, agent_base=4, term=48, effort=20,
  rel=REL_VASSAL_OR_COURTIER, pick=PICK_VICTIMS,
  target_valid="scope:secondary_recipient = { NOT = { this = scope:actor } NOT = { this = scope:recipient } }",
  deliver="""
scope:qpq_target = {
    OR = {
        is_imprisoned_by = scope:qpq_agent
        is_imprisoned_by = scope:qpq_payer
    }
}
""",
  invalid=TARGET_DEAD,
  on_deliver="""
if = {
    limit = { scope:qpq_target = { is_imprisoned_by = scope:qpq_agent } }
    qpq_hand_prisoner_to_payer_effect = yes
}
""",
  attempt="""
random = {
    chance = 25
    qpq_ai_start_abduction_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }
}
""",
  exposed=VICTIM_HOUSE_HOSTILE + """
if = {
    limit = { scope:qpq_target = { is_imprisoned_by = scope:qpq_payer } }
    scope:qpq_payer = { add_tyranny = 15 }
}
""")

K(key="dispossession", cat="A", group="shadows", secret="dynastic", icon="revoke_title",
  icategory="interaction_category_vassal",
  name="Dispossession",
  ask="imprison or strip [qpq_target.GetTitledFirstName] of their lands, and bear the tyranny for it",
  desc="A [vassal|E] strips or imprisons one of their own vassals whom you want gone, and bears the [tyranny|E] for it.",
  payer_base=3, agent_base=3, term=36, effort=15,
  rel=REL_VASSAL + "scope:recipient = { any_vassal = { is_landed = yes } }",
  pick="""
scope:recipient = {
    every_vassal = {
        limit = { is_landed = yes }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { liege ?= scope:recipient }",
  deliver="""
scope:qpq_target = {
    OR = {
        is_imprisoned_by = scope:qpq_agent
        is_landed = no
        NOT = { liege ?= scope:qpq_agent }
    }
}
""",
  invalid=TARGET_DEAD,
  attempt="""
random = {
    chance = 25
    scope:qpq_agent = {
        imprison = { target = scope:qpq_target type = dungeon }
        add_tyranny = 20
    }
}
""",
  exposed="""
scope:qpq_payer = { add_tyranny = 20 }
scope:qpq_agent = { add_tyranny = -20 }
""" + VICTIM_HOUSE_HOSTILE)

K(key="the_cloister", cat="A", group="family", secret="dynastic", icon="religious",
  name="Abdicate to Heir",
  ask="abdicate in favour of their heir and take holy vows",
  desc="They give up their titles to their [heir|E] and retire to holy orders.",
  echo="Abdications into monasteries were a standard way to clear a claimant.",
  payer_base=2, agent_base=2, target="derived", derive="scope:recipient", mode="perform", term=24, effort=15,
  rel=REL_VASSAL,
  target_valid="scope:secondary_recipient = { NOT = { has_trait = devoted } }",
  demand=[("-65", "always = yes", "QPQ_REASON_MUST_ABDICATE"),
          ("10", "scope:recipient = { has_trait = zealous }", "QPQ_REASON_ZEALOUS_VOWS")],
  can_perform="scope:qpq_target = { is_alive = yes NOT = { has_trait = devoted } }",
  invalid=TARGET_DEAD,
  perform="""
if = {
    limit = { exists = scope:qpq_agent.primary_heir }
    scope:qpq_payer_secret ?= { set_variable = { name = qpq_successor value = scope:qpq_agent.primary_heir } }
}
scope:qpq_agent = { depose = yes }
scope:qpq_target = {
    if = {
        limit = { is_married = yes }
        every_spouse = { divorce = scope:qpq_target }
    }
    add_trait = devoted
}
""",
  exposed="""
if = {
    limit = { exists = scope:qpq_payer_secret.var:qpq_successor }
    scope:qpq_payer_secret.var:qpq_successor = {
        if = {
            limit = { qpq_uses_legitimacy_trigger = yes }
            add_legitimacy = -20
        }
    }
}
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -40 }
    }
}
""")

K(key="marriage_by_command", cat="A", group="family", secret="dynastic", icon="icon_marriage",
  name="Marriage by Command",
  ask="set aside any spouse and marry [qpq_target.GetTitledFirstName]",
  desc="A [vassal|E] sets aside any [spouse|E] and marries the person you choose.",
  payer_base=2, agent_base=2, mode="perform", term=24, effort=10,
  rel=REL_VASSAL,
  pick="""
scope:actor = {
    every_courtier = {
        limit = { is_adult = yes is_married = no }
        add_to_list = characters
    }
    every_close_family_member = {
        limit = { is_adult = yes is_married = no }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { this = scope:recipient } is_married = no }",
  valid=[("qpq_valid_can_marry", "scope:recipient = { can_marry_character_trigger = { CHARACTER = scope:secondary_recipient } }")],
  can_perform="scope:qpq_target = { is_alive = yes is_married = no }",
  invalid=TARGET_DEAD,
  perform="""
scope:qpq_agent = {
    every_spouse = {
        save_temporary_scope_as = qpq_discarded_spouse
        scope:qpq_payer_secret ?= { add_to_variable_list = { name = qpq_discarded target = scope:qpq_discarded_spouse } }
        divorce = scope:qpq_agent
    }
    marry = scope:qpq_target
}
""",
  exposed="""
scope:qpq_payer = { add_piety = medium_piety_loss }
scope:qpq_agent = { add_piety = medium_piety_loss }
scope:qpq_payer_secret ?= {
    if = {
        limit = { has_variable_list = qpq_discarded }
        every_in_list = {
            variable = qpq_discarded
            house.house_head ?= {
                add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_my_house_opinion }
                add_opinion = { target = scope:qpq_agent modifier = qpq_betrayed_my_house_opinion }
            }
        }
    }
}
""")

K(key="hand_over_artifact", cat="A", group="favours", secret="bribery", icon="artifact",
  name="Surrender a Treasure",
  ask="hand [qpq_target_artifact.GetName] over to [qpq_payer.GetShortUIName]",
  desc="Surrender a named [artifact|E] from their treasury.",
  payer_base=1, agent_base=1, mode="perform", target="artifact", term=12, effort=5,
  rel=REL_VASSAL + "scope:recipient = { any_character_artifact = { always = yes } }",
  pick=dict(source="recipient", filter="artifacts", can_pick="always = yes"),
  target_valid="exists = scope:target",
  can_perform="scope:qpq_target_artifact.artifact_owner ?= scope:qpq_agent",
  invalid="NOT = { scope:qpq_target_artifact.artifact_owner ?= scope:qpq_agent }",
  perform="""
scope:qpq_target_artifact = {
    set_owner = {
        target = scope:qpq_payer
        history = {
            type = given
            actor = scope:qpq_agent
            recipient = scope:qpq_payer
        }
    }
}
""",
  exposed="scope:qpq_agent = { add_prestige = minor_prestige_loss }")

K(key="renunciation", cat="A", group="favours", secret="dynastic", icon="icon_claim_pressed",
  name="Renunciation",
  ask="renounce any claim on [qpq_target_title.GetName]",
  desc="Renounce a [claim|E] on a [title|E] you hold or want.",
  payer_base=1, agent_base=1, mode="perform", target="title", term=12, effort=5,
  rel=REL_VASSAL + "scope:recipient = { any_claim = { always = yes } }",
  pick=dict(source="recipient", filter="claimed_titles", can_pick="always = yes"),
  target_valid="scope:recipient = { has_claim_on = scope:target }",
  can_perform="scope:qpq_agent = { has_claim_on = scope:qpq_target_title }",
  invalid="NOT = { scope:qpq_agent = { has_claim_on = scope:qpq_target_title } }",
  perform="scope:qpq_agent = { remove_claim = scope:qpq_target_title }",
  exposed="")

K(key="hush_money", cat="A", group="favours", secret="bribery", icon="secret",
  name="Hush Money",
  ask="never expose what they know about [qpq_payer.GetShortUIName]",
  desc="Pay someone who knows your [secrets|E] never to expose them. The cover-up is worse than the crime: if the original secret comes out later, its tier rises by one.",
  payer_base=2, agent_base=2, target="none", mode="restraint", term=120, effort=0,
  rel="""
scope:recipient = { NOT = { this = scope:actor } }
scope:actor = {
    any_secret = { is_known_by = scope:recipient }
}
""",
  on_seal="""
scope:qpq_payer = {
    every_secret = {
        limit = {
            is_known_by = scope:qpq_agent
            NOT = { var:qpq_story ?= scope:qpq_story }
            trigger_if = {
                limit = { exists = scope:qpq_hush_secret }
                OR = {
                    this = scope:qpq_hush_secret
                    scope:qpq_hush_secret.var:qpq_twin ?= this
                }
            }
        }
        if = {
            limit = { qpq_is_pact_secret_trigger = yes }
            set_variable = qpq_cover_up
            set_variable = { name = qpq_hushed_by value = scope:qpq_agent }
        }
        else = {
            disable_exposure_by = scope:qpq_agent
        }
    }
}
""",
  breach="has_variable = qpq_agent_exposed_hushed",
  exposed="")

###############################################################################
# CATALOGUE B: vassal-initiated and vassal-to-vassal
###############################################################################

K(key="price_of_loyalty", cat="B", group="favours", secret="bribery", icon="icon_gold",
  icategory="interaction_category_vassal", initiator="agent", offers=AGENT_DEMANDS,
  name="Price of Loyalty",
  ask="answer [qpq_payer.GetShortUINamePossessive] call to arms and stay loyal through the war",
  desc="Demand gold from your [liege|E] before you answer their call to arms. Refusing you is a public slight; if a payment comes out, other vassals raise their own prices.",
  echo="Henry the Lion demanding Goslar before aiding Barbarossa, 1176; refused, Legnano was lost, and Henry was later stripped of his duchies.",
  payer_base=1, agent_base=1, target="none", mode="restraint", term=24, effort=0,
  rel=REL_LIEGE + "scope:recipient = { is_at_war = yes }",
  breach="scope:qpq_agent = { joined_faction ?= { faction_target = scope:qpq_payer } }",
  on_deliver="scope:qpq_payer = { add_opinion = { target = scope:qpq_agent modifier = qpq_kept_our_pact_opinion } }",
  exposed="""
scope:qpq_payer = {
    set_variable = { name = qpq_precedent value = yes years = 10 }
    every_vassal = {
        limit = { NOT = { this = scope:qpq_agent } }
        add_opinion = { target = scope:qpq_payer modifier = qpq_precedent_opinion }
    }
}
""")

K(key="blessing_for_a_feud", cat="B", group="war", secret="conquest", icon="declare_war_interaction",
  icategory="interaction_category_vassal",
  name="Blessing for a Feud",
  ask="look away while [qpq_payer.GetShortUIName] attacks fellow vassal [qpq_target.GetTitledFirstName]",
  desc="Ask your [liege|E] to look away while you attack a fellow [vassal|E]. You get a Pact War [casus_belli|E]; your liege promises not to intervene.",
  payer_base=3, agent_base=3, term=60, mode="restraint", effort=10,
  rel=REL_LIEGE, pick=PICK_PEER_VASSALS,
  target_valid="scope:secondary_recipient = { liege ?= scope:recipient }",
  on_seal="""
qpq_grant_war_licence_effect = { AGENT = scope:qpq_payer TARGET = scope:qpq_target }
scope:qpq_payer = { add_hook = { type = favor_hook target = scope:qpq_agent } }
""",
  deliver=PAYER_BEAT_TARGET,
  breach="""
OR = {
    scope:qpq_agent = { is_at_war_with = scope:qpq_payer }
    scope:qpq_payer = { is_imprisoned_by = scope:qpq_agent }
}
""",
  on_end="""
if = {
    limit = { exists = scope:qpq_target }
    qpq_revoke_war_licence_effect = { AGENT = scope:qpq_payer TARGET = scope:qpq_target }
}
""",
  exposed="""
scope:qpq_agent = {
    every_vassal = {
        limit = {
            NOT = { this = scope:qpq_payer }
            NOT = { this = scope:qpq_target }
        }
        add_opinion = { target = scope:qpq_agent modifier = qpq_plays_favourites_opinion }
    }
}
scope:qpq_payer = { add_character_modifier = { modifier = qpq_known_schemer_modifier years = 8 } }
""",
  ai=dict(weight=6, valid="""is_landed = yes exists = liege any_relation = { type = rival liege ?= root.liege is_landed = yes }""", find="""
# leave from the liege to fall on the rival fellow vassal root most wants beaten, and can beat
liege = { save_scope_as = recipient }
save_scope_as = qpq_ai_fighter
ordered_relation = {
    type = rival
    limit = { liege ?= root.liege is_landed = yes }
    order_by = qpq_ai_war_target_value
    save_scope_as = secondary_recipient
}
"""))

K(key="clemency_bargain", cat="B", group="shadows", secret="bribery", icon="prison",
  icategory="interaction_category_vassal",
  name="Clemency Bargain",
  ask="pardon [qpq_payer.GetShortUIName] in exchange for secrets on others",
  desc="Trade [secrets|E] on others for a pardon of your own [crime|E]. If it comes out, the people you informed on turn hostile.",
  payer_base=2, agent_base=2, target="none", mode="perform", term=12, effort=0,
  rel="""
scope:actor = {
    OR = {
        liege ?= scope:recipient
        is_imprisoned_by = scope:recipient
    }
    any_known_secret = {
        NOT = { secret_owner = scope:actor }
        NOT = { secret_owner = scope:recipient }
        NOT = { is_known_by = scope:recipient }
    }
}
""",
  demand=[("30", "always = yes", "QPQ_REASON_SECRETS_OFFERED")],
  on_seal="""
scope:qpq_payer = {
    every_known_secret = {
        limit = {
            NOT = { secret_owner = scope:qpq_payer }
            NOT = { secret_owner = scope:qpq_agent }
            NOT = { is_known_by = scope:qpq_agent }
        }
        reveal_to = scope:qpq_agent
        secret_owner = { save_scope_as = qpq_informed }
        scope:qpq_payer_secret ?= { add_to_variable_list = { name = qpq_informed_on target = scope:qpq_informed } }
    }
}
""",
  can_perform="always = yes",
  perform="""
if = {
    limit = { scope:qpq_payer = { is_imprisoned_by = scope:qpq_agent } }
    scope:qpq_payer = { release_from_prison = yes }
}
scope:qpq_agent = {
    if = {
        limit = { has_opinion_modifier = { target = scope:qpq_payer modifier = qpq_criminal_pact_opinion } }
        remove_opinion = { target = scope:qpq_payer modifier = qpq_criminal_pact_opinion }
    }
    if = {
        limit = { has_opinion_modifier = { target = scope:qpq_payer modifier = qpq_conspirator_opinion } }
        remove_opinion = { target = scope:qpq_payer modifier = qpq_conspirator_opinion }
    }
    add_opinion = { target = scope:qpq_payer modifier = qpq_pardoned_opinion }
}
""",
  exposed="""
scope:qpq_payer_secret ?= {
    every_in_list = {
        variable = qpq_informed_on
        limit = { is_alive = yes }
        add_opinion = { target = scope:qpq_payer modifier = qpq_informer_opinion }
    }
}
""",
  ai=dict(weight=3, valid="""
exists = liege
any_known_secret = { NOT = { secret_owner = root } NOT = { is_known_by = root.liege } }
liege = { has_imprisonment_reason = root }
""", find="liege = { save_scope_as = recipient }"))

K(key="mutual_defense_league", cat="B", group="shadows", secret="faction", icon="alliance",
  icategory="interaction_category_vassal",
  name="Mutual Defense",
  ask="stand with [qpq_payer.GetShortUIName] if [qpq_target.GetTitledFirstName] revokes from either of you",
  desc="Two [vassals|E] swear to stand against their [liege|E] together if either has titles revoked. Tier III towards the liege, IV if armed. If it comes out, the liege may [imprison|E] both as conspirators.",
  payer_base=3, agent_base=3, target="derived", derive="scope:actor.liege", mode="restraint", term=120, effort=10,
  # the tier already counts that the league is aimed at the liege: no context shifts on top
  agent_ctx=False, payer_ctx=False,
  rel=REL_PEER_VASSAL,
  extra_options=[dict(flag="qpq_x_armed", loc="qpq_x_armed", desc="qpq_x_armed_desc", is_shown="always = yes")],
  payer_adj="if = { limit = { scope:qpq_x_armed ?= yes } add = 1 }",
  agent_adj="if = { limit = { scope:qpq_x_armed ?= yes } add = 1 }",
  demand=[("15", "scope:recipient = { opinion = { target = scope:actor.liege value <= -20 } }", "QPQ_REASON_RESENTS_LIEGE")],
  tick="""
if = {
    limit = {
        has_variable = qpq_league_called
        scope:qpq_agent = { joined_faction ?= { faction_target = scope:qpq_target } }
    }
    remove_variable = qpq_league_called
    set_variable = qpq_league_answered
}
""",
  breach="""
has_variable = qpq_league_called
NOT = { has_variable = qpq_league_grace }
NOT = { has_variable = qpq_league_answered }
""",
  on_seal="""
scope:qpq_payer = { add_to_variable_list = { name = qpq_league_stories target = scope:qpq_story } }
""",
  on_end="""
scope:qpq_payer = {
    if = {
        limit = { is_target_in_variable_list = { name = qpq_league_stories target = scope:qpq_story } }
        remove_list_variable = { name = qpq_league_stories target = scope:qpq_story }
    }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_conspirator_opinion }
        add_opinion = { target = scope:qpq_agent modifier = qpq_conspirator_opinion }
    }
}
""",
  ai=dict(weight=3, valid="""
exists = liege
opinion = { target = root.liege value <= -10 }
liege = { any_vassal = { count >= 2 } }
""", find="""
liege = { save_scope_as = qpq_ai_liege }
scope:qpq_ai_liege = {
    ordered_vassal = {
        limit = {
            NOT = { this = root }
            is_landed = yes
            opinion = { target = scope:qpq_ai_liege value <= 0 }
        }
        order_by = max_military_strength
        save_scope_as = recipient
    }
}
"""))

K(key="faction_pledge", cat="B", group="shadows", secret="faction", icon="faction",
  icategory="interaction_category_vassal",
  name="Faction Pledge",
  ask="stand in the faction against [qpq_target.GetTitledFirstName] until it wins, and share the spoils",
  desc="[vassals|E] agree to split the spoils of a successful [faction|E] war. If it comes out, the [liege|E] gains grounds to [imprison|E] them, and their allies fall away.",
  payer_base=3, agent_base=3, target="derived", derive="scope:actor.liege", term=96, effort=10,
  # the tier already counts that the faction stands against the liege: no context shifts on top
  agent_ctx=False, payer_ctx=False,
  rel=REL_PEER_VASSAL + "scope:actor = { exists = joined_faction joined_faction = { faction_target = scope:actor.liege } }",
  on_seal="""
scope:qpq_agent = {
    if = {
        limit = {
            NOT = { exists = joined_faction }
            scope:qpq_payer = { exists = joined_faction }
        }
        join_faction_forced = {
            faction = scope:qpq_payer.joined_faction
            forced_by = scope:qpq_payer
            years = 5
        }
    }
}
""",
  deliver="""
OR = {
    is_target_in_variable_list = { name = qpq_agent_beat target = scope:qpq_target }
    is_target_in_variable_list = { name = qpq_payer_beat target = scope:qpq_target }
}
""",
  breach="""
scope:qpq_payer = { exists = joined_faction }
scope:qpq_agent = {
    NOT = { joined_faction ?= { faction_target = scope:qpq_target } }
}
""",
  on_deliver="""
scope:qpq_payer = { add_prestige = minor_prestige_gain }
scope:qpq_agent = { add_prestige = minor_prestige_gain }
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_conspirator_opinion }
        add_opinion = { target = scope:qpq_agent modifier = qpq_conspirator_opinion }
    }
}
scope:qpq_payer = {
    every_ally = { break_alliance = scope:qpq_payer }
}
scope:qpq_agent = {
    every_ally = { break_alliance = scope:qpq_agent }
}
""")

# Between fellow vassals, a transfer hidden from the liege is two tiers worse
COUNTY_HIDDEN = """
if = {
    limit = {
        exists = scope:actor.liege
        exists = scope:recipient.liege
        scope:actor.liege = scope:recipient.liege
        NOT = { scope:qpq_x_consent ?= yes }
    }
    add = 2
}
"""

K(key="title_swap", cat="B", group="family", secret="dynastic", icon="grant_titles_interaction",
  name="Transfer a County",
  ask="cede [qpq_target_title.GetName] to [qpq_payer.GetShortUIName]",
  desc="Someone cedes you a [county|E]. A fellow [vassal|E]: Tier I with your [liege|E]'s consent, III if hidden, and a hidden transfer can be voided by the liege. A foreign house married into yours: Tier I, as a dowry the marriage contract leaves out, and if it comes out their house feels cheated.",
  payer_base=1, agent_base=1, mode="perform", target="title", term=24, effort=10,
  # the tiers the text states: the deal's own terms set them, not who holds what
  agent_ctx=False, payer_ctx=False,
  rel="""
OR = {
    AND = {
""" + REL_PEER_VASSAL + """
    }
    AND = {
""" + REL_FOREIGN + """
        exists = scope:actor.house
        scope:recipient = {
            is_landed = yes
            OR = {
                any_spouse = { house ?= scope:actor.house }
                any_close_family_member = {
                    OR = {
                        any_spouse = { house ?= scope:actor.house }
                        betrothed.house ?= scope:actor.house
                    }
                }
            }
        }
    }
}
""",
  pick=dict(source="recipient", filter="domain_titles", can_pick="""
scope:target = {
    tier = tier_county
    NOT = { this = scope:recipient.capital_county }
}
"""),
  target_valid="scope:target = { tier = tier_county holder ?= scope:recipient }",
  extra_options=[dict(flag="qpq_x_consent", loc="qpq_x_consent", desc="qpq_x_consent_desc",
                      is_shown="exists = scope:actor.liege exists = scope:recipient.liege scope:actor.liege = scope:recipient.liege")],
  payer_adj=COUNTY_HIDDEN, agent_adj=COUNTY_HIDDEN,
  on_seal="""
if = {
    limit = { scope:qpq_x_consent ?= yes }
    scope:qpq_payer.liege = {
        send_interface_message = {
            type = event_generic_neutral_text
            title = qpq_msg_title_swap_consent_title
            desc = qpq_msg_title_swap_consent_desc
            left_icon = scope:qpq_payer
            right_icon = scope:qpq_agent
        }
    }
}
""",
  can_perform="scope:qpq_target_title.holder ?= scope:qpq_agent",
  invalid="NOT = { scope:qpq_target_title.holder ?= scope:qpq_agent }",
  perform="qpq_agent_cedes_title_effect = yes",
  exposed="""
if = {
    limit = { scope:qpq_agent.top_liege = scope:qpq_payer.top_liege }
    scope:qpq_payer.liege ?= {
        add_opinion = { target = scope:qpq_payer modifier = qpq_conspirator_opinion opinion = -15 }
    }
}
else = {
    scope:qpq_agent = {
        every_close_family_member = {
            limit = { is_alive = yes }
            add_opinion = { target = scope:qpq_payer modifier = qpq_cheated_by_marriage_opinion }
        }
    }
}
""",
  ai=dict(weight=2, valid="exists = liege is_landed = yes", find="""
liege = {
    random_vassal = {
        limit = {
            NOT = { this = root }
            is_landed = yes
            any_held_title = { tier = tier_county count >= 2 }
        }
        save_scope_as = recipient
    }
}
if = {
    limit = { exists = scope:recipient }
    scope:recipient = {
        random_held_title = {
            limit = {
                tier = tier_county
                NOT = { this = scope:recipient.capital_county }
            }
            save_scope_as = target
        }
    }
}
"""))

K(key="coup_pact", cat="B", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="Coup Pact",
  ask="kill [qpq_target.GetTitledFirstName] so [qpq_payer.GetShortUIName] can seize the regency",
  desc="Plot with a [courtier|E] or [vassal|E] to kill your [liege|E] and seize the [regency|E]. Treason: grounds to [execute|E] without [tyranny|E], and [renown|E] lost for both houses.",
  payer_base=5, agent_base=5, target="derived", derive="scope:actor.liege", term=60, effort=30,
  rel="""
exists = scope:actor.liege
scope:recipient = {
    is_adult = yes
    NOT = { this = scope:actor }
    NOT = { this = scope:actor.liege }
    OR = {
        is_courtier_of = scope:actor.liege
        is_courtier_of = scope:actor
    }
}
""",
  demand=[("20", "scope:recipient = { opinion = { target = scope:actor.liege value <= -30 } }", "QPQ_REASON_RESENTS_LIEGE")],
  deliver=TARGET_DEAD,
  on_seal="""
scope:qpq_target.primary_title ?= {
    save_scope_as = qpq_coup_title
    scope:qpq_story ?= { set_variable = { name = qpq_coup_title value = scope:qpq_coup_title } }
    scope:qpq_payer_secret ?= { set_variable = { name = qpq_coup_title value = scope:qpq_coup_title } }
}
""",
  attempt="""
random = {
    chance = 20
    qpq_ai_start_murder_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }
}
""",
  on_deliver="""
# Seize the regency: the new ruler owes the plotter
if = {
    limit = { exists = var:qpq_coup_title.holder }
    var:qpq_coup_title.holder = { save_scope_as = qpq_new_ruler }
    if = {
        limit = {
            scope:qpq_new_ruler = { is_adult = no }
        }
        scope:qpq_payer = {
            add_hook = { type = strong_favor_hook target = scope:qpq_new_ruler }
            add_prestige = medium_prestige_gain
        }
    }
}
""",
  exposed=VICTIM_HOUSE_HOSTILE + """
if = {
    limit = { exists = scope:qpq_payer_secret.var:qpq_coup_title.holder }
    scope:qpq_payer_secret.var:qpq_coup_title.holder = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_traitor_opinion }
        add_opinion = { target = scope:qpq_agent modifier = qpq_traitor_opinion }
    }
}
""",
  ai=dict(weight=1, valid="""
exists = liege
opinion = { target = root.liege value <= -50 }
OR = { has_trait = ambitious has_trait = deceitful has_trait = callous }
""", find="""
liege = {
    ordered_courtier = {
        limit = {
            is_adult = yes
            is_ai = yes
            NOT = { this = root }
            intrigue >= 10
        }
        order_by = intrigue
        save_scope_as = recipient
    }
}
"""))

###############################################################################
# CATALOGUE C: foreign courts
###############################################################################

PROXY_FALLOUT = """
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_avenge_perfidy_opinion }
    }
}
scope:qpq_payer = {
    every_ally = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_my_ally_opinion }
    }
}
""" + TRUCE_BREAKER

K(key="proxy_war", licence=True, cat="C", group="war", secret="conquest", icon="declare_war_interaction",
  name="Proxy War",
  ask="attack [qpq_target.GetTitledFirstName]",
  desc="Pay someone to attack a named target: your own [vassal|E], who fights a neighbour with their own [casus_belli|E], a [claim|E] you fabricate or the Pact War you license, or a foreign ruler. Set a vassal on a fellow vassal and it is far more scandalous: they also get a favour [hook|E] on you, to get it past [crown_authority|E]. If it comes out, the victim gains the Avenge Perfidy [casus_belli|E] against you, and your allies cool.",
  echo="Nikephoros II paid Svyatoslav of Kiev to attack Bulgaria (967-968); Svyatoslav then tried to keep it.",
  payer_base=1, agent_base=1, claim_ok=True, term=84, effort=20,
  rel="""
OR = {
    AND = {
""" + REL_VASSAL + """
    }
    AND = {
""" + REL_FOREIGN_RULER + """
    }
}
""",
  pick=PICK_NEIGHBOUR_RULERS_OF_RECIPIENT + """
if = {
    limit = { scope:recipient = { liege ?= scope:actor } }
    scope:actor = {
        every_vassal = {
            limit = {
                is_landed = yes
                NOT = { this = scope:recipient }
            }
            add_to_list = characters
        }
    }
}
""",
  # your vassal may go abroad or against a fellow vassal; a foreign ruler goes where the money says
  target_valid="""
scope:secondary_recipient = {
    is_landed = yes
    NOT = { this = scope:actor }
    NOT = { this = scope:recipient }
}
OR = {
    scope:recipient = { NOT = { liege ?= scope:actor } }
    scope:secondary_recipient = { liege ?= scope:actor }
    NOT = { scope:secondary_recipient.top_liege = scope:actor.top_liege }
}
""",
  # a foreign hand costs the payer one tier more; a feud inside the realm costs both two
  payer_adj="""
if = {
    limit = { scope:recipient = { NOT = { liege ?= scope:actor } } }
    add = 1
}
else_if = {
    limit = {
        exists = scope:secondary_recipient
        scope:secondary_recipient = { liege ?= scope:actor }
    }
    add = 2
}
""",
  agent_adj="""
if = {
    limit = {
        scope:recipient = { liege ?= scope:actor }
        exists = scope:secondary_recipient
        scope:secondary_recipient = { liege ?= scope:actor }
    }
    add = 2
}
""",
  demand=[("10", "scope:recipient = { has_trait = ambitious }", "QPQ_REASON_AMBITIOUS_CONQUEST"),
          ("-15", "scope:recipient = { has_trait = craven }", "QPQ_REASON_CRAVEN_WAR"),
          ("10", "scope:recipient = { has_relation_rival = scope:secondary_recipient }", "QPQ_REASON_HATES_TARGET"),
          ("-20", "scope:recipient = { is_allied_to = scope:secondary_recipient }", "QPQ_REASON_ALLIED_TO_TARGET")],
  # a vassal must win it; a foreign ruler has done what was paid for by fighting it
  deliver="""
OR = {
""" + AGENT_BEAT_TARGET + """
    AND = {
        scope:qpq_agent = { NOT = { liege ?= scope:qpq_payer } }
        qpq_beat_trigger = { LIST = qpq_agent_fought WHO = scope:qpq_target }
    }
}
""",
  invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE + """
if = {
    limit = {
        scope:qpq_agent = { liege ?= scope:qpq_payer }
        scope:qpq_target = { liege ?= scope:qpq_payer }
    }
    scope:qpq_agent = { add_hook = { type = favor_hook target = scope:qpq_payer } }
}
""",
  attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed="""
if = {
    limit = {
        exists = scope:qpq_target
        scope:qpq_agent = { liege ?= scope:qpq_payer }
        scope:qpq_target = { liege ?= scope:qpq_payer }
    }
    scope:qpq_payer = {
        every_vassal = {
            limit = {
                NOT = { this = scope:qpq_agent }
                NOT = { this = scope:qpq_target }
            }
            add_opinion = { target = scope:qpq_payer modifier = qpq_plays_favourites_opinion }
        }
    }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_avenge_perfidy_opinion }
    }
}
else_if = {
    limit = { scope:qpq_agent = { liege ?= scope:qpq_payer } }
    # The target's liege treats the war as yours
    if = {
        limit = { scope:qpq_target = { is_alive = yes } }
        scope:qpq_target = {
            add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -30 }
        }
    }
    """ + TRUCE_BREAKER + """
}
else = {
    """ + PROXY_FALLOUT + """
}
""",
  ai=dict(weight=18, valid="""
OR = {
    AND = {
        is_landed = yes
        any_vassal = { is_landed = yes is_ai = yes }
    }
    AND = {
        is_independent_ruler = yes
        any_relation = { type = rival is_landed = yes }
    }
}
""", find="""
random_list = {
    8 = {
        trigger = { any_vassal = { is_landed = yes is_ai = yes } }
        # the strongest vassal free to fight, against the neighbour root most wants brought low and they can beat
        ordered_vassal = {
            limit = {
                is_landed = yes
                is_ai = yes
                is_at_war = no
                any_neighboring_and_across_water_top_liege_realm_owner = {
                    NOT = { top_liege = root.top_liege }
                }
            }
            order_by = max_military_strength
            save_scope_as = recipient
        }
        scope:recipient ?= {
            save_scope_as = qpq_ai_fighter
            ordered_neighboring_and_across_water_top_liege_realm_owner = {
                limit = {
                    NOT = { top_liege = root.top_liege }
                    NOT = { this = root }
                }
                order_by = qpq_ai_war_target_value
                save_scope_as = secondary_recipient
            }
        }
    }
    6 = {
        trigger = {
            is_independent_ruler = yes
            any_relation = { type = rival is_landed = yes }
        }
        # the foreign rival root hates most, attacked by the neighbour of theirs best placed and keenest to do it
        ordered_relation = {
            type = rival
            limit = { is_landed = yes NOT = { top_liege = root.top_liege } }
            order_by = qpq_ai_enmity_value
            save_scope_as = secondary_recipient
        }
        if = {
            limit = { exists = scope:secondary_recipient }
            scope:secondary_recipient.top_liege = {
                ordered_neighboring_and_across_water_top_liege_realm_owner = {
                    limit = {
                        NOT = { this = root }
                        is_ai = yes
                        is_at_war = no
                        NOT = { is_allied_to = scope:secondary_recipient }
                    }
                    order_by = qpq_ai_hired_sword_value
                    save_scope_as = recipient
                }
            }
        }
    }
    4 = {
        trigger = { any_vassal = { count >= 2 is_landed = yes } }
        # the strongest vassal with a rival among root's vassals, against the weakest such rival
        ordered_vassal = {
            limit = {
                is_landed = yes
                is_ai = yes
                any_relation = { type = rival liege ?= root is_landed = yes }
            }
            order_by = max_military_strength
            save_scope_as = recipient
            save_scope_as = qpq_ai_fighter
            ordered_relation = {
                type = rival
                limit = { liege ?= root is_landed = yes }
                order_by = qpq_ai_weakness_value
                save_scope_as = secondary_recipient
            }
        }
    }
}
"""))

K(key="partition_pact", licence=True, cat="C", group="war", secret="conquest", icon="declare_war_interaction",
  name="Partition Pact",
  ask="join the conquest of [qpq_target.GetTitledFirstName] and keep off the counties bordering [qpq_payer.GetShortUIName]",
  desc="Jointly conquer a third [realm|E] and split it on a line agreed in advance: every [county|E] bordering your realm is yours.",
  echo="Treaty of Tudilén, 1151: Castile and Barcelona carved up Navarre and al-Andalus in advance.",
  payer_base=1, agent_base=1, claim_ok=True, term=96, effort=15,
  rel=REL_FOREIGN_RULER,
  pick="""
scope:actor = {
    every_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            NOT = { this = scope:recipient }
            any_neighboring_and_across_water_top_liege_realm_owner = { this = scope:recipient }
        }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { this = scope:recipient } }",
  on_seal=GRANT_LICENCE + """
scope:qpq_target = {
    every_realm_county = {
        limit = { is_neighbor_to_realm = scope:qpq_payer }
        scope:qpq_story ?= { add_to_variable_list = { name = qpq_payer_share target = prev } }
    }
}
""",
  deliver=AGENT_BEAT_TARGET,
  breach="""
has_variable_list = qpq_payer_share
any_in_list = {
    variable = qpq_payer_share
    holder ?= {
        OR = {
            this = scope:qpq_agent
            top_liege = scope:qpq_agent
        }
    }
}
""",
  invalid=TARGET_GONE_INVALID,
  attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        every_neighboring_and_across_water_top_liege_realm_owner = {
            limit = {
                NOT = { this = scope:qpq_payer }
                NOT = { this = scope:qpq_agent }
            }
            add_opinion = { target = scope:qpq_target modifier = qpq_feared_partition_opinion }
        }
    }
}
""" + TRUCE_BREAKER)

K(key="secret_alliance", cat="C", group="abroad", secret="betrayal", icon="alliance",
  name="Secret Alliance",
  ask="come to [qpq_payer.GetShortUINamePossessive] defence if they are attacked, without telling a soul",
  desc="An [alliance|E] that only activates when either party is attacked, and stays hidden from everyone else. Tier I between [independent_rulers|E]; IV for a party who is someone's [vassal|E].",
  payer_base=1, agent_base=1, target="none", mode="restraint", term=120, effort=10,
  rel=REL_FOREIGN + "scope:actor = { is_landed = yes } scope:recipient = { is_landed = yes }",
  payer_adj="if = { limit = { scope:actor = { is_independent_ruler = no } } add = 3 }",
  agent_adj="if = { limit = { scope:recipient = { is_independent_ruler = no } } add = 3 }",
  breach="has_variable = qpq_agent_refused_call",
  exposed="",
  ai=dict(weight=4, valid="is_landed = yes is_at_war = no", find="""
ordered_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        is_ai = yes
        NOT = { top_liege = root.top_liege }
        opinion = { target = root value >= 20 }
    }
    order_by = max_military_strength
    save_scope_as = recipient
}
"""))

K(key="bought_truce", cat="C", group="war", secret="bribery", icon="negotiate_settlement_interaction",
  name="Bought Truce",
  ask="make peace with [qpq_payer.GetShortUIName] and keep it",
  desc="Pay a ruler you are not at war with to keep the peace: a [truce|E] between you for the term. No truce can call off a [great_holy_war|E], and a [head_of_faith|E] will not sell peace. If it comes out, raiders mark the payer as an easy mark.",
  echo="Danegeld.",
  payer_base=1, agent_base=1, target="none", mode="restraint", term=60, effort=0,
  rel=REL_FOREIGN + "scope:actor = { is_landed = yes } scope:recipient = { is_landed = yes }",
  # Taking money to stand down is far worse for a priest-king than for a border lord
  agent_adj="""
if = { limit = { scope:recipient = { qpq_is_head_of_faith_trigger = yes } } add = 3 }
else_if = { limit = { scope:recipient = { is_clergy = yes } } add = 1 }
if = { limit = { scope:recipient = { is_in_ongoing_great_holy_war = yes } } add = 1 }
""",
  agent_ctx=False,
  # A truce cannot call off a holy war, so it cannot be bought while one is running
  # a truce is bought before a war, not to end one: deals do not settle wars
  valid=[("qpq_valid_no_holy_war", "NOT = { scope:recipient = { is_in_ongoing_great_holy_war = yes } } NOT = { scope:actor = { is_in_ongoing_great_holy_war = yes } }"),
         ("qpq_valid_at_peace", "NOT = { scope:actor = { is_at_war_with = scope:recipient } }")],
  demand=[("-60", "scope:recipient = { qpq_is_head_of_faith_trigger = yes }", "QPQ_REASON_HEAD_OF_FAITH")],
  on_seal="""
scope:qpq_payer = {
    add_truce_both_ways = {
        character = scope:qpq_agent
        name = qpq_truce_name
        months = qpq_term_months_value
    }
}
""",
  breach="is_target_in_variable_list = { name = qpq_agent_attacked target = scope:qpq_payer }",
  exposed="scope:qpq_payer = { add_character_modifier = { modifier = qpq_easy_mark_modifier years = 10 } }",
  ai=dict(weight=5, valid="""
is_landed = yes
is_independent_ruler = yes
gold >= 50
any_neighboring_and_across_water_top_liege_realm_owner = {
    NOT = { is_at_war_with = root }
    NOT = { has_truce = root }
    max_military_strength > root.max_military_strength
    qpq_ai_threatens_trigger = yes
}
""", find="""
# the strongest neighbour that means root harm, while there is still peace to keep
ordered_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        NOT = { this = root }
        NOT = { is_at_war_with = root }
        NOT = { has_truce = root }
        max_military_strength > root.max_military_strength
        qpq_ai_threatens_trigger = yes
    }
    order_by = max_military_strength
    save_scope_as = recipient
}
"""))

K(key="faithless_ally", cat="C", group="abroad", secret="betrayal", icon="alliance",
  name="Faithless Ally",
  ask="abandon [qpq_target.GetTitledFirstName] in any war against [qpq_payer.GetShortUIName]",
  desc="Pay an ally of a ruler you mean to fight to ignore their call to arms in any war against you, for the term. Joining one after all is a breach. If it comes out, they are branded Faithless.",
  payer_base=3, agent_base=3, mode="restraint", term=60, effort=10,
  rel=REL_FOREIGN_RULER,
  pick="""
scope:recipient = {
    every_ally = {
        limit = { NOT = { this = scope:actor } }
        add_to_list = characters
    }
}
""",
  target_valid="scope:recipient = { is_allied_to = scope:secondary_recipient }",
  # a promise for wars to come: someone already fighting you cannot sell it (deals do not take anyone out of a war)
  valid=[("qpq_valid_not_fighting_you", "NOT = { scope:actor = { is_at_war_with = scope:recipient } }")],
  demand=[("-15", "scope:recipient = { opinion = { target = scope:secondary_recipient value >= 50 } }", "QPQ_REASON_LOVES_TARGET"),
          ("-10", "scope:recipient = { has_trait = honest }", "QPQ_REASON_HONOUR_BOUND")],
  breach="has_variable = qpq_agent_fought_payer",
  exposed="scope:qpq_agent = { add_character_modifier = { modifier = qpq_faithless_modifier years = 10 } }",
  ai=dict(weight=6, valid="""
is_landed = yes
is_independent_ruler = yes
is_at_war = no
gold >= 50
any_neighboring_and_across_water_top_liege_realm_owner = {
    qpq_ai_wants_war_on_trigger = yes
    max_military_strength <= root.max_military_strength
    any_ally = {
        NOT = { this = root }
        max_military_strength > { value = root.max_military_strength subtract = prev.max_military_strength }
    }
}
""", find="""
# War preparation. Root means to fall on a neighbour it wants to fight (a rival, or the holder of land it has a
# claim on) and could beat alone, but one of their allies would tip the war against it: buy that ally's promise
# to ignore the call to arms. The likeliest target first, then the ally who matters most.
save_scope_as = qpq_ai_fighter
ordered_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        NOT = { this = root }
        qpq_ai_wants_war_on_trigger = yes
        max_military_strength <= root.max_military_strength
        any_ally = {
            NOT = { this = root }
            max_military_strength > { value = root.max_military_strength subtract = prev.max_military_strength }
        }
    }
    order_by = qpq_ai_war_target_value
    save_scope_as = secondary_recipient
}
scope:secondary_recipient ?= {
    ordered_ally = {
        limit = {
            NOT = { this = root }
            NOT = { is_allied_to = root }
            NOT = { is_at_war_with = root }
            max_military_strength > { value = root.max_military_strength subtract = scope:secondary_recipient.max_military_strength }
        }
        order_by = max_military_strength
        save_scope_as = recipient
    }
}
"""))

K(key="turncoat", cat="C", group="abroad", secret="betrayal", icon="declare_war_interaction",
  name="Turncoat",
  ask="desert [qpq_target.GetTitledFirstName] and join [qpq_payer.GetShortUIName] mid-war",
  desc="A foreign [vassal|E] or commander withdraws before a battle or changes sides mid-war. Treason for them.",
  echo="Andronikos Doukas abandoning Romanos IV at Manzikert, 1071.",
  payer_base=2, agent_base=5, target="derived", derive="scope:recipient.liege", mode="perform", term=24, effort=20,
  rel=REL_FOREIGN + """
scope:recipient = {
    exists = liege
    is_independent_ruler = no
}
scope:actor = { is_at_war_with = scope:recipient.liege }
""",
  can_perform="scope:qpq_payer = { is_at_war_with = scope:qpq_target }",
  invalid="NOT = { scope:qpq_payer = { is_at_war_with = scope:qpq_target } }",
  perform="""
if = {
    limit = { scope:qpq_agent = { is_landed = yes } }
    create_title_and_vassal_change = {
        type = independency
        save_scope_as = qpq_turn_change
        add_claim_on_loss = no
    }
    scope:qpq_agent = { becomes_independent = { change = scope:qpq_turn_change } }
    resolve_title_and_vassal_change = scope:qpq_turn_change
    scope:qpq_payer = {
        random_character_war = {
            limit = {
                is_attacker = scope:qpq_payer
                is_defender = scope:qpq_target
            }
            add_attacker = scope:qpq_agent
        }
    }
}
else = {
    scope:qpq_payer = { add_courtier = scope:qpq_agent }
}
""",
  exposed=VICTIM_HOUSE_HOSTILE,
  ai=dict(weight=3, valid="is_at_war = yes", find="""
random_character_war = {
    limit = { is_attacker = root }
    primary_defender = {
        ordered_vassal = {
            limit = {
                is_ai = yes
                opinion = { target = prev value <= 0 }
            }
            order_by = max_military_strength
            save_scope_as = recipient
        }
    }
}
"""))

K(key="seed_the_separatists", cat="C", group="abroad", secret="faction", icon="independence",
  name="Seed the Separatists",
  ask="win independence from [qpq_target.GetTitledFirstName] on [qpq_payer.GetShortUINamePossessive] gold",
  desc="Fund a foreign [vassal|E]'s independence. If they win, their half becomes a public Charter and they gain [prestige|E] as liberators; you still pay with their former [liege|E].",
  echo="Michael VIII's gold behind the 1282 Sicilian Vespers against Charles of Anjou, a role he later claimed credit for.",
  payer_base=3, agent_base=4, target="derived", derive="scope:recipient.liege", term=120, effort=25, victors=True,
  rel=REL_FOREIGN_VASSAL,
  payer_adj="""
if = {
    limit = {
        scope:recipient.liege.faith = scope:actor.faith
        NOT = { scope:actor = { is_at_war_with = scope:recipient.liege } }
    }
    add = 1
}
""",
  demand=[("15", "scope:recipient = { opinion = { target = scope:recipient.liege value <= -20 } }", "QPQ_REASON_RESENTS_LIEGE"),
          ("10", "scope:recipient = { has_trait = ambitious }", "QPQ_REASON_AMBITIOUS_CONQUEST")],
  deliver="scope:qpq_agent = { NOT = { liege ?= scope:qpq_target } }",
  invalid="scope:qpq_agent = { is_landed = no }",
  attempt="""
if = {
    limit = {
        scope:qpq_agent = {
            NOT = { exists = joined_faction }
            can_create_faction = { type = independence_faction target = scope:qpq_target }
        }
    }
    random = {
        chance = 15
        scope:qpq_agent = { create_faction = { type = independence_faction target = scope:qpq_target } }
    }
}
else_if = {
    limit = { scope:qpq_agent = { exists = joined_faction } }
    scope:qpq_agent.joined_faction = { add_faction_discontent = 2 }
}
""",
  on_deliver="qpq_victors_justice_effect = yes",
  exposed="",
  ai=dict(weight=5, valid="""is_independent_ruler = yes any_relation = { type = rival is_independent_ruler = yes }""", find="""
# the rival realm root hates most, broken up through its strongest discontented vassal
ordered_relation = {
    type = rival
    limit = { is_independent_ruler = yes NOT = { this = root } }
    order_by = qpq_ai_enmity_value
    save_scope_as = qpq_ai_rival
}
if = {
    limit = { exists = scope:qpq_ai_rival }
    scope:qpq_ai_rival = {
        ordered_vassal = {
            limit = {
                is_ai = yes
                highest_held_title_tier >= tier_duchy
                opinion = { target = scope:qpq_ai_rival value <= 0 }
            }
            order_by = max_military_strength
            save_scope_as = recipient
        }
    }
}
"""))

K(key="shelter_the_pretender", cat="C", group="abroad", secret="betrayal", icon="icon_claim_pressed",
  name="Shelter the Pretender",
  ask="take [qpq_target_title.GetName] with [qpq_payer.GetShortUINamePossessive] backing, and never forget who made it possible",
  desc="Host a [claimant|E] to a rival throne and back their [claim|E]. Mostly public already; the secret clause, armies quietly promised, is what hurts.",
  echo="Byzantine backing for the Ottoman pretender Mustafa Çelebi against Murad II, 1421-1422.",
  payer_base=1, agent_base=1, target="title", term=120, effort=10, victors=True,
  rel="""
scope:recipient = {
    is_adult = yes
    NOT = { this = scope:actor }
    any_claim = { tier >= tier_duchy NOT = { holder ?= scope:actor } }
}
scope:actor = { is_landed = yes }
""",
  pick=dict(source="recipient", filter="claimed_titles", can_pick="scope:target = { tier >= tier_duchy NOT = { holder ?= scope:actor } }"),
  target_valid="scope:recipient = { has_claim_on = scope:target }",
  extra_options=[dict(flag="qpq_x_armies", loc="qpq_x_armies", desc="qpq_x_armies_desc", is_shown="always = yes")],
  payer_adj="if = { limit = { scope:qpq_x_armies ?= yes } add = 1 }",
  demand=[("20", "always = yes", "QPQ_REASON_BACKED_CLAIM"), ("20", "scope:qpq_x_armies ?= yes", "QPQ_REASON_ARMIES_PROMISED")],
  on_seal="""
if = {
    limit = { scope:qpq_agent = { is_landed = no NOT = { is_courtier_of = scope:qpq_payer } } }
    scope:qpq_payer = { add_courtier = scope:qpq_agent }
}
""",
  deliver="scope:qpq_target_title.holder ?= scope:qpq_agent",
  invalid="""
NOT = { scope:qpq_agent = { has_claim_on = scope:qpq_target_title } }
NOT = { scope:qpq_target_title.holder ?= scope:qpq_agent }
""",
  on_deliver="""
qpq_victors_justice_effect = yes
scope:qpq_agent = {
    add_opinion = { target = scope:qpq_payer modifier = qpq_grateful_patron_opinion }
}
scope:qpq_payer = { add_hook = { type = strong_favor_hook target = scope:qpq_agent } }
""",
  exposed="")

K(key="extradition", cat="C", group="blood", secret="abduction", icon="prison",
  icategory="interaction_category_hostile",
  name="Extradition",
  ask="hand [qpq_target.GetTitledFirstName] over to [qpq_payer.GetShortUIName]",
  desc="Surrender a [prisoner|E], [hostage|E], [claimant|E] or refugee they hold or shelter. Tier I from your own [vassal|E]; Tier III from a foreign ruler, or if the person is their kin or [guest|E]. If it comes out, they are known to have betrayed a [guest|E].",
  payer_base=1, agent_base=1, mode="perform", term=12, effort=10,
  # kin, guests and foreign courts are counted below (as the text says), not again by the general context
  agent_ctx=False,
  rel="""
OR = {
    AND = {
""" + REL_VASSAL + """
    }
    AND = {
""" + REL_FOREIGN_RULER + """
    }
}
""",
  pick="""
scope:recipient = {
    every_prisoner = { add_to_list = characters }
    every_courtier = {
        limit = {
            OR = {
                is_hostage = yes
                any_claim = { holder ?= scope:actor }
                NOT = { is_close_family_of = scope:recipient }
            }
        }
        add_to_list = characters
    }
    every_foreign_court_guest = { add_to_list = characters }
    every_pool_guest = { add_to_list = characters }
}
""",
  agent_adj="""
if = {
    limit = {
        OR = {
            NOT = { scope:recipient.top_liege = scope:actor.top_liege }
            AND = {
                exists = scope:secondary_recipient
                scope:secondary_recipient = {
                    OR = {
                        is_close_family_of = scope:recipient
                        is_pool_guest_of = scope:recipient
                        is_foreign_court_guest_of = scope:recipient
                    }
                }
            }
        }
    }
    add = 2
}
""",
  payer_adj="""
if = {
    limit = { NOT = { scope:recipient.top_liege = scope:actor.top_liege } }
    add = 2
    if = {
        limit = {
            exists = scope:secondary_recipient
            scope:secondary_recipient = { any_claim = { holder ?= scope:actor } }
        }
        add = 1
    }
}
else_if = {
    limit = {
        exists = scope:secondary_recipient
        scope:secondary_recipient = {
            OR = {
                is_pool_guest_of = scope:recipient
                is_foreign_court_guest_of = scope:recipient
            }
        }
    }
    add = 1
}
""",
  can_perform="scope:qpq_target = { is_alive = yes }",
  invalid=TARGET_DEAD,
  # their own vassal's courtier simply comes to court; anyone else arrives a prisoner
  perform="""
if = {
    limit = {
        scope:qpq_agent = { liege ?= scope:qpq_payer }
        scope:qpq_target = { is_imprisoned = no }
    }
    scope:qpq_payer = { add_courtier = scope:qpq_target }
}
else = {
    qpq_hand_prisoner_to_payer_effect = yes
}
""",
  exposed="""
scope:qpq_agent = {
    every_courtier = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_betrayed_a_guest_opinion }
    }
}
""")

K(key="buy_a_councillor", cat="C", group="shadows", secret="espionage", icon="council",
  name="Buy a Councillor",
  ask="leak and sabotage from [qpq_target.GetShortUINamePossessive] council",
  desc="Bribe a foreign [councillor|E] to leak secrets, sabotage, and sour relations for the whole term.",
  payer_base=2, agent_base=4, target="derived", derive="scope:recipient.liege", mode="restraint", term=48, effort=15,
  rel=REL_FOREIGN + """
scope:recipient = {
    is_councillor = yes
    exists = liege
    is_councillor_of = scope:recipient.liege
}
""",
  demand=[("-15", "scope:recipient = { opinion = { target = scope:recipient.liege value >= 40 } }", "QPQ_REASON_LOVES_TARGET")],
  on_seal="""
scope:qpq_target = {
    add_character_modifier = { modifier = qpq_council_sabotage_modifier months = qpq_term_months_value }
}
""",
  tick="""
random = {
    chance = 8
    scope:qpq_target = {
        random_secret = {
            limit = { NOT = { is_known_by = scope:qpq_payer } }
            reveal_to = scope:qpq_payer
        }
    }
}
""",
  invalid="NOT = { scope:qpq_agent = { is_councillor_of = scope:qpq_target } }",
  on_end="""
scope:qpq_target = {
    if = {
        limit = { has_character_modifier = qpq_council_sabotage_modifier }
        remove_character_modifier = qpq_council_sabotage_modifier
    }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_spied_for_a_foreigner_opinion }
        add_opinion = { target = scope:qpq_payer modifier = qpq_avenge_perfidy_opinion }
        if = {
            limit = { scope:qpq_agent = { is_councillor_of = scope:qpq_target } }
            fire_councillor = scope:qpq_agent
        }
    }
}
""")

K(key="stay_home", cat="C", group="abroad", secret="betrayal", icon="icon_combat",
  name="Stay Home",
  ask="ignore [qpq_target.GetShortUINamePossessive] call to arms when [qpq_payer.GetShortUIName] attacks",
  desc="A foreign [vassal|E] ignores their [liege|E]'s call to arms when you attack: their [levies|E] stay home for the whole term.",
  payer_base=2, agent_base=3, target="derived", derive="scope:recipient.liege", mode="restraint", term=48, effort=10,
  rel=REL_FOREIGN_VASSAL,
  on_seal="""
scope:qpq_agent = {
    add_character_modifier = { modifier = qpq_withholding_levies_modifier months = qpq_term_months_value }
}
""",
  deliver=PAYER_BEAT_TARGET,
  on_end="""
scope:qpq_agent = {
    if = {
        limit = { has_character_modifier = qpq_withholding_levies_modifier }
        remove_character_modifier = qpq_withholding_levies_modifier
    }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_traitor_opinion opinion = -40 }
    }
}
scope:qpq_agent = { add_character_modifier = { modifier = qpq_faithless_modifier years = 10 } }
""")

K(key="defection_pact", cat="C", group="abroad", secret="betrayal", icon="independence",
  name="Defection Pact",
  ask="become [qpq_payer.GetShortUINamePossessive] vassal, lands and all, if [qpq_target.GetTitledFirstName] loses",
  desc="A foreign [vassal|E] swears to become your vassal, lands and all, if you win a war against their [liege|E]. Treason for them if the war is lost.",
  echo="Frontier magnates changing sides was common on the Iberian and Balkan frontiers.",
  payer_base=2, agent_base=4, target="derived", derive="scope:recipient.liege", term=96, effort=15, victors=True,
  rel=REL_FOREIGN_VASSAL,
  deliver=PAYER_BEAT_TARGET,
  breach="qpq_beat_trigger = { LIST = qpq_payer_lost_to WHO = scope:qpq_target }",
  invalid="scope:qpq_agent = { is_landed = no }",
  on_deliver="""
create_title_and_vassal_change = {
    type = swear_fealty
    save_scope_as = qpq_defect_change
    add_claim_on_loss = no
}
scope:qpq_agent = {
    change_liege = {
        liege = scope:qpq_payer
        change = scope:qpq_defect_change
    }
}
resolve_title_and_vassal_change = scope:qpq_defect_change
qpq_victors_justice_effect = yes
""",
  on_end="""
# The war was lost: the defector's treason is laid bare to their liege
if = {
    limit = {
        var:qpq_closed ?= flag:breached
        exists = scope:qpq_agent_secret
        scope:qpq_target = { is_alive = yes }
    }
    scope:qpq_agent_secret = { reveal_to = scope:qpq_target }
}
""",
  exposed="")

K(key="hire_the_hashashin", cat="C", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="Hire Holy Order Assassins",
  ask="have [qpq_target.GetTitledFirstName] killed by their order",
  desc="Commission a murder through a foreign [holy_order|E]. If it comes out, the victim's house and [faith|E] turn hostile.",
  echo="Conrad of Montferrat, 1192: rumours of a paymaster pointed at Richard I.",
  payer_base=5, agent_base=5, term=36, effort=20,
  rel="""
NOT = { scope:recipient.top_liege = scope:actor.top_liege }
scope:recipient = {
    any_held_title = { is_holy_order = yes }
}
""",
  pick=PICK_VICTIMS,
  target_valid="scope:secondary_recipient = { NOT = { this = scope:actor } NOT = { this = scope:recipient } }",
  deliver=TARGET_DEAD,
  attempt="qpq_hired_blade_attempt_effect = { AGENT = scope:qpq_agent TARGET = scope:qpq_target }",
  exposed=VICTIM_HOUSE_HOSTILE + """
if = {
    limit = { exists = scope:qpq_target.faith.religious_head }
    scope:qpq_target.faith.religious_head = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -30 }
    }
}
""")

###############################################################################
# CATALOGUE D1: any faith with a head of faith
###############################################################################

D_VALID = [("qpq_valid_not_excommunicated_agent", "scope:recipient = { NOT = { has_trait = excommunicated } }")]

K(key="excommunication_for_hire", cat="D1", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Excommunication for Hire",
  ask="excommunicate [qpq_target.GetTitledFirstName]",
  desc="Pay the [head_of_faith|E] to [excommunicate|E] a rival. If it comes out, the excommunication may be lifted and the head of faith's standing suffers.",
  payer_base=4, agent_base=4, mode="perform", term=24, effort=15,
  rel=REL_HOF + "scope:recipient.faith = { qpq_faith_has_church_trigger = yes }", pick=PICK_SAME_FAITH_RIVALS,
  target_valid="scope:secondary_recipient = { faith = scope:recipient.faith NOT = { has_trait = excommunicated } }",
  can_perform="scope:qpq_target = { is_alive = yes NOT = { has_trait = excommunicated } faith = scope:qpq_agent.faith }",
  invalid="scope:qpq_target = { is_alive = no }",
  perform="""
excommunicate_character = {
    REQUESTING_CHARACTER = scope:qpq_agent
    EXCOMMUNICATOR = scope:qpq_agent
    TARGET_CHARACTER = scope:qpq_target
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { has_trait = excommunicated } }
    scope:qpq_target = { remove_trait = excommunicated }
}
""")

K(key="dispensation_for_gold", cat="D1", group="church_favours", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Dispensation for Gold",
  ask="grant a dispensation concerning [qpq_target.GetTitledFirstName]",
  desc="An annulment of your [marriage|E] to a chosen [spouse|E], or the legitimisation of your [bastard|E], for payment. If it comes out, the ruling may be reversed.",
  payer_base=2, agent_base=2, mode="perform", term=24, effort=5,
  rel=REL_HOF + """
scope:recipient.faith = {
    OR = {
        qpq_faith_has_church_trigger = yes
        has_doctrine = doctrine_divorce_approval
    }
}
""",
  pick="""
scope:actor = {
    every_spouse = { add_to_list = characters }
    every_child = {
        limit = { has_trait = bastard }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { OR = { is_spouse_of = scope:actor has_trait = bastard } }",
  can_perform="scope:qpq_target = { is_alive = yes OR = { is_spouse_of = scope:qpq_payer has_trait = bastard } }",
  invalid="scope:qpq_target = { is_alive = no }",
  perform="""
if = {
    limit = { scope:qpq_target = { is_spouse_of = scope:qpq_payer } }
    scope:qpq_payer = { divorce = scope:qpq_target }
}
else = {
    scope:qpq_target = {
        remove_trait = bastard
        add_trait = legitimized_bastard
    }
}
""",
  exposed="""
scope:qpq_payer = { add_piety = medium_piety_loss }
if = {
    limit = { scope:qpq_target = { has_trait = legitimized_bastard } }
    scope:qpq_target = {
        remove_trait = legitimized_bastard
        add_trait = bastard
    }
}
""")

K(key="steer_the_holy_war", cat="D1", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Steer the Holy War",
  ask="aim the next great holy war at [qpq_target.GetTitledFirstName]",
  desc="Aim the next [great_holy_war|E] at a rival, or away from your own lands. If it comes out, the faith's holy warriors and the [faith|E] itself turn on you.",
  payer_base=3, agent_base=3, term=120, effort=10,
  rel=REL_HOF + "scope:recipient.faith = { suitable_faith_for_any_ghw_trigger = yes }", pick=PICK_RIVALS,
  target_valid="scope:secondary_recipient = { is_landed = yes highest_held_title_tier >= tier_kingdom NOT = { this = scope:actor } }",
  deliver="has_variable = qpq_ghw_steered",
  invalid="scope:qpq_target = { is_landed = no }",
  tick="""
if = {
    limit = {
        NOT = { has_variable = qpq_ghw_steered }
        exists = scope:qpq_agent.faith.great_holy_war
        exists = scope:qpq_target.primary_title
        scope:qpq_target.primary_title = { tier >= tier_kingdom }
    }
    scope:qpq_agent.faith.great_holy_war = {
        set_great_holy_war_target = {
            target_title = scope:qpq_target.primary_title
            target_character = scope:qpq_target
        }
    }
    set_variable = qpq_ghw_steered
}
""",
  exposed="""
scope:qpq_agent.faith = {
    every_faith_holy_order = {
        leader ?= {
            add_opinion = { target = scope:qpq_payer modifier = qpq_clergy_scandal_opinion }
        }
    }
}
""")

K(key="purchase_a_mitre", cat="D1", group="church_favours", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Buy a Bishopric",
  ask="give [qpq_target.GetTitledFirstName] a bishopric or temple",
  desc="Buy a bishopric, [temple_holding|E] or other theocratic seat for a relative.",
  echo="The core grievance of the Investiture Controversy.",
  payer_base=3, agent_base=3, mode="perform", term=36, effort=10,
  rel=REL_HOF + "scope:recipient.faith = { qpq_faith_has_church_trigger = yes }",
  pick="""
scope:actor = {
    every_close_family_member = {
        limit = {
            is_adult = yes
            faith = scope:recipient.faith
            is_landed = no
        }
        add_to_list = characters
    }
}
""",
  agent_adj="if = { limit = { scope:recipient.faith = { has_doctrine_parameter = has_clerical_electors } } add = 1 }",
  payer_adj="if = { limit = { scope:recipient.faith = { has_doctrine_parameter = has_clerical_electors } } add = 1 }",
  target_valid="scope:secondary_recipient = { is_landed = no faith = scope:recipient.faith }",
  can_perform="scope:qpq_target = { is_alive = yes is_landed = no }",
  invalid="scope:qpq_target = { is_alive = no }",
  perform="""
scope:qpq_agent = {
    random_held_title = {
        limit = {
            tier = tier_barony
            is_capital_barony = no
            title_province ?= { has_holding_type = church_holding }
        }
        save_scope_as = qpq_mitre
    }
}
if = {
    limit = { exists = scope:qpq_mitre }
    create_title_and_vassal_change = {
        type = granted
        save_scope_as = qpq_mitre_change
        add_claim_on_loss = no
    }
    scope:qpq_mitre = {
        change_title_holder = {
            holder = scope:qpq_target
            change = scope:qpq_mitre_change
        }
    }
    resolve_title_and_vassal_change = scope:qpq_mitre_change
    scope:qpq_payer_secret ?= { set_variable = { name = qpq_mitre_title value = scope:qpq_mitre } }
}
scope:qpq_target = {
    add_piety = medium_piety_gain
    add_character_modifier = { modifier = qpq_bought_mitre_modifier years = 20 }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { has_character_modifier = qpq_bought_mitre_modifier } }
    scope:qpq_target = { remove_character_modifier = qpq_bought_mitre_modifier }
}
scope:qpq_payer = { add_character_modifier = { modifier = qpq_clerical_denunciation_modifier years = 10 } }
# The holder may be deposed: the bought see returns to the head of faith
if = {
    limit = {
        exists = scope:qpq_payer_secret.var:qpq_mitre_title
        scope:qpq_payer_secret.var:qpq_mitre_title.holder ?= scope:qpq_target
        scope:qpq_agent = { is_alive = yes is_landed = yes }
    }
    scope:qpq_payer_secret.var:qpq_mitre_title = { save_scope_as = qpq_lost_mitre }
    create_title_and_vassal_change = {
        type = revoked
        save_scope_as = qpq_mitre_revoke
        add_claim_on_loss = no
    }
    scope:qpq_lost_mitre = {
        change_title_holder = {
            holder = scope:qpq_agent
            change = scope:qpq_mitre_revoke
        }
    }
    resolve_title_and_vassal_change = scope:qpq_mitre_revoke
}
""")

K(key="bought_claim", cat="D1", group="church_favours", secret="simony", icon="icon_claim_pressed",
  icategory="interaction_category_religion",
  name="Bought Claim",
  ask="grant [qpq_payer.GetShortUIName] a claim on [qpq_target.GetShortUINamePossessive] title",
  desc="The [head_of_faith|E] grants you a [claim|E] on a rival's primary [title|E], where the faith allows it. If it comes out, the claim loses its sanctity.",
  payer_base=3, agent_base=3, mode="perform", term=24, effort=10,
  rel=REL_HOF + "scope:recipient.faith = { has_doctrine = doctrine_spiritual_head }", pick=PICK_RIVALS,
  target_valid="scope:secondary_recipient = { is_landed = yes exists = primary_title NOT = { this = scope:actor } }",
  can_perform="""
exists = scope:qpq_target.primary_title
NOT = { scope:qpq_payer = { has_claim_on = scope:qpq_target.primary_title } }
""",
  invalid="scope:qpq_target = { is_landed = no }",
  perform="""
scope:qpq_payer = { add_unpressed_claim = scope:qpq_target.primary_title }
scope:qpq_payer_secret ?= { set_variable = { name = qpq_bought_claim_title value = scope:qpq_target.primary_title } }
""",
  exposed="""
if = {
    limit = {
        exists = scope:qpq_payer_secret.var:qpq_bought_claim_title
        scope:qpq_payer = { has_claim_on = scope:qpq_payer_secret.var:qpq_bought_claim_title }
    }
    scope:qpq_payer = { remove_claim = scope:qpq_payer_secret.var:qpq_bought_claim_title }
}
""",
  ai=dict(weight=3, valid="""exists = faith.religious_head NOT = { faith.religious_head = root } faith.religious_head = { is_ai = yes } faith = { has_doctrine = doctrine_spiritual_head } any_relation = { type = rival is_landed = yes }""", find="""
faith.religious_head = { save_scope_as = recipient }
ordered_relation = {
    type = rival
    limit = { is_landed = yes }
    order_by = qpq_ai_enmity_value
    save_scope_as = secondary_recipient
}
"""))

K(key="absolution_by_concession", cat="D1", group="church_favours", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Absolution by Concession",
  ask="lift [qpq_payer.GetShortUINamePossessive] excommunication",
  desc="Have your [excommunication|E] lifted in return for land or rights. Mostly public; a hidden price is what stings.",
  echo="Henry IV at Canossa, 1077.",
  payer_base=1, agent_base=1, target="none", mode="perform", term=12, effort=0,
  rel=REL_HOF + "scope:actor = { has_trait = excommunicated } scope:recipient.faith = { qpq_faith_has_church_trigger = yes }",
  can_perform="scope:qpq_payer = { has_trait = excommunicated }",
  invalid="NOT = { scope:qpq_payer = { has_trait = excommunicated } }",
  perform="scope:qpq_payer = { remove_trait = excommunicated }",
  exposed="",
  ai=dict(weight=8, valid="has_trait = excommunicated exists = faith.religious_head faith.religious_head = { is_ai = yes } faith = { qpq_faith_has_church_trigger = yes }",
          find="faith.religious_head = { save_scope_as = recipient }"))

K(key="holy_warrant", licence=True, cat="D1", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Holy Warrant",
  ask="declare a holy war on [qpq_target.GetTitledFirstName] on [qpq_payer.GetShortUINamePossessive] behalf",
  desc="A [temporal_head_of_faith|E] declares a [holy_war|E] on your behalf, for gold. Exposure stacks with Proxy War fallout, one tier higher.",
  payer_base=3, agent_base=3, term=60, effort=20,
  rel=REL_HOF + "scope:recipient = { is_landed = yes highest_held_title_tier >= tier_county } scope:recipient.faith = { has_doctrine = doctrine_temporal_head }",
  pick=PICK_RIVALS,
  target_valid="""
scope:secondary_recipient = {
    is_landed = yes
    NOT = { faith = scope:recipient.faith }
}
""",
  deliver="qpq_beat_trigger = { LIST = qpq_agent_attacked WHO = scope:qpq_target }",
  invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE, attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed=PROXY_FALLOUT)

###############################################################################
# CATALOGUE D2: the Catholic Church (By God Alone)
###############################################################################

BGA = "has_dlc_feature = by_god_alone"
PAPAL = """
scope:recipient.faith = { has_doctrine_parameter = has_clerical_electors }
"""

K(key="buy_a_bull", cat="D2", group="church_favours", secret="simony", icon="religious",
  icategory="interaction_category_religion", dlc=BGA,
  name="Buy a Bull",
  ask="issue a bull concerning [qpq_target.GetTitledFirstName]",
  desc="Pay the Pope to issue a bull favouring you (pick yourself) or condemning a rival. If it comes out, the Pope loses authority, and the buyer loses [piety|E] and risks [excommunication|E].",
  payer_base=4, agent_base=4, mode="perform", term=24, effort=10,
  rel=REL_HOF + PAPAL, pick=PICK_SELF_OR_RIVALS,
  target_valid="exists = scope:secondary_recipient",
  can_perform="always = yes",
  perform="""
if = {
    limit = { scope:qpq_target = scope:qpq_payer }
    scope:qpq_payer = { add_character_modifier = { modifier = qpq_papal_favour_modifier years = 10 } }
}
else = {
    scope:qpq_target = { add_character_modifier = { modifier = qpq_papal_condemnation_modifier years = 10 } }
}
""",
  exposed="""
scope:qpq_agent = { add_piety = major_piety_loss }
if = {
    limit = { scope:qpq_target = { has_character_modifier = qpq_papal_condemnation_modifier } }
    scope:qpq_target = { remove_character_modifier = qpq_papal_condemnation_modifier }
}
if = {
    limit = { scope:qpq_payer = { has_character_modifier = qpq_papal_favour_modifier } }
    scope:qpq_payer = { remove_character_modifier = qpq_papal_favour_modifier }
}
""")

K(key="conclave_votes", cat="D2", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion", dlc=BGA,
  name="Conclave Votes",
  ask="vote for [qpq_target.GetTitledFirstName] in the next papal election",
  desc="Buy a cardinal's vote in a papal [election|E]. If it comes out, the new Pope's standing collapses and the risk of schism rises.",
  payer_base=4, agent_base=4, mode="restraint", term=120, effort=5,
  rel="""
scope:recipient = {
    exists = clerical_elector_title
    NOT = { this = scope:actor }
}
scope:recipient.faith = { has_doctrine_parameter = has_clerical_electors }
""",
  pick="""
scope:recipient.faith = {
    every_clerical_elector_title = {
        holder ?= {
            if = {
                limit = {
                    is_alive = yes
                    is_papabile = yes
                    NOT = { this = scope:recipient }
                }
                add_to_list = characters
            }
        }
    }
}
""",
  target_valid="exists = scope:secondary_recipient",
  on_seal="""
scope:qpq_agent = {
    set_variable = {
        name = pam_forced_papal_vote_target
        value = scope:qpq_target
        years = 20
    }
    recalculate_succession_election_vote = yes
}
""",
  deliver="scope:qpq_target = { qpq_is_head_of_faith_trigger = yes }",
  invalid="scope:qpq_target = { is_alive = no }",
  exposed="""
if = {
    limit = { scope:qpq_target = { qpq_is_head_of_faith_trigger = yes } }
    scope:qpq_target = {
        add_piety = major_piety_loss
        add_character_modifier = { modifier = qpq_bought_legitimacy_modifier years = 15 }
    }
    scope:qpq_target.faith = {
        change_fervor = {
            value = -10
            desc = qpq_fervor_pact_exposed
        }
    }
}
""")

K(key="council_lobbying", cat="D2", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion", dlc=BGA,
  name="Council Lobbying",
  ask="vote with [qpq_payer.GetShortUIName] at the next Ecumenical Council",
  desc="Buy a delegate's votes at an Ecumenical Council on a tenet question. If it comes out, delegates lose [piety|E] and the losing side may refuse the result.",
  payer_base=2, agent_base=2, target="none", mode="restraint", term=60, effort=0,
  rel="""
scope:recipient = {
    is_clergy = yes
    NOT = { this = scope:actor }
}
scope:recipient.faith = scope:actor.faith
scope:recipient.faith = { has_doctrine_parameter = has_clerical_electors }
""",
  on_seal="""
scope:qpq_agent = {
    add_opinion = { target = scope:qpq_payer modifier = qpq_bought_support_opinion }
}
""",
  exposed="""
scope:qpq_agent = { add_piety = medium_piety_loss }
scope:qpq_agent.faith = {
    change_fervor = {
        value = -5
        desc = qpq_fervor_pact_exposed
    }
}
""")

###############################################################################
# CATALOGUE D3: signature pacts of other faiths
###############################################################################

K(key="caliphal_investiture", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Caliphal Investiture",
  ask="formally recognise [qpq_payer.GetShortUINamePossessive] title as sultan or emir",
  desc="Protect or pay the caliph in return for formal recognition of your [title|E]. Rivals call it bought [legitimacy|E].",
  echo="Tughril Beg's recognition as sultan by the Abbasid caliph, 1055.",
  payer_base=1, agent_base=1, target="none", mode="perform", term=12, effort=0,
  rel=REL_HOF + "scope:recipient.faith = { has_doctrine = muhammad_succession_sunni_doctrine }",
  can_perform="always = yes",
  perform="""
scope:qpq_payer = {
    add_character_modifier = { modifier = qpq_caliphal_investiture_modifier years = 20 }
    add_prestige = medium_prestige_gain
    if = {
        limit = { qpq_uses_legitimacy_trigger = yes }
        add_legitimacy = 25
    }
}
""",
  exposed="""
scope:qpq_payer = {
    add_character_modifier = { modifier = qpq_bought_legitimacy_modifier years = 10 }
    if = {
        limit = { qpq_uses_legitimacy_trigger = yes }
        add_legitimacy = -10
    }
}
""")

K(key="name_in_the_khutba", cat="D3", group="church_weapons", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Name in the Khutba",
  ask="read the Friday prayers in [qpq_payer.GetShortUINamePossessive] caliph's name instead of [qpq_target.GetShortUINamePossessive]",
  desc="A foreign Muslim [vassal|E] has the Friday prayers read in your caliph's name instead of their [liege|E]'s: a public renunciation of allegiance, and treason for them.",
  echo="Saladin restoring the Abbasid khutba in Fatimid Egypt, 1171.",
  payer_base=2, agent_base=4, target="derived", derive="scope:recipient.liege", mode="perform", term=24, effort=15,
  rel=REL_FOREIGN_VASSAL + """
scope:actor.religion = religion:islam_religion
scope:recipient.religion = religion:islam_religion
""",
  can_perform="always = yes",
  perform="""
scope:qpq_agent = {
    add_character_modifier = { modifier = qpq_khutba_read_modifier years = 10 }
    if = {
        limit = { NOT = { faith = scope:qpq_payer.faith } }
        set_character_faith = scope:qpq_payer.faith
    }
}
scope:qpq_payer = { add_prestige = medium_prestige_gain }
scope:qpq_target = { add_character_modifier = { modifier = qpq_khutba_slighted_modifier years = 5 } }
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_traitor_opinion }
    }
}
""")

K(key="fatwa_for_hire", cat="D3", group="church_weapons", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Fatwa for Hire",
  ask="rule [qpq_target.GetShortUINamePossessive] war or reign unlawful",
  desc="A respected jurist, or the [head_of_faith|E], rules a rival's war or reign unlawful. If it comes out, the jurist is discredited and the ruling voided.",
  payer_base=2, agent_base=2, mode="perform", term=24, effort=10,
  rel="""
scope:recipient = {
    NOT = { this = scope:actor }
    religion = religion:islam_religion
    OR = {
        qpq_is_head_of_faith_trigger = yes
        AND = {
            is_clergy = yes
            learning >= 15
        }
    }
}
scope:actor.religion = religion:islam_religion
""",
  pick=PICK_RIVALS,
  agent_adj="if = { limit = { exists = scope:secondary_recipient scope:secondary_recipient = { highest_held_title_tier >= tier_kingdom } } add = 1 }",
  target_valid="scope:secondary_recipient = { is_landed = yes religion = religion:islam_religion }",
  can_perform="scope:qpq_target = { is_alive = yes }",
  invalid=TARGET_DEAD,
  perform="scope:qpq_target = { add_character_modifier = { modifier = qpq_declared_unlawful_modifier years = 10 } }",
  exposed="""
scope:qpq_agent = { add_prestige = medium_prestige_loss }
if = {
    limit = { scope:qpq_target = { has_character_modifier = qpq_declared_unlawful_modifier } }
    scope:qpq_target = { remove_character_modifier = qpq_declared_unlawful_modifier }
}
""")

K(key="fund_the_dawa", cat="D3", group="church_weapons", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Fund the Da'wa",
  ask="send missionaries to turn [qpq_target.GetShortUINamePossessive] capital to [qpq_payer.GetFaith.GetName]",
  desc="Pay missionaries to convert a rival's [capital|E] [county|E]. If it comes out, the target realm turns hostile.",
  echo="The Fatimid missionary network.",
  payer_base=2, agent_base=2, term=96, effort=10,
  rel="""
scope:recipient = {
    NOT = { this = scope:actor }
    faith = scope:actor.faith
    OR = {
        qpq_is_head_of_faith_trigger = yes
        AND = { is_clergy = yes learning >= 12 }
    }
}
scope:actor.faith = { has_doctrine = muhammad_succession_shia_doctrine }
""",
  pick=PICK_RIVALS,
  target_valid="scope:secondary_recipient = { is_landed = yes NOT = { faith = scope:actor.faith } }",
  deliver="scope:qpq_target.capital_county.faith ?= scope:qpq_payer.faith",
  invalid="scope:qpq_target = { is_landed = no }",
  attempt="""
random = {
    chance = {
        value = 1
        add = { value = scope:qpq_agent.learning divide = 10 }
    }
    scope:qpq_target.capital_county ?= { set_county_faith = scope:qpq_payer.faith }
}
""",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -30 }
    }
}
""")

K(key="crowning_the_usurper", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Crowning the Usurper",
  ask="bless and crown [qpq_payer.GetShortUIName] against [qpq_target.GetTitledFirstName]",
  desc="The patriarch blesses and crowns you against the emperor. If it comes out, the patriarch is disgraced and your [legitimacy|E] falls.",
  echo="Patriarch Michael Keroularios backing Isaac Komnenos's revolt, 1057.",
  payer_base=4, agent_base=4, target="derived", derive="scope:actor.top_liege", mode="perform", term=24, effort=15,
  rel=REL_HOF + """
scope:recipient.faith = faith:orthodox
scope:actor = {
    is_independent_ruler = no
    top_liege = { highest_held_title_tier >= tier_empire }
}
""",
  can_perform="always = yes",
  perform="""
scope:qpq_payer = {
    add_character_modifier = { modifier = qpq_crowned_by_patriarch_modifier years = 20 }
    add_prestige = major_prestige_gain
    if = {
        limit = { qpq_uses_legitimacy_trigger = yes }
        add_legitimacy = 30
    }
}
""",
  exposed="""
scope:qpq_agent = {
    add_piety = major_piety_loss
    add_character_modifier = { modifier = qpq_clerical_denunciation_modifier years = 10 }
}
if = {
    limit = { scope:qpq_payer = { has_character_modifier = qpq_crowned_by_patriarch_modifier } }
    scope:qpq_payer = { remove_character_modifier = qpq_crowned_by_patriarch_modifier }
}
""")

K(key="pliant_patriarch", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Pliant Patriarch",
  ask="owe [qpq_payer.GetShortUIName] a favour for the patriarchal throne",
  desc="The patriarch you installed owes the throne a favour [hook|E]. If it comes out, the clergy think less of the emperor.",
  echo="Emperors deposing and installing patriarchs.",
  payer_base=2, agent_base=2, target="none", mode="perform", term=12, effort=0,
  rel=REL_HOF + """
scope:recipient.faith = faith:orthodox
scope:actor = { highest_held_title_tier >= tier_kingdom }
""",
  can_perform="always = yes",
  perform="scope:qpq_payer = { add_hook = { type = qpq_pliant_cleric_hook target = scope:qpq_agent } }",
  exposed="scope:qpq_payer = { add_character_modifier = { modifier = qpq_clerical_denunciation_modifier years = 10 } }")

OMEN_ADVISER = """
scope:recipient = {
    NOT = { this = scope:actor }
    faith = scope:actor.faith
    OR = {
        qpq_is_head_of_faith_trigger = yes
        this = scope:actor.realm_priest
    }
}
"""

K(key="favourable_omens", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Favourable Omens",
  ask="read the omens for [qpq_target.GetTitledFirstName] as [qpq_payer.GetShortUIName] wishes",
  desc="Priests or seers read good omens before your war (pick yourself), or bad ones before a rival's. If it comes out, the seers are discredited.",
  payer_base=1, agent_base=1, mode="perform", term=12, effort=0,
  rel=OMEN_ADVISER + "scope:actor.religion = { is_in_family = rf_pagan }",
  pick=PICK_SELF_OR_RIVALS,
  target_valid="exists = scope:secondary_recipient",
  can_perform="always = yes",
  perform="""
if = {
    limit = { scope:qpq_target = scope:qpq_payer }
    scope:qpq_payer = { add_character_modifier = { modifier = qpq_favourable_omens_modifier years = 2 } }
}
else = {
    scope:qpq_target = { add_character_modifier = { modifier = qpq_ill_omens_modifier years = 2 } }
}
""",
  exposed="scope:qpq_agent = { add_piety = minor_piety_loss } scope:qpq_payer = { add_piety = minor_piety_loss }")

K(key="consecration_rites", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Consecration Rites",
  ask="perform the rites that raise [qpq_payer.GetShortUIName] to kingship",
  desc="Priests perform the rites that raise a low-born or usurping ruler to kingship. Rival claimants call the rite bought.",
  echo="Rites such as the hiranyagarbha, performed by early medieval Indian kings.",
  payer_base=1, agent_base=1, target="none", mode="perform", term=12, effort=0,
  rel=OMEN_ADVISER + "scope:actor.religion = { is_in_family = rf_eastern }",
  payer_adj="""
if = {
    limit = {
        scope:actor = {
            OR = {
                NOT = { exists = dynasty }
                dynasty = { dynasty_prestige_level <= 1 }
                primary_title.title_held_years < 5
            }
        }
    }
    add = 1
}
""",
  can_perform="always = yes",
  perform="""
scope:qpq_payer = {
    add_character_modifier = { modifier = qpq_consecrated_ruler_modifier years = 20 }
    if = {
        limit = { qpq_uses_legitimacy_trigger = yes }
        add_legitimacy = 25
    }
}
""",
  exposed="""
scope:qpq_payer = {
    every_relation = {
        type = rival
        add_opinion = { target = scope:qpq_payer modifier = qpq_bought_legitimacy_opinion }
    }
}
""")

K(key="temple_patronage", cat="D3", group="church_favours", secret="rites", icon="religious",
  icategory="interaction_category_religion",
  name="Temple Patronage",
  ask="have the clergy back [qpq_payer.GetShortUIName] against [qpq_target.GetTitledFirstName]",
  desc="Endow a temple whose clergy then speak for you against a rival. Mild if it comes out, since patronage was expected; hidden strings sting.",
  payer_base=1, agent_base=1, mode="perform", term=12, effort=0,
  rel="""
scope:recipient = {
    NOT = { this = scope:actor }
    faith = scope:actor.faith
    OR = {
        is_clergy = yes
        government_has_flag = government_is_theocracy
    }
}
NOT = { exists = scope:actor.faith.religious_head }
""",
  pick=PICK_RIVALS,
  target_valid="exists = scope:secondary_recipient",
  can_perform="always = yes",
  perform="""
scope:qpq_payer = { add_character_modifier = { modifier = qpq_clerical_backing_modifier years = 10 } }
scope:qpq_target = { add_character_modifier = { modifier = qpq_clerical_denunciation_modifier years = 5 } }
""",
  exposed="scope:qpq_payer = { add_piety = minor_piety_loss }")

###############################################################################
# CATALOGUE G: in time of war. A war is named by the leader of the other side: the deed's target character.
# At sealing the deed finds that very war, and keeps it on the deal (var:qpq_target_war) where it must watch it.
###############################################################################

# The leader of the other side in each war the proposer is fighting (for deeds that join or keep out of it)
PICK_WARS_ACTOR_FIGHTS = """
scope:actor = {
    every_character_war = {
        if = {
            limit = { is_attacker = scope:actor }
            primary_defender = { add_to_list = characters }
        }
        else = {
            primary_attacker = { add_to_list = characters }
        }
    }
}
"""
def _find_war(who):
    """Story context: save the war that `who` fights against scope:qpq_target as scope:qpq_target_war."""
    return """
%s = {
    random_character_war = {
        limit = { qpq_war_foe_trigger = { WHO = %s FOE = scope:qpq_target } }
        save_scope_as = qpq_target_war
    }
}
""" % (who, who)


K(key="join_war", cat="G", group="wartime", secret="conquest", icon="declare_war_interaction",
  name="Join the War",
  ask="join [qpq_payer.GetShortUINamePossessive] war against [qpq_target.GetTitledFirstName] and see it through",
  desc="They join your [war|E] against a named enemy, on your side, and stay in it to the end. They weigh how much they want that fight and whether your side, with them in it, would win. Leaving early is a breach; the gold due on delivery is paid when the war is over and they are still in it.",
  payer_base=0, agent_base=1, payer_ctx=True, agent_ctx=True, term=60, effort=20, mode="restraint",
  rel="scope:actor = { is_at_war = yes }", pick=PICK_WARS_ACTOR_FIGHTS,
  target_valid="""
NOT = { scope:secondary_recipient = scope:recipient }
scope:recipient = {
    is_landed = yes
    NOT = { is_at_war_with = scope:actor }
    NOT = { top_liege = scope:secondary_recipient.top_liege }
}
scope:actor = {
    any_character_war = {
        qpq_war_foe_trigger = { WHO = scope:actor FOE = scope:secondary_recipient }
        NOT = { is_participant = scope:recipient }
    }
}
""",
  demand=[("10", "scope:recipient = { has_relation_rival = scope:secondary_recipient }", "QPQ_REASON_HATES_TARGET"),
          ("-15", "scope:recipient = { has_trait = craven }", "QPQ_REASON_CRAVEN_WAR")],
  on_seal=_find_war("scope:qpq_payer") + """
scope:qpq_target_war ?= {
    if = {
        limit = { NOT = { is_participant = scope:qpq_agent } }
        if = {
            limit = { is_attacker = scope:qpq_payer }
            add_attacker = scope:qpq_agent
        }
        else = {
            add_defender = scope:qpq_agent
        }
        scope:qpq_story ?= {
            set_variable = { name = qpq_target_war value = scope:qpq_target_war }
            set_variable = qpq_war_joined
        }
    }
}
""",
  # Seen through: the war is over and they never left it
  deliver="""
has_variable = qpq_war_joined
NOT = { exists = var:qpq_target_war }
""",
  breach="""
exists = var:qpq_target_war
var:qpq_target_war = { NOT = { is_participant = scope:qpq_agent } }
""",
  # They could not be brought into it after all: nobody is at fault
  invalid="NOT = { has_variable = qpq_war_joined }",
  exposed="")

K(key="stay_out", cat="G", group="wartime", secret="betrayal", icon="icon_combat",
  name="Stay Out of the War",
  ask="stay out of [qpq_payer.GetShortUINamePossessive] war against [qpq_target.GetTitledFirstName]",
  desc="They promise not to join a [war|E] you are fighting against a named enemy, until it ends or the deadline passes. The more they want to fight you, and the better the enemy's chances with them, the dearer the promise. Joining it after all is a breach. If it comes out, the enemy knows who sold them out.",
  payer_base=0, agent_base=1, payer_ctx=False, agent_ctx=False, term=36, effort=10, mode="restraint",
  rel="scope:actor = { is_at_war = yes }", pick=PICK_WARS_ACTOR_FIGHTS,
  target_valid="""
NOT = { scope:secondary_recipient = scope:recipient }
scope:actor = {
    any_character_war = {
        qpq_war_foe_trigger = { WHO = scope:actor FOE = scope:secondary_recipient }
        NOT = { is_participant = scope:recipient }
    }
}
""",
  demand=[("-30", "scope:recipient = { is_allied_to = scope:secondary_recipient }", "QPQ_REASON_ALLIED_TO_TARGET")],
  on_seal=_find_war("scope:qpq_payer") + """
scope:qpq_story ?= {
    if = {
        limit = { exists = scope:qpq_target_war }
        set_variable = { name = qpq_target_war value = scope:qpq_target_war }
        set_variable = qpq_war_watched
    }
}
""",
  # Kept: the war ended without them
  deliver="""
has_variable = qpq_war_watched
NOT = { exists = var:qpq_target_war }
""",
  breach="""
exists = var:qpq_target_war
var:qpq_target_war = { is_participant = scope:qpq_agent }
""",
  invalid="NOT = { has_variable = qpq_war_watched }",
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_betrayed_me_opinion opinion = -20 }
    }
}
""")

# An AI at war deals too. Root: the AI proposing (the payer, scope:actor once it proposes). Each finder names the
# one it puts the deal to (scope:recipient) and the war's other leader (scope:secondary_recipient).
_AI_OWN_WAR = """
random_character_war = {
    limit = {
        OR = {
            primary_attacker = root
            primary_defender = root
        }
        %s
    }
    save_scope_as = qpq_ai_war
    if = {
        limit = { primary_attacker = root }
        primary_defender = { save_scope_as = qpq_ai_foe }
    }
    else = {
        primary_attacker = { save_scope_as = qpq_ai_foe }
    }
}
"""
_KIND_BY_KEY = {k["key"]: k for k in KINDS}
# Not winning: hire a neighbour who has no love for the enemy and no quarrel with you
_KIND_BY_KEY["join_war"]["ai"] = dict(weight=5, valid="""
is_at_war = yes
gold >= 50
any_character_war = {
    OR = {
        primary_attacker = root
        primary_defender = root
    }
    NOT = { qpq_war_side_winning_trigger = { WHO = root SCORE = 25 } }
}
""", find=_AI_OWN_WAR % "NOT = { qpq_war_side_winning_trigger = { WHO = root SCORE = 25 } }" + """
if = {
    limit = { exists = scope:qpq_ai_foe }
    scope:qpq_ai_foe = { save_scope_as = secondary_recipient }
    ordered_neighboring_and_across_water_top_liege_realm_owner = {
        limit = {
            NOT = { this = scope:secondary_recipient }
            is_at_war = no
            NOT = { top_liege = scope:secondary_recipient.top_liege }
            NOT = { is_allied_to = scope:secondary_recipient }
            NOT = { is_close_family_of = scope:secondary_recipient }
            opinion = { target = root value >= -10 }
        }
        order_by = qpq_ai_hired_sword_value
        save_scope_as = recipient
    }
}
""")
# Keep the enemy's friends at home: an ally of the enemy leader who has not come in yet
_KIND_BY_KEY["stay_out"]["ai"] = dict(weight=3, valid="""
is_at_war = yes
gold >= 50
any_character_war = {
    OR = {
        primary_attacker = root
        primary_defender = root
    }
}
""", find=_AI_OWN_WAR % "" + """
if = {
    limit = { exists = scope:qpq_ai_foe }
    scope:qpq_ai_foe = {
        save_scope_as = secondary_recipient
        ordered_ally = {
            limit = {
                NOT = { this = root }
                NOT = { is_at_war_with = root }
                NOT = { scope:qpq_ai_war = { is_participant = prev } }
            }
            order_by = max_military_strength
            save_scope_as = recipient
        }
    }
}
""")
###############################################################################
# CATALOGUE F: tribute, between suzerains and tributaries
###############################################################################

def _tribute_step(who, frm, to):
    return """
    else_if = {
        limit = { vassal_contract_obligation_level:default_tributary_taxes = %d }
        tributary_contract_set_obligation_level = { type = default_tributary_taxes level = %d }
    }""" % (frm, to)


TRIBUTE_UP = """
scope:qpq_agent = {
    if = {
        limit = { is_tributary_of = scope:qpq_payer }
        if = {
            limit = { vassal_contract_obligation_level:default_tributary_taxes = 0 }
            tributary_contract_set_obligation_level = { type = default_tributary_taxes level = 1 }
        }""" + _tribute_step("agent", 1, 2) + """
    }
}
"""

TRIBUTE_DOWN = """
scope:qpq_payer = {
    if = {
        limit = { is_tributary_of = scope:qpq_agent }
        if = {
            limit = { vassal_contract_obligation_level:default_tributary_taxes = 2 }
            tributary_contract_set_obligation_level = { type = default_tributary_taxes level = 1 }
        }""" + _tribute_step("payer", 1, 0) + """
    }
}
"""

K(key="heavier_tribute", cat="F", group="tribute", secret="bribery", icon="demand_tributary_interaction",
  name="Heavier Tribute",
  ask="raise the tribute paid to [qpq_payer.GetShortUIName]",
  desc="Your [tributary|E] raises the [tribute|E] it pays you by one step, and keeps paying it.",
  payer_base=0, agent_base=0, target="none", term=12, effort=25,
  rel="scope:recipient = { is_tributary_of = scope:actor }",
  valid=[("qpq_valid_tribute_can_rise", "scope:recipient = { tributary_contract_obligation_level_can_be_increased = default_tributary_taxes }")],
  on_seal=TRIBUTE_UP, deliver="always = yes", exposed="")

K(key="lighter_tribute", cat="F", group="tribute", secret="bribery", icon="cease_paying_tributary_interaction",
  name="Lighter Tribute",
  ask="lower the tribute [qpq_payer.GetShortUIName] pays",
  desc="Your [suzerain|E] lowers the [tribute|E] you pay by one step.",
  payer_base=0, agent_base=0, target="none", term=12, effort=20,
  rel="scope:actor = { is_tributary_of = scope:recipient }",
  valid=[("qpq_valid_tribute_can_fall", "scope:actor = { tributary_contract_obligation_level_can_be_decreased = default_tributary_taxes }")],
  on_seal=TRIBUTE_DOWN, deliver="always = yes", exposed="")

K(key="bought_freedom", cat="F", group="tribute", secret="bribery", icon="release_tributary_interaction",
  name="Bought Freedom",
  ask="release [qpq_payer.GetShortUIName] from tribute",
  desc="Your [suzerain|E] releases you from [tribute|E], and a five-year [truce|E] follows. A suzerain who sells a tributary its freedom is thought the poorer for it.",
  payer_base=0, agent_base=1, target="none", term=12, effort=40,
  rel="scope:actor = { is_tributary_of = scope:recipient }",
  on_seal="""
scope:qpq_payer = {
    if = {
        limit = { is_tributary_of = scope:qpq_agent }
        end_tributary = yes
        add_truce_both_ways = {
            character = scope:qpq_agent
            years = 5
            override = yes
            name = TRUCE_TRIBUTARY_STOPPED
        }
        add_opinion = { target = scope:qpq_agent modifier = tributary_released_opinion opinion = 25 }
    }
}
""",
  deliver="always = yes", exposed="")

# Vanilla's -200 for a demand with nothing behind it
TRIBUTE_NO_CB = "NOT = { scope:recipient = { has_government = herder_government } } scope:actor = { NOT = { has_any_cb_on = scope:recipient } }"

K(key="accept_the_yoke", cat="F", group="tribute", secret="bribery", icon="become_tributary_interaction",
  name="Become a Tributary",
  ask="become [qpq_payer.GetShortUINamePossessive] tributary",
  desc="An [independent_ruler|E] becomes your [tributary|E]: they pay you [tribute|E] and keep their realm, and do not become your [vassal|E]. They weigh it as they would a demand for tribute: they want a [casus_belli|E] behind it, though what you pay or do in return can make up for most of one, and a king or emperor is very hard to persuade.",
  payer_base=0, agent_base=1, target="none", term=12, effort=30,
  # the panel settles this once both legs are priced: see qpq_ui_deal_finish_effect
  relief="qpq_tribute_paid_relief_value", relief_when=TRIBUTE_NO_CB, relief_max="qpq_tribute_paid_relief_max_value",
  rel="""
scope:actor = {
    is_landed = yes
    is_independent_ruler = yes
}
scope:recipient = {
    is_landed = yes
    is_independent_ruler = yes
    is_tributary = no
    NOT = { this = scope:actor }
}
""",
  valid=[("qpq_valid_can_be_tributary", "scope:recipient = { can_be_tributary_of = scope:actor }")],
  # demand_tributary_interaction, as far as it applies outside the nomad, Mandala and hegemon rules
  demand=[("qpq_tribute_boldness_value", "NOT = { scope:recipient.ai_boldness = 0 }", "QPQ_REASON_TRIB_BOLD"),
          ("qpq_tribute_greed_value", "scope:recipient.ai_greed > 0", "QPQ_REASON_TRIB_GREED"),
          ("40", "scope:recipient = { is_obedient_to = scope:actor }", "QPQ_REASON_TRIB_OBEDIENT"),
          ("dominant_negative_ai_value", TRIBUTE_NO_CB, "QPQ_REASON_TRIB_NO_CB"),
          # the one change from vanilla: a demand with nothing behind it is empty, and payment puts something behind it
          ("qpq_tribute_paid_relief_value", TRIBUTE_NO_CB, "QPQ_REASON_TRIB_PAID"),
          ("qpq_tribute_demand_threat_value", "always = yes", "QPQ_REASON_TRIB_POWER"),
          ("-100", "scope:recipient = { highest_held_title_tier = tier_kingdom }", "QPQ_REASON_TRIB_RANK"),
          ("-200", "scope:recipient = { highest_held_title_tier >= tier_empire }", "QPQ_REASON_TRIB_RANK"),
          ("-100", "scope:recipient = { has_relation_rival = scope:actor NOT = { has_relation_nemesis = scope:actor } }", "QPQ_REASON_TRIB_RIVAL"),
          ("-200", "scope:recipient = { has_relation_nemesis = scope:actor }", "QPQ_REASON_TRIB_NEMESIS"),
          ("10", "scope:recipient.dynasty ?= scope:actor.dynasty", "QPQ_REASON_TRIB_DYNASTY"),
          ("qpq_tribute_foreign_faith_value", "NOT = { scope:actor.faith = scope:recipient.faith } scope:actor = { NOT = { rite = { rite_has_doctrine = doctrine_pluralism_pluralistic } } }", "QPQ_REASON_TRIB_FAITH"),
          ("30", "scope:recipient = { NOT = { any_neighboring_top_suzerain_realm_owner = { this != scope:actor } } NOT = { any_realm_county = { is_coastal_county = yes } } }", "QPQ_REASON_TRIB_ENCIRCLED"),
          ("qpq_tribute_foreign_culture_value", "scope:actor = { NOT = { has_same_culture_as = scope:recipient } culture = { cultural_acceptance = { target = scope:recipient.culture value < 50 } } }", "QPQ_REASON_TRIB_CULTURE"),
          ("5", "scope:actor = { knows_language_of_culture = scope:recipient.culture }", "QPQ_REASON_TRIB_LANGUAGE"),
          ("-15", "scope:actor = { has_legitimacy_flag = slightly_reduced_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("-25", "scope:actor = { has_legitimacy_flag = reduced_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("-50", "scope:actor = { has_legitimacy_flag = very_reduced_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("-75", "scope:actor = { has_legitimacy_flag = massively_reduced_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("25", "scope:actor = { has_legitimacy_flag = increased_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("50", "scope:actor = { has_legitimacy_flag = very_increased_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY"),
          ("75", "scope:actor = { has_legitimacy_flag = extra_increased_tributarization_acceptance }", "QPQ_REASON_TRIB_LEGITIMACY")],
  # to the one who would be suzerain: become_tributary_interaction
  worth="""
value = 50
if = {
    limit = { scope:recipient = { tier_difference = { target = scope:actor value > 1 } } }
    add = 20
}
if = {
    limit = { scope:recipient = { NOT = { any_neighboring_top_liege_realm_owner = { this = scope:actor } } } }
    add = -15
}
if = {
    limit = { scope:actor = { has_relation_rival = scope:recipient NOT = { has_relation_nemesis = scope:recipient } } }
    add = -10
}
if = {
    limit = { scope:actor = { has_relation_nemesis = scope:recipient } }
    add = -100
}
if = {
    limit = { scope:actor.dynasty ?= scope:recipient.dynasty }
    add = 10
}
if = {
    limit = { scope:recipient = { has_variable = conqueror } }
    add = -1000
}
add = {
    value = scope:actor.ai_greed
    multiply = 0.75
    min = 0
}
""",
  on_seal="""
if = {
    limit = {
        scope:qpq_agent = {
            is_tributary = no
            can_be_tributary_of = scope:qpq_payer
        }
    }
    start_tributary_interaction_effect = { TRIBUTARY = scope:qpq_agent SUZERAIN = scope:qpq_payer }
}
""",
  deliver="always = yes", exposed="")

K(key="cast_off_the_yoke", cat="F", group="tribute", secret="betrayal", icon="cease_paying_tributary_interaction",
  name="Reject a Suzerain",
  ask="reject [qpq_target.GetTitledFirstName] as their suzerain and stop paying tribute",
  desc="Pay another ruler's [tributary|E] to reject their [suzerain|E] and stop paying [tribute|E]. They weigh it as they would ceasing tribute on their own, so a tributary afraid of its suzerain will want a great deal. If it comes out, the suzerain knows whose gold it was.",
  payer_base=2, agent_base=2, target="derived", derive="scope:recipient.suzerain", term=12, effort=25,
  rel="""
scope:actor = { is_landed = yes }
scope:recipient = {
    is_tributary = yes
    exists = suzerain
    NOT = { this = scope:actor }
    NOT = { suzerain = scope:actor }
}
""",
  # cease_paying_tribute_interaction's ai_will_do, as far as it applies outside the nomad and Mandala rules
  base_ask=-25,
  demand=[("qpq_tribute_cease_threat_value", "always = yes", "QPQ_REASON_TRIB_POWER"),
          ("30", "scope:recipient = { has_relation_rival = scope:recipient.suzerain NOT = { has_relation_nemesis = scope:recipient.suzerain } }", "QPQ_REASON_TRIB_RIVAL"),
          ("50", "scope:recipient = { has_relation_nemesis = scope:recipient.suzerain }", "QPQ_REASON_TRIB_NEMESIS"),
          ("25", "scope:recipient.faith = { NOT = { faith_is_in_same_rf = { FAITH = scope:recipient.suzerain.faith } } }", "QPQ_REASON_TRIB_OTHER_RELIGION"),
          ("-100", "scope:recipient = { any_memory = { has_memory_type = suzerain_defended_me_in_war has_memory_participant = scope:recipient.suzerain memory_age_years < 10 } }", "QPQ_REASON_TRIB_DEFENDED")],
  on_seal="""
scope:qpq_agent = {
    if = {
        limit = { is_tributary = yes }
        end_tributary = yes
    }
}
if = {
    limit = { exists = scope:qpq_target }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = tributary_ceased_payments_opinion }
    }
}
""",
  deliver="always = yes", invalid=TARGET_GONE_INVALID,
  exposed="""
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -40 }
    }
}
""")

###############################################################################
# The carrier: a deal whose side asks for no deed, only goods. Not offered as an Ask in the panel
# (carrier=True); it exists so that "I give gold, you give land" has a deal to live in.
###############################################################################

K(key="barter", cat="E", group="favours", secret="exchange", icon="icon_gold", carrier=True,
  name="Exchange of Goods",
  ask="hand over what was agreed, and nothing more",
  desc="No deed on either side: only goods change hands, [gold|E] for land, favours for favours.",
  payer_base=0, agent_base=0, target="none", term=1, effort=0, mode="restraint",
  rel="NOT = { scope:actor = scope:recipient }",
  # done at the next monthly check, unless something in it lasts: then it holds until the deadline
  deliver="NOR = { has_variable = qpq_offer_office has_variable = qpq_offer_restraint has_variable = qpq_gave_arms }",
  exposed="")


GROUPS = [
    ("war", "Commission a war"),
    ("favours", "Ask a favour"),
    ("family", "Family and succession"),
    ("blood", "Blood and abduction"),
    ("shadows", "Factions and spies"),
    ("abroad", "Betrayal abroad"),
    ("church_favours", "Favours of the faith"),
    ("church_weapons", "The faith as a weapon"),
    ("tribute", "Tribute and overlordship"),
    ("wartime", "In time of war"),
]

SECRET_CATEGORIES = {
    # key: (vanilla icon category, display name)
    "conquest": ("civil", "War"),
    "bribery": ("civil", "Bribery"),
    "faction": ("civil", "Conspiracy"),
    "espionage": ("civil", "Espionage"),
    "murder": ("murder", "Murder"),
    "abduction": ("murder", "Abduction"),
    "dynastic": ("civil", "Dynastic"),
    "betrayal": ("civil", "Betrayal"),
    "simony": ("religious", "Simony"),
    "rites": ("religious", "Sacred Rites"),
    "exchange": ("civil", "Exchange"),
}

TIER_NAMES = {0: "Charter", 1: "Discreet", 2: "Unseemly", 3: "Scandalous", 4: "Disgraceful", 5: "Damnable"}
