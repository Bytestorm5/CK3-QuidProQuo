"""Quid Pro Quo - the in-world voice of each Ask.

FLAVOR is the pitch of whoever wants the deed done (the payer, or the agent for the Asks an agent proposes),
spoken to the other side. It is shown as a quotation: in the deal panel (your own words when you would ask for
it, "[they] might put it like this" when it is a deed you would do for them), the hub tooltips and the
proposal events. It must not use scopes, since it is shown in all of those places.

What each Ask does, in the game's plain tooltip voice, is its `desc` in tools/qpq_kinds.py.

GROUP_FLAVOR opens each group of Asks in the classic proposal events.
"""

FLAVOR = {
    # ---------------- Catalogue A: liege to vassal
    "chartered_conquest": "There is good land beyond your border, and it does not answer to me. Take it under my charter, and let every court know it was done by my leave.",
    "sanctioned_conquest": "I cannot be seen to set one lord against another. But if you were to ride out on your own account, you would find my purse open and my eyes turned elsewhere.",
    "marcher_charge": "A border is only as strong as the lord who holds it. Keep your levies raised and your watchfires lit, and I will see you paid for every cold night.",
    "holy_sponsorship": "Souls are won with sermons, and sermons are paid for in coin. Bring that county to the true faith, and the labour will not go unrewarded.",
    "development_charter": "A county is worth what it yields. Build the roads, raise the mills, fill the markets, and I will make it worth your while.",
    "electoral_purchase": "When the electors gather, I want your voice raised for the right candidate. Name your price. I would rather pay it than lose.",
    "loyal_mole": "There are lords in my realm who whisper of rising against me. Go among them as one of their own, and when the moment comes, be the one who falters.",
    "agent_provocateur": "Disloyalty festers best unseen. Raise a banner against me, gather every malcontent beneath it, and let me cut out the rot in a single stroke.",
    "licensed_feud": "The law forbids you to war on your neighbour, and keeping the law is my duty. Ride against them all the same. I will find reasons to look the other way.",
    "dossier": "Everyone has something they would rather keep buried. Find what your rival hides, or give the world something to find, and bring it to me.",
    "quiet_removal": "I want no trial, no war and no witnesses. Only that, before the year is out, a certain name is no longer spoken among the living.",
    "heir_question": "The succession troubles me. My heir is not the heir I would have chosen. I think you understand me, and I would rather not say more.",
    "snatch": "A guest at my court, invited or otherwise, would serve me better than any treaty. Bring me the one I ask for, and bring them unharmed.",
    "dispossession": "One of your vassals has become a thorn in my side. Strip them, chain them, do what you must, and let the blame rest with you rather than me.",
    "the_cloister": "There is a peace behind cloister walls that no crown can give. Some would be happier there. I can make it worth their while to find out.",
    "marriage_by_command": "Marriages are made in the interest of the realm, and unmade in it too. Set aside whoever you must, and wed the one I name.",
    "hand_over": "You keep someone in your halls whom I would very much like to keep in mine. Give them up, and you will not find me ungrateful.",
    "hand_over_artifact": "You own a treasure that would look far finer in my hall. I am prepared to make you forget you ever had it.",
    "renunciation": "A claim is a dagger kept for later. Lay yours down before witnesses, and I will see that you lose nothing by it.",
    "hush_money": "What you know about me will stay with you. That is all I ask, and I am prepared to pay handsomely for your silence.",
    # ---------------- Catalogue B: vassal to liege, vassal to vassal
    "price_of_loyalty": "You call, and I come; such is the bond between us. But bonds cost something to keep, my liege, and this war will cost me dearly.",
    "blessing_for_a_feud": "There is a quarrel between my neighbour and me that only steel will settle. Look the other way, my liege, and the realm will be quieter for it.",
    "clemency_bargain": "I have done wrong, and I will not deny it. But I know where others have done worse, and I will tell you all of it, if you will forget my part.",
    "electoral_capitulation": "My vote is yours if you want it. All I ask is that you remember who gave it, and write my terms into the bargain.",
    "mutual_defense_league": "Our liege takes whatever lands catch the royal eye. Today it is another lord's; tomorrow it may be yours or mine. Let us swear to stand together when it is.",
    "faction_pledge": "Our cause will triumph, or we will hang together. Stand with me to the end, and when the spoils are counted, you will have your share.",
    "title_swap": "Your county lies in the heart of my lands, and mine in the heart of yours. Let us trade, quietly, and both be the stronger for it.",
    "coup_pact": "The crown sits on the wrong head, and a regent would rule better than a fool. You know what I am asking. Do not make me say it aloud.",
    # ---------------- Catalogue C: foreign courts
    "proxy_war": "You have an army and an appetite. My rival has lands. I have the gold to bring the three together.",
    "partition_pact": "Our neighbour's realm is too large for one master. Strike with me, and let us draw the line now, while we are still friends.",
    "secret_alliance": "Let no herald announce it and no clerk write it down. But if either of us is attacked, the other will march.",
    "bought_truce": "This war costs us both, and I would rather spend my gold on peace than on sellswords. Name the sum.",
    "faithless_ally": "Your ally will call on you when we fight. When that call comes, I would have your levies find themselves otherwise occupied.",
    "turncoat": "Your lord leads you into a war that will not end well for you. Change your banner before the battle, and you will find a warmer welcome on my side of the field.",
    "seed_the_separatists": "Why bow to a distant crown? I will pay for your freedom. You need only take it.",
    "shelter_the_pretender": "Your claim is just, and the usurper knows it. Stay beneath my roof, and when the time comes, my armies will remember your name.",
    "extradition": "You shelter someone who has no right to your protection. Hand them over, and the matter is closed between us.",
    "buy_a_councillor": "Your liege trusts you with the secrets of the realm. I would trust you with a purse. Tell me what is said at that council table, and see that the wrong advice is taken.",
    "stay_home": "When I march against your liege, your levies will be called. See that they are needed at home instead.",
    "defection_pact": "Should your liege lose this war, there will be a new order in these lands. Swear to me now, and you will keep everything you hold.",
    "secret_clause": "Let the marriage contract say what it must. Between ourselves, there is a county in the dowry that no clerk needs to write down.",
    "hire_the_hashashin": "Your order is said never to fail and never to speak. I have a name, and I have the gold.",
    # ---------------- Catalogue D: the Church
    "excommunication_for_hire": "My rival has sinned against heaven; I am certain of it. The Church need only say so, and I will show my gratitude in the way the Church likes best.",
    "dispensation_for_gold": "What the Church has bound, the Church may loosen, for the right offering. I ask only for what is within your power to grant.",
    "steer_the_holy_war": "The faithful will march wherever you point them. Point them where it serves us both.",
    "purchase_a_mitre": "My kin is pious, learned, and in want of a see. I am certain a generous gift to the Church will help you see their virtues.",
    "bought_claim": "Heaven decides who should rule, and you speak for heaven. Let it be heard that my claim is just.",
    "absolution_by_concession": "I have knelt and I have prayed. I will give the Church whatever it requires, if only you will lift this curse from my house.",
    "holy_warrant": "Proclaim a holy war against my enemy, and I will pay for the privilege of fighting it.",
    "buy_a_bull": "A word from the Holy Father carries further than any army. Let that word be spoken, and the Church's coffers will not suffer for it.",
    "conclave_votes": "When the cardinals gather behind locked doors, I would have a friend among them, with the right name on their lips.",
    "council_lobbying": "The question before the council will be settled by votes, and votes can be counted in advance. Let yours be counted with mine.",
    "caliphal_investiture": "I have taken these lands by the sword. All I ask of the Commander of the Faithful is the word that I hold them rightly, and my protection comes with the asking.",
    "name_in_the_khutba": "On Friday, when the prayers are read, let the name spoken be my caliph's, and not your lord's.",
    "fatwa_for_hire": "A learned ruling carries the weight of the law itself. I would have one that says my rival is in the wrong.",
    "fund_the_dawa": "Let your preachers carry the truth to my rival's very capital. My gold will see that they want for nothing on the road.",
    "crowning_the_usurper": "The emperor has lost the favour of heaven. Bless my cause, crown me before the people, and history will remember that the Church chose rightly.",
    "pliant_patriarch": "You sit on the patriarchal throne because I put you there. I would like to know that you remember it.",
    "favourable_omens": "The gods speak through signs, and signs can be read many ways. Read them the way I need.",
    "consecration_rites": "My blood may not be as old as theirs, but rites rightly performed can raise anyone to kingship. Perform them for me.",
    "temple_patronage": "I would see your temple endowed beyond the dreams of its founders. All I ask is that your priests remember their benefactor when they speak to the people.",
    # ---------------- Catalogue F: tribute
    "heavier_tribute": "Your people prosper under my protection, and protection has its price. Let the tribute rise with your fortunes.",
    "lighter_tribute": "The harvests have failed and my treasury is bare. Ease the tribute a little, and I will not forget the kindness.",
    "bought_freedom": "Every year I send you gold, and every year my people curse your name. Name a price for our freedom, and be rid of the cursing.",
    "accept_the_yoke": "My armies are close, and my friendship is worth more than your pride. Send tribute, and you will have both.",
    "cast_off_the_yoke": "You pay tribute to a master who does nothing for you. Stop paying, and let my gold cover what you lose.",
    # ---------------- Catalogue G: in time of war
    "make_peace": "This war bleeds us both, and neither of us will see the end of it in the field. Sign a white peace, and let us both go home.",
    "yield_war": "You cannot win this war, and every month you fight it costs you more. Concede it now, while you still have something to keep.",
    "join_war": "My war is just and my enemies are many. March beside me until it is won, and you will share in what we take.",
    "leave_war": "Their war is not yours. Take your men home before the next battle, and let others bleed for it.",
    "stay_out": "When my enemies send for you, find a reason to stay at home. This war need not be yours.",
    # ---------------- the carrier: goods for goods, no deed
    "barter": "No deed, no blood, nothing that needs hiding. Only what each of us has, and what each of us wants.",
}

GROUP_FLAVOR = {
    "war": "Wars can be bought like anything else: by the season, by the county, or by the corpse.",
    "favours": "Not every bargain needs a battlefield. Some need only a quiet word and a full purse.",
    "family": "Blood binds tighter than any oath, and marriages, vows and votes can all be arranged.",
    "blood": "Some problems are solved by removing them. It is ugly work, and the price reflects it.",
    "shadows": "Factions, plots and informers: the realm is a web, and every thread can be pulled.",
    "abroad": "A foreign court is full of loyalties for sale, if one knows whom to ask.",
    "church_favours": "Grace, they say, is freely given. Everything else the Church dispenses has a price.",
    "church_weapons": "A curse from the altar cuts deeper than any blade, and can be aimed with the same care.",
    "tribute": "Tribute is a bargain renewed every year: what is paid, what is owed, and what neither side says aloud.",
    "wartime": "A war is a bargain too: who fights, who stays home, and what it will take for the killing to stop.",
}
