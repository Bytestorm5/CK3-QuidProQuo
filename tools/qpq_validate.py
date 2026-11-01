#!/usr/bin/env python3
"""Static checks for the Quid Pro Quo mod.

    python3 tools/qpq_validate.py --vanilla /path/to/ck3/game [--tiger /path/to/tiger]

Checks: script syntax (braces, operators), every effect/trigger/iterator keyword against the
vanilla game files (and the tiger tables when given), references to our own and vanilla
definitions (scripted effects/triggers, script values, opinion modifiers, modifiers, hooks,
secret types, events, interactions, casus belli, story cycles, traits), saved scopes and
variables that are used but never set, and localization keys that are used but missing.
Exit code 1 if anything is reported.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ parser
TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|<=|>=|!=|\?=|==|[{}=<>]|[^\s{}=<>"#]+')


class Node:
    __slots__ = ("key", "op", "value", "line", "file")

    def __init__(self, key, op, value, line, file):
        self.key, self.op, self.value, self.line, self.file = key, op, value, line, file


def tokenize(text):
    toks = []
    for lineno, line in enumerate(text.split("\n"), 1):
        # strip comments outside strings
        out, in_str = [], False
        for i, c in enumerate(line):
            if c == '"':
                in_str = not in_str
            if c == "#" and not in_str:
                break
            out.append(c)
        for m in TOKEN_RE.finditer("".join(out)):
            toks.append((m.group(0), lineno))
    return toks


class ParseError(Exception):
    pass


def parse(text, fname):
    toks = tokenize(text.lstrip("﻿"))
    pos = 0
    OPS = {"=", "<", ">", "<=", ">=", "!=", "?=", "=="}

    def parse_block(depth):
        nonlocal pos
        items = []
        while pos < len(toks):
            tok, line = toks[pos]
            if tok == "}":
                if depth == 0:
                    raise ParseError("%s:%d unexpected }" % (fname, line))
                pos += 1
                return items
            if tok == "{":
                pos += 1
                items.append(Node(None, None, parse_block(depth + 1), line, fname))
                continue
            if tok in OPS:
                raise ParseError("%s:%d unexpected operator %s" % (fname, line, tok))
            # key [op value]
            pos += 1
            if pos < len(toks) and toks[pos][0] in OPS:
                op = toks[pos][0]
                pos += 1
                if pos >= len(toks):
                    raise ParseError("%s:%d missing value" % (fname, line))
                vtok, vline = toks[pos]
                if vtok == "{":
                    pos += 1
                    items.append(Node(tok, op, parse_block(depth + 1), line, fname))
                elif vtok in OPS or vtok == "}":
                    raise ParseError("%s:%d bad value after %s" % (fname, line, tok))
                else:
                    pos += 1
                    items.append(Node(tok, op, vtok, line, fname))
            else:
                items.append(Node(None, None, tok, line, fname))
        if depth != 0:
            raise ParseError("%s: unclosed {" % fname)
        return items

    return parse_block(0)


def walk(nodes, parents=()):
    for n in nodes:
        yield n, parents
        if isinstance(n.value, list):
            yield from walk(n.value, parents + (n,))


def read(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def files_under(base, ext=".txt"):
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            if fn.endswith(ext):
                yield os.path.join(dp, fn)


# ------------------------------------------------------------------ vanilla knowledge
def top_keys(path_glob_dir):
    keys = set()
    if not os.path.isdir(path_glob_dir):
        return keys
    for f in files_under(path_glob_dir):
        try:
            for n in parse(read(f), f):
                if n.key and isinstance(n.value, list):
                    keys.add(n.key)
                elif n.key and n.key.startswith("@"):
                    pass
        except ParseError:
            pass
    return keys


def all_keys(base_dirs):
    keys = set()
    for d in base_dirs:
        for f in files_under(d):
            try:
                for n, _p in walk(parse(read(f), f)):
                    if n.key:
                        keys.add(n.key)
            except ParseError:
                pass
    return keys


def load_loc_keys(base):
    keys = set()
    for f in files_under(base, ".yml"):
        for line in read(f).split("\n"):
            m = re.match(r'\s*([A-Za-z0-9_.\-]+):\d*\s*"', line)
            if m:
                keys.add(m.group(1))
    return keys


def tiger_names(tiger):
    names = set()
    iters = set()
    if not tiger:
        return names, iters
    t = os.path.join(tiger, "src/ck3/tables")
    for fn in ("effects.rs", "triggers.rs", "targets.rs"):
        p = os.path.join(t, fn)
        if os.path.exists(p):
            names |= set(re.findall(r'"([a-z_0-9]+)"', read(p)))
    p = os.path.join(t, "iterators.rs")
    if os.path.exists(p):
        iters |= set(re.findall(r'\(Scopes::[A-Za-z:|() ]+, "([a-z_0-9]+)"', read(p)))
    return names, iters


STRUCTURAL = {
    # control flow and scripting structure
    "if", "else_if", "else", "limit", "trigger_if", "trigger_else_if", "trigger_else", "AND", "OR", "NOT", "NOR",
    "NAND", "ALL_FALSE", "ANY_TRUE", "switch", "random", "random_list", "chance", "modifier", "weight", "value",
    "add", "subtract", "multiply", "divide", "min", "max", "round", "floor", "ceiling", "desc", "text", "trigger",
    "effect", "base", "factor", "count", "percent", "order_by", "position", "type", "target", "name", "years",
    "months", "days", "weeks", "list", "variable", "save_scope_as", "save_temporary_scope_as", "show_as_tooltip",
    "hidden_effect", "custom_tooltip", "custom_description", "subject", "object", "triggered_desc", "first_valid",
    "random_valid", "fallback", "even_if_dead", "always", "exists", "this", "root", "prev", "from", "abs",
    "opinion_modifier", "who", "opinion_target", "multiplier", "history", "actor", "recipient", "title", "flag",
    "localization", "current_description", "is_shown", "is_valid", "can_be_changed", "starts_enabled",
    "localization_key", "setup_scope", "random_valid", "log_loc_errors", "if_invalid_loc", "weight_multiplier",
    "option", "immediate", "after", "theme", "left_portrait", "right_portrait", "lower_right_portrait",
    "lower_left_portrait", "character", "animation", "events", "on_actions", "random_events", "delay", "id",
    "categories", "default", "icon", "reference", "category", "on_expose", "on_discover", "is_valid", "is_shunned",
    "is_criminal", "on_owner_death", "visible", "visualization", "basic_counter", "variable_name", "label",
    "min_label", "max_label", "tooltip", "custom_string_key", "on_setup", "on_end", "effect_group",
    "triggered_effect", "level", "opinion", "decaying", "stacking", "imprisonment_reason", "revoke_title_reason",
    "execute_reason", "strong", "expiration_days", "requires_secret", "change", "holder", "add_claim_on_loss",
    "liege", "faction", "forced_by", "allied_through_owner", "allied_through_target", "casus_belli",
    "target_title", "target_character", "claimant", "death_reason", "killer", "gold", "piety", "prestige",
    "cost", "group", "picture", "desc", "selection_tooltip", "ai_check_interval", "ai_will_do",
    "decision_group_type", "sort_order", "is_shown", "redirect", "send_option", "interaction", "remove_existing_councillor",
    "trait", "VICTIM",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla", required=True, help="CK3 game directory (contains common/, events/, localization/)")
    ap.add_argument("--tiger", help="tiger checkout, for its effect/trigger tables")
    args = ap.parse_args()
    V = args.vanilla
    problems = []

    def report(msg):
        problems.append(msg)

    # ---- parse our files
    mod_files = [f for d in ("common", "events") for f in files_under(os.path.join(ROOT, d))]
    trees = {}
    for f in mod_files:
        txt = read(f)
        try:
            trees[f] = parse(txt, os.path.relpath(f, ROOT))
        except ParseError as e:
            report("SYNTAX " + str(e))
    for f in files_under(os.path.join(ROOT, "localization"), ".yml"):
        raw = open(f, "rb").read()
        if not raw.startswith(b"\xef\xbb\xbf"):
            report("LOC %s: missing UTF-8 BOM" % os.path.relpath(f, ROOT))
        if not os.path.basename(f).endswith("_l_english.yml"):
            report("LOC %s: file name must end in _l_english.yml" % f)

    def defs(sub):
        out = {}
        for f, tree in trees.items():
            rel = os.path.relpath(f, ROOT)
            if rel.startswith(sub):
                for n in tree:
                    if n.key and (isinstance(n.value, list) or sub.startswith("common/script_values")):
                        if n.key in out:
                            report("DUPLICATE %s defined in %s and %s" % (n.key, out[n.key], rel))
                        out[n.key] = rel
        return out

    my = {
        "effects": defs("common/scripted_effects"),
        "triggers": defs("common/scripted_triggers"),
        "values": defs("common/script_values"),
        "opinions": defs("common/opinion_modifiers"),
        "modifiers": defs("common/modifiers"),
        "hooks": defs("common/hook_types"),
        "secrets": defs("common/secret_types"),
        "stories": defs("common/story_cycles"),
        "cbs": defs("common/casus_belli_types"),
        "interactions": defs("common/character_interactions"),
        "decisions": defs("common/decisions"),
        "custom_loc": defs("common/customizable_localization"),
        "on_actions": defs("common/on_action"),
        "rules": defs("common/game_rules"),
    }
    events = {}
    for f, tree in trees.items():
        if os.path.relpath(f, ROOT).startswith("events"):
            for n in tree:
                if n.key and re.match(r"^qpq_[a-z]+\.\d+$", n.key):
                    events[n.key] = f

    # ---- vanilla knowledge
    vc = os.path.join(V, "common")
    van = {
        "effects": top_keys(os.path.join(vc, "scripted_effects")),
        "triggers": top_keys(os.path.join(vc, "scripted_triggers")),
        "values": set(),
        "opinions": top_keys(os.path.join(vc, "opinion_modifiers")),
        "modifiers": top_keys(os.path.join(vc, "modifiers")),
        "hooks": top_keys(os.path.join(vc, "hook_types")),
        "traits": top_keys(os.path.join(vc, "traits")),
        "schemes": top_keys(os.path.join(vc, "schemes/scheme_types")),
        "factions": top_keys(os.path.join(vc, "factions")),
        "cbs": top_keys(os.path.join(vc, "casus_belli_types")),
        "councils": top_keys(os.path.join(vc, "council_positions")),
        "scripted_modifiers": top_keys(os.path.join(vc, "scripted_modifiers")),
    }
    for f in files_under(os.path.join(vc, "script_values")):
        for line in read(f).split("\n"):
            m = re.match(r"^([A-Za-z_0-9]+)\s*=", line.lstrip("﻿"))
            if m:
                van["values"].add(m.group(1))
    print("vanilla: %d effects, %d triggers, %d values, %d traits" % (
        len(van["effects"]), len(van["triggers"]), len(van["values"]), len(van["traits"])))
    vanilla_keys = all_keys([os.path.join(V, "common"), os.path.join(V, "events")])
    tnames, titers = tiger_names(args.tiger)
    known_kw = vanilla_keys | tnames | STRUCTURAL
    for it in titers:
        for p in ("any_", "every_", "random_", "ordered_"):
            known_kw.add(p + it)
    loc = load_loc_keys(os.path.join(V, "localization/english")) | load_loc_keys(os.path.join(ROOT, "localization"))
    my_loc = load_loc_keys(os.path.join(ROOT, "localization"))

    known_scripted = set(my["effects"]) | set(my["triggers"]) | van["effects"] | van["triggers"] | \
        set(my["values"]) | van["values"] | van["scripted_modifiers"]
    known_kw |= known_scripted

    # ---- walk our trees
    saved, used_scopes = set(), defaultdict(list)
    set_vars, used_vars = set(), defaultdict(list)
    loc_used = defaultdict(list)
    BUILTIN_SCOPES = {"actor", "recipient", "secondary_recipient", "secondary_actor", "target", "attacker",
                      "defender", "war", "secret_owner", "secret_target", "secret_exposer", "discoverer", "story",
                      "killer", "transfer_type", "new_holder", "imprisoner", "previous_holder", "title",
                      "puppet_or_actor", "claimant", "change", "landed_title", "old_liege", "intermediary"}
    LOC_FIELDS = {"desc", "title", "name", "text", "localization", "current_description", "custom_tooltip",
                  "send_name", "prompt", "on_invalidated_desc", "war_name", "war_name_base", "cb_name",
                  "selection_tooltip", "label", "min_label", "max_label", "tooltip", "custom_string_key",
                  "localization_key", "options_heading", "notification_text"}
    for f, tree in trees.items():
        rel = os.path.relpath(f, ROOT)
        top_dir = rel.split(os.sep)[1] if rel.startswith("common") else "events"
        for n, parents in walk(tree):
            k = n.key
            if k is None:
                continue
            pkeys = [p.key for p in parents]
            # saved scopes
            if k in ("save_scope_as", "save_temporary_scope_as", "SAVE") and isinstance(n.value, str):
                saved.add(n.value)
                saved.add(n.value.replace("$ROLE$", "payer"))
                saved.add(n.value.replace("$ROLE$", "agent"))
                if "$SLOT$" in n.value:
                    saved.update("qpq_l%d" % i for i in range(1, 6))
            if k in ("save_scope_value_as", "save_temporary_scope_value_as") and isinstance(n.value, list):
                for c in n.value:
                    if c.key == "name":
                        saved.add(c.value)
                        saved.add(c.value.replace("$ROLE$", "payer"))
                        saved.add(c.value.replace("$ROLE$", "agent"))
            if k == "flag" and parents and parents[-1].key == "send_option":
                saved.add(n.value)
            if k == "save_scope_as" and isinstance(n.value, str) and False:
                pass
            for tok in ([k] + ([n.value] if isinstance(n.value, str) else [])):
                for m in re.finditer(r"scope:([A-Za-z_0-9]+)", tok):
                    used_scopes[m.group(1)].append("%s:%d" % (rel, n.line))
                for m in re.finditer(r"var:([A-Za-z_0-9]+)", tok):
                    used_vars[m.group(1)].append("%s:%d" % (rel, n.line))
            # variables
            if k in ("set_variable", "add_to_variable_list", "change_variable"):
                if isinstance(n.value, str):
                    set_vars.add(n.value)
                else:
                    for c in n.value:
                        if c.key == "name":
                            set_vars.add(c.value)
            if k in ("has_variable", "remove_variable") and isinstance(n.value, str):
                used_vars[n.value].append("%s:%d" % (rel, n.line))
            if k in ("has_variable_list", "clear_variable_list") and isinstance(n.value, str):
                used_vars[n.value].append("%s:%d" % (rel, n.line))
            if k in ("is_target_in_variable_list", "remove_list_variable", "variable_list_size") and isinstance(n.value, list):
                for c in n.value:
                    if c.key == "name" and not c.value.startswith("$") and c.value != "pam_forced_papal_vote_target":
                        used_vars[c.value].append("%s:%d" % (rel, n.line))
            if k == "variable" and isinstance(n.value, str) and pkeys and re.match(r"^(any|every|random|ordered)_in_list$", pkeys[-1] or ""):
                used_vars[n.value].append("%s:%d" % (rel, n.line))
            # keyword check in effect/trigger-like files
            in_call = len(parents) >= 2 and parents[-1].key in known_scripted
            depth_ok = len(parents) >= 1 and top_dir not in ("customizable_localization",) and not in_call
            if depth_ok and isinstance(n.key, str):
                kk = k
                if kk.startswith(("scope:", "var:", "local_var:", "global_var:", "flag:", "title:", "faith:",
                                  "religion:", "culture:", "trait:", "cp:", "$")) or "." in kk or kk.startswith("@"):
                    pass
                elif re.match(r"^-?\d+(\.\d+)?$", kk):
                    pass
                elif "$" in kk:
                    pass
                elif kk.startswith("qpq_") and kk not in known_kw and not (
                        top_dir in ("secret_types", "story_cycles", "game_rules", "on_action", "modifiers",
                                    "opinion_modifiers", "hook_types")):
                    report("UNDEFINED %s:%d %s" % (rel, n.line, kk))
                elif kk not in known_kw and not kk.startswith("qpq_"):
                    report("UNKNOWN-KEYWORD %s:%d %s" % (rel, n.line, kk))
            # references to definitions
            v = n.value if isinstance(n.value, str) else None
            if v:
                def chk(kind, pool, label):
                    if v.startswith("$") or v.startswith("scope:"):
                        return
                    if v not in pool:
                        report("MISSING-%s %s:%d %s" % (label, rel, n.line, v))
                if k == "modifier" and any(p in ("add_opinion", "reverse_add_opinion", "has_opinion_modifier", "remove_opinion") for p in pkeys[-1:]):
                    chk("opinion", set(my["opinions"]) | van["opinions"], "OPINION")
                if k == "modifier" and any(p in ("add_character_modifier", "remove_character_modifier", "has_character_modifier") for p in pkeys[-1:]):
                    chk("modifier", set(my["modifiers"]) | van["modifiers"], "MODIFIER")
                if k in ("has_character_modifier", "remove_character_modifier"):
                    chk("modifier", set(my["modifiers"]) | van["modifiers"], "MODIFIER")
                if k == "type" and pkeys and pkeys[-1] in ("add_hook", "has_hook_of_type"):
                    chk("hook", set(my["hooks"]) | van["hooks"], "HOOK")
                if k == "type" and pkeys and pkeys[-1] == "add_secret":
                    if "$" not in v:
                        chk("secret", set(my["secrets"]), "SECRET")
                if k == "type" and pkeys and pkeys[-1] in ("start_scheme", "can_start_scheme"):
                    chk("scheme", van["schemes"], "SCHEME")
                if k == "type" and pkeys and pkeys[-1] in ("create_faction", "can_create_faction"):
                    chk("faction", van["factions"], "FACTION")
                if k == "type" and pkeys and pkeys[-1] == "create_story":
                    chk("story", set(my["stories"]), "STORY")
                if k == "type" and pkeys and pkeys[-1] == "assign_councillor_type":
                    chk("council", van["councils"], "COUNCIL")
                if k in ("has_trait", "add_trait", "remove_trait"):
                    chk("trait", van["traits"], "TRAIT")
                if k == "casus_belli":
                    chk("cb", set(my["cbs"]) | van["cbs"], "CB")
                if k == "trigger_event" and v.startswith("qpq_"):
                    if v not in events:
                        report("MISSING-EVENT %s:%d %s" % (rel, n.line, v))
                if k == "interaction" and v.startswith("qpq_") and v not in my["interactions"]:
                    report("MISSING-INTERACTION %s:%d %s" % (rel, n.line, v))
                if k in LOC_FIELDS and re.match(r"^[A-Za-z0-9_.\-]+$", v) and not v.startswith("$"):
                    if k == "name" and pkeys and pkeys[-1] in ("set_variable", "add_to_variable_list", "change_variable",
                                                                "save_scope_value_as", "is_target_in_variable_list",
                                                                "remove_list_variable", "variable_list_size",
                                                                "save_temporary_scope_value_as", "change_global_variable",
                                                                "set_local_variable"):
                        pass
                    elif k == "text" and pkeys and pkeys[-1] == "custom_description" and False:
                        pass
                    elif k == "title" and pkeys and pkeys[-1] in ("save_scope_as",):
                        pass
                    elif v in ("yes", "no"):
                        pass
                    else:
                        loc_used[v].append("%s:%d" % (rel, n.line))
                if k == "trigger_event" and isinstance(n.value, str):
                    pass
            if k == "trigger_event" and isinstance(n.value, list):
                for c in n.value:
                    if c.key == "id" and c.value.startswith("qpq_") and c.value not in events:
                        report("MISSING-EVENT %s:%d %s" % (rel, n.line, c.value))
            # script value references by name (qpq_*_value)
            for tok in ([n.value] if isinstance(n.value, str) else []):
                if re.match(r"^qpq_[a-z_0-9]+_value$", tok) and tok not in my["values"]:
                    report("MISSING-VALUE %s:%d %s" % (rel, n.line, tok))

    # scopes used but never saved
    for s, where in sorted(used_scopes.items()):
        if s in BUILTIN_SCOPES or s in saved or s.startswith("$"):
            continue
        if "$" in s:
            continue
        report("SCOPE-NEVER-SAVED scope:%s (%s)" % (s, where[0]))
    for vname, where in sorted(used_vars.items()):
        if vname in set_vars or vname.startswith("$"):
            continue
        if vname in ("pam_forced_papal_vote_target",):
            continue
        report("VAR-NEVER-SET %s (%s)" % (vname, where[0]))

    # variables written but never read (1.20 logs these as errors)
    read_in_loc = set()
    for f in files_under(os.path.join(ROOT, "localization"), ".yml"):
        read_in_loc |= set(re.findall(r"Var\('([A-Za-z_0-9]+)'\)", read(f)))
    for f, tree in trees.items():
        for n, _p in walk(tree):
            if n.key == "variable_name" and isinstance(n.value, str):
                read_in_loc.add(n.value.strip('"'))
    for vname in sorted(set_vars):
        if vname in used_vars or vname in read_in_loc or vname.startswith("$"):
            continue
        if vname in ("pam_forced_papal_vote_target",):
            continue
        report("VAR-NEVER-READ %s" % vname)

    # localization: interactions, decisions, modifiers, opinions, secrets, CBs, rules need keys
    def need(key, why):
        if key not in loc:
            report("LOC-MISSING %s (%s)" % (key, why))
    for k in my["interactions"]:
        need(k, "interaction")
        need(k + "_desc", "interaction desc")
    for k in my["decisions"]:
        need(k, "decision")
        need(k + "_desc", "decision desc")
        need(k + "_tooltip", "decision tooltip")
    for k in my["opinions"]:
        need(k, "opinion modifier")
    for k in my["modifiers"]:
        need(k, "modifier")
    for k in my["hooks"]:
        need(k, "hook")
    for k in my["secrets"]:
        need(k, "secret")
        need(k + "_desc", "secret desc")
    for k in my["cbs"]:
        need(k, "casus belli")
    for k in my["stories"]:
        need(k, "story")
    for k in my["rules"]:
        need("rule_" + k, "game rule")
    for k, where in sorted(loc_used.items()):
        if k not in loc and not k.startswith(("qpq_k_",)):
            if k in known_scripted or k in my["values"]:
                continue
            report("LOC-MISSING %s (%s)" % (k, where[0]))
    # loc lines: unbalanced brackets / unknown $keys$
    for f in files_under(os.path.join(ROOT, "localization"), ".yml"):
        for i, line in enumerate(read(f).split("\n"), 1):
            m = re.match(r'\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$', line)
            if not m:
                if line.strip() and not line.startswith("l_english"):
                    report("LOC-SYNTAX %s:%d" % (os.path.relpath(f, ROOT), i))
                continue
            text = m.group(2)
            if text.count("[") != text.count("]"):
                report("LOC-BRACKETS %s:%d %s" % (os.path.relpath(f, ROOT), i, m.group(1)))
            for ref in re.findall(r"\$([A-Za-z0-9_]+)(?:\|[^$]*)?\$", text):
                if ref not in loc and ref.upper() != ref:
                    report("LOC-REF %s:%d $%s$" % (os.path.relpath(f, ROOT), i, ref))
            if re.search(r'(?<!\\)"', text):
                report("LOC-QUOTE %s:%d unescaped quote" % (os.path.relpath(f, ROOT), i))

    for p in sorted(set(problems)):
        print(p)
    print("\n%d problem(s)" % len(set(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
