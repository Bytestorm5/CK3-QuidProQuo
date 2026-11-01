# Quid Pro Quo

A Crusader Kings III mod (1.20 "Crozier", By God Alone era) that turns favours into **Pacts**: one Ask (what they do), one or more Offers (what you give), a deadline and a **Scandal tier**. From Tier I up, sealing a pact creates a secret both parties hold, and that shared secret is the enforcement mechanism. Tier 0 pacts are public **Charters** instead.

Everything is prefixed `qpq_` and no vanilla file or object is overridden, so it sits alongside other mods.

## Install

1. Copy this folder to `Documents/Paradox Interactive/Crusader Kings III/mod/QuidProQuo`.
2. Copy `launcher/QuidProQuo.mod` to `Documents/Paradox Interactive/Crusader Kings III/mod/`.
3. Enable **Quid Pro Quo** in the launcher playset.

`descriptor.mod` targets `1.20.*`. The By God Alone pacts (Buy a Bull, Conclave Votes, Council Lobbying) only appear with that DLC; influence fallout only applies to administrative (Roads to Power) governments.

## How to play

| Where | What |
| --- | --- |
| Right-click a character, **Propose a Pact** | Pick a kind of deal, then the Ask. That opens the Ask's own window: choose the target and tick what you offer (gold and its timing, land, claims, office, marriage, hooks, secrets, contract terms, succession, clemency, arms, artifacts, church favour, restraint, a hook to call in, or publishing it as a Charter). The usual acceptance breakdown shows how they weigh value, opinion, traits and tier. |
| Situations window | Every active pact shows for both parties, with the target and the months left. |
| **Honour the Pact** (on the payer) | For Asks done by a single act (take vows, marry, hand someone over, excommunicate, cede a county...). AI agents do this on their own. |
| **Break the Pact** | Walk away openly. The other side becomes the wronged party. |
| **Proclaim as a Charter** | A private pact whose floor is Tier 0 can go public, but only before its war is declared. |
| **Renegotiate (Blackmail)** | If you know someone's pact secret, demand hush money or a hook. Paying hush money is itself a Tier II pact, and the cover-up raises the original's tier by one. |
| **Confess our Pact** | Pay 75% of your own share plus a penance (gold, piety or a pilgrimage); the other party pays in full. |
| Decision: **Open the Pact Ledger** | Two tabs, *My pacts* (halves you hold, including old ones) and *Known pacts* (dirt you hold on others), five entries a page. |
| Vanilla **Expose secret** | Exposing either half exposes both. |
| Game rule **Quid Pro Quo: AI Pacts** | Rare / Normal / Frequent AI proposals. |

## The rules as implemented

**Sealing.** A story cycle (`qpq_pact_story`, owned by the payer) holds the Ask, target, payment, deadline (1 to 10 years, by Ask) and tiers, and checks every month for delivery, breach or expiry. Each party gets one half of a linked secret (`qpq_secret_<category>_<tier>`, ten Ask categories by five tiers); each half is revealed to the other party. Tier IV halves are criminal and Tier V halves criminal and shunned, so vanilla blackmail treats them as the strong dirt they are.

**Payment.** Up front, on delivery, half and half, or yearly installments. Up-front gold is simply lost if the agent breaches. A player payer may renege on what is due on delivery; an AI payer pays if it can.

**Deliver or breach.** Every Ask maps to something the game tracks: a war won (recorded on the pact by `on_war_won_*`), a death, a title held, a faction joined or left, a county's faith or development, a prisoner taken, or the deadline passing with a promise kept. A breach gives the wronged party a strong hook and a 75% discount on exposing the pact. Deaths and impossible Asks void a pact without fault.

**Scandal tiers.** Each Ask has a base tier for the payer and for the agent (Catalogue C and D list them separately), then the context table shifts it and clamps to 0-V: hostile-faith foreigner -1, co-religionist ally +1, fellow vassal +1, close family or heir +1, your own liege +2, clergy or head of faith +1. At exposure: more than 20 years or a dead party -1, the exposer's culture or faith tolerating intrigue -1 (read from By God Alone rite parameters plus a short tradition list), the winners of a pact that changed who rules -1 or -2, a cover-up +1.

