"""The Backroom Deal window (gui/qpq_pact_window.gui), generated. Called from qpq_ui_gen.gen_all.

Layout: your side on the left, theirs on the right, the table in the middle.
    Each side has two columns. The first lists every action that side could take: goods to give (gold, land,
    claims, hooks...) and deeds to do, grouped. The second configures what is picked: a deed's target and terms,
    the timing of gold, the titles to hand over.
    The middle's top half is the two characters; its bottom half is two lists of what each side has put in.

Which engine leg an action belongs to (see qpq_ui_gen): a deed that YOU do is leg "i" and a deed THEY do is leg
"t"; goods YOU give are leg "t" (you pay for their deed) and goods THEY give are leg "i".
"""
from qpq_kinds import GROUPS

SIDES = {
    "me": dict(D="i", G="t", title="QPQ_UI_YOU_WILL", tier="QpqUiMyTier"),
    "them": dict(D="t", G="i", title="QPQ_UI_THEY_WILL", tier="QpqUiTheirTier"),
}


def gen_gui(write):
    import qpq_ui_gen as U
    GS, GS_ROOT = U.GS, U.GS_ROOT

    def sg(name, what, scope=GS):
        return "[GetScriptedGui('%s').%s( %s )]" % (name, what, scope)

    def not_none(L):
        return "[Not( EqualTo_string( GetPlayer.MakeScope.Var('qpq_ui_%s_kind').GetFlagName, 'none' ) )]" % L

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
                onclick = "[GetVariableSystem.Toggle( 'qpq_land_%s' )]" % side
                down = "[GetVariableSystem.Exists( 'qpq_land_%s' )]" % side
            else:
                onclick = sg("qpq_ui_offer_%s_%s" % (G, o), "Execute")
                down = "[GetPlayer.MakeScope.Var('qpq_ui_%s_o_%s').IsSet]" % (G, o)
            s += """
						button_standard_list = {
							visible = "%s"
							layoutpolicy_horizontal = expanding
							size = { 0 32 }
							text = "qpq_offer_%s"
							tooltip = "%s"
							using = tooltip_ne
							onclick = "%s"
							down = "%s"
						}
""" % (sg("qpq_ui_offer_%s_%s" % (G, o), "IsShown"), o, tip, onclick, down)
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
							down = "[EqualTo_string( GetPlayer.MakeScope.Var('qpq_ui_%s_kind').GetFlagName, '%s' )]"
						}
""" % (sg(n, "IsShown"), k["key"], sg(n, "IsValid"), sg(n, "IsValid")[1:-1], k["key"], sg(n, "BuildTooltip")[1:-1],
                sg(n, "Execute"), D, k["key"])
        return s

    # ------------------------------------------------------------------ the configuration column
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

    def config_col(side):
        D, G = SIDES[side]["D"], SIDES[side]["G"]
        return """
			scrollbox = {
				layoutpolicy_horizontal = expanding
				layoutpolicy_vertical = expanding
				size = { 330 400 }

				blockoverride "scrollbox_content" {
					vbox = {
						layoutpolicy_horizontal = expanding
						spacing = 6
						margin_right = 6

						# The deed
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
								max_width = 290
								autoresize = yes
								text = "[GetPlayer.Custom('QpqUiKindDesc_%(D)s')]"
							}
							text_multi = {
								layoutpolicy_horizontal = expanding
								max_width = 290
								autoresize = yes
								default_format = "#weak"
								text = "QPQ_UI_HINT_LINE_%(DU)s"
							}
						}

						# Its target
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

						# Its terms
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

						# Gold
						vbox = {
							visible = "[GetPlayer.MakeScope.Var('qpq_ui_%(G)s_o_gold').IsSet]"
							layoutpolicy_horizontal = expanding
							margin = { 10 8 }
							spacing = 4

							background = {
								using = Background_Area_Dark
							}

							text_single = {
								layoutpolicy_horizontal = expanding
								text = "QPQ_UI_GOLD_HEADER"
								default_format = "#T"
							}
							text_multi = {
								layoutpolicy_horizontal = expanding
								max_width = 290
								autoresize = yes
								text = "QPQ_UI_GOLD_INFO_%(GU)s"
							}
%(timing_items)s
						}

						# Land: the titles to hand over
						vbox = {
							visible = "[GetVariableSystem.Exists( 'qpq_land_%(side)s' )]"
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
					}
				}
			}
