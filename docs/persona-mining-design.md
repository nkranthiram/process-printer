# Persona Mining — design for implementation

**Status**: approved design, ready to build against real data.
**Audience**: whoever implements this (this document is written to be handed
to a fresh Claude/agent session with no other context and be sufficient on
its own).
**Produced by**: a structured debate between two independent models
(Claude and GPT), converged over three rounds. Disagreements and how they
were resolved are called out explicitly below, not smoothed over — where a
design choice was contested, this document says so and states the resolved
rule.

---

## 1. Why this exists

This is the "Building the personas" stage of the broader testing-strategy
argument in `docs/testing-strategy-confluence.html`: an agentic claims
process cannot be proven safe by replaying historical claims (a historical
claim is a *transcript* of what one human did, not a *simulator* that
responds to a different decision) — so end-to-end process testing instead
requires **simulated claim episodes**, played out by **personas** that react
to what the agentic workflow actually does. Those personas have to come from
somewhere real, not be invented in a workshop — this document is the design
for the pipeline that **mines them from the actual historical claims
corpus**.

Read `docs/testing-strategy-confluence.html` first if you haven't — this
document assumes its vocabulary (personas' four layers: Grounding /
Behavioural / Context / Frame; the deliberately over-sampled hard cohorts:
vulnerable, adversarial, structurally-hard, operationally-hard, surge, and
combinatorial). This document is the concrete "how do we actually build the
persona bank" answer that doc gestures at but doesn't specify.

**Input**: thousands of historical claims. Each claim is a chronologically
ordered bundle of structured fields (product, severity, dates, channel,
tenure...) plus unstructured content (case notes, correspondence, emails,
medical/trade reports, letters). Each claim involves **multiple actors** —
not just the claimant: nominated representatives, treating doctors,
builders/repairers, third parties, witnesses, assessors, and others.

**Output**: a versioned, validated **persona bank** — a nested
JSON/YAML artifact usable to build the simulated testing environment
described in the testing-strategy document.

**This document does not cover**: the simulation harness itself (turning
personas into running claim episodes against the agentic workflow), or the
SME Agent's separate current-state process mining. Those are downstream
consumers of this pipeline's output, not part of it.

---

## 2. The core design decisions (converged)

### 2.1 Granularity — clustering with a stopping rule, not a headcount

Don't classify actors directly into a fixed taxonomy as extraction proceeds
— that only ever finds personas already guessed to exist, which defeats the
point of mining. Don't leave it fully open either — one persona per
actor-instance is a database, not an archetype.

**Do this:**

1. Extract a **behavioural feature vector per actor-instance** (one
   claimant-instance per claim, one doctor-instance per claim they appear
   in, etc.) — not a label, a vector: documentation promptness (latency
   distribution), channel preference (categorical + entropy), escalation
   propensity (rate + trigger conditions), trust/cooperation signals,
   literacy register (readability/formality), responsiveness volatility,
   and similar signals derived from the actor's actual recorded behaviour.
2. Cluster **within actor role only** — claimants against claimants, doctors
   against doctors, never mixed; the feature space isn't comparable across
   roles.
3. The cluster count is not chosen by hand. It's decided in three ordered
   steps:
   - **Statistical range-finding**: HDBSCAN (not k-means — "doesn't fit any
     persona" must be a valid outcome, i.e. genuine noise points, not forced
     membership). Use a stability metric (silhouette / DBCV) to find a
     stable range (e.g. "9–14 stable clusters for claimant"), not a single
     number.
   - **LLM-assisted merge/split review**: within that range, an agent
     reviews cluster exemplars and asks whether two clusters are genuinely
     distinct or the same behavioural story told slightly differently
     (catches over-splitting from a noisy feature — e.g. splitting on
     channel preference alone when the real archetype is about trust, and
     channel is just downstream of trust).
   - **Utility cap**: a persona only earns a place in the bank if it changes
     what the simulated environment needs to do differently from an
     existing persona. If two personas would produce indistinguishable
     expected workflow behaviour, merge them.
4. **Stability gate before freezing** (this was a real, explicitly resolved
   disagreement in the debate — see §2.5): a candidate cluster is only
   promoted to a frozen persona once it **reappears** under bootstrap
   resampling and across disjoint time slices of the corpus (e.g. an
   Adjusted Rand Index or similar re-appearance check above an agreed
   threshold). A cluster that's a one-off artifact of a single quarter's
   claim mix (a surge event, a product launch) does not earn persona status
   just because it was statistically separable once.

