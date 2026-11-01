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

ALL_OFFERS = ["gold", "on_delivery", "split", "stipend", "land", "claim", "office", "marriage",
              "release_hook", "my_word", "secret", "contract", "succession", "clemency", "arms",
              "artifact", "church", "restraint", "hook", "charter"]
NO_CLAIM = [o for o in ALL_OFFERS if o != "claim"]
AGENT_DEMANDS = ["gold", "on_delivery", "split", "stipend", "land", "office", "contract", "release_hook",
                 "my_word", "clemency", "artifact", "church"]

KINDS = []


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
  desc="Publicly charter a vassal to take land from a named neighbour. They may use the Crown Mandate casus belli, borrowing your de jure right where they have no claim of their own.",
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
random_vassal = {
    limit = {
        is_landed = yes
        is_at_war = no
        any_neighboring_and_across_water_top_liege_realm_owner = {
            NOT = { top_liege = root.top_liege }
        }
    }
    save_scope_as = recipient
    random_neighboring_and_across_water_top_liege_realm_owner = {
        limit = { NOT = { top_liege = root.top_liege } }
        save_scope_as = secondary_recipient
    }
}
"""))

K(key="sanctioned_conquest", licence=True, cat="A", group="war", secret="conquest", icon="declare_war_interaction",
  name="Sanctioned Conquest",
  ask="privately take land from [qpq_target.GetTitledFirstName]",
  desc="Privately back a vassal's conquest of a named target. They use their own casus belli, a claim you fabricate as part of the payment, or the Pact War you license.",
  payer_base=1, agent_base=1, claim_ok=True, term=96, effort=20,
  rel=REL_VASSAL, pick=PICK_NEIGHBOUR_RULERS_OF_RECIPIENT,
  target_valid="""
scope:secondary_recipient = {
    is_landed = yes
    NOT = { top_liege = scope:actor.top_liege }
}
""",
  demand=[("10", "scope:recipient = { has_trait = ambitious }", "QPQ_REASON_AMBITIOUS_CONQUEST"),
          ("-15", "scope:recipient = { has_trait = craven }", "QPQ_REASON_CRAVEN_WAR")],
  deliver=AGENT_BEAT_TARGET, invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE, attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed="""
# The target's liege treats the war as yours; truce-breaker by proxy if you had a truce
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_payer modifier = qpq_betrayed_me_opinion opinion = -30 }
    }
    if = {
        limit = { scope:qpq_payer = { has_truce = scope:qpq_target } }
        scope:qpq_payer = { add_prestige = major_prestige_loss }
    }
}
""",
  ai=dict(weight=8, valid="""
is_landed = yes
any_vassal = { is_landed = yes is_ai = yes }
""", find="""
random_vassal = {
    limit = {
        is_landed = yes
        is_at_war = no
        any_neighboring_and_across_water_top_liege_realm_owner = {
            NOT = { top_liege = root.top_liege }
        }
    }
    save_scope_as = recipient
    random_neighboring_and_across_water_top_liege_realm_owner = {
        limit = { NOT = { top_liege = root.top_liege } }
        save_scope_as = secondary_recipient
    }
}
"""))

K(key="marcher_charge", cat="A", group="war", secret="conquest", icon="military_strength",
  name="Marcher Charge",
  ask="hold the border against [qpq_target.GetTitledFirstName]",
  desc="Hold a named border: keep levies raised and defend against a named enemy for the whole term. Failure is a breach, not a scandal.",
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
  ai=dict(weight=5, valid="is_landed = yes any_vassal = { is_landed = yes is_ai = yes }", find="""
random_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        NOT = { top_liege = root.top_liege }
        OR = {
            has_relation_rival = root
            faith = { faith_hostility_level = { target = root.faith value >= faith_hostile_level } }
        }
    }
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    random_vassal = {
        limit = {
            is_landed = yes
            any_neighboring_and_across_water_top_liege_realm_owner = { this = scope:secondary_recipient }
        }
        save_scope_as = recipient
    }
}
"""))

K(key="holy_sponsorship", cat="A", group="favours", secret="conquest", icon="religious",
  name="Holy Sponsorship",
  ask="convert [qpq_target_title.GetName] to [qpq_payer.GetFaith.GetName]",
  desc="Sponsor a vassal to bring a named county into your faith. Mercenary piety looks bad if it comes out.",
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

K(key="development_charter", cat="A", group="favours", secret="bribery", icon="county_modifier_development_positive",
  name="Development Charter",
  ask="raise the development of [qpq_target_title.GetName]",
  desc="Pay a vassal to build up one of their counties, five levels of development within the term.",
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
  desc="Buy an elector's vote for your chosen heir. If it comes out, the vote stands, but the other electors remember it was bought.",
  echo="The 1257 double election, where both candidates spent heavily on the electors.",
  payer_base=2, agent_base=2, term=120, mode="restraint", effort=0,
  rel=REL_VASSAL + """