""" % dict(side=side, D=D, G=G, DU=D.upper(), GU=G.upper(), not_none=not_none(D),
           any_target=sg("qpq_ui_needs_any_target_%s" % D, "IsShown", GS_ROOT),
           needs_char=sg("qpq_ui_needs_char_target_%s" % D, "IsShown", GS_ROOT),
           needs_char_expr=sg("qpq_ui_needs_char_target_%s" % D, "IsShown", GS_ROOT)[1:-1],
           needs_title=sg("qpq_ui_needs_title_target_%s" % D, "IsShown", GS_ROOT),
           needs_artifact=sg("qpq_ui_needs_artifact_target_%s" % D, "IsShown", GS_ROOT),
           has_extras=sg("qpq_ui_has_extras_%s" % D, "IsShown", GS_ROOT), extra_items=extra_items(D),
           timing_items=timing_items(G))

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

    # ------------------------------------------------------------------ the table: what each side has put in
    def summary(side):
        D, G = SIDES[side]["D"], SIDES[side]["G"]
        s = """
				vbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					margin = { 12 8 }
					spacing = 3

					background = {
						using = Background_Area_Dark
					}

					text_single = {
						layoutpolicy_horizontal = expanding
						text = "%s"
						default_format = "#T"
					}
					text_multi = {
						visible = "%s"
						layoutpolicy_horizontal = expanding
						max_width = 300
						autoresize = yes
						text = "QPQ_UI_BULLET_DEED_%s"
					}
					text_single = {
						visible = "[GetPlayer.MakeScope.Var('qpq_ui_%s_o_gold').IsSet]"
						layoutpolicy_horizontal = expanding
						text = "[GetPlayer.Custom('QpqUiGoldLine_%s')]"
					}
""" % (SIDES[side]["title"], not_none(D), D.upper(), G, G)
        for o in U.UI_OFFERS[1:]:
            s += """
					text_single = {
						visible = "[GetPlayer.MakeScope.Var('qpq_ui_%s_o_%s').IsSet]"
						layoutpolicy_horizontal = expanding
						text = "QPQ_UI_BULLET_OFFER_%s"
					}
""" % (G, o, o)
            if o == "land":
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

    gui = GUI_TEMPLATE
    for tag, val in (("@@LIST_ME@@", list_col("me")), ("@@CONFIG_ME@@", config_col("me")),
                     ("@@LIST_THEM@@", list_col("them")), ("@@CONFIG_THEM@@", config_col("them")),
                     ("@@CHAR_ME@@", character("me")), ("@@CHAR_THEM@@", character("them")),
                     ("@@SUM_ME@@", summary("me")), ("@@SUM_THEM@@", summary("them"))):
        gui = gui.replace(tag, val)
    gui = gui.replace("@@GS@@", GS).replace("@@GS_ROOT@@", GS_ROOT)
    assert "@@" not in gui
    write("gui/qpq_pact_window.gui", gui)
    # No byte-order mark here: the line is read as a file path
    write("gui/scripted_widgets/qpq_scripted_widgets.txt", "gui/qpq_pact_window.gui = qpq_pact_window\n")  # the game wants utf8-bom here too


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
				onclick = "[GetScriptedGui('qpq_ui_close').Execute( @@GS_ROOT@@ )]"
			}
		}

		hbox = {
			layoutpolicy_horizontal = expanding
			layoutpolicy_vertical = expanding
			spacing = 10

			############ YOUR SIDE: what you can do or give, then its details ############
			hbox = {
				layoutpolicy_vertical = expanding
				spacing = 6
@@LIST_ME@@
@@CONFIG_ME@@
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

				# What each side has put in
				hbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					spacing = 6
@@SUM_ME@@
@@SUM_THEM@@
				}

				# The scandal
				hbox = {
					layoutpolicy_horizontal = expanding
					margin = { 12 6 }
					spacing = 8

					background = {
						using = Background_Area_Dark
					}

					text_multi = {
						layoutpolicy_horizontal = expanding
						max_width = 420
						autoresize = yes
						text = "QPQ_UI_SCANDAL_TEXT"
					}

					button_checkbox_label = {
						visible = "[GetScriptedGui('qpq_ui_charter').IsShown( @@GS_ROOT@@ )]"
						onclick = "[GetScriptedGui('qpq_ui_charter').Execute( @@GS_ROOT@@ )]"
						tooltip = "qpq_offer_charter_desc"
						blockoverride "checkbox" {
							checked = "[GetPlayer.MakeScope.Var('qpq_ui_charter').IsSet]"
						}
						blockoverride "text" {
							text = "qpq_offer_charter"
						}
					}
				}
			}

			############ THEIR SIDE ############
			hbox = {
				layoutpolicy_vertical = expanding
				spacing = 6
@@CONFIG_THEM@@
@@LIST_THEM@@
			}
		}

		############ FOOTER: ACCEPTANCE AND PROPOSE ############
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
				onclick = "[GetScriptedGui('qpq_ui_close').Execute( @@GS_ROOT@@ )]"
			}

			text_multi = {
				layoutpolicy_horizontal = expanding
				max_width = 700
				autoresize = yes
				align = center|nobaseline
				text = "[GetPlayer.Custom('QpqUiAcceptance')]"
				tooltip = "QPQ_UI_ACC_BREAKDOWN"
			}

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
'''
