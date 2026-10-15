# Selector NBT list matching

Upstream `5b53f064af8708ba33fcaa533b81ca29a53a3310` treats an empty
expected NBT list as matching any actual list, and permits expected lists longer
than the actual list when values repeat. A tagged marker therefore incorrectly
matches `nbt={Tags:[]}` and an oversized repeated-tag pattern. Inverting the
empty pattern also incorrectly excludes the marker.

The selector matcher now requires an empty actual list for an empty pattern and
rejects a pattern longer than the actual list. Other nonempty patterns keep
unordered subset matching. Repeated expected entries can still reuse a matching
actual value when the length guard passes, matching vanilla behavior.

The verified official vanilla 26.3 server JAR was inspected locally with
Vineflower 1.12.0. `NbtUtils.compareNbt` applies both guards before unordered
matching; `EntitySelectorOptions` uses partial-list matching for `nbt` selectors.
Decompiled source remains private and is not included here. The only production
caller changed is the selector NBT predicate, through its existing recursive
matcher and compound wrapper; no other command or shared NBT codec is changed.

Open-PR review found #4069 (selector permissions) and #4003 (SNBT nesting bounds),
with no identical open selector NBT-list patch. No external patch was integrated.

Validation:

- Both new regression tests fail with original list matching. The original red
  log is `artifacts/jaron-entities-red2.log` (exit 101); an earlier test compile
  type error is separately retained in `jaron-entities-red.log`.
- `cargo test --locked -p pumpkin-core --lib`: all 435 tests pass after the fix.
- Live vanilla/current-source comparison under the shared engine lock, repeated
  twice, confirms empty-list and oversized-list failures plus inversion. Entity
  existence and nonempty-subset positive controls pass on both targets. Evidence:
  `artifacts/jaron-entity-console-20261015T213529.773992Z/report.json`.
- `cargo fmt --all -- --check`,
  `cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
  `cargo build --locked -p pumpkin` pass under the shared cargo lock and required
  resource limits. The first verification job was interrupted; its log remains
  separate from the successful detached retry. Clippy/build report only the
  existing `proc-macro-error2` dependency future-compatibility warning.
- Final live vanilla/upstream/patched comparison passes all eight checks on
  vanilla and patched code, twice each. Upstream fails empty-list, oversized-list
  and inverted-empty-list checks on both repetitions; all positive controls pass.
  Additional controls verify empty actual lists and repeated subset values when
  length permits. Both scratch servers stop cleanly with no ERROR or panic lines.
  Evidence: `artifacts/jaron-entity-console-20261015T214446.446756Z/report.json`.

Patched source commit: `31a781da7ec52a274bc8104a6875508f832e7055`.
Immutable binary SHA-256:
`93dd2de578ccaa3878f3e18d8af84713331b4999672e4e87a04e1bac18f3f0d3`.

Current upstream has no RCON. The bounded source comparison uses separate,
loopback-only scratch consoles and scoreboard sentinels, because upstream also
lacks terminal `execute if entity`. This does not validate a full RCON catalog.
Real-client gameplay, inventory, combat, visuals and effect expiration are
untested. The released RCON candidate is left running.
