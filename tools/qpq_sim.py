#!/usr/bin/env python3
"""Quid Pro Quo - deal evaluator: runs the mod's own script against a mock world.

    python3 tools/qpq_sim.py [--vanilla /path/to/ck3/game] [spot | kinds | dump DEAL.json]

Nothing here restates the mod's numbers. The simulator parses the mod's scripted effects, triggers, script
values and scripted GUIs (and vanilla's, which they call), builds a small world of characters, titles, faiths
and wars, then drives the Backroom Deal panel the way a player does: it opens the panel on someone, clicks the
panel's own buttons (each scripted GUI's is_shown, is_valid and effect run as written) and reads back the
variables the panel shows: every part of the acceptance, the refusal reasons, the candidates offered.

It is strict. A keyword it does not know raises SimError: teach it the keyword (in the tables below), never
skip it, or the numbers would quietly be wrong. Things the game would log as script errors (a variable
compared that was never set, a scope that does not exist) are collected in Run.errors.

tools/qpq_deal_tests.py holds the deterministic property tests built on this.
"""
import argparse
import itertools
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from qpq_validate import Node, ParseError, files_under, parse, read  # noqa: E402

DEFAULT_VANILLA = [
    os.environ.get("CK3_GAME", ""),
    "/home/user/jesec/ck3-mod-base/base/game",
]


DATABASES = {"religion": "Religion", "faith": "Faith", "culture": "Culture", "title": "Title"}


class SimError(Exception):
    """The simulator met something it does not know. Teach it; never paper over it."""


class Refused(Exception):
    """A panel button was clicked that is not shown or not valid."""


NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
PARAM_RE = re.compile(r"\$([A-Za-z0-9_]+)(\|[^$]*)?\$")
CALL_RE = re.compile(r"^([a-z_]+)\((.*)\)$")
CMP_OPS = {"=", "==", "!=", "<", "<=", ">", ">=", "?="}


# ====================================================================== script objects
class Flag:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __eq__(self, o):
        return isinstance(o, Flag) and o.name == self.name

    def __hash__(self):
        return hash(("flag", self.name))

    def __repr__(self):
        return "flag:" + self.name


class Obj:
    KIND = "object"
    _ids = itertools.count(1)

    def __init__(self, name=None, **kw):
        self.id = next(Obj._ids)
        self.name = name or "%s_%d" % (self.KIND, self.id)
        self.vars = {}
        self.var_lists = {}
        for k, v in kw.items():
            if not hasattr(self, k):
                raise SimError("%s has no field %s" % (self.KIND, k))
            setattr(self, k, v)

    def __repr__(self):
        return "<%s %s>" % (self.KIND, self.name)


class Religion(Obj):
    KIND = "religion"
    family = "rf_abrahamic"


class Faith(Obj):
    KIND = "faith"
    religion = None
    head_title = None          # the title of the Head of Faith, if any
    doctrines = ()             # doctrine keys
    parameters = ()            # doctrine parameters
    hostility = None           # {faith: level}; default by religion: same 0, else 2 (hostile)

    def hostility_to(self, other):
        if other is self:
            return 0
        if self.hostility and other in self.hostility:
            return self.hostility[other]
        return 1 if (self.religion is not None and self.religion is other.religion) else 2


class Culture(Obj):
    KIND = "culture"
    era = 2


class Dynasty(Obj):
    KIND = "dynasty"
    prestige_level = 1
    perks = ()


class Title(Obj):
    KIND = "title"
    tier = 2                   # 1 barony .. 5 empire (vanilla tier_* values)
    holder = None
    held_years = 10
    de_jure_liege = None
    is_head_of_faith_title = False
    faith = None               # a county's faith
    development = 10
    electors = ()
    holy_order = False
    mercenary_company = False


class Artifact(Obj):
    KIND = "artifact"
    owner = None
    rarity = "masterwork"      # common, masterwork, famed, illustrious
    modifiers = ()


class Secret(Obj):
    KIND = "secret"
    type = "secret_murder"
    owner = None
    target = None
    known_by = ()
    criminal = False
    shunned = False


class War(Obj):
    KIND = "war"
    attackers = ()
    defenders = ()
    attacker_war_score = 0
    war_days = 200
    casus_belli = "conquest"
    claimant = None


class Faction(Obj):
    KIND = "faction"
    type = "independence_faction"
    target = None
    leader = None


class Story(Obj):
    KIND = "story"
    owner = None


class Character(Obj):
    KIND = "character"
    world = None
    is_ai = True
    alive = True
    age = 35
    female = False
    gold = 100
    income = 5                 # monthly_character_income
    prestige = 500
    piety = 200
    prestige_level = 2
    piety_level = 2
    legitimacy_level = 2
    legitimacy = 50
    has_legitimacy = True
    diplomacy = 8
    martial = 8
    stewardship = 8
    intrigue = 8
    learning = 8
    traits = ()
    faith = None
    culture = None
    dynasty = None
    liege = None               # liege of a vassal, or the court a courtier belongs to
    suzerain = None
    titles = ()
    capital = None
    claims = ()
    spouses = ()
    betrothed = None
    concubine_of = None
    father = None
    mother = None
    designated_heir = None
    primary_heir = None
    relations = None           # {relation: set(characters)}
    max_strength = 0           # an unlanded character commands no army
    current_strength = 0
    boldness = 0
    energy = 0
    compassion = 0
    honor = 0
    zeal = 0
    greed = 0
    rationality = 0
    vengefulness = 0
    sociability = 0
    imprisoned_by = None
    hostage_of = None
    guest_of = None            # a foreign court guest of
    pool_guest_of = None
    councillor_of = None
    clergy = False
    papabile = False
    mercenary = False
    government_flags = ("government_is_feudal", "government_is_landed")
    character_flags = ()
    powerful_vassal = False
    contract_reign_days = 3650  # days_since_vassal_contract_liege_dynasty_reign_start
    obligations = None         # {contract: level}
    opinion_modifiers = ()     # (target, modifier)
    preferred_heir_of = ()     # lieges whose preferred heir they were
    joined_faction = None
    realm_priest = None
    clerical_elector_title = None

    def __init__(self, name=None, **kw):
        super().__init__(name, **kw)
        self.traits = set(self.traits)
        self.titles = list(self.titles)
        self.claims = list(self.claims)
        self.spouses = list(self.spouses)
        self.character_flags = set(self.character_flags)
        self.relations = {k: set(v) for k, v in (self.relations or {}).items()}

    @property
    def is_landed(self):
        return bool(self.titles)

    def rel(self, kind):
        return self.relations.get(kind, set())


class World:
    """A small world. Character relations that run both ways (alliances, truces, opinions of each other)
    are kept here."""

    def __init__(self):
        self.chars = []
        self.titles = []
        self.wars = []
        self.artifacts = []
        self.secrets = []
        self.alliances = set()
        self.truces = set()
        self.neighbors = set()      # pairs of top lieges whose realms touch (or face each other across water)
        self.opinions = {}          # (who, of_whom) -> value
        self.dread = {}             # (who, of_whom) -> level
        self.hooks = {}             # (holder, target) -> "weak" | "strong"
        self.tributaries = {}       # tributary -> suzerain (also Character.suzerain)
        self.game_rules = {}
        self.global_vars = {}
        self.factions = {}          # character -> faction type they lead
        self.db = {k: {} for k in DATABASES}
        self.dlc_features = None    # None: every DLC feature; else the set owned

    def register(self, db, key, obj):
        self.db[db][key] = obj
        return obj

    def lookup(self, db, key):
        """A database entry (religion:x, faith:x ...). Every vanilla key exists in the game; one not placed
        in this world is a bare object of its kind."""
        if key not in self.db[db]:
            cls = {"religion": Religion, "faith": Faith, "culture": Culture, "title": Title}[db]
            self.db[db][key] = cls(key)
        return self.db[db][key]

    # ---- building
    def char(self, name, **kw):
        c = Character(name, world=self, **kw)
        self.chars.append(c)
        return c

    def title(self, name, tier, holder=None, **kw):
        t = Title(name, tier=tier, holder=holder, **kw)
        self.titles.append(t)
        if holder is not None:
            holder.titles.append(t)
            if tier == 2 and holder.capital is None:
                holder.capital = t
        return t

    def war(self, attackers, defenders, **kw):
        w = War(attackers=list(attackers), defenders=list(defenders), **kw)
        self.wars.append(w)
        return w

    def artifact(self, name, owner, **kw):
        a = Artifact(name, owner=owner, **kw)
        self.artifacts.append(a)
        return a

    def secret(self, owner, type="secret_murder", target=None, known_by=(), **kw):
        s = Secret(owner=owner, type=type, target=target, known_by=list(known_by), **kw)
        self.secrets.append(s)
        return s

    def ally(self, a, b):
        self.alliances.add(frozenset((a, b)))

    def truce(self, a, b):
        self.truces.add(frozenset((a, b)))

    def border(self, a, b):
        self.neighbors.add(frozenset((a, b)))

    def opinion(self, who, of_whom, value):
        self.opinions[(who, of_whom)] = value

    def tribute(self, tributary, suzerain):
        tributary.suzerain = suzerain
        self.tributaries[tributary] = suzerain

    def relate(self, a, kind, b):
        a.relations.setdefault(kind, set()).add(b)
        b.relations.setdefault(kind, set()).add(a)

    # ---- queries
    def top_liege(self, c):
        seen = set()
        while c.liege is not None and c.is_landed and c not in seen:
            seen.add(c)
            if not c.liege.is_landed:
                break
            c = c.liege
        return c

    def realm_owner(self, c):
        """Whose realm a character belongs to: a courtier belongs to their court's."""
        if not c.is_landed and c.liege is not None:
            return self.top_liege(c.liege)
        return self.top_liege(c)

    def vassals(self, c):
        return [x for x in self.chars if x.alive and x.liege is c and x.is_landed]

    def courtiers(self, c):
        return [x for x in self.chars if x.alive and x.liege is c and not x.is_landed]

    def liege_chain(self, c):
        out, seen = [], set()
        while c.liege is not None and c not in seen:
            seen.add(c)
            c = c.liege
            out.append(c)
        return out

    def wars_of(self, c):
        return [w for w in self.wars if c in w.attackers or c in w.defenders]

    def at_war_with(self, a, b):
        for w in self.wars:
            if (a in w.attackers and b in w.defenders) or (a in w.defenders and b in w.attackers):
                return True
        return False

    def children(self, c):
        return [x for x in self.chars if x.father is c or x.mother is c]

    def parents(self, c):
        return [p for p in (c.father, c.mother) if p is not None]

    def siblings(self, c):
        ps = set(self.parents(c))
        return [x for x in self.chars if x is not c and ps and set(self.parents(x)) & ps]

    def close_family(self, c):
        out = []
        for x in self.parents(c) + self.children(c) + self.siblings(c):
            if x not in out:
                out.append(x)
        return out

    def opinion_of(self, who, of_whom):
        return self.opinions.get((who, of_whom), 0)