exists = scope:actor.primary_title
scope:actor.primary_title = { any_elector = { this = scope:recipient } }
""",
  pick="""
scope:actor = {
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
""")

K(key="loyal_mole", cat="A", group="shadows", secret="faction", icon="faction",
  name="The Loyal Mole",
  ask="join a faction against [qpq_payer.GetShortUIName] and sabotage it",
  desc="A vassal joins a faction against you, then sabotages it or walks out at the critical moment.",
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
  desc="A vassal starts a revolt on purpose so you can crush and revoke everyone who joins.",
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

K(key="licensed_feud", licence=True, cat="A", group="war", secret="conquest", icon="declare_war_interaction",
  name="Licensed Feud",
  ask="wage war on fellow vassal [qpq_target.GetTitledFirstName], with your quiet blessing",
  desc="You quietly sanction their war on a fellow vassal despite crown authority. They get a Pact War against the target and a favour on you to get it past the law.",
  payer_base=3, agent_base=3, term=72, effort=15,
  rel=REL_VASSAL, pick=PICK_FELLOW_VASSALS,
  target_valid="scope:secondary_recipient = { liege ?= scope:actor is_landed = yes }",
  demand=[("15", "scope:recipient = { has_relation_rival = scope:secondary_recipient }", "QPQ_REASON_HATES_TARGET")],
  deliver=AGENT_BEAT_TARGET, invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE + """
scope:qpq_agent = { add_hook = { type = favor_hook target = scope:qpq_payer } }
""",
  attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed="""
scope:qpq_payer = {
    every_vassal = {
        limit = {
            NOT = { this = scope:qpq_agent }
            NOT = { this = scope:qpq_target }
        }
        add_opinion = { target = scope:qpq_payer modifier = qpq_plays_favourites_opinion }
    }
}
if = {
    limit = { scope:qpq_target = { is_alive = yes } }
    scope:qpq_target = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_avenge_perfidy_opinion }
    }
}
""",
  ai=dict(weight=4, valid="is_landed = yes any_vassal = { count >= 2 is_landed = yes }", find="""
random_vassal = {
    limit = {
        is_landed = yes
        is_ai = yes
        any_relation = { type = rival liege ?= root is_landed = yes }
    }
    save_scope_as = recipient
    random_relation = {
        type = rival
        limit = { liege ?= root is_landed = yes }
        save_scope_as = secondary_recipient
    }
}
"""))

K(key="dossier", cat="A", group="shadows", secret="espionage", icon="secret",
  name="Dossier",
  ask="find or plant dirt on [qpq_target.GetTitledFirstName]",
  desc="Find or plant secrets on a rival vassal and hand them over. If it comes out, the target's opinion collapses and the spy is branded an informer.",
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
  ai=dict(weight=6, valid="is_landed = yes any_vassal = { count >= 2 }", find="""
random_relation = {
    type = rival
    limit = { liege ?= root }
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
  desc="Kill a rival vassal, courtier or foreign figure. If it comes out, both of you carry the murder and the victim's house turns hostile.",
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
  ai=dict(weight=4, valid="""
is_landed = yes
any_relation = { type = rival }
OR = { has_trait = deceitful has_trait = callous has_trait = sadistic has_trait = vengeful has_trait = schemer }
""", find="""
random_relation = {
    type = rival
    limit = { is_alive = yes }
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    random_vassal = {
        limit = {
            is_ai = yes
            intrigue >= 10
            NOT = { this = scope:secondary_recipient }
            NOT = { is_close_family_of = scope:secondary_recipient }
        }
        save_scope_as = recipient
    }
}
"""))