This naturally produces **asymmetric counts across roles** (e.g. 8–12
claimant personas, 3–4 doctor personas) — don't force parity; roles differ
in their real behavioural degrees of freedom.

The taxonomy is **versioned and re-clustered on a defined cadence** as new
claims land — treat it like a schema migration. Old persona IDs are
deprecated, never deleted, so provenance in simulations run under an earlier
persona-bank version stays interpretable.

### 2.2 The role taxonomy is *also* mined — but through a stricter gate than personas

A role (claimant, doctor, nominated representative, builder/repairer, third
party, witness, assessor...) is not the same kind of thing as a persona
within a role, and shouldn't be governed identically:

- A new **persona** changes one leaf of the schema.
- A new **role** changes the schema's branching structure — every downstream
  consumer (the simulation harness, scenario generation, coverage
  dashboards) has to know about it.

**Mechanism**: start with a small, explicitly provisional core role set
(claimant, nominated representative/proxy, treating provider, assessor,
repairer/vendor, third party/witness — extend only as the real corpus
demands). Extraction never force-fits an actor into the nearest existing
role: if confidence against every existing role's classifier is below
threshold, the actor is logged as `role: unclassified` with its full
extracted feature vector — never discarded, never guessed. Unclassified
actors accumulate across the corpus and get clustered on the same re-mining
cadence as everything else, using the same four-part gate as personas
(coverage / stability / separability / utility) — but with utility
redefined at role-scope: a candidate role must show it occupies a **genuinely
distinct position in the actor graph** (distinct relationship to the
claimant, distinct interaction pattern with the workflow, distinct
decision-relevance) — not merely a distinct behavioural profile, which
would just make it a persona within an existing role. A role candidate that
clears this bar requires **mandatory SME sign-off** before it enters the
schema (role changes are rarer and more structurally consequential than
persona additions, so the governance bar is asymmetric). On promotion, the
new role starts its own persona-mining sub-pipeline from zero personas.

### 2.3 State / persona / relationship — three distinct things

This resolves the specific case that motivated the whole exercise: a
claimant hospitalized after a motor vehicle accident, temporarily unable to
communicate directly.

Three structurally distinct concepts, never collapsed into one:

- **Persona** — a stable behavioural bundle (Grounding + Behavioural +
  Context template + Frame template), scoped to one role, discovered and
  gated as in §2.1.
