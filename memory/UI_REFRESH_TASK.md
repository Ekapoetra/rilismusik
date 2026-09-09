# Active task — Dashboard UI, language, theme, audio and notification refresh

## User requirements (2026-09-08)
1. Genuine Rilis Musik admin logo suited to dark backgrounds.
2. Sidebar collapse button centered on divider, simpler clear icon.
3. Language applies to all admin/label system text and content, not only sidebar; move language button top right next to notification icon.
4. Never translate label/artist names, song titles, release metadata or user messages.
5. Light/dark/auto controls top right, contrasting text/logos; auto follows WIB.
6. New chat popup bottom right: "Pesan Chat Baru", offset clear of chat button.
7. Large modern bottom audio preview in release submission/detail, Artlist/Epidemic-inspired, download preserved.
8. Role & Permission preview shows configured website simulation, not merely menu list.
9. Remove Label Rates.
10. Remove Reset Data Bisnis in Admin Users.
11. Clearly audible sounds for new notification/chat/internal account online.

## Confirmed choices
- Indonesian ↔ English across admin and label UI; protected data not translated.
- Auto light06:00–17:59 and dark18:00–05:59 Asia/Jakarta.
- Item9 clarified: remove only Import Rate Label TAB; individual Manajemen Label rate/fee edit remains.
- Reset Data Bisnis UI+endpoint removed WITHOUT deleting any business data.

## Work status
- Requirements approved, source inventory + design/auth preview playbooks read.
- **2026-09-09 — P0 implemented and scoped acceptance verified.** Final evidence `/app/test_reports/iteration_66_followup.json`, initial reports Iter65/66 retained with follow-up dispositions. User acceptance remains pending.
- Existing brand assets inspected: logo-icon-gradient.png is WHITE-outline mark (dark background); logo-icon-outline.png DARK-outline mark (light background). Full marks logo-mark.png white wordmark vs logo-mono.png black wordmark. Crop copied assets to transparent bounding box; don't invent logo.
- Preserve Manrope/Plus Jakarta Sans despite design agent's generic font suggestion. Actual images take precedence over its inverted icon recommendations.
- i18n approach: static bundled language catalog; only code-authored UI literals/known system labels translated, not arbitrary DOM/user data. No runtime external translation service or user metadata sent anywhere.
- Role preview isolated/read-only with simulated data, no permission/session mutation or API writes. Must clearly label preview data as simulation.
- Test all11 together, one smoke screenshot, then testing agent. Strict isolated QA fixtures; NEVER copy broad notification deletion from original Iter64 tests. Current fixed fixture cleanup uses exact owned references and sentinel assertion.

## Final implementation / verification (2026-09-09)
- Real dashboard branding and shared shell, middle-divider collapse, top-right ID/EN + Light/Dark/Auto + sound controls. WIB boundaries and actual timer transition18:00 passed; selected mode persists, loaded assets/foreground/background checked.
- Authored JSX/system props localized using local Babel plugin/SystemText; database expressions/metadata/user chat excluded. Offline generator fixed to Moses+subword-nmt matching the OPUS model instead of incompatible OpenNMT tokenization. Reviewed glossary overrides important dashboard/form terms; runtime invalid entries fall back to authored text. No external translation service/API.
- CRACO Babel cache identifier now hashes the local plugin, with webpack build dependencies. Added declared dev dependency `@babel/helper-plugin-utils`; current compiler configuration loaded after dependency install. Final build compiled successfully without lint warnings.
- Role iframe reuses actual sidebar with order/nesting/visibility and unsaved permissions, including implied view permissions; inactive roles empty, Super Admin full. Zero app API calls in iframe; all rows SIMULATED/read-only and explicitly disclosed.
- Bottom audio dock includes real play/pause/progress/seek, previous/next, volume/mute, cover, protected title/artist, download, close/Escape/error. Real uploaded20s WAV playback and successful download verified; wizard draft metadata retained, no submission. Width320/768/1024/1440 and audio/chat clearance passed.
- New-chat bottom-right notice and distinct sound triggers verified. Ordinary notification initial failure was test timing: emitter ran before first browser baseline. Controlled event after initialization produced2 new WebAudio oscillators. Browser sound requires prior user gesture; physical speakers were not assessed.
- Removed Import Rate Label TAB/route UI only; manual label rate/fee preserved. Reset Data Bisnis UI/endpoint removed; no business reset/data deletion run.
- Fixed redundant admin chat thread polling caused by dependency on changing `active` object; now tracks conversation ID. Chat pending attachment removal has test ID; message/attachment identifiers unique.
- Final shared-icon CSS respects responsive visibility and width-auto instead of overriding Tailwind utilities. Verified desktop hides mobile-only menu;320px header language and drawer open/close remain within viewport after resize settles.
- Iter66 fixtures and generated release assets cleaned; final API state draft before own release deletion. Fixed Iter66 helper cleanup to use actual conversation IDs; one previously orphaned owned QA message was removed by exact traced ID. No user balance/CSV changes.
- Remaining: user acceptance; optional continued glossary review/device-specific sound UX and P2 backlog only.

## Existing relevant sources
- frontend/src/components/shared/{AdminLayout,LabelLayout,Brand,LogoMark,NotificationBell}.jsx
- frontend/src/contexts/AdminNavigationContext.jsx
- frontend/src/components/chat/{AdminChatWidget,LabelChatWidget,chatUtils}.jsx/js
- frontend/src/components/releases/ReleaseMetadataView.jsx; pages/label/release-form/{TracksStep,AssetsReviewStep}.jsx
- frontend/src/components/admin/access/RoleNavPreview.jsx; pages/admin/{AccessControl,AdminUsers,Labels}.jsx
- backend/routes/admin.py `/admin/admin/danger/reset-all-data`, admin_reset_service.py
- backend/routes/admin_permission_service.py default nav label_rates; label_rate_import.py backend (keep individual editing intact)
- design_guidelines.json (advisory; preserve existing brand/fonts and correct actual asset colors)

## Testing/credentials reminders
Read memory/test_credentials.md. Demo PPR/VIP currently KYC incomplete for full protected label flows. Create documented isolated fixtures, never mutate demos or real label balances/files. No user-data reset is authorized.