K(key="heir_question", cat="A", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="The Heir Question",
  ask="remove [qpq_target.GetTitledFirstName], [qpq_payer.GetShortUINamePossessive] own heir",
  desc="Remove your heir or a disfavoured child. If it comes out: kinslayer, a realm-wide opinion hit, and your next heir's opinion of you collapses.",
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
  desc="Kidnap a named character, such as a rival's child as a hostage or ward.",
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

K(key="dispossession", cat="A", group="shadows", secret="dynastic", icon="revoke_title_interaction",
  icategory="interaction_category_vassal",
  name="Dispossession",
  ask="imprison or strip [qpq_target.GetTitledFirstName], their own vassal, and absorb the tyranny",
  desc="Have a vassal revoke or imprison one of their own sub-vassals that you want gone, absorbing the tyranny themselves.",
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
  name="The Cloister",
  ask="see [qpq_target.GetTitledFirstName] take vows",
  desc="They, or an awkward relative, take vows. If the vassal themself takes vows, they abdicate to their heir.",
  echo="Abdications into monasteries were a standard way to clear a claimant.",
  payer_base=2, agent_base=2, mode="perform", term=24, effort=15,
  rel=REL_VASSAL,
  pick="""
scope:recipient = {
    add_to_list = characters
    every_close_family_member = {
        limit = {
            is_adult = yes
            NOT = { has_trait = devoted }
        }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { has_trait = devoted } NOT = { this = scope:actor } }",
  demand=[("-25", "scope:secondary_recipient = scope:recipient", "QPQ_REASON_MUST_ABDICATE"),
          ("10", "scope:recipient = { has_trait = zealous }", "QPQ_REASON_ZEALOUS_VOWS")],
  can_perform="scope:qpq_target = { is_alive = yes NOT = { has_trait = devoted } }",
  invalid=TARGET_DEAD,
  perform="""
if = {
    limit = { scope:qpq_target = scope:qpq_agent }
    if = {
        limit = { exists = scope:qpq_agent.primary_heir }
        scope:qpq_payer_secret ?= { set_variable = { name = qpq_successor value = scope:qpq_agent.primary_heir } }
    }
    scope:qpq_agent = { depose = yes }
}
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

K(key="marriage_by_command", cat="A", group="family", secret="dynastic", icon="marriage",
  name="Marriage by Command",
  ask="set aside their spouse and marry [qpq_target.GetTitledFirstName]",
  desc="A vassal sets aside a spouse and marries the person you choose.",
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

K(key="hand_over", cat="A", group="favours", secret="abduction", icon="prison",
  name="Hand-Over",
  ask="surrender [qpq_target.GetTitledFirstName] to [qpq_payer.GetShortUIName]",
  desc="Surrender a prisoner, hostage or a claimant they shelter. Tier III if the person is kin or a guest.",
  payer_base=1, agent_base=1, mode="perform", term=12, effort=5,
  rel=REL_VASSAL,
  pick="""
scope:recipient = {
    every_prisoner = { add_to_list = characters }
    every_courtier = {
        limit = {
            OR = {
                is_hostage = yes
                any_claim = { holder ?= scope:actor }
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
        exists = scope:secondary_recipient
        scope:secondary_recipient = {
            OR = {
                is_close_family_of = scope:recipient
                is_pool_guest_of = scope:recipient
                is_foreign_court_guest_of = scope:recipient
            }
        }
    }
    add = 2
}
""",
  payer_adj="""
if = {
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
  perform="""
if = {
    limit = { scope:qpq_target = { is_imprisoned = yes } }
    qpq_hand_prisoner_to_payer_effect = yes
}
else = {
    scope:qpq_payer = { add_courtier = scope:qpq_target }
}
""",
  exposed="""
scope:qpq_agent = {
    every_courtier = {
        add_opinion = { target = scope:qpq_agent modifier = qpq_betrayed_a_guest_opinion }
    }
}
""")

K(key="hand_over_artifact", cat="A", group="favours", secret="bribery", icon="artifact",
  name="Hand-Over: Treasure",
  ask="hand [qpq_target_artifact.GetName] over to [qpq_payer.GetShortUIName]",
  desc="Surrender a named artifact from their treasury.",
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

K(key="renunciation", cat="A", group="favours", secret="dynastic", icon="claim",
  name="Renunciation",
  ask="renounce their claim on [qpq_target_title.GetName]",
  desc="Renounce a claim on a title you hold or want.",
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
  desc="Pay someone who holds your secrets never to expose them. The cover-up is worse: if the original secret comes out later, its tier rises by one.",
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

K(key="price_of_loyalty", cat="B", group="favours", secret="bribery", icon="gold",
  icategory="interaction_category_vassal", initiator="agent", offers=AGENT_DEMANDS,
  name="Price of Loyalty",
  ask="answer [qpq_payer.GetShortUINamePossessive] call to arms and stay loyal through the war",
  desc="A vassal demands a title or gold before answering your call to arms. Refusing is a public slight; if a payment comes out, other vassals raise their own prices.",
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
  desc="Ask your liege to look away while you attack a fellow vassal. You get a Pact War against them; your liege promises not to intervene.",
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
  ai=dict(weight=6, valid="""
is_landed = yes
exists = liege
any_relation = { type = rival liege ?= root.liege is_landed = yes }
""", find="""
liege = { save_scope_as = recipient }
random_relation = {
    type = rival
    limit = { liege ?= root.liege is_landed = yes }
    save_scope_as = secondary_recipient
}
"""))

K(key="clemency_bargain", cat="B", group="shadows", secret="bribery", icon="prison",
  icategory="interaction_category_vassal",
  name="Clemency Bargain",
  ask="pardon [qpq_payer.GetShortUIName] in exchange for secrets on others",
  desc="A vassal trades secrets on others for a pardon of their own crime. If it comes out, the people they informed on turn hostile.",
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

K(key="electoral_capitulation", cat="B", group="family", secret="bribery", icon="heir",
  icategory="interaction_category_vassal", initiator="agent", offers=AGENT_DEMANDS,
  name="Electoral Capitulation",
  ask="vote for [qpq_target.GetTitledFirstName], [qpq_payer.GetShortUINamePossessive] candidate",
  desc="An elector trades their vote for contract concessions. If it comes out, the other electors demand the same terms.",
  payer_base=1, agent_base=2, term=120, mode="restraint", effort=0,
  rel="""
exists = scope:recipient.primary_title
scope:recipient.primary_title = { any_elector = { this = scope:actor } }
NOT = { scope:actor = scope:recipient }
""",
  pick="""
scope:recipient = {
    add_to_list = characters
    every_close_family_member = {
        limit = { is_adult = yes }
        add_to_list = characters
    }
}
""",
  target_valid="scope:secondary_recipient = { NOT = { this = scope:actor } }",
  on_seal="""
scope:qpq_agent = {
    add_opinion = { target = scope:qpq_target modifier = qpq_bought_vote_opinion }
    recalculate_succession_election_vote = yes
}
""",
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
            add_opinion = { target = scope:qpq_payer modifier = qpq_precedent_opinion }
        }
    }
}
""",
  ai=dict(weight=3, valid="""
exists = liege
exists = liege.primary_title
liege.primary_title = { any_elector = { this = root } }
OR = { has_trait = greedy has_trait = ambitious }
""", find="""
liege = { save_scope_as = recipient }
if = {
    limit = { exists = liege.primary_heir }
    liege.primary_heir = { save_scope_as = secondary_recipient }
}
"""))

K(key="mutual_defense_league", cat="B", group="shadows", secret="faction", icon="alliance",
  icategory="interaction_category_vassal",
  name="Mutual Defense League",
  ask="stand with [qpq_payer.GetShortUIName] if [qpq_target.GetTitledFirstName] revokes from either of you",
  desc="Two vassals swear to resist revocations together. Tier III towards the liege, IV if armed. If it comes out, the liege may imprison them as conspirators.",
  payer_base=3, agent_base=3, target="derived", derive="scope:actor.liege", mode="restraint", term=120, effort=10,
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
    random_vassal = {
        limit = {
            NOT = { this = root }
            is_landed = yes
            opinion = { target = scope:qpq_ai_liege value <= 0 }
        }
        save_scope_as = recipient
    }
}
"""))

K(key="faction_pledge", cat="B", group="shadows", secret="faction", icon="faction",
  icategory="interaction_category_vassal",
  name="Faction Pledge",
  ask="stand in the faction against [qpq_target.GetTitledFirstName] until it wins, and share the spoils",
  desc="Vassals agree to split the spoils of a successful faction war. If it comes out, the liege gains grounds to imprison them, and their allies fall away.",
  payer_base=3, agent_base=3, target="derived", derive="scope:actor.liege", term=96, effort=10,
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

K(key="title_swap", cat="B", group="family", secret="dynastic", icon="grant_titles_interaction",
  icategory="interaction_category_vassal",
  name="Title Swap",
  ask="cede [qpq_target_title.GetName] to [qpq_payer.GetShortUIName]",
  desc="Vassals exchange counties. Tier I with your liege's consent, III if hidden; hidden swaps let the liege void them.",
  payer_base=3, agent_base=3, mode="perform", target="title", term=12, effort=10,
  rel=REL_PEER_VASSAL,
  pick=dict(source="recipient", filter="domain_titles", can_pick="""
scope:target = {
    tier = tier_county
    NOT = { this = scope:recipient.capital_county }
}
"""),
  target_valid="scope:target = { tier = tier_county holder ?= scope:recipient }",
  extra_options=[dict(flag="qpq_x_consent", loc="qpq_x_consent", desc="qpq_x_consent_desc", is_shown="always = yes")],
  payer_adj="if = { limit = { scope:qpq_x_consent ?= yes } add = -2 }",
  agent_adj="if = { limit = { scope:qpq_x_consent ?= yes } add = -2 }",
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
scope:qpq_payer.liege ?= {
    add_opinion = { target = scope:qpq_payer modifier = qpq_conspirator_opinion opinion = -15 }
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
  desc="A vassal and a courtier plot to kill their liege and seize the regency. Treason: execution without tyranny, dynasty renown loss for both houses.",
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
    random_courtier = {
        limit = {
            is_adult = yes
            is_ai = yes
            NOT = { this = root }
            intrigue >= 10
        }
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
"""

K(key="proxy_war", licence=True, cat="C", group="war", secret="conquest", icon="declare_war_interaction",
  name="Proxy War",
  ask="attack [qpq_target.GetTitledFirstName]",
  desc="Pay a foreign ruler to attack your rival. If it comes out, the victim gains Avenge Perfidy against you and your allies cool.",
  echo="Nikephoros II paid Svyatoslav of Kiev to attack Bulgaria (967-968); Svyatoslav then tried to keep it.",
  payer_base=2, agent_base=1, claim_ok=True, term=72, effort=20,
  rel=REL_FOREIGN_RULER, pick=PICK_NEIGHBOUR_RULERS_OF_RECIPIENT,
  target_valid="scope:secondary_recipient = { NOT = { this = scope:actor } NOT = { this = scope:recipient } is_landed = yes }",
  demand=[("10", "scope:recipient = { has_relation_rival = scope:secondary_recipient }", "QPQ_REASON_HATES_TARGET"),
          ("-20", "scope:recipient = { is_allied_to = scope:secondary_recipient }", "QPQ_REASON_ALLIED_TO_TARGET")],
  deliver="""
OR = {
""" + AGENT_BEAT_TARGET + """
    qpq_beat_trigger = { LIST = qpq_agent_fought WHO = scope:qpq_target }
}
""",
  invalid=TARGET_GONE_INVALID,
  on_seal=GRANT_LICENCE, attempt=AI_PACT_WAR, on_end=REVOKE_LICENCE,
  exposed=PROXY_FALLOUT,
  ai=dict(weight=6, valid="is_independent_ruler = yes any_relation = { type = rival is_landed = yes }", find="""
random_relation = {
    type = rival
    limit = { is_landed = yes NOT = { top_liege = root.top_liege } }
    save_scope_as = secondary_recipient
}
if = {
    limit = { exists = scope:secondary_recipient }
    scope:secondary_recipient.top_liege = {
        random_neighboring_and_across_water_top_liege_realm_owner = {
            limit = {
                NOT = { this = root }
                is_ai = yes
                is_at_war = no
                NOT = { is_allied_to = scope:secondary_recipient }
            }
            save_scope_as = recipient
        }
    }
}
"""))

K(key="partition_pact", licence=True, cat="C", group="war", secret="conquest", icon="declare_war_interaction",
  name="Partition Pact",
  ask="join the conquest of [qpq_target.GetTitledFirstName] and keep off the counties bordering [qpq_payer.GetShortUIName]",
  desc="Jointly conquer a third realm and split it on a pre-agreed line: every county bordering your realm is yours.",
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
""")

K(key="secret_alliance", cat="C", group="abroad", secret="betrayal", icon="alliance",
  name="Secret Alliance",
  ask="come to [qpq_payer.GetShortUINamePossessive] defence if they are attacked, without telling a soul",
  desc="An alliance that only activates when either party is attacked and stays hidden from everyone else. Tier I between independents; IV for a party who is someone's vassal.",
  payer_base=1, agent_base=1, target="none", mode="restraint", term=120, effort=10,
  rel=REL_FOREIGN + "scope:actor = { is_landed = yes } scope:recipient = { is_landed = yes }",
  payer_adj="if = { limit = { scope:actor = { is_independent_ruler = no } } add = 3 }",
  agent_adj="if = { limit = { scope:recipient = { is_independent_ruler = no } } add = 3 }",
  breach="has_variable = qpq_agent_refused_call",
  exposed="",
  ai=dict(weight=4, valid="is_landed = yes is_at_war = no", find="""
random_neighboring_and_across_water_top_liege_realm_owner = {
    limit = {
        is_ai = yes
        NOT = { top_liege = root.top_liege }
        opinion = { target = root value >= 20 }
    }
    save_scope_as = recipient
}
"""))

K(key="bought_truce", cat="C", group="war", secret="bribery", icon="peace",
  name="Bought Truce",
  ask="make peace with [qpq_payer.GetShortUIName] and keep it",
  desc="Pay to end or avoid a war. If it comes out, raiders mark the payer as an easy mark.",
  echo="Danegeld.",
  payer_base=1, agent_base=1, target="none", mode="restraint", term=60, effort=0,
  rel=REL_FOREIGN + "scope:actor = { is_landed = yes } scope:recipient = { is_landed = yes }",
  payer_adj="if = { limit = { scope:actor = { is_at_war_with = scope:recipient } } add = 1 }",
  agent_ctx=False,
  demand=[("-15", "scope:recipient = { is_at_war_with = scope:actor }", "QPQ_REASON_AT_WAR")],
  on_seal="""
scope:qpq_payer = {
    every_character_war = {
        limit = {
            OR = {
                AND = { is_attacker = scope:qpq_payer is_defender = scope:qpq_agent }
                AND = { is_defender = scope:qpq_payer is_attacker = scope:qpq_agent }
            }
        }
        end_war = white_peace
    }
    add_truce_both_ways = {
        character = scope:qpq_agent
        months = qpq_term_months_value
    }
}
""",
  breach="is_target_in_variable_list = { name = qpq_agent_attacked target = scope:qpq_payer }",
  exposed="scope:qpq_payer = { add_character_modifier = { modifier = qpq_easy_mark_modifier years = 10 } }",
  ai=dict(weight=5, valid="is_at_war = yes gold >= 50", find="""
random_character_war = {
    limit = {
        is_defender = root
        primary_attacker = { is_ai = yes }
    }
    primary_attacker = { save_scope_as = recipient }
}
"""))

K(key="faithless_ally", cat="C", group="abroad", secret="betrayal", icon="alliance",
  name="Faithless Ally",
  ask="abandon [qpq_target.GetTitledFirstName] in any war against [qpq_payer.GetShortUIName]",
  desc="Pay an ally of your enemy to ignore their call to arms, or withdraw mid-war. If it comes out, they are branded Faithless.",
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
  demand=[("-15", "scope:recipient = { opinion = { target = scope:secondary_recipient value >= 50 } }", "QPQ_REASON_LOVES_TARGET"),
          ("-10", "scope:recipient = { has_trait = honest }", "QPQ_REASON_HONOUR_BOUND")],
  on_seal="""
scope:qpq_agent = {
    every_character_war = {
        limit = {
            OR = {
                AND = { is_attacker = scope:qpq_agent is_defender = scope:qpq_payer }
                AND = { is_defender = scope:qpq_agent is_attacker = scope:qpq_payer }
            }
            NOR = {
                primary_attacker = scope:qpq_agent
                primary_defender = scope:qpq_agent
            }
        }
        remove_participant = scope:qpq_agent
    }
}
""",
  breach="has_variable = qpq_agent_fought_payer",
  exposed="scope:qpq_agent = { add_character_modifier = { modifier = qpq_faithless_modifier years = 10 } }",
  ai=dict(weight=4, valid="is_at_war = yes", find="""
random_character_war = {
    limit = {
        OR = { is_attacker = root is_defender = root }
    }
    random_war_participant = {
        limit = {
            is_ai = yes
            NOT = { this = root }
            NOT = { top_liege = root.top_liege }
            is_independent_ruler = yes
            any_ally = { is_at_war_with = root }
        }
        save_scope_as = recipient
        random_ally = {
            limit = { is_at_war_with = root }
            save_scope_as = secondary_recipient
        }
    }
}
"""))

K(key="turncoat", cat="C", group="abroad", secret="betrayal", icon="declare_war_interaction",
  name="Turncoat",
  ask="desert [qpq_target.GetTitledFirstName] and join [qpq_payer.GetShortUIName] mid-war",
  desc="A foreign vassal or commander withdraws before a battle or switches sides mid-war. Treason for the agent.",
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
        random_vassal = {
            limit = {
                is_ai = yes
                opinion = { target = prev value <= 0 }
            }
            save_scope_as = recipient
        }
    }
}
"""))

K(key="seed_the_separatists", cat="C", group="abroad", secret="faction", icon="independence",
  name="Seed the Separatists",
  ask="win independence from [qpq_target.GetTitledFirstName] on [qpq_payer.GetShortUINamePossessive] gold",
  desc="Fund a foreign vassal's independence. If the rebels win, their half becomes a public Charter and they gain prestige as liberators; the funder still pays with the former liege.",
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
  ai=dict(weight=5, valid="is_independent_ruler = yes any_relation = { type = rival is_independent_ruler = yes }", find="""
random_relation = {
    type = rival
    limit = { is_independent_ruler = yes NOT = { this = root } }
    save_scope_as = qpq_ai_rival
}
if = {
    limit = { exists = scope:qpq_ai_rival }
    scope:qpq_ai_rival = {
        random_vassal = {
            limit = {
                is_ai = yes
                highest_held_title_tier >= tier_duchy
                opinion = { target = scope:qpq_ai_rival value <= 0 }
            }
            save_scope_as = recipient
        }
    }
}
"""))

K(key="shelter_the_pretender", cat="C", group="abroad", secret="betrayal", icon="claim",
  name="Shelter the Pretender",
  ask="take [qpq_target_title.GetName] with [qpq_payer.GetShortUINamePossessive] backing, and remember who made them",
  desc="Host a claimant to a rival throne and back their claim. Mostly public already; the secret clause, armies quietly promised, is what hurts.",
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
  ask="hand [qpq_target.GetTitledFirstName], who sought their hospitality, over to [qpq_payer.GetShortUIName]",
  desc="A foreign ruler hands over a refugee, claimant or exile who sought their hospitality. If it comes out: Betrayed a Guest.",
  payer_base=3, agent_base=3, mode="perform", term=12, effort=15,
  rel=REL_FOREIGN_RULER,
  pick="""
scope:recipient = {
    every_courtier = {
        limit = { NOT = { is_close_family_of = scope:recipient } }
        add_to_list = characters
    }
    every_foreign_court_guest = { add_to_list = characters }
    every_pool_guest = { add_to_list = characters }
    every_prisoner = { add_to_list = characters }
}
""",
  payer_adj="""
if = {
    limit = {
        exists = scope:secondary_recipient
        scope:secondary_recipient = { any_claim = { holder ?= scope:actor } }
    }
    add = 1
}
""",
  can_perform="scope:qpq_target = { is_alive = yes }",
  invalid=TARGET_DEAD,
  perform="qpq_hand_prisoner_to_payer_effect = yes",
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
  desc="Bribe a foreign council member to leak secrets, sabotage, and sour relations for the whole term.",
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

K(key="stay_home", cat="C", group="abroad", secret="betrayal", icon="military_strength",
  name="Stay Home",
  ask="ignore [qpq_target.GetShortUINamePossessive] call to arms when [qpq_payer.GetShortUIName] attacks",
  desc="A foreign vassal ignores their liege's call to arms when you attack: their levies stay home for the whole term.",
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
  desc="A foreign vassal agrees to become your vassal with their lands if you win a war against their liege. Treason for the defector if the war is lost.",
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

K(key="secret_clause", cat="C", group="family", secret="dynastic", icon="marriage",
  name="Secret Clause",
  ask="hand over [qpq_target_title.GetName] as a hidden dowry",
  desc="A marriage between your houses with a hidden term: a dowry county handed over later. If it comes out, the other house feels cheated.",
  payer_base=1, agent_base=1, mode="perform", target="title", term=60, effort=10,
  rel=REL_FOREIGN + """
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
""",
  pick=dict(source="recipient", filter="domain_titles", can_pick="scope:target = { tier = tier_county NOT = { this = scope:recipient.capital_county } }"),
  target_valid="scope:target = { tier = tier_county holder ?= scope:recipient }",
  can_perform="scope:qpq_target_title.holder ?= scope:qpq_agent",
  invalid="NOT = { scope:qpq_target_title.holder ?= scope:qpq_agent }",
  perform="qpq_agent_cedes_title_effect = yes",
  exposed="""
scope:qpq_agent = {
    every_close_family_member = {
        limit = { is_alive = yes }
        add_opinion = { target = scope:qpq_payer modifier = qpq_cheated_by_marriage_opinion }
    }
}
""")

K(key="hire_the_hashashin", cat="C", group="blood", secret="murder", icon="icon_scheme_murder",
  icategory="interaction_category_hostile",
  name="Hire the Hashashin",
  ask="have [qpq_target.GetTitledFirstName] killed by their order",
  desc="Commission a murder through a foreign order. If it comes out, the victim's house and faith turn hostile.",
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
  desc="Pay the head of faith to excommunicate a rival. If it comes out, the excommunication may be lifted and the head of faith's standing suffers.",
  payer_base=4, agent_base=4, mode="perform", term=24, effort=15,
  rel=REL_HOF, pick=PICK_SAME_FAITH_RIVALS,
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
  desc="An annulment of your marriage to the chosen spouse, or the legitimisation of your bastard child, for payment. If it comes out, the ruling may be reversed.",
  payer_base=2, agent_base=2, mode="perform", term=24, effort=5,
  rel=REL_HOF,
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
  desc="Aim a holy war at a rival, or away from your own lands. If it comes out, the faith's holy warriors and the faith itself turn on the payer.",
  payer_base=3, agent_base=3, term=120, effort=10,
  rel=REL_HOF, pick=PICK_RIVALS,
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
  name="Purchase a Mitre",
  ask="give [qpq_target.GetTitledFirstName] a bishopric or temple",
  desc="Buy a bishopric, temple or other theocratic holding for a relative. The core grievance of the Investiture Controversy.",
  echo="The core grievance of the Investiture Controversy.",
  payer_base=3, agent_base=3, mode="perform", term=36, effort=10,
  rel=REL_HOF,
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

K(key="bought_claim", cat="D1", group="church_favours", secret="simony", icon="claim",
  icategory="interaction_category_religion",
  name="Bought Claim",
  ask="grant [qpq_payer.GetShortUIName] a claim on [qpq_target.GetShortUINamePossessive] title",
  desc="The head of faith grants you a claim on a rival's primary title, where the faith allows it. If it comes out, the claim loses its sanctity.",
  payer_base=3, agent_base=3, mode="perform", term=24, effort=10,
  rel=REL_HOF, pick=PICK_RIVALS,
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
  ai=dict(weight=3, valid="""
exists = faith.religious_head
NOT = { faith.religious_head = root }
faith.religious_head = { is_ai = yes }
any_relation = { type = rival is_landed = yes }
""", find="""
faith.religious_head = { save_scope_as = recipient }
random_relation = {
    type = rival
    limit = { is_landed = yes }
    save_scope_as = secondary_recipient
}
"""))

K(key="absolution_by_concession", cat="D1", group="church_favours", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Absolution by Concession",
  ask="lift [qpq_payer.GetShortUINamePossessive] excommunication",
  desc="Lift an excommunication in return for land or rights. Mostly public; a hidden price is what stings.",
  echo="Henry IV at Canossa, 1077.",
  payer_base=1, agent_base=1, target="none", mode="perform", term=12, effort=0,
  rel=REL_HOF + "scope:actor = { has_trait = excommunicated }",
  can_perform="scope:qpq_payer = { has_trait = excommunicated }",
  invalid="NOT = { scope:qpq_payer = { has_trait = excommunicated } }",
  perform="scope:qpq_payer = { remove_trait = excommunicated }",
  exposed="",
  ai=dict(weight=8, valid="has_trait = excommunicated exists = faith.religious_head faith.religious_head = { is_ai = yes }",
          find="faith.religious_head = { save_scope_as = recipient }"))

K(key="holy_warrant", licence=True, cat="D1", group="church_weapons", secret="simony", icon="religious",
  icategory="interaction_category_religion",
  name="Holy Warrant",
  ask="declare a holy war on [qpq_target.GetTitledFirstName] on [qpq_payer.GetShortUINamePossessive] behalf",
  desc="Temporal heads only: the head of faith declares a holy war on your behalf, for gold. Stacks with Proxy War fallout, one tier higher.",
  payer_base=3, agent_base=3, term=60, effort=20,
  rel=REL_HOF + "scope:recipient = { is_landed = yes highest_held_title_tier >= tier_county }",
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
  desc="Pay the Pope to issue a bull favouring you (pick yourself) or condemning a rival. If it comes out, the Pope loses authority within the Church; the buyer loses piety and risks excommunication.",
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
  desc="Buy cardinals' votes in a papal election. If it comes out, the new Pope's standing collapses and the risk of a schism rises.",
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
  desc="Buy a delegate's votes at an Ecumenical Council on a tenet question. If it comes out, delegates lose piety and the losing side may refuse the result.",
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
  desc="Protect or pay the caliph in return for formal recognition of your title. Rivals call it bought legitimacy.",
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
  desc="A foreign Muslim vassal has Friday prayers read in your caliph's name instead of their liege's: a public renunciation of allegiance, and treason for the vassal.",
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
  desc="A respected jurist or the head of faith rules a rival's war or reign unlawful. If it comes out, the jurist is discredited and the ruling voided.",
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
  desc="Pay missionaries to convert a rival's capital county. If it comes out, the target realm turns hostile.",
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
  desc="The patriarch blesses or crowns a rebel against the emperor. If it comes out, the patriarch is disgraced and the usurper's legitimacy falls.",
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
  desc="The emperor installs a patriarch who owes the throne a favour. If it comes out, the clergy's opinion of the emperor drops.",
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
  desc="Pay priests or seers to read good omens before your war (pick yourself), or bad ones before a rival's. If it comes out, the seers are discredited.",
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
  desc="Pay priests to perform kingship rites that raise a low-born or usurping ruler. Rival claimants call the rite bought.",
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
  desc="Endow a monastery or temple whose clergy then back you against a rival. Mild if it comes out, since patronage was expected; hidden strings sting.",
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


GROUPS = [
    ("war", "Commission a war"),
    ("favours", "Ask a favour"),
    ("family", "Family and succession"),
    ("blood", "Blood and abduction"),
    ("shadows", "Factions and spies"),
    ("abroad", "Betrayal abroad"),
    ("church_favours", "Church favours"),
    ("church_weapons", "The Church as a weapon"),
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
}

TIER_NAMES = {0: "Charter", 1: "Discreet", 2: "Unseemly", 3: "Scandalous", 4: "Disgraceful", 5: "Damnable"}
