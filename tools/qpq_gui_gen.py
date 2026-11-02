"""The Backroom Deal windows (gui/qpq_pact_window.gui), generated. Called from qpq_ui_gen.gen_all.

Layout: your side on the left, theirs on the right, the table in the middle.
    Each side has two columns: the list of every action that side could take (goods to give: gold, land, claims,
    hooks...; deeds to do, grouped), and next to it what that side has put into the deal, each with Edit / Remove.
    An action that needs configuring (gold's amount and timing, a deed's target and terms, the titles to hand
    over) opens its own pop-out window (qpq_config_window).
    The middle: the two characters on top, then whether they would agree, the Scandal tier of each side with what
    exposure would cost it, and the secrecy of the deal (public Charter or secret).

Which engine leg an action belongs to (see qpq_ui_gen): a deed that YOU do is leg "i" and a deed THEY do is leg
"t"; goods YOU give are leg "t" (you pay for their deed) and goods THEY give are leg "i".
"""
from qpq_kinds import GROUPS

SIDES = {
    "me": dict(D="i", G="t", title="QPQ_UI_YOU_WILL", tier="QpqUiMyTier", conseq="QpqUiConseqMy"),
    "them": dict(D="t", G="i", title="QPQ_UI_THEY_WILL", tier="QpqUiTheirTier", conseq="QpqUiConseqTheir"),
}


