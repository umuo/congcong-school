# Forest redesign QA — reopened after user review

Source visual truth: `deploy-output/child-ui-redesign/concepts/02-home-mission.png` (the user's selected second design). Options01/03 are retained unchanged. Supporting page board: `baseline/selected-key-pages.png`.

## Findings and corrective history

- [P1] The previous r12 background ended after one image height, so scrolling revealed plain paper. Earlier first-viewport-only acceptance did not verify this. Fixed with a pointer-transparent fixed scene covering the viewport; no background-attachment dependency. At scrollY3697 of a4972px document, the scene remains fixed and844px high. Evidence: `repair-scroll-3697-390.png`.
- [P1] Child pages exposed long tool lists and technical records; beginning a course required another Start confirmation. Fixed by a task-first home, collapsed curriculum/tools, one explicit course action that resumes an original session or starts one, one introductory concept plus optional expanded tips, and one “开始练习”. Cottage records/account tools now live under “家长小帮手”; supplies, wardrobe and weekly rewards are collapsed. No permissions, course locks or economy rules changed.
- [P1] A normal write appeared as a failed unsynced operation. Fixed by separate in-memory sending state and retryable pending state. Normal work shows “正在保存进度”; failures retain original bytes/key and a recovery action. Only existing interrupted time receipts may be resumed automatically; starts/answers/rewards require explicit actions.
- [P2] Some question controls looked enabled while their handlers ignored clicks during saving. Fixed native disabled state across numeric/text/matching/word-order/true-false; a regression assertion checks every rendered question button while locked.
- [P2] The old mascot/header/title hierarchy drifted from the selected illustrated design. Added matching transparent default/graduate guide illustrations, compact separate identity/XP/gem/sound controls, headline hierarchy and brighter accessible leaf green#517c2c. Other earned outfits retain the existing renderer, and a failed raster falls back to it.

Historic comparison: `comparison-r2.png` → `comparison-final.png` (r12, superseded after user rejection) → `comparison-repair.png`. The earlier pass was insufficient and is not evidence that the reported long-page issues were absent.

## Current comparison evidence

Full joint input: `deploy-output/child-ui-redesign/comparison-repair.png`, reference left and browser right, opened and inspected together. Browser capture: `repair-home-a1-390.png`, exactly390×844pixels at390×844CSS px/DPR1. Source853×1844 is normalized to390×844 only for QA; original retained. Final deployment is r17, same verified home styling/assets as the repair capture.

State is authorized synthetic A1, frog avatar, earned graduate hat,190XP/119gems, actual active math course “分一分，够不够”. These actual values and longer titles intentionally replace the mock name,120XP/71 and illustrative second course. Course labels and numbers are not baked into scene images.

Focused comparison: `comparison-repair-focus.png` zooms the header/hero and mission card from both inputs without changing their CSS scale. Full-scroll evidence is reviewed separately; it is not replaced by a tall top-only screenshot.

### Required fidelity surfaces

- Typography: measured PingFang SC with existing Chinese/system fallbacks, body/display weight900, headline26px with36px lead word. The generated reference has no supplied font file; matching hierarchy is implemented with available fonts. Real long names/titles wrap naturally rather than changing data to match the mock.
- Spacing/layout:14px phone outer gutters, bounded mission, illustrated hero, complete primary action(bottom~517px), three previews and four destinations. Header and default action density now track the reference; full curriculum and secondary tools remain accessible through disclosures.
- Colors/tokens: warm paper, deep green text and#517c2c main action with measured white-label contrast~4.92:1. Default plus all ten equipped themes/two modes pass contrast checks. Existing equipped theme and earned outfit data are preserved.
- Image quality: seven explicit WebP assets,total407582bytes; transparent default/graduate guides use generated raster art from the selected reference. No code-drawn substitute for the new guide. Existing nonmatching wardrobe art remains only where needed to preserve actual earned outfits. Decorative book/lesson images do not claim to be real textbook covers or encode answers.
- Copy/content: normal children see task/route/play/settings labels rather than synchronization terminology or management exports. Mock values remain separate from authorized content; simulator explanation is retained, weekly reward is explicit and never triggered by viewing a ranking.

## Interaction and responsive verification

B1 direct login: restore original4c8770a8…session, advance, select and submit a real choice, confirmed correct. Single click on a different course confirms new72c126a9…session with no second Start. One “开始练习” opens real question sequence. Select a draft, observe actual sending, refresh: original session/question and pressed choice retained; submission confirmed by the server. Evidence: `repair-confirmed-answer-b1-390.png`, `repair-draft-restored-b1-390.png`. No fake completion/rewards.

`repair-responsive.json`:360/390/430,844×390landscape,768×1024tablet,1440×900desktop: no horizontal overflow; inspected visible controls at least44px; fixed scene remains. Expanded all-course list and tools still usable at the bottom. Avatar preview/cancel, one trigger and native modal remain operational. Final cottage exposes the parent tools only after expansion; ranking weekly reward remains closed and balances unchanged.

Type checks,16LearningClient cases,Provider/local-profile regressions,16avatars,web-experience,visual-controls and child-ui pass. r17cloud/local production builds and merged publication scan pass. API image/container and both database versions unchanged; detailed audit and logs in `docs/child-forest-acceptance.md`.

## Limits and follow-up

The exact original user-reported exception text has not been provided and was not reproduced; do not claim its specific root cause is known. The observable entry/saving failures and tested paths above are corrected. Keep this distinction in the handoff.

OpenSpec6.2 remains open: no second controllable independent browser, actual200%zoom, physical iOS/Android keyboard/listening/recording evidence. No personal Chrome profile changes. M1recording and M2plan untouched.

P3: small stock-icon/cover-detail differences and natural extra wrapping for real longer course names. A long third preview may extend below the initial fold; it remains fully reachable by normal scrolling with reserved bottom space. Do not shorten real course names or forge progress for screenshot matching.

final result: passed

## Reopened: premature answer feedback

User screenshot shows first letter y rendered red during automatic draft save, before Check answer. Cause: locked editing reused as grading state in text/numeric/word-order answer displays. Reopen until phase/result styling is independent from lock, with regression and browser verification.

Premature-feedback finding resolved in r18: three answer surfaces now use checked+known-result for color, independent of editing lock; regression fails before the fix and passes after (36 combinations). Actual components in browser stay white/blue for the single-letter y while saving, green/red only for the explicit checked examples. See early-feedback-neutral-y-390.png; synthetic state verification is distinguished from live account interaction.

## Reopened: repeated account-check interstitial

Child routes mounted separate guards/learning clients; some tool links performed full document navigation. Reopen until one verified child shell survives route changes without losing pending writes, while expiry and identity changes still revoke old data.

Repeated-session interstitial finding resolved in r19: shared root child guard/client, scoped nested destination gate and client-side tool links. Live six-route navigation keeps one frame/avatar and190XP119gems without the account-check interstitial. Initial checks and invalidation remain; automated expiry/cross-tab/reauth cases pass. See session-shell-navigation.json and session-shell-after-profile.png.

## User-directed subject navigation

The user explicitly replaced the child textbook selector with a prominent subject switcher. Add the four subject buttons near the header, keep parent-configured editions authoritative, preserve the first-viewport learning action and isolate late subject responses. This deliberate addition supersedes the original mock’s lack of a subject bar.

Subject navigation finding resolved in r20. Four subject buttons before the hero, 46px high; selected parent-configured textbook is authoritative. Real 390×844 CTA bottom586.86px remains visible, long-list scroll3780px keeps bar top8px. Tested360/390/430/landscape/tablet/desktop without horizontal overflow. Four-subject live switching and explore return keep the same verified shell, balances and scoped content; late-response regression passes. The temporary synthetic fixture was restored. This visual QA pass does not complete the explicitly open OpenSpec6.2 device/browser coverage.

## Reopened: league/cottage clutter and typing latency
User requests removal of league prose/refresh, simpler cottage without goal select or header logout, and no network save per typed letter. Verify streamlined layout and input recovery before closing.

League/cottage/input findings resolved in r22. Real mobile league has16 avatar rows without refresh button or introduction block. Cottage shows one selected section, no goal select or header logout; parent/account area hides exit until opened. Goal and section buttons remain >=44px across tested phone/landscape/tablet/desktop widths, no overflow. Tasks/achievements use readable core names. Continuous draft input has no checkpoint network writes or input lock; same-tab refresh recovery and explicit submit/exit verified by actual component tests and real number-task interaction. Original synthetic selections/balances preserved. Screens and limits are recorded in child-forest-acceptance.md; this does not close OpenSpec6.2.

## Reopened: feedback reflow and wardrobe state
User screenshot shows inline confirmation moving the cottage tabs and every owned outfit still displaying Equip. Verify auto-dismiss fixed notices, confirmed per-slot equipped states and stable card positions across an equip operation.

Feedback/wardrobe finding resolved in r25. Actual390×844 equip/restore keeps the four row document positions and heights unchanged (0px), button116×48px, page993px. Fixed confirmation appears and auto-dismisses without moving content; per-slot equipped states are confirmed and repeat operations disabled. Original graduate outfit and190XP134gems restored/preserved. Phone/landscape/tablet/desktop widths have no overflow. See toast-layout-proof.json and toast-equipped-390.png; separately open OpenSpec6.2 coverage remains unchanged.

## Reopened: ambiguous initial avatar focus and perceived latency
Verify initial focus on the dialog heading with one selected radio, keyboard focus distinction, and measured read optimizations without cached authority or learner state.

Avatar-focus/latency finding resolved in r26. Actual390px first open focuses the heading, has one selected tiger and zero focus outlines on other choices. Keyboard Tab gives the current selection a dashed outline; cancelling lion preview restores tiger and trigger focus without writes.18 client regressions and avatar suite pass; catalogue-only scoped TTL cache and response reuse reduce redundant reads. Loopback/common-read and separate public health-connection samples/limits are recorded in acceptance; no claim that server cache fixes the user's4G connection. OpenSpec6.2 remains open.

## Reopened: child UI refinement round
Verify visible cosmetic slot groups/previews and stable equipped actions, actionable exploration empty states without changing book, and readable fallback session titles while preserving the original resume ID.

Child refinement round resolved in r29: real wardrobe4items/shop30items retain three explicit slots with previews and confirmed equipped buttons; phone2columns/desktop4columns, action heights48px and widths<=180px, no overflow on tested sizes. Empty exploration's return action is now in the first390×844 viewport (bottom464.44px), story/listening switch and original-book return verified. Home names the existing Jump session and keeps CTA bottom586.86px.260XP190gems/Avatar unchanged; no purchase/equip/learning writes. UI-round final evidence distinguishes resolved interim493px desktop buttons and below-fold951px recovery link. OpenSpec6.2 still open.