- **State module** — a time-bounded, **reversible** circumstance
  (incapacitation, financial-hardship-onset, language-barrier-onset,
  bereavement-adjacent, digital-access-loss, and similar), defined **once**
  in a top-level registry, attachable to *any* persona of *any* role by
  reference. Each state module carries: an activation trigger, a duration
  distribution mined from real data, and a **measured** (not assumed)
  behavioural delta while active (e.g. escalation propensity often *drops*,
  not rises, during incapacitation — measure it, don't assume it).
- **Relationship / actor-activation** — a state module can additionally
  declare `activates_actor: {role, persona_pool_ref}`, spawning a second
  actor (a nominated representative, an interpreter, a case manager) for its
  active window. This is how "claimant is hospitalized" simultaneously
  modifies the claimant's Frame *and* brings a new actor into the episode.

**The general rule**: a situational variation is a **state** if the actor's
underlying trait vector is unaffected once it lifts. It becomes a
**distinct actor activation** if it changes *who* is capable of performing
the actor's functional role during that window. It is promoted to a genuine
**new persona/trait** only under the narrow conditions in §2.5 below —
never by default.

This produces a library of **reusable state modules**, attachable to any
persona, which is what makes the design doc's combinatorial hard-cohorts
(vulnerable *and* structurally-hard, hardship *and* surge) **generative**
(base persona + state module + degraded process conditions) rather than
hand-authored per combination.

### 2.4 Extraction pipeline at scale (cost scales with claims × ambiguity, then clusters — never claims × documents)

Seven stages, deterministic-and-cheap first, LLM reserved for genuine
judgment, escalating only where needed:

1. **Canonicalize** the claim bundle: normalize chronology, segment
   documents into interaction units. No LLM.
2. **Deterministic actor graph pass**: structured-field actors resolved for
   free (a claim system field already names the claimant); rule-based
   NER/coreference over documents for the unambiguous cases (an email
   signature naming a doctor). No LLM.
3. **Ambiguity-gated LLM adjudication only** — escalate to an LLM
   specifically when a concrete trigger fires:
   - a coreference candidate spans documents with no exact string/ID match,
   - an extracted actor mention has no corresponding structured-field
     record, or
   - a lightweight classifier's role-assignment confidence falls below
     threshold.
   Unresolvable/low-confidence actors are logged as `role: unclassified`
   rather than force-fit (feeding the role-taxonomy-mining loop in §2.2).
   Use a small/fast model — this is pattern extraction, not judgment. Cost
   scales with **ambiguity volume**, not claim volume.
4. **Structured actor-episode summaries** per actor-instance: what they
   knew, what they wanted, how they communicated, response latency,
   escalation behaviour, whether they needed prompting, whether they
   deferred/resisted/complied, constraints present. Deterministic
   (arithmetic) wherever computable directly from the event log (latencies,
   channel-switch counts, document-completeness ratios). For genuinely
   qualitative signals (trust, tone, literacy register), a **cheap LLM
   scoring call against a rubric, on the extracted summary** (a few hundred
   tokens) — never on raw documents.
5. **Embed + cluster within role**: explicit features plus semantic
   embeddings for free-text signals. Clustering **proposes candidates; it
   does not finalize them.**
6. **LLM-assisted archetype naming/validation**: **one call per cluster**,
   not per instance — sample N exemplars per stable cluster (nearest to
   centroid), have the model write the archetype's name and Behavioural
   summary, and flag within-cluster incoherence for SME review. Cost scales
   with **cluster count**, not claim count — the same handful of LLM calls
   whether the corpus is 5,000 or 50,000 claims.
7. **Freeze as a versioned checkpoint** (not permanent): serialize
   provenance, evidence, **and counterexamples** (instances that almost fit
   a cluster and were excluded, with rationale — this is what lets the bank
   be checked for overreach later, not just supporting evidence). Stamp a
   `validation_status`. Version the whole bank. Re-run on a defined cadence
   as new claims land.

**Cost shape**: O(claims) cheap deterministic pass + O(ambiguous spans) LLM
adjudication + O(actors) cheap rubric scoring + O(1) clustering + O(clusters)
expensive naming. Total LLM spend scales with **ambiguity and cluster
count**, not raw document or claim volume — this is the property that makes
it viable at thousands-of-claims scale.

### 2.5 State → persona promotion — resolved disagreement

This was a genuine, explicitly contested point in the debate, worth stating
precisely because getting it wrong reopens exactly the persona-explosion
problem the state/persona split exists to prevent.

**The resolved rule**: "never" applies to *causal labels*, not to the
*behaviour* a circumstance produces.

- **Never**: a circumstantial/causal label (hospitalized, bereaved,
  relocated, imprisoned, deployed overseas...) becomes a persona identity.
  This is not just discipline for its own sake — circumstances are causally
  interchangeable. Hospitalization, advancing cognitive decline, a language
  barrier, and a period of incarceration can all independently produce the
  *exact same* downstream behaviour (sustained reliance on a delegate to
  communicate). Encoding the cause as the persona would force minting a
  separate persona per cause even when the resulting behaviour is
  identical — precisely the explosion this principle exists to prevent.
- **Can be promoted, through the ordinary gate, no special case**: the
  *behavioural pattern* a circumstance produces, described in pure
  behavioural terms, stripped of its trigger. E.g. "chronically low-autonomy,
  representative-reliant claimant" is a valid persona candidate purely on
  Behavioural grounds — the fact that it happens to be triggered by several
  different state modules (incapacitation, cognitive-decline-onset,
  language-barrier-onset) doesn't disqualify it; it's evidence for it.

**Three hard constraints gate every promotion** (all required, not a soft
judgment call):

1. **Cross-cause consolidation or measured persistence**: a promotion
   candidate must either (a) be triggered by ≥2 distinct state modules in
   the data and cluster to the *same* behavioural profile regardless of
   cause, or (b) show the pattern persisting in a large, stable fraction of
   instances **after** the triggering state has resolved (measured
   directly — the trait vector doesn't revert to baseline post-window). A
   single-cause, still-reverting pattern is disqualified outright, no
   exception — it stays a state effect.
2. **Same statistical bar as any other persona candidate** (§2.1's
   coverage/stability/separability/utility gate). Being "clearly caused by
   something real" is not itself evidence of stability.
3. **The causal state module is retained regardless of promotion outcome**,
   as trigger vocabulary — promotion adds a persona/trait, it never deletes
   or folds the state module away. This keeps the
   many-causes-one-behaviour structure explicit and machine-checkable
   rather than silently collapsing back into cause-labeled personas.

### 2.6 Output schema

Role-first, with **separate top-level registries** for states and
relationships (defined once, referenced by id from any persona — never
duplicated inline per persona).

```yaml
persona_bank:
  meta:
    version: "..."
    source_window: "..."          # date range of claims mined
    modeling_policy: "..."        # e.g. clustering params, gate thresholds used
    generated_at: "..."

  roles:
    claimant:
      archetypes:
        - persona_id: claimant.anxious_over_communicator.v3
          display_name: "Anxious Over-Communicator"
          grounding:
            role: claimant
            applicable_products: [motor, home]
            cluster_stats: {n_instances: 0, stability_score: 0.0}
          behavioural:
            tendencies:
              documentation_promptness: "..."
              channel_preference: "..."
              escalation_propensity: "..."
              trust_level: "..."
              literacy_register: "..."
              responsiveness: "..."
            response_patterns:
              prompt_following: "..."
              clarification_behaviour: "..."
              complaint_style: "..."
          context:
            known_information: ["..."]
            pressure_conditions: ["..."]
            common_constraints: ["..."]
          frame:
            fixed:
              claim_stage: ["..."]
              obligations: ["..."]
            variable:
              injury_severity: ["..."]
              product_line: ["..."]
              channel: ["..."]
          modifiers:
            supported_states:
              - state_id: claimant.hospitalized.incapacitated
              - state_id: claimant.represented.by_proxy
          sampling:
            real_incidence_rate: 0.0     # observed frequency in the corpus
            oversample_factor: 1.0       # explicit if this persona is deliberately oversampled for hard-cohort testing
          provenance:
            evidence_claim_ids: ["..."]
            evidence_doc_ids: ["..."]
            evidence_spans:
              - doc_id: "..."
                span: "..."
                rationale: "..."
            counterexamples: ["..."]     # near-misses excluded from this cluster, with rationale
            stability_notes: "..."
            validation_status: "approved"   # or provisional | rejected
            confidence_note: "..."

    doctor:
      archetypes: []
    nominated_representative:
      archetypes: []
    # ... other roles

  states:
    claimant.hospitalized.incapacitated:
      applies_to_roles: ["claimant"]
      type: temporary_state
      duration_distribution: "..."     # mined from data, not assumed
      effects:
        communication_access: "reduced"
        response_latency: "increased"
        escalation_propensity_delta: "..."  # measured, not assumed direction
        proxy_activation: "allowed"
    claimant.represented.by_proxy:
      applies_to_roles: ["claimant"]
      type: relationship_activation
      effects:
        actor_role_swapped_to: "nominated_representative"

  relationships:
    nominated_representative:
      description: "Authorized proxy acting on behalf of claimant"
      activation_conditions: ["incapacity", "delegated authority", "medical restriction"]

  role_taxonomy:
    core_roles: ["claimant", "nominated_representative", "treating_provider",
                 "assessor", "repairer_vendor", "third_party_witness"]
    candidate_roles:
      - role_id: "..."
        status: "unclassified"        # unclassified | candidate | sme_review | promoted | rejected
        supporting_actor_instances: 0

  validation:
    holdout_design: "time-and-claim-family-stratified, not random"
    distribution_checks: []           # marginal checks, per attribute
    joint_combination_checks: []      # PRIMARY check — see §2.7
    stability_checks: []              # resample/time-slice reappearance
    drift_checks: []
```

Key points, stated explicitly so an implementer doesn't have to infer them:

- Persona lives under a role; never mixed across roles.
- A state or relationship is defined once in its own registry and
  *referenced* from any persona via id — never copy-pasted per persona.
- Every persona carries provenance **and counterexamples**, not just
  supporting evidence.
- `sampling.oversample_factor` / `real_incidence_rate` are first-class
  fields specifically so deliberate oversampling of hard cohorts (per the
  testing-strategy doc) is declared honestly in the schema, not hidden.
- `validation_status` lives on the persona itself (queryable at use-time by
  the simulation harness — e.g. "exclude non-`approved` personas from a
  compliance-sensitive test run"), not only in a separate top-level block.

### 2.7 Validation — a hard gate, not a final report

Fit into the pipeline as an actual gate, not a narrative:

1. Discover candidate personas (and candidate roles) on **training claims
   only**.
2. Hold out claims **stratified by time and by claim family** — not a
   random split, which would leak correlated claims (the same
   policyholder, the same incident type) across train/holdout.
3. Apply the frozen candidate bank to the holdout set.
4. Check whether it reproduces real distributions **and transitions** on
   the holdout data — specifically on **joint combinations**, not just
   marginals. This is the primary check: a persona bank can pass every
   single-dimension check (product mix looks right, severity mix looks
   right) and still fail on the exact combinatorial cells the whole testing
   strategy depends on (vulnerable + structurally-hard + low-literacy +
   proxy-communication). Use a distributional-distance measure per joint
   cell against an agreed threshold (e.g. population stability index or KL
   divergence, flagging any cell exceeding a pre-agreed cutoff), computed
   separately for marginals and for the specific hard-cohort combinatorial
   cells, logged per persona-bank version.
5. Check **stability** separately from fidelity: does the same archetype
   reappear if the training set is resampled? Does it stay coherent across
   time slices? Do SMEs agree it's meaningfully distinct?
6. Merge, split, retire, or hold at `provisional` status anything that
   fails. Nothing — persona or role — is promoted to `approved` without
   clearing every check.

---

## 3. Implementation shape

This section answers "do we just write a skill, or build a real
pipeline?" — also debated and resolved.

**The resolved answer: real backend pipeline code, with a skill file that
orchestrates/interprets it — not a skill alone, and not a fully standalone
service outside wherever this gets built.**

### 3.1 What's agent-work vs. what requires real code

| Stage | Agent-doable | Requires real code |
|---|---|---|
| Role-scoping a claim / actor ("this text is spoken from the adjuster's role, not the claimant's") | ✅ single-item semantic judgment | |
| State/persona/relationship tagging on an ambiguous instance | ✅ classification against a fixed taxonomy | |
| Embedding generation | | ❌ a deterministic model call, not something reasoned about |
| HDBSCAN clustering over thousands of instance-vectors | | ❌ a global optimization over a full distance matrix — no amount of prose instructs an LLM to hold and cluster thousands of vectors correctly; this needs a real `sklearn`/`hdbscan` call |
| Selecting cluster exemplars for review | | ❌ needs code to do nearest-to-centroid sampling cheaply; an agent can't scan thousands of raw rows to find them |
| Persona/role naming & summarization from a small (10–30 item) exemplar sample | ✅ generative synthesis over a small, contextually-holdable sample | |
| Merge/split review of borderline clusters | ✅ agent reviews exemplars and proposes a call | needs code to surface the exemplars |
| Persona-bank versioning, dedup, diffing against the prior version | | ❌ deterministic diff/versioning logic |
| Train/holdout validation gate (stability metrics, distributional-distance thresholds) | | ❌ a statistical procedure — an LLM "eyeballing" a split is a vibe check, not a validation gate |
| Re-mining cadence / scheduling | | ❌ infrastructure, not judgment |

**The general rule**: wherever a written procedure would have to say "for
each of the N items, do X" with N in the thousands, that belongs in code,
not prose — it's not a documentation-quality problem, it's a category
error (token generation cannot substitute for a statistical/ML operation
over a data structure it cannot hold in context).

### 3.2 Concrete module split

**Real code** (a pipeline module, or a small set of them — file layout is
an implementation preference, not an architectural decision):
- Ingestion/canonicalization of the claims corpus.
- Deterministic actor-graph extraction (structured fields + rule-based
  NER/coreference).
- Ambiguity-gated LLM adjudication (small/fast model, structured output,
  triggered only per §2.4 step 3's concrete conditions).
- Actor-episode summary construction (deterministic arithmetic + cheap
  rubric-scoring LLM calls on summaries, never raw documents).
- Embedding generation.
- Per-role HDBSCAN clustering, with a stability-metric-based range finder.
- Exemplar selection (nearest-to-centroid sampling) for the naming/review
  stage.
- Persona-bank persistence, versioning, and diffing against prior versions.
- The train/holdout validation gate: distributional-distance computation
  (joint-cell and marginal), stability-under-resampling checks, threshold
  comparison, pass/fail/provisional status assignment.
- A scheduled/batch entrypoint that runs the pipeline end to end.

**Skill file** (agent's job — orchestrate and interpret, never
re-implement):
- Tells the agent to *invoke* the pipeline rather than attempt clustering,
  embedding, or validation math itself.
- Tells the agent how to interpret the pipeline's output: for each
  candidate cluster, review the exemplars the code selected and decide the
  persona/role name, the Behavioural/Context/Frame summary, and whether it
  looks ambiguous against an existing bank entry (merge/split flag).
- Tells the agent to read the validation gate's output and narrate what a
  failed check means for the business, not to recompute the gate itself.
- States the anti-pattern explicitly: never cluster or embed by reasoning
  about text similarity in prose — call the real function. The agent's job
  starts at exemplar review, not before.

### 3.3 Data model note

Whatever gets built should **not** reuse an existing "extracted claim from a
policy document" model if one exists in the target codebase (e.g. an
`AtomicClaim`-style model meant for policy-clause extraction) — that's a
different kind of thing (a clause from a *policy document*) from an actor's
behavioural episode within a *customer's historical claim*. This pipeline
needs its own models for the historical-claim corpus and its actors (e.g.
something like a claim-episode record and an actor-instance record per
claim), separate from any policy-document extraction pipeline that may
already exist in the target codebase. Confirm the actual target codebase's
existing models before reusing anything — don't assume.

### 3.4 Where this fits, structurally

This is a **parallel pipeline**, not a downstream stage bolted onto any
existing single-document extraction chain — it consumes a fundamentally
different corpus (thousands of historical claims, each with multiple
actors) and produces a different, standing artifact (a versioned persona
bank) that a *separate* simulation harness will later consume. Build it as
its own subsystem: its own data model, its own pipeline module(s), its own
skill file, its own scheduled entrypoint — sharing only general
infrastructure (database, API pattern, versioning approach) with whatever
else exists in the target codebase, not sharing pipeline stages with it.

---

## 4. What to build, in order

1. Data model: claim-episode record, actor-instance record, persona-bank
   record (versioned), state-registry record, relationship-registry
   record.
2. Deterministic ingestion + actor-graph extraction (canonicalization,
   structured-field resolution, rule-based NER/coreference).
3. Ambiguity-gated LLM adjudication step, with the three concrete escalation
   triggers from §2.4.
4. Actor-episode summary construction (deterministic + cheap rubric
   scoring).
5. Embedding + per-role HDBSCAN clustering, with the stability-range-finding
   mechanism from §2.1.
6. Exemplar selection + LLM-assisted archetype naming/merge-split review.
7. Role-taxonomy mining loop (§2.2) for `unclassified` actors, with the
   stricter role-promotion gate.
8. State-module registry + the promotion path from §2.5, with its three
   hard constraints enforced as code, not convention.
9. Persona-bank versioning/diffing/freeze logic, matching the schema in
   §2.6.
10. Train/holdout validation gate (§2.7) — build this **before** trusting
    any output of steps 5–9 for real use.
11. Tests, at minimum: a synthetic fixture with known ground-truth clusters
    to prove the clustering pipeline actually recovers them; a fixture
    proving the ambiguity-gating trigger logic fires/doesn't fire correctly;
    a fixture proving the validation gate correctly fails a bank that
    shouldn't pass (red-before-green, not just a green run on real data).
12. Run against the real historical claims corpus, review output, iterate.

---

## Appendix — open items not resolved by the debate, flagged honestly

- **Exact statistical test/threshold for the validation gate's
  distributional-distance check** (population stability index vs. KL
  divergence vs. another measure, and what threshold counts as a fail) was
  raised in the debate but not pinned to a specific number — both models
  proposed PSI > 0.25 as a reasonable starting cutoff, but this should be
  set with input from whoever owns risk/statistical sign-off on the actual
  programme, not assumed.
- **Concrete embedding model choice** was not specified — pick one
  available in the target environment; the design doesn't depend on which.
- **Re-mining cadence** (weekly/monthly/quarterly) was not specified —
  depends on real claim volume and how fast the book changes; start
  conservative and tune once the first few runs show how much the bank
  actually moves between re-mining passes.
- **How this pipeline's persona bank plugs into the simulation harness
  itself** (turning a persona + a scenario into a full simulated claim
  episode played against the agentic workflow) is explicitly out of scope
  for this document — it's the next design step, not this one.
