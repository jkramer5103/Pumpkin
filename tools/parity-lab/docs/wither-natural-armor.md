# Wither natural armor absorption

Source commit: `0412e6b8f3ce558f79d35ec3f266fa44e47c802b`.

Withers previously took full physical damage despite their extracted armor base
of 4. Damage absorption summed equipment alone. It now reads effective armor
and toughness attributes, flooring armor as vanilla does. Mob equipment loaded
from NBT applies the existing equipment modifier helper, preserving its armor
contribution without counting it twice. Armor bypass, breach, damage ordering,
events and equipment durability retain their existing paths.

Vanilla 26.3 `WitherBoss.createAttributes` supplies armor 4;
`LivingEntity.getArmorValue` floors the armor attribute, and
`getDamageAfterArmorAbsorb` passes it and effective toughness to `CombatRules`.
The extracted Wither attributes already contained the right value, so no new
hardcoded entity data is needed. Other living entities share this correction.

## Validation

The final source passed these checks under the shared Cargo lock with one build
job, debug information and incremental compilation disabled, MemoryMax=5G,
MemorySwapMax=0 and CPUQuota=200%:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 443 passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Nine `wither-armor-*.json` regression fixtures ran twice each against the previous
campaign binary, vanilla 26.3 and the final patched binary. Each target used an
isolated scratch arena and a connected headless protocol 777 client. Frozen
NoAI fixtures isolate absorption from regeneration and attacks.

Vanilla and patched Pumpkin each passed 94/94 focused checks. Baseline passed
84/94, failing only the five armor health assertions in each repetition:

| Stimulus | Baseline health | Vanilla and patched health |
| --- | --- | --- |
| Real arrow, Wither starting at 151 HP | 149 | 149.24 |
| 4 physical damage, natural armor | 296 | 296.32 |
| 20 physical damage, natural armor | 280 | 280.64 |
| 4 physical damage, armor base 4.9 | 296 | 296.32 |
| 20 physical damage, armor 20/toughness 8 | 280 | 292 |

Zero armor, armor-bypassing magic, equipped sheep and NBT-loaded equipment
controls passed on all three targets. Both equipment controls start at the
sheep's actual 8 HP and advance one verified equipment-update tick before the
hit; the resulting health is 4.64. Final source, binary, fixture and gameplay
hashes matched. Scratch servers stopped cleanly without ERROR or panic lines.

Local evidence: `artifacts/jaron-wither22-final-verify.json`,
`artifacts/jaron-wither22-validation.json` and
`artifacts/jaron-wither22-source-provenance.json` in the deployment workspace.
The final binary SHA-256 is
`0574390c089149069e29c9518e08f7bdf1844566249d9f753f55bd1c1ec33a13`.

Fork master `65bca3f` was already an ancestor. Upstream master was `b57d821`.
Open PRs were checked again before publication; #3845 changes attribute
persistence/weapon modifiers, #3835 projectile damage context/knockback, and
#3988 skeleton/combat filtering. None changes this armor absorption calculation.

## Limits and excluded evidence

These are server-state observations from headless clients, with no rendered
client capture, complete boss fight or restart/persistence round trip. All
player equipment, enchantment, shielding and combat side-effect permutations
remain unproven. The existing proc-macro-error2 future-compatibility warning
remains.

An attempted resource-ID armor modifier command was rejected by Pumpkin with
`Invalid UUID`; vanilla accepted it. Its two rows remain in the raw ten-case
reports and are explicitly excluded from the supported 94-check comparison.
The unsupported fixture is not published, and this patch does not claim to fix
that command. Initial incorrect health expectations and the initial source
build without the loaded-equipment prerequisite are also excluded.
