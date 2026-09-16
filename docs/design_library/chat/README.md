# Chat workspace — reference patterns

## Current URI reality (verified 2026-09-15)

Chat is **not** a first-class screen today. `uri_ui/lib/app.dart` defines
exactly six routed `AppShell` sections: Home, Tasks, Connections, Activity,
History, Settings. There is no "Chat" section. The visible "Chat" nav label
in `uri_ui/lib/widgets/app_shell.dart:186` routes to `ShellIndex.home`, i.e.
back to the Home dashboard. The actual conversation surface,
`UriCommandDock` (defined in `uri_ui/lib/screens/ask/ask_uri_screen.dart:189`),
is embedded as a fixed dock bar at the bottom of `HomeScreen`
(`uri_ui/lib/screens/home/home_screen.dart:84`), always present under
whichever dashboard tab is selected.

A separate `AskUriScreen` class exists in the same file
(`ask_uri_screen.dart:17`) but is never instantiated anywhere in the app —
it is dead code, not a working alternate chat screen.

This is exactly the condition the User asked to change: Chat must become
its own standalone workspace, not a dock riding along under System/Home.

## Reference patterns

Rendered screenshots captured 2026-09-15 from each project's live demo:
`../screenshots/kiranism_chat.jpg`, `../screenshots/tabler_chat.jpg`,
`../screenshots/shadcnstore_chat.jpg`. All three render as a
conversation-list rail + active thread + composer — none of them show a
single-thread-only layout in practice, despite tabler's source naming
(`chat.astro`, singular) suggesting otherwise; tabler's actual rendered
page still includes a contact/conversation list down the left side.

- **Kiranism/next-shadcn-dashboard-starter** — `src/app/dashboard/chat/`,
  `src/app/dashboard/ai-chat/`, and `src/features/chat/components/`
  (`chat-area.tsx`, `chat-header.tsx`, `conversation-list.tsx`,
  `message-bubble.tsx`, `message-composer.tsx`, `messenger.tsx`). Chat is a
  routed sibling of `dashboard/overview`, not a widget inside it. Good
  reference for a two-pane layout: conversation list rail + active thread.
- **tabler/tabler** — `preview/pages/chat.astro`,
  `core/scss/ui/_chat.scss`. Renders (screenshot:
  `../screenshots/tabler_chat.jpg`) as a team-chat-style contact list +
  thread, lower-chrome than Kiranism's or shadcnstore's version but still
  two-pane, not single-thread as the source filename alone suggested —
  corrected from this document's earlier assumption.
- **shadcnstore/shadcn-dashboard-landing-template** —
  `nextjs-version/src/app/(dashboard)/chat/components/` (`chat.tsx`,
  `conversation-list.tsx`, `message-input.tsx`, `message-list.tsx`). Same
  two-pane shape as Kiranism, in a lighter-weight template — closer in
  spirit to how simple URI's actual conversation model is today.

## Real backend shape this must map onto

- `ConversationHistoryStore` (`uri_core/core/conversation_history.py`) and
  the orchestrator's turn loop back the conversation — there is one
  continuous exchange per session, not a multi-conversation inbox, unlike
  the reference repos' conversation-list pattern (which assumes many
  saved threads a user switches between). A reference structure with a
  conversation list rail should be adopted only if/when URI actually grows
  multi-session switching in the UI; until then the rail may be a
  simplification target, not a feature to copy wholesale.
- Proposed actions awaiting approval surface inside the conversation turn
  itself (see `uri_ui/lib/models/uri_turn.dart`) — any reference layout
  adopted must leave room for an inline approval/decision card in the
  message stream, which none of the reference repos need to model (they
  have no approval-gate concept).

## Decisions

None yet. Record a decision under `../approved/` or `../rejected/` once a
concrete Chat workspace design is chosen or turned down.