# ====================================================================== the script library
class Library:
    """Every definition the mod can reach: its own and vanilla's."""

    def __init__(self, vanilla=None, mod=ROOT):
        self.effects, self.triggers, self.values, self.guis = {}, {}, {}, {}
        self.vanilla = vanilla
        dirs = (("scripted_effects", self.effects), ("scripted_triggers", self.triggers),
                ("script_values", self.values))
        for base in ([vanilla] if vanilla else []) + [mod]:
            for sub, table in dirs:
                for f in sorted(files_under(os.path.join(base, "common", sub))):
                    self._load(f, table)
        for f in sorted(files_under(os.path.join(mod, "common", "scripted_guis"))):
            self._load(f, self.guis)
        # trait flags (has_trait_with_flag), from the trait files themselves
        self.trait_flags = {}
        traits = {}
        for base in ([vanilla] if vanilla else []) + [mod]:
            for f in sorted(files_under(os.path.join(base, "common", "traits"))):
                self._load(f, traits)
        for name, body in traits.items():
            if isinstance(body, list):
                self.trait_flags[name] = {x.value for x in body if x.key == "flag" and isinstance(x.value, str)}
        self._expanded = {}
        self.stubs = set()          # scripted effects run as a recorded no-op (Run.events), for testing around them

    @staticmethod
    def _load(path, table):
        try:
            nodes = parse(read(path), path)
        except ParseError:
            return
        for n in nodes:
            if n.key and not n.key.startswith("@"):
                table[n.key] = n.value

    def expand(self, kind, name, params):
        """A scripted effect or trigger with its $PARAMS$ substituted (cached)."""
        table = self.effects if kind == "effect" else self.triggers
        body = table[name]
        if not params:
            return body
        key = (kind, name, tuple(sorted(params.items())))
        if key not in self._expanded:
            self._expanded[key] = _subst(body, params)
        return self._expanded[key]


def _subst(nodes, params):
    def s(x):
        if not isinstance(x, str) or "$" not in x:
            return x

        def rep(m):
            if m.group(1) in params:
                return params[m.group(1)]
            if m.group(2):
                return m.group(2)[1:]
            raise SimError("parameter $%s$ not given" % m.group(1))
        return PARAM_RE.sub(rep, x)
    out = []
    for n in nodes:
        v = _subst(n.value, params) if isinstance(n.value, list) else s(n.value)
        out.append(Node(s(n.key), n.op, v, n.line, n.file))
    return out