def gen_gui(write):
    import qpq_ui_gen as U
    GS, GS_ROOT = U.GS, U.GS_ROOT

    def sg(name, what, scope=GS):
        return "[GetScriptedGui('%s').%s( %s )]" % (name, what, scope)

    def not_none(L):
        return "[Not( EqualTo_string( GetPlayer.MakeScope.Var('qpq_ui_%s_kind').GetFlagName, 'none' ) )]" % L

    def popup(name):
        return "[GetVariableSystem.Set( 'qpq_popup', '%s' )]" % name

    # ------------------------------------------------------------------ the action list
    def goods_rows(side):
        G = SIDES[side]["G"]
        s = """
						text_single = {
							layoutpolicy_horizontal = expanding
							margin = { 6 4 }
							text = "QPQ_UI_LIST_GOODS"
							default_format = "#T"
							using = Font_Size_Medium
						}
"""
        for o in U.UI_OFFERS:
            tip = ("qpq_demand_%s_desc" if side == "them" and o in U.DEMAND_KEYS else "qpq_offer_%s_desc") % o
            if o == "land":
                clicks = '						onclick = "%s"\n' % popup("land_" + side)
            elif o == "gold":
                clicks = ('						onclick = "%s"\n						onclick = "%s"\n') % (
                    sg("qpq_ui_gold_add_%s" % G, "Execute", GS_ROOT), popup("gold_" + side))
            else:
                clicks = '						onclick = "%s"\n' % sg("qpq_ui_offer_%s_%s" % (G, o), "Execute")
            s += """
					button_standard_list = {
						visible = "%s"
						layoutpolicy_horizontal = expanding
						size = { 0 32 }
						text = "qpq_offer_%s"
						tooltip = "%s"
						using = tooltip_ne
%s						down = "[GetPlayer.MakeScope.Var('qpq_ui_%s_o_%s').IsSet]"
					}
""" % (sg("qpq_ui_offer_%s_%s" % (G, o), "IsShown"), o, tip, clicks, G, o)
        return s

    def deed_rows(side):
        D = SIDES[side]["D"]
        s = ""
        for g, _gname in GROUPS:
            kinds = [k for k in U.DEEDS if k["group"] == g]
            if not kinds:
                continue
            s += """
					text_single = {
						visible = "%s"
						layoutpolicy_horizontal = expanding
						margin = { 6 4 }
						text = "qpq_hub.group.%s"
						default_format = "#T"
						using = Font_Size_Medium
					}
""" % (sg("qpq_ui_group_%s_%s" % (D, g), "IsShown"), g)
            for k in kinds:
                n = "qpq_ui_kind_%s_%s" % (D, k["key"])
                s += """
					button_standard_list = {
						visible = "%s"
						layoutpolicy_horizontal = expanding
						size = { 0 32 }
						text = "qpq_%s_name"
						enabled = "%s"
						tooltip = "[Select_CString( %s, Localize( 'qpq_%s_hub_tt' ), %s )]"
						using = tooltip_ne
						onclick = "%s"
						onclick = "%s"
						down = "[EqualTo_string( GetPlayer.MakeScope.Var('qpq_ui_%s_kind').GetFlagName, '%s' )]"
					}
""" % (sg(n, "IsShown"), k["key"], sg(n, "IsValid"), sg(n, "IsValid")[1:-1], k["key"], sg(n, "BuildTooltip")[1:-1],
                sg(n, "Execute"), popup("deed_" + side), D, k["key"])
        return s

    def list_col(side):
        return """
			scrollbox = {
				layoutpolicy_vertical = expanding
				size = { 290 400 }

				blockoverride "scrollbox_content" {
					vbox = {
						layoutpolicy_horizontal = expanding
						spacing = 2
%s%s
					}
				}
			}
""" % (goods_rows(side), deed_rows(side))

    # ------------------------------------------------------------------ what this side has put in
    def row(visible, text_widget, edit_popup, edit_visible, remove_click):
        edit = ""
        if edit_popup:
            edit = """
						button_standard = {
							%s
							size = { 70 30 }
							text = "QPQ_UI_EDIT"
							onclick = "%s"
						}
""" % ('visible = "%s"' % edit_visible if edit_visible else "", popup(edit_popup))
        return """
					hbox = {
						visible = "%s"
						layoutpolicy_horizontal = expanding
						spacing = 4
%s%s
						button_standard = {
							size = { 90 30 }
							text = "QPQ_UI_REMOVE"
							onclick = "%s"
						}
					}
""" % (visible, text_widget, edit, remove_click)

    def info_col(side):
        D, G = SIDES[side]["D"], SIDES[side]["G"]
        s = """
			vbox = {
				layoutpolicy_vertical = expanding
				size = { 330 400 }
				margin = { 12 8 }
				spacing = 4

				background = {
					using = Background_Area_Dark
				}

				text_single = {
					layoutpolicy_horizontal = expanding
					text = "%s"
					default_format = "#T"
					using = Font_Size_Medium
				}
""" % SIDES[side]["title"]
        # the deed
        s += row(not_none(D), """
						text_multi = {
							layoutpolicy_horizontal = expanding
							max_width = 160
							autoresize = yes
							text = "QPQ_UI_BULLET_DEED_%s"
						}
""" % D.upper(), "deed_" + side, sg("qpq_ui_config_%s" % D, "IsShown", GS_ROOT), sg("qpq_ui_nodeed_%s" % D, "Execute", GS_ROOT))
        # gold
        s += row("[GetPlayer.MakeScope.Var('qpq_ui_%s_o_gold').IsSet]" % G, """
						text_multi = {
							layoutpolicy_horizontal = expanding
							max_width = 160
							autoresize = yes
							text = "[GetPlayer.Custom('QpqUiGoldLine_%s')]"
						}
""" % G, "gold_" + side, None, sg("qpq_ui_offer_%s_gold" % G, "Execute"))
        # the other goods
        for o in U.UI_OFFERS[1:]:
            text = """
						text_single = {
							layoutpolicy_horizontal = expanding
							text = "QPQ_UI_BULLET_OFFER_%s"
						}
""" % o
            if o == "land":
                s += row("[GetPlayer.MakeScope.Var('qpq_ui_%s_o_land').IsSet]" % G, text, "land_" + side, None,
                         sg("qpq_ui_land_clear_%s" % G, "Execute", GS_ROOT))
                s += """
					vbox = {
						layoutpolicy_horizontal = expanding
						margin_left = 14
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%s_land')]"

						item = {
							text_single = {
								layoutpolicy_horizontal = expanding
								text = "[Scope.Title.GetNameNoTooltip]"
								default_format = "#low"
							}
						}
					}
""" % G
            else:
                s += row("[GetPlayer.MakeScope.Var('qpq_ui_%s_o_%s').IsSet]" % (G, o), text, None, None,
                         sg("qpq_ui_offer_%s_%s" % (G, o), "Execute"))
        s += """
				text_single = {
					visible = "%s"
					layoutpolicy_horizontal = expanding
					text = "QPQ_UI_NOTHING_YET"
					default_format = "#weak"
				}
				expand = {}
			}
""" % sg("qpq_ui_%s_empty" % side, "IsShown", GS_ROOT)
        return s

    # ------------------------------------------------------------------ the pop-out window
    def timing_items(G):
        s = ""
        for t in U.TIMINGS:
            if t == "up_front":
                label = "qpq_demand_up_front" if G == "i" else "QPQ_UI_TIMING_UP_FRONT"
            else:
                label = ("qpq_demand_%s" % t) if G == "i" else ("qpq_offer_%s" % t)
            s += """
						button_radio_label = {
							visible = "%s"
							onclick = "%s"
							tooltip = "%s_desc"
							blockoverride "radio" {
								frame = "[BoolTo1And2( EqualTo_string( GetPlayer.MakeScope.Var('qpq_ui_%s_timing').GetFlagName, '%s' ) )]"
							}
							blockoverride "text" {
								text = "%s"
							}
						}
""" % (sg("qpq_ui_timing_%s_%s" % (G, t), "IsShown", GS_ROOT), sg("qpq_ui_timing_%s_%s" % (G, t), "Execute", GS_ROOT),
                label, G, t, label)
        return s

    def extra_items(D):
        s = ""
        for flag, (x, _kinds) in U.extras().items():
            s += """
						button_checkbox_label = {
							visible = "%s"
							onclick = "%s"
							tooltip = "%s"
							blockoverride "checkbox" {
								checked = "[GetPlayer.MakeScope.Var('qpq_ui_%s_%s').IsSet]"
							}
							blockoverride "text" {
								text = "%s"
							}
						}
""" % (sg("qpq_ui_extra_%s_%s" % (D, flag), "IsShown", GS_ROOT), sg("qpq_ui_extra_%s_%s" % (D, flag), "Execute", GS_ROOT),
                x["desc"], D, flag, x["loc"])
        return s

    def deed_popup(side):
        D = SIDES[side]["D"]
        return """
				vbox = {
					visible = "[GetVariableSystem.HasValue( 'qpq_popup', 'deed_%(side)s' )]"
					layoutpolicy_horizontal = expanding
					spacing = 6

					vbox = {
						visible = "%(not_none)s"
						layoutpolicy_horizontal = expanding
						margin = { 10 8 }
						spacing = 4

						background = {
							using = Background_Area_Dark
						}

						text_single = {
							layoutpolicy_horizontal = expanding
							text = "[GetPlayer.Custom('QpqUiKindName_%(D)s')]"
							default_format = "#T"
							using = Font_Size_Medium
						}
						text_multi = {
							layoutpolicy_horizontal = expanding
							max_width = 480
							autoresize = yes
							text = "[GetPlayer.Custom('QpqUiKindDesc_%(D)s')]"
						}
						text_multi = {
							layoutpolicy_horizontal = expanding
							max_width = 480
							autoresize = yes
							default_format = "#weak"
							text = "QPQ_UI_HINT_LINE_%(DU)s"
						}
					}

					text_single = {
						visible = "%(any_target)s"
						layoutpolicy_horizontal = expanding
						margin_left = 6
						text = "QPQ_UI_PICK_TARGET"
						default_format = "#T"
					}
					vbox = {
						visible = "%(needs_char)s"
						layoutpolicy_horizontal = expanding
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%(D)s_candidates')]"

						item = {
							potential_selectable_target_portrait_widget = {
								datacontext = "[Scope.Char]"

								blockoverride "onclick" {
									onclick = "[GetScriptedGui('qpq_ui_pick_char_%(D)s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'qpq_pick', Character.MakeScope ).End )]"
									down = "[ObjectsEqual( GetPlayer.MakeScope.Var('qpq_ui_%(D)s_pick_char').Char, Character.Self )]"
								}
							}
						}
					}
					text_single = {
						visible = "[And( %(needs_char_expr)s, IsDataModelEmpty( GetPlayer.MakeScope.GetList('qpq_ui_%(D)s_candidates') ) )]"
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_NO_CANDIDATES"
					}
					vbox = {
						visible = "%(needs_title)s"
						layoutpolicy_horizontal = expanding
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%(D)s_title_candidates')]"

						item = {
							button_standard_list = {
								layoutpolicy_horizontal = expanding
								size = { 0 34 }
								text = "[Scope.Title.GetNameNoTooltip]"
								onclick = "[GetScriptedGui('qpq_ui_pick_title_%(D)s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'qpq_pick', Scope.Title.MakeScope ).End )]"
								down = "[ObjectsEqual( GetPlayer.MakeScope.Var('qpq_ui_%(D)s_target_title').Title, Scope.Title )]"
							}
						}
					}
					vbox = {
						visible = "%(needs_artifact)s"
						layoutpolicy_horizontal = expanding
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%(D)s_artifact_candidates')]"

						item = {
							button_standard_list = {
								layoutpolicy_horizontal = expanding
								size = { 0 34 }
								text = "[Scope.Artifact.GetName]"
								onclick = "[GetScriptedGui('qpq_ui_pick_artifact_%(D)s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'qpq_pick', Scope.Artifact.MakeScope ).End )]"
								down = "[ObjectsEqual( GetPlayer.MakeScope.Var('qpq_ui_%(D)s_target_artifact').Artifact, Scope.Artifact )]"
							}
						}
					}
					vbox = {
						visible = "%(has_extras)s"
						layoutpolicy_horizontal = expanding
						margin = { 10 8 }
						spacing = 4

						background = {
							using = Background_Area_Dark
						}

						text_single = {
							layoutpolicy_horizontal = expanding
							text = "QPQ_UI_EXTRAS_HEADER"
							default_format = "#T"
						}
%(extra_items)s
					}
				}
""" % dict(side=side, D=D, DU=D.upper(), not_none=not_none(D),
           any_target=sg("qpq_ui_needs_any_target_%s" % D, "IsShown", GS_ROOT),
           needs_char=sg("qpq_ui_needs_char_target_%s" % D, "IsShown", GS_ROOT),
           needs_char_expr=sg("qpq_ui_needs_char_target_%s" % D, "IsShown", GS_ROOT)[1:-1],
           needs_title=sg("qpq_ui_needs_title_target_%s" % D, "IsShown", GS_ROOT),
           needs_artifact=sg("qpq_ui_needs_artifact_target_%s" % D, "IsShown", GS_ROOT),
           has_extras=sg("qpq_ui_has_extras_%s" % D, "IsShown", GS_ROOT), extra_items=extra_items(D))

    def gold_steps(G, sign):
        s = ""
        order = list(reversed(U.GOLD_STEPS)) if sign < 0 else list(U.GOLD_STEPS)
        for n in order:
            name = "qpq_ui_gold_%s_%s_%d" % ("up" if sign > 0 else "down", G, n)
            s += """
							button_standard_list = {
								size = { 64 30 }
								text = "%s%d"
								onclick = "%s"
							}
""" % ("+" if sign > 0 else "-", n, sg(name, "Execute", GS_ROOT))
        return s

    def gold_popup(side):
        G = SIDES[side]["G"]
        return """
				vbox = {
					visible = "[GetVariableSystem.HasValue( 'qpq_popup', 'gold_%(side)s' )]"
					layoutpolicy_horizontal = expanding
					margin = { 10 8 }
					spacing = 6

					background = {
						using = Background_Area_Dark
					}

					text_single = {
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_GOLD_HEADER"
						default_format = "#T"
						using = Font_Size_Medium
					}
					text_multi = {
						layoutpolicy_horizontal = expanding
						max_width = 480
						autoresize = yes
						text = "QPQ_UI_GOLD_INFO_%(GU)s"
					}
						hbox = {
							layoutpolicy_horizontal = expanding
							spacing = 4
%(steps_down)s
							text_single = {
								layoutpolicy_horizontal = expanding
								align = center|nobaseline
								text = "QPQ_UI_GOLD_AMOUNT_%(GU)s"
								using = Font_Size_Medium
							}
%(steps_up)s
						}
						button_standard_list = {
							layoutpolicy_horizontal = expanding
							size = { 0 30 }
							text = "QPQ_UI_GOLD_FAIR"
							visible = "%(fair_shown)s"
							onclick = "%(fair_exec)s"
							tooltip = "QPQ_UI_GOLD_FAIR_TT"
						}
						text_multi = {
							layoutpolicy_horizontal = expanding
							max_width = 480
							autoresize = yes
							align = center|nobaseline
							text = "[GetPlayer.Custom('QpqUiAcceptance')]"
						}
%(timing_items)s
				}
""" % dict(side=side, GU=G.upper(), timing_items=timing_items(G), steps_down=gold_steps(G, -1), steps_up=gold_steps(G, 1),
           fair_shown=sg("qpq_ui_gold_fair_%s" % G, "IsShown", GS_ROOT), fair_exec=sg("qpq_ui_gold_fair_%s" % G, "Execute", GS_ROOT))

    def land_popup(side):
        G = SIDES[side]["G"]
        return """
				vbox = {
					visible = "[GetVariableSystem.HasValue( 'qpq_popup', 'land_%(side)s' )]"
					layoutpolicy_horizontal = expanding
					margin = { 10 8 }
					spacing = 4

					background = {
						using = Background_Area_Dark
					}

					text_single = {
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_LAND_CHOSEN"
						default_format = "#T"
						using = Font_Size_Medium
					}
					vbox = {
						layoutpolicy_horizontal = expanding
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%(G)s_land')]"

						item = {
							button_standard_list = {
								layoutpolicy_horizontal = expanding
								size = { 0 34 }
								down = yes
								text = "[Scope.Title.GetNameNoTooltip]"
								onclick = "[GetScriptedGui('qpq_ui_land_toggle_%(G)s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'qpq_pick', Scope.Title.MakeScope ).End )]"
							}
						}
					}
					text_single = {
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_LAND_AVAILABLE"
						default_format = "#T"
					}
					vbox = {
						layoutpolicy_horizontal = expanding
						datamodel = "[GetPlayer.MakeScope.GetList('qpq_ui_%(G)s_land_candidates')]"

						item = {
							button_standard_list = {
								layoutpolicy_horizontal = expanding
								size = { 0 34 }
								text = "[Scope.Title.GetNameNoTooltip]"
								onclick = "[GetScriptedGui('qpq_ui_land_toggle_%(G)s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'qpq_pick', Scope.Title.MakeScope ).End )]"
							}
						}
					}
					text_single = {
						visible = "[IsDataModelEmpty( GetPlayer.MakeScope.GetList('qpq_ui_%(G)s_land_candidates') )]"
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_LAND_NONE"
						default_format = "#weak"
					}
				}
""" % dict(side=side, G=G)

    def character(side):
        who = "GetPlayer" if side == "me" else "GetPlayer.MakeScope.Var('qpq_ui_recipient').Char"
        label = "QPQ_UI_YOU_LABEL" if side == "me" else "QPQ_UI_THEM_LABEL"
        return """
				vbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					spacing = 2

					portrait_shoulders = {
						datacontext = "[%s]"
						size = { 190 190 }
						parentanchor = hcenter
					}
					text_single = {
						layoutpolicy_horizontal = expanding
						text = "%s"
						default_format = "#T"
						align = center|nobaseline
					}
					text_single = {
						layoutpolicy_horizontal = expanding
						text = "[GetPlayer.Custom('%s')]"
						default_format = "#low"
						align = center|nobaseline
						tooltip = "QPQ_UI_TIER_TT"
					}
				}
""" % (who, label, SIDES[side]["tier"])

    def conseq(side):
        return """
				vbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					spacing = 3

					text_single = {
						layoutpolicy_horizontal = expanding
						text = "%s"
						default_format = "#T"
					}
					text_single = {
						layoutpolicy_horizontal = expanding
						text = "[GetPlayer.Custom('%s')]"
						default_format = "#high"
					}
					text_multi = {
						layoutpolicy_horizontal = expanding
						max_width = 190
						autoresize = yes
						text = "[GetPlayer.Custom('%s')]"
					}
				}
""" % ("QPQ_UI_YOUR_HALF" if side == "me" else "QPQ_UI_THEIR_HALF", SIDES[side]["tier"], SIDES[side]["conseq"])

    popups = "".join(deed_popup(s) + gold_popup(s) + land_popup(s) for s in ("me", "them"))
    # The pop-out has something to show unless a deed with nothing to configure was just picked
    visible = ("[And( GetVariableSystem.Exists( 'qpq_popup' ), And( "
               "Or( Not( GetVariableSystem.HasValue( 'qpq_popup', 'deed_me' ) ), %s ), "
               "Or( Not( GetVariableSystem.HasValue( 'qpq_popup', 'deed_them' ) ), %s ) ) )]") % (
        sg("qpq_ui_config_i", "IsShown", GS_ROOT)[1:-1], sg("qpq_ui_config_t", "IsShown", GS_ROOT)[1:-1])

    gui = GUI_TEMPLATE
    for tag, val in (("@@LIST_ME@@", list_col("me")), ("@@INFO_ME@@", info_col("me")),
                     ("@@LIST_THEM@@", list_col("them")), ("@@INFO_THEM@@", info_col("them")),
                     ("@@CHAR_ME@@", character("me")), ("@@CHAR_THEM@@", character("them")),
                     ("@@CONSEQ_ME@@", conseq("me")), ("@@CONSEQ_THEM@@", conseq("them")),
                     ("@@POPUPS@@", popups), ("@@POPUP_VISIBLE@@", visible)):
        gui = gui.replace(tag, val)
    gui = gui.replace("@@GS@@", GS).replace("@@GS_ROOT@@", GS_ROOT)
    assert "@@" not in gui
    write("gui/qpq_pact_window.gui", gui)
    # One line per window in the file
    write("gui/scripted_widgets/qpq_scripted_widgets.txt",
          "gui/qpq_pact_window.gui = qpq_pact_window\ngui/qpq_pact_window.gui = qpq_config_window\n")


