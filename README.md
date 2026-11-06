# Quid Pro Quo

A Crusader Kings III mod (1.20 "Crozier", By God Alone era) that turns favours into **Deals**: one Ask (what they do), one or more Offers (what you give), a deadline and a **Scandal tier**. From Tier I up, sealing a deal creates a secret both parties hold, and that shared secret is the enforcement mechanism. Tier 0 deals are public **Charters** instead.

Everything is prefixed `qpq_` and no vanilla file or object is overridden, so it sits alongside other mods.

## Install

1. Copy this folder to `Documents/Paradox Interactive/Crusader Kings III/mod/QuidProQuo`.
2. Copy `launcher/QuidProQuo.mod` to `Documents/Paradox Interactive/Crusader Kings III/mod/`.
3. Enable **Quid Pro Quo** in the launcher playset.

`descriptor.mod` targets `1.20.*`. The By God Alone deals (Buy a Bull, Conclave Votes, Council Lobbying) only appear with that DLC; influence fallout only applies to administrative (Roads to Power) governments.

## How to play

| Where | What |
| --- | --- |
| Right-click a character, **Strike a Backroom Deal** | Opens the deal panel, built from the game's own window parts. Your side is on the left, theirs on the right: each has a list of every deed and good it could put in, and what it has put in, with Edit and Remove. Anything that needs choosing (a deed's target, terms and how long it runs, how much gold and when, which titles, artifacts or secrets) opens its own pop-out. The middle shows whether they would agree (with the breakdown, and if they will not at any price, exactly why), your **authority** over them if they are under you in your realm, each side's Scandal tier and what exposure would cost it, and whether the deal is secret or a public Charter. Propose lists anything still missing. |
| Situations window | Every active deal shows for both parties, with the target and the months left. |
| **Honour the Deal** (on the payer) | For Asks done by a single act (take vows, marry, hand someone over, excommunicate, cede a county...). AI agents do this on their own. |
| **Break the Deal** | Walk away openly. The other side becomes the wronged party. |
| **Proclaim as a Charter** | A private deal whose floor is Tier 0 can go public, but only before its war is declared. |
| **Renegotiate (Blackmail)** | If you know someone's deal secret, demand hush money or a hook. Paying hush money is itself a Tier II deal, and the cover-up raises the original's tier by one. |
| **Confess our Deal** | Pay 75% of your own share plus a penance (gold, piety or a pilgrimage); the other party pays in full. |
| Decision: **Open the Deal Ledger** | Two tabs, *My deals* (halves you hold, including old ones) and *Known deals* (dirt you hold on others), five entries a page. |
| Vanilla **Expose secret** | Exposing either half exposes both. |
| Game rule **Quid Pro Quo: AI Deals** | Rare / Normal / Frequent AI proposals. |
| Game rule **Quid Pro Quo: Proposal Window** | *Deal panel* (default) or *Classic*: pick a kind of deal and Ask through events, then the game's own interaction window. |

## The rules as implemented

**Two-way deals.** The Deal panel is a trade, as in Stellaris: the same pool of deeds and goods on both sides. *You will...* and *They will...* pick a deed each (or none), *You give* and *They give* pick the goods (gold, land, claims, hooks...). Each side's Scandal tier is derived from what is put in, and the panel shows whether an AI would agree. Under the hood a deal is up to two linked pacts: "they do the deed, you give the goods" and "you do the deed, they give the goods". A side with goods but no deed rides on a carrier pact (*Exchange of Goods*). Breaking one pact releases the other, and exposing one exposes both.

**Goods are named, not waved at.** Land, artifacts and secrets are chosen item by item, and each is worth what it actually is to the one who gets it: a title by what it is and who wants land; an artifact by its rarity and wear, plus a share for each thing it does that they need (prestige for the prestige-poor, piety, gold, strength in war, schemes, standing), read from the artifact's own modifiers; a secret by who it is on, how bad it is (a crime, a shame, or neither) and what that person is to the one getting it (rival, liege, vassal, kin). There is no "marriage" good: its value swings too wildly to price.

