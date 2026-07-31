# Graph Report - .  (2026-07-29)

## Corpus Check
- Corpus is ~20,992 words - fits in a single context window. You may not need a graph.

## Summary
- 846 nodes · 2022 edges · 65 communities (52 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 101 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Static Assets Index
- Static Assets Index
- App Rationale Extract
- Models Ocr Rationale
- Static Assets Index
- Blockchain Block Rationale
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- App Backup Certificate
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Architecture Blockchain Certificate
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Readme Certificate Authentication
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Upload Routes Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Ocr Utils Extract
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Static Assets Index
- Graphify Agents Rules
- Graphify Agents Workflows
- Static Assets Index
- Static Assets Index

## God Nodes (most connected - your core abstractions)
1. `hk` - 69 edges
2. `s()` - 49 edges
3. `i()` - 48 edges
4. `Ac()` - 34 edges
5. `of` - 31 edges
6. `De()` - 26 edges
7. `mE` - 22 edges
8. `qe()` - 20 edges
9. `Mt` - 19 edges
10. `_E` - 19 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `Blockchain`  [EXTRACTED]
  test_ocr.py → blockchain.py
- `_extract_date()` --calls--> `get_date_patterns()`  [EXTRACTED]
  models/ocr.py → config/extraction_patterns.py
- `_extract_cert_id()` --calls--> `get_id_patterns()`  [EXTRACTED]
  models/ocr.py → config/extraction_patterns.py
- `_extract_name()` --calls--> `get_name_patterns()`  [EXTRACTED]
  models/ocr.py → config/extraction_patterns.py
- `_extract_course()` --calls--> `get_course_patterns()`  [EXTRACTED]
  models/ocr.py → config/extraction_patterns.py

## Import Cycles
- None detected.

## Communities (65 total, 13 thin omitted)

### Community 0 - "Static Assets Index"
Cohesion: 0.03
Nodes (63): Aa, Ay, b1, ba, bE, bT, Bu, cx (+55 more)

### Community 1 - "Static Assets Index"
Cohesion: 0.08
Nodes (24): af(), aT, av, cE(), fT, get(), hf(), hg() (+16 more)

### Community 2 - "App Rationale Extract"
Cohesion: 0.08
Nodes (51): add_certificate(), allowed_file(), api_issue(), api_verify(), _clean(), _deskew(), _details_to_api(), _detect_name_from_layout() (+43 more)

### Community 3 - "Models Ocr Rationale"
Cohesion: 0.07
Nodes (41): get_course_patterns(), get_date_patterns(), get_id_patterns(), get_name_patterns(), Any, Pattern-based extraction config for certificate fields. No certificate-specific…, Configuration for certificate extraction and app behavior., add_certificate() (+33 more)

### Community 4 - "Static Assets Index"
Cohesion: 0.06
Nodes (33): bp, cf(), Ec, ek(), Em(), Et(), ex(), Fg() (+25 more)

### Community 5 - "Blockchain Block Rationale"
Cohesion: 0.13
Nodes (14): Block, Blockchain, BlockchainCorruptionError, Any, Blockchain module for certificate authenticity. Persists the chain to…, In-memory blockchain with persistence to blockchain.json. Loads chain on init;…, Load chain from legacy issue_certificate.json. Runs only when blockchain.json…, Write chain to JSON file (used during migration before self.chain is set). (+6 more)

### Community 6 - "Static Assets Index"
Cohesion: 0.12
Nodes (8): Dt(), h1(), Kc(), p1(), Xc, xE(), _y(), Yc()

### Community 7 - "Static Assets Index"
Cohesion: 0.15
Nodes (3): mE, My(), pE()

### Community 8 - "Static Assets Index"
Cohesion: 0.18
Nodes (20): Ai(), constructor(), gS(), i(), IE(), iw(), lg(), lT() (+12 more)

### Community 9 - "Static Assets Index"
Cohesion: 0.16
Nodes (19): Ca(), Da, _E, Hc, hE(), Ip(), jT, mv() (+11 more)

### Community 10 - "Static Assets Index"
Cohesion: 0.12
Nodes (17): dS(), ef(), Fc(), fm(), Gy(), hS(), Ii(), La (+9 more)

### Community 11 - "Static Assets Index"
Cohesion: 0.14
Nodes (3): og, tn(), WS

### Community 12 - "Static Assets Index"
Cohesion: 0.14
Nodes (10): bg(), dc(), _g(), Gc, gf(), Hi, xg(), yg() (+2 more)

### Community 13 - "Static Assets Index"
Cohesion: 0.16
Nodes (16): c1(), d1(), f1(), g1(), k1(), l1(), m1(), n1() (+8 more)

### Community 14 - "Static Assets Index"
Cohesion: 0.16
Nodes (4): Dp(), Jr, jy, sf

### Community 17 - "Static Assets Index"
Cohesion: 0.19
Nodes (14): _c(), fy(), Gm(), gw(), lp(), Mn(), Nc(), op() (+6 more)

### Community 18 - "Static Assets Index"
Cohesion: 0.18
Nodes (4): eg(), nf(), nn(), rf

### Community 19 - "App Backup Certificate"
Cohesion: 0.33
Nodes (12): add_certificate(), allowed_file(), extract_details(), generate_hash(), home(), issue(), load_hashes(), perform_ocr() (+4 more)

### Community 20 - "Static Assets Index"
Cohesion: 0.18
Nodes (13): aw(), fw(), Go(), hp(), jw(), nw(), st(), sw() (+5 more)

### Community 21 - "Static Assets Index"
Cohesion: 0.17
Nodes (12): _a(), a1(), ey(), jx(), nx(), pp(), qw(), render() (+4 more)

### Community 22 - "Static Assets Index"
Cohesion: 0.21
Nodes (12): bi(), cy(), ew(), fS(), ic(), mS(), os(), ts() (+4 more)

### Community 23 - "Static Assets Index"
Cohesion: 0.18
Nodes (6): Ct(), ig(), ja(), Qp(), QS, vf()

### Community 24 - "Architecture Blockchain Certificate"
Cohesion: 0.18
Nodes (10): 1. Persistent blockchain (`blockchain.json`), 2. Pattern-based extraction (no hardcoded certificate text), 3. Canonical hashing and verification, 4. Chain validation, 5. Modular layout, Certificate Authentication System — Architecture, File layout, Major Structural Choices (+2 more)

### Community 25 - "Static Assets Index"
Cohesion: 0.22
Nodes (3): bS, Qy(), zS()

### Community 26 - "Static Assets Index"
Cohesion: 0.25
Nodes (10): gE(), Ht(), Qr(), Un(), uw(), vE(), vp(), wr() (+2 more)

### Community 28 - "Static Assets Index"
Cohesion: 0.29
Nodes (6): is(), j1(), lw(), mw(), rs(), yy()

### Community 29 - "Static Assets Index"
Cohesion: 0.20
Nodes (5): ag(), eE, Py(), rg(), tE()

### Community 30 - "Static Assets Index"
Cohesion: 0.22
Nodes (10): bo(), bx(), Qm(), sp(), um(), va(), Vc(), Xm() (+2 more)

### Community 31 - "Static Assets Index"
Cohesion: 0.28
Nodes (3): cc(), Oi(), rm()

### Community 32 - "Static Assets Index"
Cohesion: 0.31
Nodes (4): ck, ev(), kk(), Ua()

### Community 33 - "Static Assets Index"
Cohesion: 0.31
Nodes (9): Dn(), kS(), lc(), Oa(), pS(), rT(), tf(), Xo() (+1 more)

### Community 34 - "Static Assets Index"
Cohesion: 0.28
Nodes (9): e1(), Ha(), hx(), i1(), Kw(), mx(), Ou(), s1() (+1 more)

### Community 36 - "Static Assets Index"
Cohesion: 0.32
Nodes (7): ak(), dg(), _k(), Ka(), kg(), tk(), Ya()

### Community 37 - "Static Assets Index"
Cohesion: 0.25
Nodes (8): ap(), cS(), Fa(), jp(), lS(), Uu(), Zr, zu()

### Community 38 - "Static Assets Index"
Cohesion: 0.32
Nodes (8): Bc(), bw(), De(), en(), fE(), mm(), ow(), zc()

### Community 39 - "Readme Certificate Authentication"
Cohesion: 0.29
Nodes (6): Certificate Authentication System, Features, Possible extensions, Project structure, Run, Setup

### Community 40 - "Static Assets Index"
Cohesion: 0.57
Nodes (3): rc(), yE(), zi()

### Community 41 - "Static Assets Index"
Cohesion: 0.29
Nodes (6): bk(), by(), $n, ov(), Sa, _T

### Community 42 - "Static Assets Index"
Cohesion: 0.40
Nodes (6): $1(), Dy(), mp(), O1(), Oy(), ss()

### Community 43 - "Static Assets Index"
Cohesion: 0.33
Nodes (6): ax(), ix(), ox(), rx(), sx(), uE

### Community 44 - "Static Assets Index"
Cohesion: 0.33
Nodes (6): cm(), Fi(), Ho(), Jc(), lm(), za()

### Community 46 - "Static Assets Index"
Cohesion: 0.40
Nodes (5): cp(), rp(), sy(), wx(), Yo()

### Community 47 - "Upload Routes Index"
Cohesion: 0.67
Nodes (3): index(), route, upload_certificate()

### Community 48 - "Static Assets Index"
Cohesion: 0.50
Nodes (4): gT(), vT(), wT(), xT()

### Community 49 - "Static Assets Index"
Cohesion: 0.50
Nodes (4): Ku(), _p(), pg(), tC()

### Community 52 - "Static Assets Index"
Cohesion: 0.67
Nodes (3): aE(), gg(), NE

### Community 53 - "Static Assets Index"
Cohesion: 0.67
Nodes (3): bm(), nT(), zm()

### Community 54 - "Static Assets Index"
Cohesion: 0.67
Nodes (3): cg, jE, pf()

### Community 55 - "Static Assets Index"
Cohesion: 0.67
Nodes (3): jk(), lv(), Qu()

## Knowledge Gaps
- **58 isolated node(s):** `Wa`, `Ay`, `b1`, `Iy`, `{schedule:We,cancel:kr,state:gt,steps:bu}` (+53 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ac()` connect `Static Assets Index` to `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `mE` connect `Static Assets Index` to `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `of` connect `Static Assets Index` to `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`, `Static Assets Index`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `s()` (e.g. with `bm()` and `ey()`) actually correct?**
  _`s()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `i()` (e.g. with `.snapToCursor()` and `c1()`) actually correct?**
  _`i()` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Wa`, `Ay`, `b1` to the rest of the system?**
  _58 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Static Assets Index` be split into smaller, more focused modules?**
  _Cohesion score 0.026965002868617326 - nodes in this community are weakly interconnected._