GUI_TEMPLATE = r'''######################################################
################ QUID PRO QUO: A BACKROOM DEAL #######
######################################################
# GENERATED by tools/qpq_gen.py (tools/qpq_gui_gen.py). Built from vanilla parts: the interaction
# window frame and header, scrollbox, button_standard_list, button_checkbox_label / button_radio_label,
# button_primary and the activity planner's selectable portrait rows.

window = {
	name = "qpq_pact_window"
	parentanchor = center
	position = { 0 10 }
	allow_outside = yes
	layer = middle
	movable = yes
	size = { 1760 900 }
	datacontext = "[GetPlayer]"

	visible = "[GetPlayer.MakeScope.Var('qpq_ui_open').IsSet]"

	using = Window_Background
	using = Window_Decoration_Spike

	state = {
		name = _show
		using = Animation_FadeIn_Quick
		using = Sound_WindowShow_Standard
	}

	state = {
		name = _hide
		using = Animation_FadeOut_Quick
		using = Sound_WindowHide_Standard
	}

	vbox = {
		using = Window_Margins
		layoutpolicy_horizontal = expanding
		layoutpolicy_vertical = expanding
		spacing = 6

		############ HEADER ############
		header_pattern_interaction = {
			layoutpolicy_horizontal = expanding

			blockoverride "header_text" {
				text = "QPQ_UI_TITLE"
			}

			blockoverride "button_close" {
				onclick = "[GetVariableSystem.Clear( 'qpq_popup' )]"
				onclick = "[GetScriptedGui('qpq_ui_close').Execute( @@GS_ROOT@@ )]"
			}
		}

		hbox = {
			layoutpolicy_horizontal = expanding
			layoutpolicy_vertical = expanding
			spacing = 10

			############ YOUR SIDE: what you can do or give, and what you have put in ############
			hbox = {
				layoutpolicy_vertical = expanding
				spacing = 6
@@LIST_ME@@
@@INFO_ME@@
			}

			############ THE TABLE ############
			vbox = {
				layoutpolicy_horizontal = expanding
				layoutpolicy_vertical = expanding
				spacing = 6

				# The two characters
				hbox = {
					layoutpolicy_horizontal = expanding
					margin = { 10 8 }
					spacing = 10

					background = {
						using = Background_Area_Dark
					}
@@CHAR_ME@@
@@CHAR_THEM@@
				}

				# Would they agree?
				vbox = {
					layoutpolicy_horizontal = expanding
					margin = { 12 8 }
					spacing = 3

					background = {
						using = Background_Area_Dark
					}

					text_multi = {
						layoutpolicy_horizontal = expanding
						max_width = 420
						autoresize = yes
						align = center|nobaseline
						text = "[GetPlayer.Custom('QpqUiAcceptance')]"
						tooltip = "QPQ_UI_ACC_BREAKDOWN"
						using = Font_Size_Medium
					}
				}

				# The scandal, and what exposure would cost each side
				vbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					margin = { 12 8 }
					spacing = 6

					background = {
						using = Background_Area_Dark
					}

					text_single = {
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_SCANDAL_HEADER"
						tooltip = "QPQ_UI_SCANDAL_TEXT"
						default_format = "#T"
						using = Font_Size_Medium
					}
					hbox = {
						layoutpolicy_horizontal = expanding
						spacing = 10
@@CONSEQ_ME@@
@@CONSEQ_THEM@@
					}

					# How secret the deal is
					text_single = {
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_SECRECY_HEADER"
						default_format = "#T"
						using = Font_Size_Medium
					}
					button_radio_label = {
						onclick = "[GetScriptedGui('qpq_ui_secrecy_secret').Execute( @@GS_ROOT@@ )]"
						tooltip = "QPQ_UI_SECRECY_SECRET_TT"
						blockoverride "radio" {
							frame = "[BoolTo1And2( Not( GetPlayer.MakeScope.Var('qpq_ui_charter').IsSet ) )]"
						}
						blockoverride "text" {
							text = "QPQ_UI_SECRECY_SECRET_LABEL"
						}
					}
					button_radio_label = {
						onclick = "[GetScriptedGui('qpq_ui_secrecy_public').Execute( @@GS_ROOT@@ )]"
						tooltip = "QPQ_UI_SECRECY_PUBLIC_TT"
						blockoverride "radio" {
							frame = "[BoolTo1And2( GetPlayer.MakeScope.Var('qpq_ui_charter').IsSet )]"
						}
						blockoverride "text" {
							text = "QPQ_UI_SECRECY_PUBLIC_LABEL"
						}
					}
					text_multi = {
						layoutpolicy_horizontal = expanding
						max_width = 420
						autoresize = yes
						text = "[GetPlayer.Custom('QpqUiSecrecyNote')]"
					}
					expand = {}
				}
			}

			############ THEIR SIDE ############
			hbox = {
				layoutpolicy_vertical = expanding
				spacing = 6
@@INFO_THEM@@
@@LIST_THEM@@
			}
		}

		############ FOOTER ############
		hbox = {
			layoutpolicy_horizontal = expanding
			margin = { 10 8 }
			spacing = 10

			background = {
				using = Background_Area_Dark
			}

			button_standard = {
				size = { 160 44 }
				text = "QPQ_UI_CANCEL"
				onclick = "[GetVariableSystem.Clear( 'qpq_popup' )]"
				onclick = "[GetScriptedGui('qpq_ui_close').Execute( @@GS_ROOT@@ )]"
			}

			expand = {}

			button_primary = {
				size = { 260 44 }
				text = "QPQ_UI_PROPOSE"
				enabled = "[GetScriptedGui('qpq_ui_propose').IsValid( @@GS@@ )]"
				tooltip = "[GetScriptedGui('qpq_ui_propose').BuildTooltip( @@GS@@ )]"
				onclick = "[GetScriptedGui('qpq_ui_propose').Execute( @@GS@@ )]"
			}
		}
	}
}

######################################################
# The pop-out for anything that needs configuring: a deed's target and terms, gold's timing, the titles to hand over
######################################################
window = {
	name = "qpq_config_window"
	parentanchor = center
	position = { 0 0 }
	allow_outside = yes
	layer = top
	movable = yes
	size = { 560 720 }
	datacontext = "[GetPlayer]"

	visible = "@@POPUP_VISIBLE@@"

	using = Window_Background
	using = Window_Decoration_Spike

	state = {
		name = _show
		using = Animation_FadeIn_Quick
		using = Sound_WindowShow_Standard
	}

	state = {
		name = _hide
		using = Animation_FadeOut_Quick
		using = Sound_WindowHide_Standard
	}

	vbox = {
		using = Window_Margins
		layoutpolicy_horizontal = expanding
		layoutpolicy_vertical = expanding
		spacing = 6

		header_pattern_interaction = {
			layoutpolicy_horizontal = expanding

			blockoverride "header_text" {
				text = "QPQ_UI_CONFIG_TITLE"
			}

			blockoverride "button_close" {
				onclick = "[GetVariableSystem.Clear( 'qpq_popup' )]"
			}
		}

		scrollbox = {
			layoutpolicy_horizontal = expanding
			layoutpolicy_vertical = expanding
			size = { 520 500 }

			blockoverride "scrollbox_content" {
				vbox = {
					layoutpolicy_horizontal = expanding
					spacing = 6
@@POPUPS@@
				}
			}
		}

		button_primary = {
			layoutpolicy_horizontal = expanding
			size = { 0 44 }
			text = "QPQ_UI_DONE"
			onclick = "[GetVariableSystem.Clear( 'qpq_popup' )]"
		}
	}
}
'''