**Discretion.** A pact whose floor is 0 can be published as a Charter (prestige for both; for conquests the **Crown Mandate** casus belli, which lends your de jure right; the target's liege and allies are alerted and their allies weigh joining the defence by their opinion of the target). Anything private is at least Tier I.

**Exposure.** The exposer pays the tier's baseline cost times their own share of guilt: the payer about 60%, the agent about 40% but always the full criminal weight of the deed. The wronged party pays 25% of their share; a third party who digs it up pays nothing and both members pay in full. The fallout menu: prestige (or Dread for rulers who already lean on it), Known Schemer, legitimacy and influence, "Betrayed Me" from the victim, their house and allies, a small capped bump to faction discontent, a strong hook for the victim, the **Avenge Perfidy** casus belli, imprisonment, revocation and (Tier V) execution reasons, piety and excommunication risk, dynasty renown, kinslaying, and lost Fervor for head-of-faith pacts. Each Ask adds its own consequence from the catalogue's "If exposed" column.

**Inheritance.** Tier I-III halves die with their members; Tier IV-V halves pass to the heir as a dynasty stain, one tier lower.

**Pact cap.** 2 + diplomacy / 5 active pacts per character, Charters included.

**AI.** AI agents work towards what they were paid for (declare the paid-for war, start the murder or abduction scheme, join or start the faction, convert or develop the county, perform the act) and occasionally renege when the deal sours. AI characters propose pacts slightly rarer than uncommonly, more often if they are intrigue-heavy; to players this arrives as an event with the terms. AI holders of pact secrets blackmail or burn them, and Honest or Zealous characters near a stress break, or on their deathbed, sometimes confess.

## The catalogue

All 61 Asks from the design doc are implemented; `tools/qpq_kinds.py` is the single source for each one's tiers, targets, delivery check, AI behaviour and exposure consequence.

| Catalogue | Pacts |
| --- | --- |
| A. Liege to vassal | Chartered Conquest, Sanctioned Conquest, Marcher Charge, Holy Sponsorship, Development Charter, Electoral Purchase, The Loyal Mole, Agent Provocateur, Licensed Feud, Dossier, Quiet Removal, The Heir Question, Snatch, Dispossession, The Cloister, Marriage by Command, Hand-Over (and Hand-Over: Treasure), Renunciation, Hush Money |
| B. Vassal-initiated | Price of Loyalty, Blessing for a Feud, Clemency Bargain, Electoral Capitulation, Mutual Defense League, Faction Pledge, Title Swap, Coup Pact |
| C. Foreign courts | Proxy War, Partition Pact, Secret Alliance, Bought Truce, Faithless Ally, Turncoat, Seed the Separatists, Shelter the Pretender, Extradition, Buy a Councillor, Stay Home, Defection Pact, Secret Clause, Hire the Hashashin |
| D1. Any head of faith | Excommunication for Hire, Dispensation for Gold, Steer the Holy War, Purchase a Mitre, Bought Claim, Absolution by Concession, Holy Warrant |
| D2. Catholic Church (By God Alone) | Buy a Bull, Conclave Votes (uses BGA's forced papal vote), Council Lobbying |
| D3. Signature faith pacts | Caliphal Investiture, Name in the Khutba, Fatwa for Hire, Fund the Da'wa, Crowning the Usurper, Pliant Patriarch, Favourable Omens, Consecration Rites, Temple Patronage |

## Interpretations and simplifications

The design doc is a brainstorm; where it left a choice open, this is what the mod does.

- **Open questions in the doc:** the borrowed de jure casus belli keeps the name *Crown Mandate*; a Charter pulls the target's allies in scaled by their opinion of the targeted vassal; confession costs are 75% of your share, 25%/10% on the deathbed, plus a penance; all catalogues are built, not just a v1 slice; Catalogue D uses the 1.20 script names (`pam_forced_papal_vote_target`, `has_clerical_electors`, `set_great_holy_war_target`, `excommunicate_character`).
- **Wars for hire** (Sanctioned Conquest, Proxy War, Partition Pact, Licensed Feud, Blessing for a Feud, Holy Warrant) grant a **Pact War** casus belli against the target, so the AI and players always have a way to deliver. Licensed Feud also gives the vassal a favour hook on the liege, meant to get the war past crown authority (vanilla gates banned vassal wars on a hook on the liege, see `war_declarer_needs_hook_on_liege`).
- **Effects CK3 cannot script directly** use modifiers: contract terms are a 20-year income modifier, lent arms a levy and knight modifier, a Pope's bull a favour or condemnation modifier, omens an advantage modifier, Stay Home and a refused Price of Loyalty a levy penalty.
- **Electoral Purchase / Electoral Capitulation** buy the vote through a strong opinion of the candidate, which the vanilla elective scripts weigh; the pact is a promise kept until the deadline.
- **The Cloister** abdicates the vassal to their own heir (choosing the heir is not scriptable reliably); a relative simply takes vows. **Dispensation for Gold** covers annulment and legitimisation, not consanguinity waivers. **Fund the Da'wa** is open to Shia faiths (Ismaili is not a separate faith key in 1.20).
- **Mutual Defense League** is called when the liege revokes from the proposer; the partner then has six months to join a faction against the liege.
- **Faith boundaries** follow vanilla's own doctrines rather than a hand-made list. Excommunication, absolution, church favour (indulgences), penance in gold and Purchase a Mitre need a sacramental faith with a spiritual head (`faith_has_sacraments_central_trigger`). Annulments also work where divorce needs the head of faith's approval. Bought Claim needs a spiritual head, Holy Warrant a temporal one, and Steer the Holy War a faith that wages great holy wars. Everywhere else a confession's gold goes to alms, and the Hajj counts as the pilgrimage.
- **Inherited halves** are priced one tier lower by the mod, but keep their original secret type, so vanilla blackmail still treats a Tier IV-V stain as criminal.
- **Hush Money** over vanilla secrets uses `disable_exposure_by`, so the holder truly can never expose them; over pact secrets, exposing it anyway breaches the hush money pact.

## Development

- `python3 tools/qpq_gen.py` regenerates the per-pact files (interactions, secret types, kind triggers/effects/values, hub events, custom localization, pact localization) from `tools/qpq_kinds.py`. Generated files are committed.
- `python3 tools/qpq_validate.py --vanilla <CK3>/game [--tiger <tiger checkout>]` parses every script file and checks keywords against the vanilla 1.20 files (and the tiger tables), references to modifiers, opinions, hooks, secrets, traits, schemes, factions, events and interactions, saved scopes and variables that are used but never set, and localization keys, BOMs and syntax. It reports 0 problems on this version.
- This was written and checked without running the game. Before relying on it, run [ck3-tiger](https://github.com/amtep/tiger) for scope-level validation and check `error.log` after a few in-game years.