# ====================================================================== the interpreter
class Run:
    """One execution: a root, its saved scopes and lists, and the errors the game would log."""

    def __init__(self, lib, world, root, scopes=None):
        self.lib, self.w, self.root = lib, world, root
        self.scopes = dict(scopes or {})
        self.lists = {}
        self.errors = []
        self.events = []         # (character, event) triggered
        self.toasts = []

    def err(self, node, msg):
        where = "%s:%s" % (os.path.basename(node.file or "?"), node.line) if node is not None else "?"
        self.errors.append("%s %s" % (where, msg))

    # -------------------------------------------------- resolving names and paths
    def resolve(self, tok, fr, node=None):
        """A token or a dotted path, in frame fr = (this, prev). Returns a number, bool, Flag, Obj, str or None."""
        if isinstance(tok, list):
            return self.val_block(tok, fr)
        if tok.startswith('"') and tok.endswith('"'):
            tok = tok[1:-1]
        if NUM_RE.match(tok):
            return float(tok)
        if tok == "yes":
            return True
        if tok == "no":
            return False
        if tok.startswith("flag:"):
            return Flag(tok[5:])
        cur = None
        for i, seg in enumerate(_split_path(tok)):
            if i == 0:
                cur = self._first(seg, fr, node)
            else:
                if cur is None:
                    return None
                cur = self._link(cur, seg, fr, node)
            if cur is None:
                return None
        return cur

    def _first(self, seg, fr, node):
        this, prev = fr
        if seg == "root":
            return self.root
        if seg == "this":
            return this
        if seg == "prev":
            return prev
        if seg.startswith("scope:"):
            return self.scopes.get(seg[6:])
        if seg.startswith("global_var:"):
            return self.w.global_vars.get(seg[11:])
        if seg.startswith("flag:"):
            return Flag(seg[5:])
        db = seg.split(":", 1)[0]
        if db in DATABASES and ":" in seg:
            return self.w.lookup(db, seg.split(":", 1)[1])
        return self._link(this, seg, fr, node)

    def _link(self, cur, seg, fr, node):
        if seg.startswith("var:"):
            if not isinstance(cur, Obj):
                raise SimError("var: on %r" % (cur,))
            return cur.vars.get(seg[4:])
        m = CALL_RE.match(seg)
        if m:
            fn = FUNCS.get(m.group(1))
            if fn is None:
                raise SimError("unknown function link %s" % seg)
            arg = self.resolve(m.group(2), fr, node)
            return fn(self, cur, arg)
        if seg in self.lib.values:
            return self.value(seg, (cur, fr[0]))
        if isinstance(cur, Obj):
            table = LINKS.get(cur.KIND, {})
            if seg in table:
                return table[seg](self, cur)
        if seg in ("faith", "religion") and isinstance(cur, Faith) and seg == "religion":
            return cur.religion
        raise SimError("unknown link or value %r on %r (%s:%s)" % (
            seg, cur, os.path.basename(node.file) if node else "?", node.line if node else "?"))

    def is_path(self, tok, fr):
        """Can tok be read as a value or scope here? (used where a key may be a trigger or a path)"""
        first = _split_path(tok)[0]
        if first in ("root", "this", "prev") or first.startswith(("scope:", "var:", "flag:", "global_var:")) \
                or first.split(":", 1)[0] in DATABASES and ":" in first:
            return True
        if first in self.lib.values or CALL_RE.match(first):
            return True
        this = fr[0]
        return isinstance(this, Obj) and first in LINKS.get(this.KIND, {})

    # -------------------------------------------------- values
    def value(self, name, fr):
        body = self.lib.values[name]
        if isinstance(body, list):
            return self.val_block(body, fr)
        return self.num(self.resolve(body, fr), None)

    def num(self, x, node, what=""):
        if isinstance(x, bool):
            return 1.0 if x else 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if x is None:
            self.err(node, "missing value %s" % what)
            return 0.0
        raise SimError("not a number: %r %s (%s:%s)" % (x, what, node.file if node else "?", node.line if node else "?"))

    def val(self, v, fr, node):
        if isinstance(v, list):
            return self.val_block(v, fr)
        return self.num(self.resolve(v, fr, node), node, v)

    def val_block(self, nodes, fr):
        acc = [0.0]
        self._val_ops(nodes, fr, acc)
        return acc[0]

    def _val_ops(self, nodes, fr, acc):
        chain = None
        for n in nodes:
            k = n.key
            if k is None:
                raise SimError("bare %r in a value (%s:%d)" % (n.value, n.file, n.line))
            if k in ("if", "else_if", "else"):
                chain = self._branch(n, chain, fr, lambda body: self._val_ops(body, fr, acc))
                continue
            chain = None
            if k == "value":
                acc[0] = self.val(n.value, fr, n)
            elif k == "add":
                acc[0] += self.val(n.value, fr, n)
            elif k == "subtract":
                acc[0] -= self.val(n.value, fr, n)
            elif k == "multiply":
                acc[0] *= self.val(n.value, fr, n)
            elif k == "divide":
                d = self.val(n.value, fr, n)
                if d == 0:
                    self.err(n, "divide by zero")
                else:
                    acc[0] /= d
            elif k == "modulo":
                acc[0] %= self.val(n.value, fr, n)
            elif k == "min":
                acc[0] = max(acc[0], self.val(n.value, fr, n))
            elif k == "max":
                acc[0] = min(acc[0], self.val(n.value, fr, n))
            elif k == "round" and n.value == "yes":
                acc[0] = float(_round_half_up(acc[0]))
            elif k == "floor" and n.value == "yes":
                acc[0] = float(int(acc[0] // 1))
            elif k == "ceiling" and n.value == "yes":
                acc[0] = float(-int((-acc[0]) // 1))
            elif k == "abs" and n.value == "yes":
                acc[0] = abs(acc[0])
            elif k in ("desc", "format"):
                pass
            elif k == "save_temporary_scope_as":
                self.scopes[n.value] = fr[0]
            elif _iter_name(k):
                for item in self._iterate(k, n.value, fr, n):
                    self._val_ops(_strip(n.value, ITER_KEYS), (item, fr[0]), acc)
            elif isinstance(n.value, list) and self.is_path(k, fr):
                tgt = self.resolve(k, fr, n)
                if tgt is None:
                    if n.op != "?=":
                        self.err(n, "value in missing scope %s" % k)
                    continue
                self._val_ops(n.value, (tgt, fr[0]), acc)
            else:
                raise SimError("unknown value operation %s (%s:%d)" % (k, n.file, n.line))

    def _branch(self, n, chain, fr, run):
        """if / else_if / else in any block. chain: None (no if before), True (a branch ran), False."""
        k = n.key
        if k in ("else_if", "else") and chain is None:
            self.err(n, "%s without if" % k)
            return None
        if k != "if" and chain:
            return True
        body = n.value
        if k == "else":
            run(body)
            return True
        lim = [x for x in body if x.key == "limit"]
        rest = [x for x in body if x.key != "limit"]
        ok = all(self.trig(x.value, fr) for x in lim) if lim else True
        if ok:
            run(rest)
            return True
        return False

    # -------------------------------------------------- triggers
    def trig(self, nodes, fr):
        chain = None
        for n in nodes:
            k = n.key
            if k in ("trigger_if", "trigger_else_if", "trigger_else"):
                if k != "trigger_if" and chain is None:
                    self.err(n, "%s without trigger_if" % k)
                if k != "trigger_if" and chain:
                    continue
                body = n.value
                lim = [x for x in body if x.key == "limit"]
                rest = [x for x in body if x.key != "limit"]
                if k == "trigger_else" or all(self.trig(x.value, fr) for x in lim):
                    chain = True
                    if not self.trig(rest, fr):
                        return False
                else:
                    chain = False
                continue
            chain = None
            if not self.trig_node(n, fr):
                return False
        return True

    def trig_node(self, n, fr):
        k, op, v = n.key, n.op, n.value
        if k is None:
            raise SimError("bare %r in a trigger (%s:%d)" % (v, n.file, n.line))
        if k == "AND":
            return self.trig(v, fr)
        if k == "OR":
            return any(self.trig([x], fr) for x in v)
        if k == "NOT":
            return not self.trig(v, fr)
        if k == "NOR":
            return not any(self.trig([x], fr) for x in v)
        if k == "NAND":
            return not self.trig(v, fr)
        if k in ("custom_description", "custom_tooltip"):
            if not isinstance(v, list):
                raise SimError("%s = %s in a trigger" % (k, v))
            return self.trig(_strip(v, ("text", "subject", "object", "value")), fr)
        if k == "exists":
            return self.resolve(v, fr, n) is not None
        if k == "always":
            return v == "yes"
        if k in self.lib.triggers:
            if isinstance(v, list):
                params = {x.key: x.value for x in v}
                return self.trig(self.lib.expand("trigger", k, params), fr)
            res = self.trig(self.lib.triggers[k], fr)
            return res if v == "yes" else not res
        if k in TRIGGERS:
            return TRIGGERS[k](self, fr, n)
        if k.startswith("any_"):
            items = self._iterate(k, v, fr, n)
            body = _strip(v, ITER_KEYS + ("count", "percent"))
            hits = sum(1 for it in items if self.trig(body, (it, fr[0])))
            cnt = [x for x in v if x.key == "count"]
            pct = [x for x in v if x.key == "percent"]
            if cnt:
                c = cnt[0]
                if c.value == "all":
                    return hits == len(items)
                return _cmp(float(hits), c.op, self.val(c.value, fr, c))
            if pct:
                p = pct[0]
                return bool(items) and _cmp(hits / len(items), p.op, self.val(p.value, fr, p))
            return hits > 0
        return self.compare(n, fr)

    def compare(self, n, fr):
        k, op, v = n.key, n.op, n.value
        if not self.is_path(k, fr):
            raise SimError("unknown trigger %s (%s:%d)" % (k, n.file, n.line))
        lhs = self.resolve(k, fr, n)
        if isinstance(v, list):
            if isinstance(lhs, Obj):
                if op not in ("=", "?="):
                    raise SimError("%s %s { } on a scope" % (k, op))
                return self.trig(v, (lhs, fr[0]))
            if lhs is None:
                if op != "?=":
                    self.err(n, "trigger on missing %s" % k)
                return False
            return _cmp(self.num(lhs, n, k), op, self.val_block(v, fr))
        if lhs is None:
            if op != "?=":
                self.err(n, "compared missing %s" % k)
            return False
        rhs = self.resolve(v, fr, n)
        if rhs is None:
            self.err(n, "compared to missing %s" % v)
            return False
        if isinstance(lhs, bool) or isinstance(rhs, bool):
            if op in ("=", "==", "?="):
                return bool(lhs) == bool(rhs)
            if op == "!=":
                return bool(lhs) != bool(rhs)
        if isinstance(lhs, float) or isinstance(rhs, float):
            return _cmp(self.num(lhs, n, k), op, self.num(rhs, n, v))
        if op in ("=", "==", "?="):
            return lhs is rhs or lhs == rhs
        if op == "!=":
            return not (lhs is rhs or lhs == rhs)
        raise SimError("cannot compare %r %s %r" % (lhs, op, rhs))

    # -------------------------------------------------- effects
    def eff(self, nodes, fr):
        chain = None
        for n in nodes:
            if n.key in ("if", "else_if", "else"):
                chain = self._branch(n, chain, fr, lambda body: self.eff(body, fr))
                continue
            chain = None
            self.eff_node(n, fr)

    def eff_node(self, n, fr):
        k, v = n.key, n.value
        if k is None:
            raise SimError("bare %r in an effect (%s:%d)" % (v, n.file, n.line))
        if k in self.lib.stubs:
            self.events.append(("stub", k, fr[0], dict(self.scopes)))
            return
        if k in self.lib.effects:
            if isinstance(v, list):
                params = {x.key: x.value for x in v}
                self.eff(self.lib.expand("effect", k, params), fr)
            elif v == "yes":
                self.eff(self.lib.effects[k], fr)
            return
        if k in EFFECTS:
            EFFECTS[k](self, fr, n)
            return
        if _iter_name(k) and not k.startswith("any_"):
            items = self._iterate(k, v, fr, n)
            body = _strip(v, ITER_KEYS)
            for it in items:
                self.eff(body, (it, fr[0]))
            return
        if isinstance(v, list) and self.is_path(k, fr):
            tgt = self.resolve(k, fr, n)
            if tgt is None:
                if n.op != "?=":
                    self.err(n, "effect in missing scope %s" % k)
                return
            if not isinstance(tgt, Obj):
                raise SimError("effect block in %r" % (tgt,))
            self.eff(v, (tgt, fr[0]))
            return
        raise SimError("unknown effect %s (%s:%d)" % (k, n.file, n.line))

    # -------------------------------------------------- iterators
    def _iterate(self, key, body, fr, n):
        prefix, name = _iter_name(key)
        this = fr[0]
        if name == "in_list":
            lst = [x for x in body if x.key in ("list", "variable")]
            if not lst:
                raise SimError("in_list without list (%s:%d)" % (n.file, n.line))
            if lst[0].key == "list":
                items = list(self.lists.get(lst[0].value, []))
            else:
                items = list(this.var_lists.get(lst[0].value, []))
        else:
            fn = ITERS.get(name)
            if fn is None:
                raise SimError("unknown iterator %s (%s:%d)" % (key, n.file, n.line))
            items = list(fn(self, this, body, fr))
        lims = [x for x in body if x.key == "limit"] if isinstance(body, list) else []
        if lims:
            items = [it for it in items if all(self.trig(x.value, (it, this)) for x in lims)]
        if prefix == "ordered":
            ob = [x for x in body if x.key == "order_by"]
            if not ob:
                raise SimError("ordered_ without order_by (%s:%d)" % (n.file, n.line))
            keyed = [(self.val(ob[0].value, (it, this), ob[0]), i, it) for i, it in enumerate(items)]
            keyed.sort(key=lambda t: (-t[0], t[1]))
            items = [t[2] for t in keyed]
            pos = [x for x in body if x.key == "position"]
            mx = [x for x in body if x.key == "max"]
            if pos:
                p = int(self.val(pos[0].value, fr, pos[0]))
                items = items[p:p + 1]
            elif mx:
                items = items[:int(self.val(mx[0].value, fr, mx[0]))]
            else:
                items = items[:1]
        elif prefix == "random":
            items = items[:1]
        return items


ITER_KEYS = ("limit", "list", "variable", "order_by", "max", "min", "position", "check_range_bounds",
             "weight", "type", "even_if_dead", "alternative_limit", "filter", "include_self")


def _strip(nodes, keys):
    return [x for x in nodes if x.key not in keys] if isinstance(nodes, list) else nodes


def _iter_name(k):
    for p in ("every_", "any_", "random_", "ordered_"):
        if k and k.startswith(p):
            return p[:-1], k[len(p):]
    return None


def _split_path(tok):
    out, depth, cur = [], 0, []
    for ch in tok:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "." and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def _round_half_up(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def _cmp(a, op, b):
    if op in ("=", "==", "?="):
        return abs(a - b) < 1e-9
    if op == "!=":
        return abs(a - b) >= 1e-9
    if op == "<":
        return a < b - 1e-9
    if op == "<=":
        return a <= b + 1e-9
    if op == ">":
        return a > b + 1e-9
    if op == ">=":
        return a >= b - 1e-9
    raise SimError("bad comparison %s" % op)


# ====================================================================== the game's vocabulary
def _w(run):
    return run.w


def _tier(c):
    return max((t.tier for t in c.titles), default=0)


def _primary_title(c):
    return max(c.titles, key=lambda t: t.tier) if c.titles else None


def _head_of_faith(f):
    if f is None or f.head_title is None:
        return None
    return f.head_title.holder


CHAR_LINKS = {
    # scopes
    "liege": lambda r, c: c.liege,
    "top_liege": lambda r, c: r.w.top_liege(c),
    "suzerain": lambda r, c: c.suzerain,
    "faith": lambda r, c: c.faith,
    "religion": lambda r, c: c.faith.religion if c.faith else None,
    "culture": lambda r, c: c.culture,
    "dynasty": lambda r, c: c.dynasty,
    "primary_title": lambda r, c: _primary_title(c),
    "capital_county": lambda r, c: c.capital,
    "primary_heir": lambda r, c: c.primary_heir,
    "designated_heir": lambda r, c: c.designated_heir,
    "betrothed": lambda r, c: c.betrothed,
    "primary_spouse": lambda r, c: c.spouses[0] if c.spouses else None,
    "father": lambda r, c: c.father,
    "mother": lambda r, c: c.mother,
    "employer": lambda r, c: c.liege if not c.is_landed else None,
    "host": lambda r, c: c.guest_of or (c.liege if not c.is_landed else c),
    "imprisoner": lambda r, c: c.imprisoned_by,
    # numbers
    "gold": lambda r, c: float(c.gold),
    "age": lambda r, c: float(c.age),
    "prestige": lambda r, c: float(c.prestige),
    "piety": lambda r, c: float(c.piety),
    "prestige_level": lambda r, c: float(c.prestige_level),
    "piety_level": lambda r, c: float(c.piety_level),
    "legitimacy_level": lambda r, c: float(c.legitimacy_level),
    "legitimacy": lambda r, c: float(c.legitimacy),
    "highest_held_title_tier": lambda r, c: float(_tier(c)),
    "max_military_strength": lambda r, c: float(c.max_strength),
    "current_military_strength": lambda r, c: float(c.current_strength),
    "monthly_character_income": lambda r, c: float(c.income),
    "diplomacy": lambda r, c: float(c.diplomacy),
    "martial": lambda r, c: float(c.martial),
    "stewardship": lambda r, c: float(c.stewardship),
    "intrigue": lambda r, c: float(c.intrigue),
    "learning": lambda r, c: float(c.learning),
    "ai_boldness": lambda r, c: float(c.boldness),
    "ai_energy": lambda r, c: float(c.energy),
    "ai_compassion": lambda r, c: float(c.compassion),
    "ai_honor": lambda r, c: float(c.honor),
    "ai_zeal": lambda r, c: float(c.zeal),
    "ai_greed": lambda r, c: float(c.greed),
    "ai_rationality": lambda r, c: float(c.rationality),
    "ai_vengefulness": lambda r, c: float(c.vengefulness),
    "ai_sociability": lambda r, c: float(c.sociability),
    "days_since_vassal_contract_liege_dynasty_reign_start": lambda r, c: float(c.contract_reign_days),
    "dynasty_prestige_level": lambda r, c: float(c.dynasty.prestige_level) if c.dynasty else 0.0,
    # yes / no
    "is_ai": lambda r, c: c.is_ai,
    "is_alive": lambda r, c: c.alive,
    "is_adult": lambda r, c: c.age >= 16,
    "is_landed": lambda r, c: c.is_landed,
    "is_ruler": lambda r, c: c.is_landed,
    "is_playable_character": lambda r, c: c.is_landed,
    "is_independent_ruler": lambda r, c: c.is_landed and (c.liege is None or not c.liege.is_landed),
    "is_clergy": lambda r, c: c.clergy,
    "is_lowborn": lambda r, c: c.dynasty is None,
    "is_married": lambda r, c: bool(c.spouses),
    "is_betrothed": lambda r, c: c.betrothed is not None,
    "is_concubine": lambda r, c: c.concubine_of is not None,
    "is_female": lambda r, c: c.female,
    "is_male": lambda r, c: not c.female,
    "is_at_war": lambda r, c: bool(r.w.wars_of(c)),
    "is_imprisoned": lambda r, c: c.imprisoned_by is not None,
    "is_hostage": lambda r, c: c.hostage_of is not None,
    "is_mercenary_company": lambda r, c: c.mercenary,
    "is_papabile": lambda r, c: c.papabile,
    "has_legitimacy": lambda r, c: c.has_legitimacy,
    "is_valid_for_legitimacy_change": lambda r, c: c.has_legitimacy,
    "is_powerful_vassal": lambda r, c: c.powerful_vassal,
    "allowed_more_spouses": lambda r, c: len(c.spouses) < 1,
    "is_in_ongoing_great_holy_war": lambda r, c: False,
    "is_incapable": lambda r, c: False,
    "is_councillor": lambda r, c: c.councillor_of is not None,
    "is_tributary": lambda r, c: c.suzerain is not None,
    "joined_faction": lambda r, c: c.joined_faction,
    "realm_priest": lambda r, c: c.realm_priest,
    "house": lambda r, c: c.dynasty,
    "clerical_elector_title": lambda r, c: c.clerical_elector_title,
    "involved_activity": lambda r, c: None,
    "rite": lambda r, c: c.faith,
    "is_pregnant": lambda r, c: False,
}

TITLE_LINKS = {
    "holder": lambda r, t: t.holder,
    "tier": lambda r, t: float(t.tier),
    "title_held_years": lambda r, t: float(t.held_years),
    "de_jure_liege": lambda r, t: t.de_jure_liege,
    "faith": lambda r, t: t.faith if t.faith is not None else (t.holder.faith if t.holder else None),
    "development_level": lambda r, t: float(t.development),
    "is_holy_order": lambda r, t: t.holy_order,
    "is_mercenary_company": lambda r, t: t.mercenary_company,
}

FAITH_LINKS = {
    "religion": lambda r, f: f.religion,
    "religious_head": lambda r, f: _head_of_faith(f),
    "religious_head_title": lambda r, f: f.head_title,
    "main_rite": lambda r, f: f,
}

WAR_LINKS = {
    "primary_attacker": lambda r, w: w.attackers[0] if w.attackers else None,
    "primary_defender": lambda r, w: w.defenders[0] if w.defenders else None,
    "attacker_war_score": lambda r, w: float(w.attacker_war_score),
    "defender_war_score": lambda r, w: float(-w.attacker_war_score),
    "war_days": lambda r, w: float(w.war_days),
    "claimant": lambda r, w: w.claimant,
}

ARTIFACT_LINKS = {
    "artifact_owner": lambda r, a: a.owner,
}

SECRET_LINKS = {
    "secret_owner": lambda r, s: s.owner,
    "secret_target": lambda r, s: s.target,
}

DYNASTY_LINKS = {
    "dynasty_prestige_level": lambda r, d: float(d.prestige_level),
}

STORY_LINKS = {
    "story_owner": lambda r, s: s.owner,
}

FACTION_LINKS = {
    "faction_target": lambda r, f: f.target,
    "faction_leader": lambda r, f: f.leader,
}

LINKS = {
    "faction": FACTION_LINKS,
    "character": CHAR_LINKS, "title": TITLE_LINKS, "faith": FAITH_LINKS, "war": WAR_LINKS,
    "artifact": ARTIFACT_LINKS, "secret": SECRET_LINKS, "dynasty": DYNASTY_LINKS, "story": STORY_LINKS,
    "religion": {}, "culture": {},
}


def _f_opinion(run, cur, target):
    if target is None:
        run.errors.append("opinion() of a missing character")
        return 0.0
    if not isinstance(cur, Character) or not isinstance(target, Character):
        raise SimError("opinion(%r) on %r" % (target, cur))
    return float(run.w.opinion_of(cur, target))


FUNCS = {
    "opinion": _f_opinion,
}


# ---------------------------------------------------------------- triggers
def _target(run, fr, n, v=None):
    t = run.resolve(n.value if v is None else v, fr, n)
    if t is None:
        run.err(n, "%s on a missing target %s" % (n.key, n.value))
    return t


def _yes(n):
    if n.value not in ("yes", "no"):
        raise SimError("%s = %s" % (n.key, n.value))
    return n.value == "yes"


def _block(n):
    if not isinstance(n.value, list):
        raise SimError("%s needs a block (%s:%d)" % (n.key, n.file, n.line))
    return {x.key: x for x in n.value}


def _char_pred(fn):
    """A trigger 'key = <character>' on a character."""
    def t(run, fr, n):
        this = fr[0]
        other = _target(run, fr, n)
        if other is None:
            return False
        return bool(fn(run, this, other))
    return t


def _t_has_trait(run, fr, n):
    return n.value in fr[0].traits


def _t_has_variable(run, fr, n):
    return n.value in fr[0].vars


def _t_has_variable_list(run, fr, n):
    return bool(fr[0].var_lists.get(n.value))


def _t_is_target_in_variable_list(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    return tgt in fr[0].var_lists.get(b["name"].value, [])


def _t_variable_list_size(run, fr, n):
    b = _block(n)
    size = len(fr[0].var_lists.get(b["name"].value, []))
    v = b["value"]
    return _cmp(float(size), v.op, run.val(v.value, fr, v))


def _t_is_in_list(run, fr, n):
    return fr[0] in run.lists.get(n.value, [])


def _t_opinion(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    v = b["value"]
    return _cmp(run.w.opinion_of(fr[0], tgt), v.op, run.val(v.value, fr, v))


def _t_has_dread_level_towards(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    lv = b["level"]
    return _cmp(float(run.w.dread.get((fr[0], tgt), 0)), lv.op, run.val(lv.value, fr, lv))


def _t_faith_hostility_level(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    if tgt is None or not isinstance(fr[0], Faith):
        run.err(n, "faith_hostility_level of %r to %r" % (fr[0], tgt))
        return False
    v = b["value"]
    return _cmp(float(fr[0].hostility_to(tgt)), v.op, run.val(v.value, fr, v))


def _t_has_hook(run, fr, n):
    return (fr[0], _target(run, fr, n)) in run.w.hooks


def _t_has_strong_hook(run, fr, n):
    return run.w.hooks.get((fr[0], _target(run, fr, n))) == "strong"


def _t_has_truce(run, fr, n):
    return frozenset((fr[0], _target(run, fr, n))) in run.w.truces


def _t_is_allied_to(run, fr, n):
    return frozenset((fr[0], _target(run, fr, n))) in run.w.alliances


def _rel(kind):
    def t(run, fr, n):
        if n.value in ("yes", "no"):
            return bool(fr[0].rel(kind)) == (n.value == "yes")
        return _target(run, fr, n) in fr[0].rel(kind)
    return t


def _t_has_character_flag(run, fr, n):
    return n.value in fr[0].character_flags


def _t_government_has_flag(run, fr, n):
    return n.value in fr[0].government_flags


def _t_has_game_rule(run, fr, n):
    rule = n.value
    for k, v in run.w.game_rules.items():
        if v == rule:
            return True
    return False


def _t_has_claim_on(run, fr, n):
    return _target(run, fr, n) in fr[0].claims


def _t_is_known_by(run, fr, n):
    return _target(run, fr, n) in fr[0].known_by


def _t_war_side(side):
    def t(run, fr, n):
        this = fr[0]
        if isinstance(this, War):
            return _target(run, fr, n) in getattr(this, side)
        raise SimError("%s on %r" % (n.key, this))
    return t


def _t_is_participant(run, fr, n):
    this = fr[0]
    c = _target(run, fr, n)
    return c in this.attackers or c in this.defenders


def _t_is_at_war_with(run, fr, n):
    return run.w.at_war_with(fr[0], _target(run, fr, n))


def _t_is_tributary_of(run, fr, n):
    return fr[0].suzerain is not None and fr[0].suzerain is _target(run, fr, n)


def _t_target_is_liege_or_above(run, fr, n):
    return _target(run, fr, n) in run.w.liege_chain(fr[0])


def _t_is_liege_or_above_of(run, fr, n):
    return fr[0] in run.w.liege_chain(_target(run, fr, n))


def _t_is_vassal_or_below_of(run, fr, n):
    return _target(run, fr, n) in run.w.liege_chain(fr[0])


def _t_is_vassal_of(run, fr, n):
    return fr[0].is_landed and fr[0].liege is _target(run, fr, n)


def _t_is_courtier_of(run, fr, n):
    return not fr[0].is_landed and fr[0].liege is _target(run, fr, n)


def _t_is_close_family_of(run, fr, n):
    return _target(run, fr, n) in run.w.close_family(fr[0])


def _t_is_spouse_of(run, fr, n):
    return _target(run, fr, n) in fr[0].spouses


def _t_is_child_of(run, fr, n):
    return _target(run, fr, n) in run.w.parents(fr[0])


def _t_is_imprisoned_by(run, fr, n):
    return fr[0].imprisoned_by is not None and fr[0].imprisoned_by is _target(run, fr, n)


def _t_is_councillor_of(run, fr, n):
    return fr[0].councillor_of is not None and fr[0].councillor_of is _target(run, fr, n)


def _t_is_foreign_court_guest_of(run, fr, n):
    return fr[0].guest_of is not None and fr[0].guest_of is _target(run, fr, n)


def _t_is_pool_guest_of(run, fr, n):
    return fr[0].pool_guest_of is not None and fr[0].pool_guest_of is _target(run, fr, n)


def _t_is_powerful_vassal_of(run, fr, n):
    return fr[0].powerful_vassal and fr[0].liege is _target(run, fr, n)


def _t_is_rightful_liege_of(run, fr, n):
    return _target(run, fr, n).liege is fr[0]


def _t_is_concubine_of(run, fr, n):
    return fr[0].concubine_of is _target(run, fr, n)


def _t_is_criminal_for(run, fr, n):
    return fr[0].criminal


def _t_is_shunned_for(run, fr, n):
    return fr[0].shunned


def _t_secret_type(run, fr, n):
    return fr[0].type == n.value


def _t_can_be_tributary_of(run, fr, n):
    other = _target(run, fr, n)
    me = fr[0]
    return me.is_landed and me.suzerain is None and other is not me and _tier(other) >= _tier(me) and \
        r_independent(me)


def r_independent(c):
    return c.is_landed and (c.liege is None or not c.liege.is_landed)


def _t_obligation_can_change(direction):
    """tributary_contract_obligation_level_can_be_increased = <obligation type>; levels 0..2 in the mock."""
    def t(run, fr, n):
        lv = (fr[0].obligations or {}).get(n.value, 1)
        return (lv < 2) if direction > 0 else (lv > 0)
    return t


def _t_has_doctrine_parameter(run, fr, n):
    this = fr[0]
    return n.value in (this.parameters if isinstance(this, Faith) else this.faith.parameters)


def _t_has_doctrine(run, fr, n):
    this = fr[0]
    return n.value in (this.doctrines if isinstance(this, Faith) else this.faith.doctrines)


def _t_has_dynasty_perk(run, fr, n):
    d = fr[0] if isinstance(fr[0], Dynasty) else fr[0].dynasty
    return d is not None and n.value in d.perks


def _t_has_cultural_era_or_later(run, fr, n):
    eras = {"culture_era_tribal": 1, "culture_era_early_medieval": 2, "culture_era_high_medieval": 3,
            "culture_era_late_medieval": 4}
    return fr[0].era >= eras[n.value]


def _t_has_opinion_modifier(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    return (tgt, b["modifier"].value) in fr[0].opinion_modifiers


def _t_is_leading_faction_type(run, fr, n):
    return run.w.factions.get(fr[0]) == n.value


def _t_rarity(run, fr, n):
    return fr[0].rarity == n.value


def _t_has_artifact_modifier(run, fr, n):
    return n.value in fr[0].modifiers


def _t_sex_opposite_of(run, fr, n):
    return fr[0].female != _target(run, fr, n).female


def _family(run, a, b):
    w = run.w
    return b in w.close_family(a)


TRIGGERS = {
    "has_trait": _t_has_trait,
    "has_variable": _t_has_variable,
    "has_variable_list": _t_has_variable_list,
    "is_target_in_variable_list": _t_is_target_in_variable_list,
    "variable_list_size": _t_variable_list_size,
    "is_in_list": _t_is_in_list,
    "opinion": _t_opinion,
    "has_dread_level_towards": _t_has_dread_level_towards,
    "faith_hostility_level": _t_faith_hostility_level,
    "has_hook": _t_has_hook,
    "has_strong_hook": _t_has_strong_hook,
    "has_usable_hook": _t_has_hook,
    "has_weak_hook": lambda r, fr, n: r.w.hooks.get((fr[0], _target(r, fr, n))) == "weak",
    "has_truce": _t_has_truce,
    "is_allied_to": _t_is_allied_to,
    "has_relation_friend": _rel("friend"),
    "has_relation_best_friend": _rel("best_friend"),
    "has_relation_rival": _rel("rival"),
    "has_relation_nemesis": _rel("nemesis"),
    "has_relation_lover": _rel("lover"),
    "has_relation_soulmate": _rel("soulmate"),
    "has_relation_victim": _rel("victim"),
    "has_relation_torturer": _rel("torturer"),
    "has_character_flag": _t_has_character_flag,
    "government_has_flag": _t_government_has_flag,
    "has_game_rule": _t_has_game_rule,
    "has_claim_on": _t_has_claim_on,
    "is_known_by": _t_is_known_by,
    "is_attacker": _t_war_side("attackers"),
    "is_defender": _t_war_side("defenders"),
    "is_participant": _t_is_participant,
    "is_at_war_with": _t_is_at_war_with,
    "is_tributary_of": _t_is_tributary_of,
    "target_is_liege_or_above": _t_target_is_liege_or_above,
    "is_liege_or_above_of": _t_is_liege_or_above_of,
    "target_is_vassal_or_below": lambda r, fr, n: fr[0] in r.w.liege_chain(_target(r, fr, n)),
    "is_vassal_or_below_of": _t_is_vassal_or_below_of,
    "is_vassal_of": _t_is_vassal_of,
    "is_courtier_of": _t_is_courtier_of,
    "is_close_family_of": _t_is_close_family_of,
    "is_close_or_extended_family_of": _t_is_close_family_of,
    "is_extended_family_of": lambda r, fr, n: False,
    "is_spouse_of": _t_is_spouse_of,
    "is_child_of": _t_is_child_of,
    "is_parent_of": lambda r, fr, n: fr[0] in r.w.parents(_target(r, fr, n)),
    "is_sibling_of": lambda r, fr, n: _target(r, fr, n) in r.w.siblings(fr[0]),
    "is_grandchild_of": lambda r, fr, n: False,
    "is_grandparent_of": lambda r, fr, n: False,
    "is_nibling_of": lambda r, fr, n: False,
    "is_uncle_or_aunt_of": lambda r, fr, n: False,
    "is_cousin_of": lambda r, fr, n: False,
    "is_imprisoned_by": _t_is_imprisoned_by,
    "is_councillor_of": _t_is_councillor_of,
    "is_foreign_court_guest_of": _t_is_foreign_court_guest_of,
    "is_pool_guest_of": _t_is_pool_guest_of,
    "is_powerful_vassal_of": _t_is_powerful_vassal_of,
    "is_rightful_liege_of": _t_is_rightful_liege_of,
    "is_concubine_of": _t_is_concubine_of,
    "is_criminal_for": _t_is_criminal_for,
    "is_shunned_for": _t_is_shunned_for,
    "can_be_tributary_of": _t_can_be_tributary_of,
    "tributary_contract_obligation_level_can_be_increased": _t_obligation_can_change(1),
    "tributary_contract_obligation_level_can_be_decreased": _t_obligation_can_change(-1),
    "has_doctrine_parameter": _t_has_doctrine_parameter,
    "has_doctrine": _t_has_doctrine,
    "has_dynasty_perk": _t_has_dynasty_perk,
    "has_cultural_era_or_later": _t_has_cultural_era_or_later,
    "has_opinion_modifier": _t_has_opinion_modifier,
    "is_leading_faction_type": _t_is_leading_faction_type,
    "rarity": _t_rarity,
    "has_artifact_modifier": _t_has_artifact_modifier,
    "sex_opposite_of": _t_sex_opposite_of,
    "sex_same_as": lambda r, fr, n: fr[0].female == _target(r, fr, n).female,
    "can_have_children_with": lambda r, fr, n: fr[0].female != _target(r, fr, n).female,
    "was_preferred_heir": lambda r, fr, n: _target(r, fr, n) in fr[0].preferred_heir_of,
    "save_temporary_scope_as": lambda r, fr, n: r.scopes.__setitem__(n.value, fr[0]) or True,
    "has_dlc_feature": lambda r, fr, n: r.w.dlc_features is None or n.value in r.w.dlc_features,
    "rite_has_doctrine": _t_has_doctrine,
    "is_in_family": lambda r, fr, n: fr[0].family == n.value,
    "has_trait_with_flag": lambda r, fr, n: any(n.value in r.lib.trait_flags.get(t, ()) for t in fr[0].traits),
    "rite_has_parameter": _t_has_doctrine_parameter,
}


# ---------------------------------------------------------------- iterators
def _i_neighbor_realms(run, c, body, fr):
    me = run.w.top_liege(c)
    out = []
    for pair in run.w.neighbors:
        if me in pair:
            other = [x for x in pair if x is not me]
            if other and other[0] not in out:
                out.append(other[0])
    return out


def _i_relation(run, c, body, fr):
    types = [x.value for x in body if x.key == "type"]
    out = []
    for t in types:
        for x in c.rel(t):
            if x not in out:
                out.append(x)
    return out


def _i_realm_county(run, c, body, fr):
    out = []
    stack = [c]
    seen = set()
    while stack:
        x = stack.pop(0)
        if x in seen:
            continue
        seen.add(x)
        out += [t for t in x.titles if t.tier == 2]
        stack += run.w.vassals(x)
    return out


def _i_known_secret(run, c, body, fr):
    return [s for s in run.w.secrets if c in s.known_by]


ITERS = {
    "vassal": lambda r, c, b, fr: r.w.vassals(c),
    "courtier": lambda r, c, b, fr: r.w.courtiers(c),
    "ally": lambda r, c, b, fr: [x for x in r.w.chars if frozenset((c, x)) in r.w.alliances],
    "child": lambda r, c, b, fr: r.w.children(c),
    "spouse": lambda r, c, b, fr: list(c.spouses),
    "close_family_member": lambda r, c, b, fr: r.w.close_family(c),
    "relation": _i_relation,
    "prisoner": lambda r, c, b, fr: [x for x in r.w.chars if x.imprisoned_by is c],
    "held_title": lambda r, c, b, fr: list(c.titles),
    "realm_county": _i_realm_county,
    "claim": lambda r, c, b, fr: list(c.claims),
    "character_artifact": lambda r, c, b, fr: [a for a in r.w.artifacts if a.owner is c],
    "character_war": lambda r, c, b, fr: r.w.wars_of(c),
    "known_secret": _i_known_secret,
    "secret": lambda r, c, b, fr: [s for s in r.w.secrets if s.owner is c],
    "neighboring_and_across_water_top_liege_realm_owner": _i_neighbor_realms,
    "neighboring_top_liege_realm_owner": _i_neighbor_realms,
    "foreign_court_guest": lambda r, c, b, fr: [x for x in r.w.chars if x.guest_of is c],
    "pool_guest": lambda r, c, b, fr: [x for x in r.w.chars if x.pool_guest_of is c],
    "war_attacker": lambda r, w, b, fr: list(w.attackers),
    "war_defender": lambda r, w, b, fr: list(w.defenders),
    "war_participant": lambda r, w, b, fr: list(w.attackers) + list(w.defenders),
    "clerical_elector_title": lambda r, c, b, fr: [],
    "elector": lambda r, t, b, fr: list(t.electors),
    "tributary": lambda r, c, b, fr: [x for x, s in r.w.tributaries.items() if s is c],
    "councillor": lambda r, c, b, fr: [x for x in r.w.chars if x.councillor_of is c],
    "living_character": lambda r, c, b, fr: [x for x in r.w.chars if x.alive],
}


# ---------------------------------------------------------------- effects
def _e_set_variable(run, fr, n):
    this = fr[0]
    if isinstance(n.value, str):
        this.vars[n.value] = True
        return
    b = _block(n)
    name = b["name"].value
    this.vars[name] = run.resolve(b["value"].value, fr, b["value"]) if "value" in b else True
    if this.vars[name] is None:
        run.err(n, "set_variable %s to a missing value %s" % (name, b["value"].value))
        del this.vars[name]


def _e_change_variable(run, fr, n):
    this = fr[0]
    b = _block(n)
    name = b["name"].value
    if name not in this.vars:
        run.err(n, "change_variable on unset %s" % name)
        this.vars[name] = 0.0
    cur = run.num(this.vars[name], n, name)
    for x in n.value:
        if x.key == "name":
            continue
        v = run.val(x.value, fr, x)
        if x.key == "add":
            cur += v
        elif x.key == "subtract":
            cur -= v
        elif x.key == "multiply":
            cur *= v
        elif x.key == "divide":
            cur = cur / v if v else cur
        elif x.key == "min":
            cur = max(cur, v)
        elif x.key == "max":
            cur = min(cur, v)
        else:
            raise SimError("change_variable %s" % x.key)
    this.vars[name] = cur


def _e_clamp_variable(run, fr, n):
    b = _block(n)
    name = b["name"].value
    cur = run.num(fr[0].vars.get(name), n, name)
    if "min" in b:
        cur = max(cur, run.val(b["min"].value, fr, n))
    if "max" in b:
        cur = min(cur, run.val(b["max"].value, fr, n))
    fr[0].vars[name] = cur


def _e_remove_variable(run, fr, n):
    if n.value not in fr[0].vars:
        run.err(n, "remove_variable on unset %s" % n.value)
    fr[0].vars.pop(n.value, None)


def _e_add_to_variable_list(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    if tgt is None:
        run.err(n, "add_to_variable_list of a missing target")
        return
    lst = fr[0].var_lists.setdefault(b["name"].value, [])
    if tgt not in lst:
        lst.append(tgt)


def _e_remove_list_variable(run, fr, n):
    b = _block(n)
    tgt = run.resolve(b["target"].value, fr, n)
    lst = fr[0].var_lists.get(b["name"].value, [])
    if tgt in lst:
        lst.remove(tgt)


def _e_clear_variable_list(run, fr, n):
    fr[0].var_lists.pop(n.value, None)


def _e_save_scope_as(run, fr, n):
    run.scopes[n.value] = fr[0]


def _e_save_scope_value_as(run, fr, n):
    b = _block(n)
    v = b["value"].value
    run.scopes[b["name"].value] = run.resolve(v, fr, n) if not isinstance(v, list) else run.val_block(v, fr)


def _e_clear_saved_scope(run, fr, n):
    run.scopes.pop(n.value, None)


def _e_add_to_list(run, fr, n):
    lst = run.lists.setdefault(n.value, [])
    if fr[0] not in lst:
        lst.append(fr[0])


def _e_remove_from_list(run, fr, n):
    lst = run.lists.get(n.value, [])
    if fr[0] in lst:
        lst.remove(fr[0])


def _e_run_block(run, fr, n):
    if isinstance(n.value, list):
        run.eff(_strip(n.value, ("text",)), fr)


def _e_noop(run, fr, n):
    pass


def _e_toast(run, fr, n):
    run.toasts.append((fr[0], n.value))


def _e_trigger_event(run, fr, n):
    run.events.append((fr[0], n.value if isinstance(n.value, str) else "block"))


def _e_add_character_flag(run, fr, n):
    fr[0].character_flags.add(n.value if isinstance(n.value, str) else _block(n)["flag"].value)


def _e_remove_character_flag(run, fr, n):
    fr[0].character_flags.discard(n.value)


EFFECTS = {
    "set_variable": _e_set_variable,
    "change_variable": _e_change_variable,
    "clamp_variable": _e_clamp_variable,
    "remove_variable": _e_remove_variable,
    "add_to_variable_list": _e_add_to_variable_list,
    "remove_list_variable": _e_remove_list_variable,
    "clear_variable_list": _e_clear_variable_list,
    "save_scope_as": _e_save_scope_as,
    "save_temporary_scope_as": _e_save_scope_as,
    "save_scope_value_as": _e_save_scope_value_as,
    "save_temporary_scope_value_as": _e_save_scope_value_as,
    "clear_saved_scope": _e_clear_saved_scope,
    "add_to_list": _e_add_to_list,
    "add_to_temporary_list": _e_add_to_list,
    "remove_from_list": _e_remove_from_list,
    "hidden_effect": _e_run_block,
    "custom_tooltip": _e_run_block,
    "custom_description": _e_run_block,
    "show_as_tooltip": _e_noop,
    "send_interface_toast": _e_toast,
    "send_interface_message": _e_toast,
    "trigger_event": _e_trigger_event,
    "add_character_flag": _e_add_character_flag,
    "remove_character_flag": _e_remove_character_flag,
}


# ====================================================================== the panel
class Panel:
    """The Backroom Deal panel, opened by ME on THEM. Every change goes through the panel's own buttons."""

    def __init__(self, lib, world, me, them):
        self.lib, self.w, self.me, self.them = lib, world, me, them
        self.errors = []
        self.run_effect("qpq_ui_open_effect", params={"RECIPIENT": "scope:qpq_sim_them"})

    # ---- running script
    def _run(self):
        return Run(self.lib, self.w, self.me, {"actor": self.me, "recipient": self.them,
                                               "qpq_sim_them": self.them})

    def run_effect(self, name, params=None):
        r = self._run()
        body = self.lib.expand("effect", name, params) if params else self.lib.effects[name]
        r.eff(body, (self.me, None))
        self.errors += r.errors
        return r

    def check(self, trigger):
        r = self._run()
        ok = r.trig(self.lib.triggers[trigger], (self.me, None))
        self.errors += r.errors
        return ok

    def explain(self, trigger="qpq_ui_can_propose_trigger"):
        """The tooltip keys of the innermost conditions that fail: what the player would read on the button."""
        r = self._run()
        out = []

        def walk(nodes, fr):
            groups = []
            for n in nodes:
                if n.key in ("trigger_else_if", "trigger_else") and groups:
                    groups[-1].append(n)
                else:
                    groups.append([n])
            for g in groups:
                if r.trig(g, fr):
                    continue
                n = g[0]
                if n.key in ("custom_description", "custom_tooltip") and isinstance(n.value, list):
                    before = len(out)
                    walk(_strip(n.value, ("text", "subject", "object", "value")), fr)
                    if len(out) == before:
                        out.append({x.key: x.value for x in n.value}.get("text"))
                elif n.key in self.lib.triggers and n.value == "yes":
                    walk(self.lib.triggers[n.key], fr)
                elif n.key in ("AND",) or n.key == "trigger_if":
                    walk(n.value if n.key == "AND" else _strip(n.value, ("limit",)), fr)
                # anything else fails silently here: the enclosing description (if any) says what it is
        walk(self.lib.triggers[trigger], (self.me, None))
        return out

    def failures(self):
        """Which of the Propose button's conditions fail (by their tooltip key)."""
        r = self._run()
        fails = []
        groups = []
        for n in self.lib.triggers["qpq_ui_can_propose_trigger"]:
            if n.key in ("trigger_else_if", "trigger_else") and groups:
                groups[-1].append(n)
            else:
                groups.append([n])
        for g in groups:
            if not r.trig(g, (self.me, None)):
                n = g[0]
                b = {x.key: x.value for x in n.value} if isinstance(n.value, list) else {}
                fails.append(b.get("text", n.key))
        self.errors += r.errors
        return fails

    def shown(self, gui, **scopes):
        g = self._gui(gui)
        r = self._run()
        r.scopes.update(scopes)
        for part in ("is_shown",):
            for x in g:
                if x.key == part and not r.trig(x.value, (self.me, None)):
                    return False
        return True

    def valid(self, gui, **scopes):
        g = self._gui(gui)
        r = self._run()
        r.scopes.update(scopes)
        for x in g:
            if x.key in ("is_shown", "is_valid") and not r.trig(x.value, (self.me, None)):
                return False
        return True

    def click(self, gui, **scopes):
        g = self._gui(gui)
        if not self.valid(gui, **scopes):
            raise Refused(gui)
        r = self._run()
        r.scopes.update(scopes)
        for x in g:
            if x.key == "effect":
                r.eff(x.value, (self.me, None))
        self.errors += r.errors
        return r

    def _gui(self, gui):
        if gui not in self.lib.guis:
            raise SimError("no scripted GUI %s" % gui)
        return self.lib.guis[gui]

    # ---- reading
    def value(self, name, this):
        """A script value, evaluated in THIS (with the panel's actor and recipient)."""
        return self._run().value(name, (this, None))

    def var(self, name, default=None):
        return self.me.vars.get("qpq_ui_" + name, default)

    def candidates(self, leg):
        return list(self.me.var_lists.get("qpq_ui_%s_candidates" % leg, []))

    def refusals(self):
        out = []
        for k, v in self.me.vars.items():
            if k.startswith("qpq_ui_ref_"):
                out.append(k[len("qpq_ui_ref_"):])
        return sorted(out)

    def acceptance(self):
        keys = ["ask", "offers", "goal", "char", "risk", "dread", "circ", "refuse", "opinion", "public", "cap", "other",
                "cmd", "before_cmd", "total"]
        out = {}
        for k in keys:
            v = self.var("acc_" + k)
            if v is not None:
                out[k] = round(v, 3)
        for L in ("t", "i"):
            ek = self.var(L + "_ekind")
            if ek is not None:
                leg = {"kind": ek.name}
                for k in ("a_ask", "a_offers", "a_goal", "a_char", "a_risk", "a_dread", "a_circ", "a_refuse", "price",
                          "fair", "payer_tier", "agent_tier"):
                    v = self.var(L + "_" + k)
                    if v is not None:
                        leg[k] = round(v, 3) if isinstance(v, float) else v
                out["leg_" + L] = leg
        return out

    def ai_accepts(self):
        """What the AI answers: the Propose button's own conditions, with them an AI."""
        return not self.failures()

    # ---- composing
    def deed(self, leg, kind, pick=None):
        """Choose the deed of a leg ('t': they do it, 'i': you do it). kind None: goods only."""
        if kind is None:
            self.click("qpq_ui_nodeed_" + leg)
            return
        self.click("qpq_ui_kind_%s_%s" % (leg, kind))
        if pick is not None:
            self.pick(leg, pick)

    def pick(self, leg, target):
        if isinstance(target, Character):
            self.click("qpq_ui_pick_char_" + leg, qpq_pick=target)
        elif isinstance(target, Title):
            self.click("qpq_ui_pick_title_" + leg, qpq_pick=target)
        elif isinstance(target, Artifact):
            self.click("qpq_ui_pick_artifact_" + leg, qpq_pick=target)
        else:
            raise SimError("cannot pick %r" % (target,))

    def gold(self, leg, amount=None):
        """Put gold in a leg (leg t: you pay it; leg i: they pay it). amount None: the fair price."""
        if "qpq_ui_%s_o_gold" % leg not in self.me.vars:
            self.click("qpq_ui_gold_add_" + leg)
        if amount is not None:
            # the amount buttons step by 10/100/1000 from the fair price; set it as they would leave it
            self.me.vars["qpq_ui_%s_amount" % leg] = float(amount)
            self.click("qpq_ui_refresh")

    def offer(self, leg, good):
        """Tick a good. Land, artifacts and secrets are chosen item by item: the first candidate is taken."""
        picked = {"land": ("land", "land_toggle"), "artifact": ("gift_artifact", "artifact_toggle"),
                  "secret": ("gift_secret", "secret_toggle")}
        if good in picked:
            lst, gui = picked[good]
            cands = self.me.var_lists.get("qpq_ui_%s_%s_candidates" % (leg, lst), [])
            if not cands:
                raise Refused("no %s to give" % good)
            self.click("qpq_ui_%s_%s" % (gui, leg), qpq_pick=cands[0])
            return
        self.click("qpq_ui_offer_%s_%s" % (leg, good))

    def timing(self, leg, when):
        self.click("qpq_ui_timing_%s_%s" % (leg, when))

    def public(self, yes=True):
        self.click("qpq_ui_secrecy_public" if yes else "qpq_ui_secrecy_secret")

    def command(self, tier):
        self.click("qpq_ui_command_%d" % tier)

    def refresh(self):
        self.click("qpq_ui_refresh")


# ====================================================================== the game's text
class Loc:
    """The mod's English localization, read as plain text: $KEY$ filled in, markup dropped, the panel's few
    data functions given the names they would show."""

    LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')

    def __init__(self, mod=ROOT):
        self.text = {}
        d = os.path.join(mod, "localization", "english")
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".yml"):
                for line in read(os.path.join(d, fn)).split("\n"):
                    m = self.LINE.match(line)
                    if m:
                        self.text[m.group(1)] = m.group(2)

    def plain(self, key, names=None, depth=0):
        t = self.text.get(key, key)
        names = names or {}
        if depth < 6:
            t = re.sub(r"\$([A-Za-z0-9_]+)\$", lambda m: self.plain(m.group(1), names, depth + 1), t)

        def data(m):
            x = m.group(1)
            if "|E" in x:
                return x.split("|")[0].replace("_", " ")
            for var, name in names.items():
                if "'%s'" % var in x:
                    return name
            return "..."
        t = re.sub(r"\[([^\]]*)\]", data, t)
        t = re.sub(r"#[A-Za-z_]+ ?|#!", "", t)
        return t.replace("\\n", " ").replace("•", "").strip()


# ====================================================================== a standard world
def standard_world(player="king"):
    """A world with something for every deed: an elective kingdom and its court, a Church, an orthodox empire,
    sunni and shia realms, a pagan jarl, a holy order, a tributary chief, and a war. W maps names to objects."""
    w = World()
    W = {"world": w}
    christ = w.register("religion", "christianity_religion", Religion("christianity"))
    islam = w.register("religion", "islam_religion", Religion("islam"))
    norse = w.register("religion", "germanic_religion", Religion("germanic", family="rf_pagan"))
    cath = w.register("faith", "catholic", Faith(
        "catholic", religion=christ, doctrines=("doctrine_spiritual_head", "doctrine_sacraments_central"),
        parameters=("has_clerical_electors", "excommunication_active", "great_holy_wars_active")))
    orth = w.register("faith", "orthodox", Faith(
        "orthodox", religion=christ, doctrines=("doctrine_spiritual_head", "doctrine_sacraments_central")))
    sunni = w.register("faith", "ashari", Faith(
        "ashari", religion=islam, doctrines=("doctrine_temporal_head", "muhammad_succession_sunni_doctrine")))
    shia = w.register("faith", "ismaili", Faith(
        "ismaili", religion=islam, doctrines=("muhammad_succession_shia_doctrine",)))
    pagan = w.register("faith", "norse_pagan", Faith("norse_pagan", religion=norse))
    dharmic = w.register("religion", "hinduism_religion", Religion("hinduism", family="rf_eastern"))
    vaishnav = w.register("faith", "vaishnavism", Faith("vaishnavism", religion=dharmic))
    for k, v in (("catholic", cath), ("orthodox", orth), ("sunni", sunni), ("shia", shia), ("pagan", pagan)):
        W[k] = v
    eng = w.register("culture", "english", Culture("english"))

    def c(name, faith=cath, **k):
        k.setdefault("dynasty", Dynasty(name + "_dyn"))
        W[name] = w.char(name, faith=faith, culture=eng, is_ai=(name != player), **k)
        return W[name]

    def t(name, tier, holder, **k):
        W[name] = w.title(name, tier, holder, **k)
        if holder is not None and tier > 2 and holder.capital is None:
            t("c_" + name[2:] + "_seat", 2, holder)     # every ruler sits in a county
        return W[name]

    # ---- the kingdom (elective), its court and vassals
    king = c("king", gold=500, income=20, prestige_level=3, legitimacy_level=3, max_strength=6000,
             current_strength=6000, diplomacy=12)
    t("k_realm", 4, king)
    t("c_crown", 2, king)
    t("c_royal_demesne", 2, king)
    queen = c("queen", liege=king, female=True, dynasty=Dynasty("queen_dyn"), gold=30, income=1)
    king.spouses.append(queen)
    queen.spouses.append(king)
    c("prince", liege=king, father=king, mother=queen, dynasty=king.dynasty, age=17, gold=10, income=1)
    duke = c("duke", liege=king, gold=200, income=8, max_strength=1500, current_strength=1500,
             powerful_vassal=True)
    t("d_duchy", 3, duke)
    t("c_duke_seat", 2, duke)
    duke2 = c("duke2", liege=king, gold=150, income=6, max_strength=1200, current_strength=1200,
              traits=("excommunicated",))
    t("d_other", 3, duke2)
    t("c_other_seat", 2, duke2)
    count = c("count", liege=duke, gold=60, income=3, max_strength=400, current_strength=400)
    t("c_county", 2, count)
    count2 = c("count2", liege=king, gold=80, income=3, max_strength=500, current_strength=500)
    t("c_county2", 2, count2)
    c("courtier", liege=king, gold=20, income=1, councillor_of=king)
    bishop = c("bishop", liege=king, clergy=True, learning=14, gold=40, income=2)
    pretender = c("pretender", liege=king, gold=15, income=1, age=24)
    W["k_realm"].electors = (duke, duke2)
    W["faction"] = Faction(type="claimant_faction", target=king, leader=duke2)
    duke.joined_faction = W["faction"]
    duke2.joined_faction = W["faction"]
    w.factions[duke2] = "claimant_faction"
    duke.claims.append(W["c_county2"])
    W["sword"] = w.artifact("sword", duke, rarity="famed")
    W["crown_jewel"] = w.artifact("crown_jewel", king, rarity="illustrious")
    W["king_secret"] = w.secret(king, "secret_murder", target=count2, known_by=[duke])
    W["count2_secret"] = w.secret(count2, "secret_deviant", known_by=[duke])
    # ---- the Church
    pope = c("pope", gold=1000, income=40, clergy=True, learning=20, max_strength=300, current_strength=300)
    cath.head_title = t("k_papal_state", 4, pope, is_head_of_faith_title=True)
    cardinal_title = t("b_cardinalate", 1, None)
    bishop.clerical_elector_title = cardinal_title
    grandmaster = c("grandmaster", gold=250, income=6, max_strength=2000, current_strength=2000)
    t("d_templars", 3, grandmaster, holy_order=True)
    # ---- the orthodox empire
    emperor = c("emperor", faith=orth, gold=900, income=35, max_strength=9000, current_strength=9000)
    t("e_empire", 5, emperor)
    t("c_city", 2, emperor)
    strategos = c("strategos", faith=orth, liege=emperor, gold=150, income=6, max_strength=1500,
                  current_strength=1500)
    t("d_theme", 3, strategos)
    patriarch = c("patriarch", faith=orth, liege=emperor, clergy=True, learning=16, gold=200, income=5)
    orth.head_title = t("b_patriarchate", 1, None)
    orth.head_title.holder = patriarch
    # ---- sunni realms, the caliph, a learned man
    foe = c("foe", faith=sunni, gold=400, income=15, max_strength=5000, current_strength=5000)
    t("k_foe", 4, foe)
    t("c_foe_seat", 2, foe)
    pretender.claims.append(W["k_foe"])
    foe_vassal = c("foe_vassal", faith=sunni, liege=foe, gold=90, income=4, max_strength=800,
                   current_strength=800, councillor_of=foe)
    t("d_foe_duchy", 3, foe_vassal)
    t("c_foe_vassal_seat", 2, foe_vassal)
    princess = c("princess", faith=sunni, liege=foe, female=True, dynasty=king.dynasty, father=king,
                 gold=20, income=1)
    foe.spouses.append(princess)
    princess.spouses.append(foe)
    caliph = c("caliph", faith=sunni, gold=600, income=18, max_strength=3000, current_strength=3000)
    sunni.head_title = t("k_caliphate", 4, caliph, is_head_of_faith_title=True)
    c("alim", faith=sunni, liege=foe, clergy=True, learning=16, gold=30, income=1)
    # ---- a shia emir and his imam (a faith with no head)
    emir = c("emir", faith=shia, gold=180, income=7, max_strength=1800, current_strength=1800)
    t("d_emirate", 3, emir)
    c("imam", faith=shia, liege=emir, clergy=True, learning=14, gold=25, income=1)
    # ---- a pagan jarl and his priest
    jarl = c("jarl", faith=pagan, gold=120, income=5, max_strength=1600, current_strength=1600)
    t("d_jarldom", 3, jarl)
    jarl.realm_priest = c("godi", faith=pagan, liege=jarl, clergy=True, learning=12, gold=15, income=1)
    # ---- a raja and his purohit (an eastern faith)
    raja = c("raja", faith=vaishnav, gold=220, income=9, max_strength=2500, current_strength=2500)
    t("k_raj", 4, raja)
    raja.realm_priest = c("purohit", faith=vaishnav, liege=raja, clergy=True, learning=13, gold=20, income=1)
    # ---- a tributary chief
    chief = c("chief", gold=70, income=3, max_strength=700, current_strength=700,
              obligations={"default_tributary_taxes": 1})
    t("d_tribe", 3, chief)
    w.tribute(chief, king)
    # ---- a third realm, at war with the foe
    third = c("third", gold=300, income=12, max_strength=4000, current_strength=3000)
    t("k_third", 4, third)
    t("c_third_seat", 2, third)
    for a_, b_ in ((king, foe), (king, third), (foe, third), (king, emperor), (foe, emir), (king, jarl),
                   (king, chief), (foe, caliph), (king, grandmaster), (king, pope)):
        w.border(a_, b_)
    W["war"] = w.war([foe], [third], attacker_war_score=10, war_days=400)
    return w, W


def kind_names(lib, leg):
    pre = "qpq_ui_kind_%s_" % leg
    return [g[len(pre):] for g in lib.guis if g.startswith(pre)]


def offered_pairs(lib, leg, kind, player_names=None):
    """Every (me, them) the deed's button is valid for, in the standard world."""
    w, W = standard_world()
    gui = lib.guis["qpq_ui_kind_%s_%s" % (leg, kind)]
    out = []
    for me in w.chars:
        if player_names and me.name not in player_names:
            continue
        for them in w.chars:
            if me is them:
                continue
            r = Run(lib, w, me, {"actor": me, "recipient": them})
            if all(r.trig(x.value, (me, None)) for x in gui if x.key in ("is_shown", "is_valid")):
                out.append((me.name, them.name))
    return out


def scenario(lib, me_name, them_name, setup):
    """A fresh standard world with ME as the player, the panel opened on THEM and SETUP(panel, W) applied."""
    w, W = standard_world(player=me_name)
    p = Panel(lib, w, W[me_name], W[them_name])
    setup(p, W)
    return p, W


def sweep_kinds(lib, verbose=True, only=None):
    """Every deed, on each leg, between every pair it can be put to; the other leg pays the fair price."""
    out = {}
    from collections import Counter
    errs = Counter()
    for leg in ("t", "i"):
        other = "i" if leg == "t" else "t"
        for kind in kind_names(lib, leg):
            if only and kind not in only:
                continue
            pairs = offered_pairs(lib, leg, kind)
            rows = []
            for me_name, them_name in pairs:
                def setup(p, W):
                    p.deed(leg, kind)
                    cands = p.candidates(leg)
                    if cands:
                        p.pick(leg, cands[0])
                    p.deed(other, None)
                    p.gold(other)
                try:
                    p, W = scenario(lib, me_name, them_name, setup)
                    rows.append((me_name, them_name, p.acceptance(), p.failures(), p.errors))
                except SimError as e:
                    rows.append((me_name, them_name, None, ["SIMERROR %s" % e], []))
                except Exception as e:  # noqa: BLE001 - a crash in the simulator itself
                    rows.append((me_name, them_name, None, ["CRASH %s: %s" % (type(e).__name__, e)], []))
            out[(leg, kind)] = rows
            for r in rows:
                for e in set(r[4]):
                    errs[e] += 1
                if r[2] is None:
                    errs[r[3][0]] += 1
            if verbose:
                bad = [r for r in rows if r[2] is None or r[4]]
                print("%s %-26s pairs=%-3d sim/script errors=%d %s" % (
                    leg, kind, len(rows), len(bad), (bad[0][:2], bad[0][3][:1], bad[0][4][:2]) if bad else ""))
    if verbose:
        print("\nscript errors, by how many scenarios hit them:")
        for e, n in errs.most_common():
            print("%5d  %s" % (n, e))
    return out


# ====================================================================== command line
def find_vanilla(arg):
    for v in [arg] + DEFAULT_VANILLA:
        if v and os.path.isdir(os.path.join(v, "common", "script_values")):
            return v
    raise SystemExit("CK3 game directory not found: pass --vanilla or set CK3_GAME")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vanilla", default="")
    ap.add_argument("what", nargs="?", default="spot")
    ap.add_argument("--only", nargs="*", help="kinds to sweep")
    args = ap.parse_args()
    lib = Library(find_vanilla(args.vanilla))
    if args.what == "kinds":
        sweep_kinds(lib, only=args.only)
    if args.what == "spot":
        w, W = standard_world()
        p = Panel(lib, w, W["king"], W["duke"])
        p.deed("t", None)
        p.gold("t", 30)
        p.deed("i", None)
        p.gold("i", 90)
        print(json.dumps(p.acceptance(), indent=1))
        print("failures:", p.failures(), "refusals:", p.refusals())
        print("errors:", p.errors)


if __name__ == "__main__":
    main()