**Contract terms are the scale.** Everything else is priced against vanilla's own contract numbers, the `score` and AI desires each obligation level defines in `common/subject_contracts` (copied in `tools/qpq_contracts.py`; a deal test fails if a patch changes them). One point of score is 15 acceptance points. A term is worth that to the one who gets it, and costs the one who gives it that, plus 15 more for each point by which vanilla says the giver wants to keep the level more than the other wants the change: a right costs a liege more than it is worth to the vassal. So lower taxes from normal is worth 15 and costs 15, a Council Guarantee is worth 45 and costs 60, both before the usual quarter more for what is given up. A weak hook is one point and a strong hook three. A promise that lapses at the deadline is worth no more than the same protection written into the contract. `python3 tools/qpq_balance.py` prints every good and deed in these units.

**What a deal is worth to them.** An AI weighs the whole deal from its own side, and agrees above 0:
- *Goods are weighed at their own purse.* Gold is five points per month of their stake (income, at least 8, times rank: half for the unlanded, up to eight for an emperor, four times for a Head of Faith), so the same sum matters more to a poorer lord. Gold they receive counts for at most twenty months of stake, less for a dirtier deed; gold they pay is never capped. What they give up weighs a quarter more than what they get, so an even swap is refused and 30 gold for their 90 is refused by every lord in the realm.
- *A deed they do* costs them its demand (its tier, the effort, their own risk), set against their wishes about the target, their traits and their circumstances.
- *An AI judges by its own lights only.* What it gets and what it gives are weighed at its own purse and by its own wishes, never by the other party's purse, rank, standing or what the deed would cost them; the panel's suggested price when they pay is likewise what the deed is worth to them. What the other party brings counts only as the substance of the good itself (the army lent, the threat lifted, the crown inherited).
- *A deed you do for them* is worth what they want from it: their wishes about the target (a rival ruined, a title or treasure gained, help in their own war, an end to one), and for a deed that serves them in itself, a share of the deed's own size (the same whoever does it); a betrayal in their war is worth the strength it takes off the enemy, against their own. A killing of someone they have no quarrel with is worth nothing to them. As the one paying, they weigh their own risk if it comes out.
- *Goodwill goes no further than the deed.* Their liking for you, dread of you and your authority (Command) can make a deed they do cheaper, never by more than it costs them, and never pay for goods. Dislike, counted apart, makes them ask more for what they do, give and get from you, but a gift that asks nothing of them is never refused for it.

**Will not, at any price.** Some deeds an AI refuses whatever it is offered, and the panel lists which reasons hold, under its answer and in the breakdown. Dislike alone is never one of them. The reasons: a rival will risk nothing for you; the honest, just, zealous or compassionate will not commit a crime; nobody not cowed by you will do the damnable; nobody does something that dirty for someone they neither like nor fear; and, by the deed, they will not turn on an ally, close kin, a friend or lover, or a realm more than twice as strong.

**What they want.** An Ask is judged by what the one deciding wants, not only by what is offered: a war on someone is attractive to their rival, their neighbour, the holder of a claim, the stronger party; repellent to their ally, kin or friend; and refused outright when the target outweighs them more than two to one in strength. Killings are wanted by enemies and refused by friends and kin; favours go to those they like; pacts to those who can protect them; matters of faith by faith. Rules live in `tools/qpq_goals.py`.

**How long.** Every deed has a term: the time to bring it about (a war won, a rival ruined, a county converted), or the time a promise must be kept (a truce, staying out of a war, a vote). Each deed comes with its usual term (1 to 10 years); in the panel you can set it anywhere from 1 year to 20, a year or five at a time, and the term weighs on both sides' answers:
- *Less time is harder.* For a deed to be brought about, the doer asks more the less time they have: a war in one year asks about two and a half times what the usual eight years does, and in ten or twenty years less (never below 70% of it). A single act asks a little more when rushed. Payment on delivery keeps the doer waiting, which they count against it, so a long term is not free either.
- *A promise held longer costs more to keep, and is worth more.* Shorter than usual, down to half the price; longer, half again for every usual term (or five years, if that is longer) beyond it. To the one it protects it is worth more in the same measure, and what it brings either side (an alliance's protection, a friend left to fight alone) weighs in proportion.
- *Sooner is better to the one who pays.* A deed done for them is worth 3% more for every year sooner than usual (up to 15%) and 3% less for every year later (down to 60%), so promising a deed in twenty years buys little.
- AIs propose their own deals at the usual term.

**Sealing.** A story cycle (`qpq_pact_story`, owned by the payer) holds the Ask, target, payment, the term agreed and tiers, and checks every month for delivery, breach or expiry. Each party gets one half of a linked secret (`qpq_secret_<category>_<tier>`, ten Ask categories by five tiers); each half is revealed to the other party. Tier IV halves are criminal and Tier V halves criminal and shunned, so vanilla blackmail treats them as the strong dirt they are.

**Payment.** In the panel, gold is an amount you name, paid at once or on delivery (the classic interaction window also offers half and half, and yearly installments). Up-front gold is simply lost if the agent breaches. A player payer may renege on what is due on delivery; an AI payer pays if it can.

**Deliver or breach.** Every Ask maps to something the game tracks: a war won (recorded on the deal by `on_war_won_*`), a death, a title held, a faction joined or left, a county's faith or development, a prisoner taken, or the deadline passing with a promise kept. A breach gives the wronged party a strong hook and a 75% discount on exposing the deal. Deaths and impossible Asks void a deal without fault.

**Scandal tiers.** Each Ask has a base tier for the payer and for the agent (Catalogue C and D list them separately), then the context table shifts it and clamps to 0-V: hostile-faith foreigner -1, co-religionist ally +1, fellow vassal +1, close family or heir +1, your own liege +2, clergy or head of faith +1. At exposure: more than 20 years or a dead party -1, the exposer's culture or faith tolerating intrigue -1 (read from By God Alone rite parameters plus a short tradition list), the winners of a deal that changed who rules -1 or -2, a cover-up +1.

**Discretion.** A deal is either secret (a secret each, never below Tier I, the full fallout if it comes out) or a public Charter at any tier: nothing to expose, prestige for both if it is honourable, and for a scandalous one half its fallout at once and a higher price from the other side. Conquest charters grant the **Crown Mandate** casus belli, which lends your de jure right; the target's liege and allies are alerted and weigh joining the defence by their opinion of the target. An already sealed deal whose floor is Tier 0 can still be proclaimed afterwards.

**Command.** Putting a deal to someone under you in your realm (a vassal, a vassal's vassal, a courtier), you can lean on your standing: *Ask*, *Remind* (of their duty), *Command* or *Decree*. Your standing is your legitimacy level (prestige level without legitimacy); what they expect of you is vanilla's legitimacy expectation of a liege (your rank, de jure ties, family, how long your dynasty has ruled them), plus one level for each step further down your realm they stand. *Remind* needs you no more than one level short of that, *Command* to meet it, *Decree* to exceed it by two. The tiers add 15, 30 and 45 to their acceptance, counted with their goodwill (so never more than the deed costs them, and never towards goods they hand over) and never enough to overturn a refusal at any price, and put minor, medium or major prestige and legitimacy at stake: you pay it if the deal comes out (half as much again in prestige without legitimacy), or half of it at once if you proclaim a scandalous command as a Charter. An AI that would have refused without the command obeys and resents it (-15, -30, -45 opinion); a person who refuses a command is remembered for it.

**Wartime.** A war is chosen by the leader of the other side ("the war against Duke X"): the deed finds that very war when sealed, and keeps it on the deal where it must watch it. *Join the War* (they join your war on your side and see it through; leaving early is a breach, and gold due on delivery is paid when the war is over with them still in it) and *Stay Out of the War* (they do not join it against you until it ends or the deadline passes). Each is judged on the war itself: how much the one deciding wants that fight (enmity, rivalry, claims, faith hostility, their boldness, energy and compassion, warlike or peaceable traits, another war on their hands) and whether their side would win it (the current strength of every participant on each side, with them added if they are joining, and the war score). Joining counts both for; staying out counts them against (what giving up the fight costs them) at a little over half weight. Nobody joins a war whose other side is more than twice as strong. Deals do not end wars or take anyone out of one: that is the business of war, not of a bargain. A *Bought Truce* keeps a peace between rulers not at war, and a *Faithless Ally* promises to ignore their ally's call to arms in wars to come; neither can be had from someone already fighting you. The panel's breakdown shows all this as *What they want from it*, beside the other parts of the answer: what they are asked to do, the goods, their opinion of you, their character, dread, their circumstances, being seen doing it in public, your authority, and any refusal at any price (a part that adds nothing is left out).

**Tribute.** A suzerain and its tributary are bound to keep the peace like a truce: a deal aimed at your own tributary or suzerain is scandalous as a co-religionist truce partner is, and a war you paid for against either makes you a truce-breaker by proxy if it comes out.

**Exposure.** The exposer pays the tier's baseline cost times their own share of guilt: the payer about 60%, the agent about 40% but always the full criminal weight of the deed. The wronged party pays 25% of their share; a third party who digs it up pays nothing and both members pay in full. The fallout menu: prestige (or Dread for rulers who already lean on it), Known Schemer, legitimacy and influence, "Betrayed Me" from the victim, their house and allies, a small capped bump to faction discontent, a strong hook for the victim, the **Avenge Perfidy** casus belli, imprisonment, revocation and (Tier V) execution reasons, piety and excommunication risk, dynasty renown, kinslaying, and lost Fervor for head-of-faith deals. Each Ask adds its own consequence from the catalogue's "If exposed" column.

**Inheritance.** Tier I-III halves die with their members; Tier IV-V halves pass to the heir as a dynasty stain, one tier lower.

**Deal cap.** 2 + diplomacy / 5 active deals per character, Charters included.

**AI.** AI rulers aim their deals where they want them: at the rival they hate most, the holder of land they claim, a neighbour of a hostile faith, and at someone the one they hire can beat, given to the vassal or neighbour best able and keenest to do it. At war, a side that is not winning hires a neighbour with no love for the enemy to join it, or pays the enemy's ally to stay home. Before a war, an AI that means to fall on a neighbour it could beat alone, but whose ally would tip the war against it, tries to buy that ally's promise to ignore the call to arms (a Faithless Ally); and a ruler threatened by a stronger neighbour with a claim on it, a rivalry or a hostile faith tries to buy a truce. An AI proposes only what is worth its price to itself, by its own lights (what the deed brings it, its own risk and scruples, against the gold at its own purse), and offers what the other side would need to agree: AIs do not overpay, so they deal less often than before, and mostly where there is a rival to ruin, a war to win or a gain to be had. An AI liege whose deal would be refused leans on its authority (Command) when its standing allows, with the lightest tier that would do, and never when even full goodwill could not cover what the deed costs; a timid ruler does not try. The command is written on the pact as a player's is, an AI commanded into it resents it, and a person who refuses it defies their liege. AI proposals obey each deed's own rules and target conditions, as the panel does. AI agents work towards what they were paid for (declare the paid-for war, start the murder or abduction scheme, join or start the faction, convert or develop the county, perform the act) and occasionally renege when the deal sours. AI characters propose deals slightly rarer than uncommonly, more often if they are intrigue-heavy; to players this arrives as an event with the terms. AI holders of deal secrets blackmail or burn them, and Honest or Zealous characters near a stress break, or on their deathbed, sometimes confess.

## What can be traded

There are 63 deeds (things a character agrees to do) and 24 goods (things handed over or promised). `tools/qpq_kinds.py` is the single source for each deed's tiers, targets, delivery check, AI behaviour and exposure consequence, and `tools/qpq_flavor.py` for its pitch. Many deeds only appear for certain relationships, faiths or situations.

### Deeds

#### Liege to vassal (17)
- **Chartered Conquest:** conquer a neighbour's land under a published charter
- **Marcher Charge:** hold the border against a target
- **Holy Sponsorship:** convert a title to the payer's faith
- **Development Charter:** raise a title's development
- **Electoral Purchase:** vote for a target in the next election (a liege can buy it, an elector can offer it)
- **The Loyal Mole:** join a faction against the payer and sabotage it
- **Agent Provocateur:** start a revolt against the payer so it can be crushed
- **Dossier:** find or plant dirt on a target
- **Quiet Removal:** see that a target doesn't live out the term
- **The Heir Question:** remove the payer's own heir
- **Snatch:** kidnap a target and deliver them to the payer
- **Dispossession:** imprison a target or strip their lands, and bear the tyranny for it
- **Abdicate to Heir:** give up their titles to their heir and take holy vows
- **Marriage by Command:** set aside any spouse and marry a target
- **Surrender a Treasure:** hand an artifact over to the payer
- **Renunciation:** renounce any claim on a title
- **Hush Money:** never expose what they know about the payer

#### Vassal-initiated (7)
- **Price of Loyalty:** answer the call to arms and stay loyal through the war
- **Blessing for a Feud:** look away while the payer attacks a fellow vassal
- **Clemency Bargain:** pardon the payer in exchange for secrets on others
- **Mutual Defense:** stand together if the liege revokes from either party
- **Faction Pledge:** stay in a faction until it wins, and share the spoils
- **Transfer a County:** a fellow vassal, or a foreign house married into yours, cedes a county to the payer
- **Coup Deal:** kill a target so the payer can seize the regency

#### Foreign courts (13)
- **Proxy War:** attack a target (asked of a foreign ruler, or of your own vassal against a neighbour or a fellow vassal)
- **Partition Deal:** join a conquest and keep off the counties bordering the payer
- **Secret Alliance:** secretly come to the payer's defence if they're attacked
- **Bought Truce:** make peace with the payer and keep it
- **Faithless Ally:** abandon an ally in any war against the payer
- **Turncoat:** desert a side and join the payer mid-war
- **Seed the Separatists:** win independence from a liege on the payer's gold
- **Shelter the Pretender:** take a title with the payer's backing
- **Extradition:** hand a prisoner, hostage, claimant or refugee over to the payer (also asked of your own vassals)
- **Buy a Councillor:** leak from and sabotage a council
- **Stay Home:** ignore a liege's call to arms when the payer attacks
- **Defection Deal:** become the payer's vassal if their liege loses
- **Hire Holy Order Assassins:** have a target killed by a holy order

#### Any head of faith (7)
- **Excommunication for Hire:** excommunicate a target
- **Dispensation for Gold:** grant a dispensation concerning a target
- **Steer the Holy War:** aim the next great holy war at a target
- **Buy a Bishopric:** give a target a bishopric or temple
- **Bought Claim:** grant the payer a claim on a target's title
- **Absolution by Concession:** lift the payer's excommunication
- **Holy Warrant:** declare a holy war on a target for the payer

#### Catholic Church, needs By God Alone (3)
- **Buy a Bull:** issue a bull concerning a target
- **Conclave Votes:** vote for a target in the next papal election
- **Council Lobbying:** vote with the payer at the next Ecumenical Council

#### Signature faith deals (9)
- **Caliphal Investiture:** recognise the payer's title as sultan or emir
- **Name in the Khutba:** read Friday prayers in the payer's caliph's name
- **Fatwa for Hire:** rule a target's war or reign unlawful
- **Fund the Da'wa:** send missionaries to turn a target's capital to the payer's faith
- **Crowning the Usurper:** bless and crown the payer against a target
- **Pliant Patriarch:** owe the payer a favour for the patriarchal throne
- **Favourable Omens:** read a target's omens as the payer wishes
- **Consecration Rites:** perform the rites that raise the payer to kingship
- **Temple Patronage:** have the clergy back the payer against a target

#### Tribute (5)
- **Heavier Tribute:** raise the tribute paid to the payer
- **Lighter Tribute:** lower the tribute the payer pays
- **Bought Freedom:** release the payer from tribute
- **Accept the Yoke:** become the payer's tributary
- **Cast Off the Yoke:** stop paying tribute to an overlord

#### In time of war (2)
- **Join the War:** join the payer's war and see it through
- **Stay Out of the War:** stay out of the payer's war

### Goods

#### General (13)
- **Gold:** an amount you name, paid at once or on delivery
- **Land:** one of your counties
- **A claim:** a fabricated claim on the target's land
- **Office:** a seat on your council, and dismissing them early is a breach
- **Release a hook:** free them from a hook you hold on them
- **Weak Hook:** a weak hook on yourself
- **Use Hook:** use a hook you hold on them to press the deal
- **A secret on someone:** what you know about a named person
- **Succession:** name them your designated heir
- **Clemency:** free them or their kin from prison, and drop charges
- **Arms:** lend levies and knights until the deadline
- **Artifacts:** chosen by name
- **Church favour:** an indulgence and absolution from a head of faith

#### Contract terms (11)
Only between a liege and their own vassal, and only where the term can still move. Each changes the vassal's real contract, one step, on delivery, and lasts. **Promise of Safety** is the exception: a promise for the term, not a contract right.

Given by the liege:
- **Lower Taxes:** the vassal's taxes fall one level
- **Lower Levies:** the vassal's levies fall one level
- **Revocation Protection:** their titles can never be revoked
- **Council Guarantee:** the right to demand a council seat
- **War Declaration Rights:** the right to declare war freely
- **Fortification Rights:** needs the liege's culture to have the innovation
- **Coinage Rights:** needs the liege's culture to have the innovation
- **Religious Protection:** for a vassal of a different faith
- **Promise of Safety:** no revocation or imprisonment until the deadline

Given by the vassal:
- **Higher Taxes:** the vassal's taxes rise one level
- **Higher Levies:** the vassal's levies rise one level

### Structure
- If neither side does a deed, the trade runs as **Exchange of Goods**, which is not counted among the 63.
- A public Charter is a setting on the whole deal, not a good.
- The classic interaction window also offers half-and-half and yearly gold payments.

## Interpretations and simplifications

The design doc is a brainstorm; where it left a choice open, this is what the mod does.

- **No deal settles a war.** The design doc's *Bought Truce* ("pay to end or avoid a war") and *Faithless Ally* ("ignore the call to arms, or withdraw mid-war") are kept to their peacetime halves: a truce bought between rulers not at war, and a promise to stay out of wars to come. Ending a war, or taking a participant out of one, is war resolution, which vanilla offers no diplomatic action for, so deals leave it alone.
- **Open questions in the doc:** the borrowed de jure casus belli keeps the name *Crown Mandate*; a Charter pulls the target's allies in scaled by their opinion of the targeted vassal; confession costs are 75% of your share, 25%/10% on the deathbed, plus a penance; all catalogues are built, not just a v1 slice; Catalogue D uses the 1.20 script names (`pam_forced_papal_vote_target`, `has_clerical_electors`, `set_great_holy_war_target`, `excommunicate_character`).
- **Wars for hire** (Proxy War, Partition Deal, Blessing for a Feud, Holy Warrant) grant a **Deal War** casus belli against the target, so the AI and players always have a way to deliver. A Proxy War between two of your own vassals also gives the one you send a favour hook on you, meant to get the war past crown authority (vanilla gates banned vassal wars on a hook on the liege, see `war_declarer_needs_hook_on_liege`).
- **Effects CK3 cannot script directly** use modifiers: lent arms a levy and knight modifier, a Pope's bull a favour or condemnation modifier, omens an advantage modifier, Stay Home and a refused Price of Loyalty a levy penalty.
- **Electoral Purchase** buys the vote through a strong opinion of the candidate, which the vanilla elective scripts weigh; the deal is a promise kept until the deadline.
- **Abdicate to Heir** abdicates the vassal to their own heir (choosing the heir is not scriptable reliably). **Dispensation for Gold** covers annulment and legitimisation, not consanguinity waivers. **Fund the Da'wa** is open to Shia faiths (Ismaili is not a separate faith key in 1.20).
- **Mutual Defense** is called when the liege revokes from the proposer; the partner then has six months to join a faction against the liege.
- **Faith boundaries** follow vanilla's own doctrines rather than a hand-made list. Excommunication, absolution, church favour (indulgences), penance in gold and Buy a Bishopric need a sacramental faith with a spiritual head (`faith_has_sacraments_central_trigger`). Annulments also work where divorce needs the head of faith's approval. Bought Claim needs a spiritual head, Holy Warrant a temporal one, and Steer the Holy War a faith that wages great holy wars. Everywhere else a confession's gold goes to alms, and the Hajj counts as the pilgrimage.
- **Inherited halves** are priced one tier lower by the mod, but keep their original secret type, so vanilla blackmail still treats a Tier IV-V stain as criminal.
- **The deal panel** decides for AI recipients with the same numbers as the interaction's acceptance (they agree above 0). A human recipient gets the proposal as an event listing every term, and can only accept while the deal still stands (target, ties, gold and room for another deal are checked again when they answer). Propose also re-checks everything at the moment it is pressed. You cannot run two deals of the same Ask with the same person. The target lists show at most 120 rows (rivals first, then people at either court or in either's service, then by rank), so a large realm does not build hundreds of portraits; a pick stays valid even if it falls outside them.
- **Hush Money** over vanilla secrets uses `disable_exposure_by`, so the holder truly can never expose them; over deal secrets, exposing it anyway breaches the hush money deal.

## Development

- `python3 tools/qpq_gen.py` regenerates the per-deal files (interactions, secret types, kind triggers/effects/values, hub events, custom localization, deal localization) from `tools/qpq_kinds.py`, and the deal panel (`gui/qpq_pact_window.gui`, its scripted GUIs, effects, triggers and text) through `tools/qpq_ui_gen.py`. Generated files are committed. The panel's hand-written parts are `common/scripted_effects/qpq_ui_effects.txt` and `common/scripted_guis/qpq_ui.txt`.
- Text follows the game's own split. Events, decisions, situations and each Ask's pitch speak in the world's voice; what things do sits under that in plain tooltip text, with the mod's rules behind game-concept links (`[qpq_deal|E]`, `[qpq_scandal_tier|E]`, `[qpq_charter|E]`, `[qpq_wronged_party|E]`, in `common/game_concepts/qpq_game_concepts.txt`). An Ask's pitch is in `tools/qpq_flavor.py`: the words of whoever wants the deed done, quoted in the panel, the hub and the proposal events. What it does is its `desc` in `tools/qpq_kinds.py`.
- `python3 tools/qpq_deal_tests.py [--vanilla <CK3>/game]` runs the deal tests: `tools/qpq_sim.py` parses the mod's own scripted effects, triggers, values and scripted GUIs (and vanilla's that they call), builds a small world (an elective kingdom and its court, a Church, an orthodox empire, sunni and shia realms, a pagan jarl, a holy order, a tributary chief, a war), and drives the Backroom Deal panel through its own buttons, reading back every part of the answer. The tests check rules of good sense on that: no free lunch on goods, goodwill held to the deed, worth judged by the one who would pay, the term weighing as it should (less time is harder, a promise held longer dearer, sooner better to the one who pays, and the term chosen the one sealed), more gold never hurts, every refusal at any price explained, the tiers a deed's text states, and no script error on any deed between any pair it is offered to (`python3 tools/qpq_sim.py kinds` sweeps them all). The simulator is strict: a keyword it does not know stops it, so it is taught, never skipped.
- `python3 tools/qpq_eval.py --n 320 --seed 1 --out <dir>` composes that many varied deals (barter, deeds each way, goods, opinion, traits, dread, rivalries, Command, Charters) and writes each as a short brief with the AI's answer and breakdown, for a reader to judge which answers do not make sense.
- `python3 tools/qpq_balance.py [--vanilla <CK3>/game]` prints every good and deed in contract score points, read from the mod's own script through the panel, for rebalancing: permanent should outweigh temporary, and nothing should sit far from what it is comparable to.
- `python3 tools/qpq_validate.py --vanilla <CK3>/game [--tiger <tiger checkout>]` parses every script file and checks keywords against the vanilla 1.20 files (and the tiger tables), references to modifiers, opinions, hooks, secrets, traits, schemes, factions, events and interactions, saved scopes and variables that are used but never set, and localization keys, BOMs and syntax. For `gui/` it checks widget types, properties, templates, block overrides, data functions, scripted GUI names and the scopes each scripted GUI is given, and the localization keys used. Every `[concept|E]` link must name a vanilla or mod game concept. On this version it reports sixteen unknown keywords it cannot confirm from vanilla's files (`clamp_variable`, `ordered_secret`, `every_elector`, `tributary_contract_obligation_level_can_be_increased` and `_decreased`); run tiger to settle them.
- This was written and checked without running the game. Before relying on it, run [ck3-tiger](https://github.com/amtep/tiger) for scope-level validation and check `error.log` after a few in-game years.
