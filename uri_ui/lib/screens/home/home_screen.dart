import 'package:flutter/material.dart';

import '../../widgets/dashboard/reference_dashboard.dart';

import '../../theme/dashboard_manifest.dart';

import '../../models/activity_event.dart';
import '../../models/connection.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/attachment_opener_service.dart';
import '../../services/file_picker_service.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../ask/ask_uri_screen.dart';

/// URI's authenticated companion dashboard.  This is deliberately a visual
/// shell over the established AppState/client boundary: all figures and actions
/// below are reports from existing endpoints or explicit unavailable states.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.filePicker, this.attachmentOpener});

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  DashboardTab _tab = DashboardTab.system;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      state.loadHome();
      state.loadConnections();
      state.loadTasks();
      if (!state.hasLoadedCapabilities) state.loadCapabilities();
      if (!state.hasLoadedMemory) state.loadMemory();
      if (!state.hasLoadedActivity) state.loadActivity();
      if (!state.hasLoadedAccountInfo) state.loadAccountInfo();
      if (!state.hasLoadedSystemPerformance) state.loadSystemPerformance();
      if (!state.hasLoadedUnreadEmailCount) state.loadUnreadEmailCount();
    });
  }

  void _goTo(int index, {String? settingsCategory}) {
    context.findAncestorStateOfType<AppShellState>()?.goTo(
      index,
      settingsCategory: settingsCategory,
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        // The mobile layout is intentionally a separate fallback.  Desktop
        // rendering below is the frozen board, scaled as one unit instead of
        // recomputing its regions from the current window dimensions.
        final boardFitsAvailableSpace =
            MediaQuery.sizeOf(context).width >= 1000;
        final center = Column(
          children: [
            _GreetingBanner(state: state),
            _DashboardTabs(
              selected: _tab,
              onSelected: (tab) => setState(() => _tab = tab),
            ),
            Expanded(
              child: _DashboardCanvas(
                state: state,
                tab: _tab,
                onGoTo: _goTo,
                attachmentOpener: widget.attachmentOpener,
              ),
            ),
            UriCommandDock(
              filePicker: widget.filePicker,
              compact: true,
              showTip: true,
            ),
          ],
        );
        final colors = UriColors.of(context);
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return DecoratedBox(
          decoration: BoxDecoration(
            // The near-black radial glow is the User-accepted dark
            // theme's own branded treatment (M26 dashboard spec) - kept
            // verbatim for dark mode. Light mode has no equivalent
            // bespoke design, so it reads the active theme's own flat
            // canvas token instead of silently staying on this
            // hardcoded dark gradient regardless of the selected
            // Appearance (User-reported: Appearance must affect the
            // dashboard, not just Settings).
            gradient: isDark
                ? const RadialGradient(
                    center: Alignment.topCenter,
                    radius: 1.2,
                    colors: [Color(0xff083051), Color(0xff020910)],
                  )
                : null,
            color: isDark ? null : colors.canvas,
          ),
          child: boardFitsAvailableSpace
              ? _FixedDashboardBoard(
                  center: center,
                  rail: ReferenceRail(state: state, onGoTo: _goTo),
                )
              : center,
        );
      },
    );
  }
}

/// The application shell owns the board's left rail.  This widget owns the
/// remaining centre and right regions and scales them together using the
/// dimensions that complete that same manifest board.
class _FixedDashboardBoard extends StatelessWidget {
  const _FixedDashboardBoard({required this.center, required this.rail});

  final Widget center;
  final Widget rail;

  @override
  Widget build(BuildContext context) {
    // Reads the SAME scale AppShell computed for the whole board (see
    // DashboardScale) instead of independently re-deriving one via its
    // own FittedBox against only this widget's own local constraints -
    // that independent computation is what let this region drift out
    // of alignment with AppShell's left rail at non-native window
    // aspect ratios (User-reported misalignment/detached-board defect).
    final scale = DashboardScale.of(context);
    return Center(
      child: SizedBox(
        width:
            (DashboardManifest.centerWidth + DashboardManifest.rightRailWidth) *
            scale,
        height: DashboardManifest.nativeHeight * scale,
        child: FittedBox(
          fit: BoxFit.fill,
          child: SizedBox(
            width:
                DashboardManifest.centerWidth +
                DashboardManifest.rightRailWidth,
            height: DashboardManifest.nativeHeight,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(width: DashboardManifest.centerWidth, child: center),
                SizedBox(width: DashboardManifest.rightRailWidth, child: rail),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

enum DashboardTab {
  system,
  activity,
  tasks,
  model,
  connections,
  storage,
  insights,
}

extension on DashboardTab {
  String get label => switch (this) {
    DashboardTab.system => 'System',
    DashboardTab.activity => 'Activity',
    DashboardTab.tasks => 'Tasks',
    DashboardTab.model => 'Model',
    DashboardTab.connections => 'Connections',
    DashboardTab.storage => 'Storage',
    DashboardTab.insights => 'Insights',
  };
}

class _GreetingBanner extends StatelessWidget {
  const _GreetingBanner({required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final name =
        state.accountInfo?.username ?? state.currentUsername ?? 'there';
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = UriColors.of(context);
    return Container(
      height: DashboardManifest.heroHeight,
      margin: const EdgeInsets.fromLTRB(20, 20, 20, 8),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDark ? const Color(0xff15334a) : colors.border,
        ),
        image: const DecorationImage(
          image: AssetImage('assets/misty_forest_sikkim.jpg'),
          fit: BoxFit.cover,
          alignment: Alignment(0, -.16),
        ),
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 3),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDark
                ? const [
                    Color(0xe6020910),
                    Color(0x66020910),
                    Color(0xd9020910),
                  ]
                : [
                    colors.canvas.withValues(alpha: .9),
                    colors.canvas.withValues(alpha: .55),
                    colors.canvas.withValues(alpha: .85),
                  ],
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Good evening,',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: DashboardManifest.greetingFontSize,
                      height: 1.1,
                      fontWeight: FontWeight.w600,
                      color: isDark ? const Color(0xffdeedf8) : colors.ink,
                    ),
                  ),
                  Text(
                    '$name.',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: DashboardManifest.greetingNameFontSize,
                      height: 1.15,
                      fontWeight: FontWeight.w800,
                      color: Color(0xff36aaf7),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    "Let's make progress today.",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: isDark ? const Color(0xffccdded) : colors.inkSoft,
                      fontSize: DashboardManifest.subtitleFontSize,
                    ),
                  ),
                ],
              ),
            ),
            if (MediaQuery.sizeOf(context).width > 700)
              SizedBox(
                width: DashboardManifest.quoteWidth,
                child: Text(
                  'Your work.\nYour ideas.\nA more organized tomorrow.\n\u2014 URI',
                  style: TextStyle(
                    color: isDark ? const Color(0xffccdded) : colors.inkSoft,
                    fontSize: DashboardManifest.quoteFontSize,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _DashboardTabs extends StatelessWidget {
  const _DashboardTabs({required this.selected, required this.onSelected});
  final DashboardTab selected;
  final ValueChanged<DashboardTab> onSelected;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return SizedBox(
      height: DashboardManifest.tabsHeight,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: UriSpace.lg),
        children: [
          for (final tab in DashboardTab.values)
            Padding(
              padding: const EdgeInsets.only(right: UriSpace.xs),
              child: TextButton(
                key: ValueKey('dashboard-tab-${tab.name}'),
                onPressed: () => onSelected(tab),
                style: TextButton.styleFrom(
                  minimumSize: Size(0, DashboardManifest.tabButtonHeight),
                  padding: EdgeInsets.symmetric(
                    horizontal: DashboardManifest.tabButtonPaddingHorizontal,
                  ),
                  foregroundColor: tab == selected
                      ? colors.accentInk
                      : colors.inkSoft,
                  backgroundColor: tab == selected
                      ? colors.accentSoft
                      : Colors.transparent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(7),
                    side: BorderSide(
                      color: tab == selected ? colors.accentInk : colors.border,
                    ),
                  ),
                ),
                child: Semantics(
                  label: '${tab.label} dashboard tab',
                  button: true,
                  child: RichText(
                    text: TextSpan(
                      text: tab.label,
                      style: DefaultTextStyle.of(context).style.copyWith(
                        color: tab == selected
                            ? colors.accentInk
                            : colors.inkSoft,
                        fontSize: DashboardManifest.tabButtonFontSize,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _DashboardCanvas extends StatelessWidget {
  const _DashboardCanvas({
    required this.state,
    required this.tab,
    required this.onGoTo,
    required this.attachmentOpener,
  });
  final AppState state;
  final DashboardTab tab;
  final void Function(int, {String? settingsCategory}) onGoTo;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  Widget build(BuildContext context) {
    final dashboard = _DashboardView(state: state, tab: tab, onGoTo: onGoTo);
    if (state.conversation.isEmpty) return dashboard;
    // Once a request is active, the transcript takes the entire central canvas
    // so its approval/result controls remain usable. The shell, status rail,
    // tabs, and persistent command dock remain mounted; selecting New chat
    // restores the operational dashboard immediately.
    return UriConversationPane(
      attachmentOpener: attachmentOpener,
      compact: true,
    );
  }
}

class _DashboardView extends StatelessWidget {
  const _DashboardView({
    required this.state,
    required this.tab,
    required this.onGoTo,
  });
  final AppState state;
  final DashboardTab tab;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) {
    final child = switch (tab) {
      DashboardTab.system => _SystemDashboard(state: state, onGoTo: onGoTo),
      DashboardTab.activity => _ActivityDashboard(state: state, onGoTo: onGoTo),
      DashboardTab.tasks => _TasksDashboard(state: state, onGoTo: onGoTo),
      DashboardTab.model => _ModelDashboard(state: state, onGoTo: onGoTo),
      DashboardTab.connections => _ConnectionsDashboard(
        state: state,
        onGoTo: onGoTo,
      ),
      DashboardTab.storage => const _UnavailableDashboard(
        title: 'Storage',
        message: 'Global storage and session file inventory are not connected to this dashboard yet.',
      ),
      DashboardTab.insights => _InsightsDashboard(state: state, onGoTo: onGoTo),
    };
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        UriSpace.lg,
        UriSpace.sm,
        UriSpace.lg,
        UriSpace.lg,
      ),
      child: child,
    );
  }
}

class _SystemDashboard extends StatelessWidget {
  const _SystemDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;
  @override
  Widget build(BuildContext context) =>
      ReferenceDashboard(state: state, onGoTo: onGoTo);
}

class _ActivityDashboard extends StatelessWidget {
  const _ActivityDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _SectionHeading(
        title: 'Current runtime activity',
        subtitle: state.hasLoadedActivity
            ? 'Audit events from this running URI server'
            : 'Loading audit trail…',
      ),
      const SizedBox(height: UriSpace.md),
      if (!state.hasLoadedActivity)
        const _UnavailableDashboard(
          title: 'Activity',
          message: 'Loading activity…',
        )
      else if (state.activity.isEmpty)
        const _UnavailableDashboard(
          title: 'No activity yet',
          message: 'Events will appear here when URI proposes, approves, or executes a runtime action.',
        )
      else
        Card(
          child: Column(
            children: [
              for (final event in state.activity.take(8))
                _ActivityRow(event: event),
              _CardAction(
                label: 'View all activity',
                onTap: () => onGoTo(ShellIndex.activity),
              ),
            ],
          ),
        ),
    ],
  );
}

class _TasksDashboard extends StatelessWidget {
  const _TasksDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _SectionHeading(
        title: 'Awaiting your approval',
        subtitle:
            'URI does not perform approval-gated actions until you decide.',
      ),
      const SizedBox(height: UriSpace.md),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.lg),
          child: Row(
            children: [
              const Icon(Icons.pending_actions_outlined),
              const SizedBox(width: UriSpace.sm),
              Expanded(
                child: Text(
                  '${state.homeSummary?.pendingApprovalCount ?? 0} pending approval${(state.homeSummary?.pendingApprovalCount ?? 0) == 1 ? '' : 's'}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              TextButton(
                onPressed: () => onGoTo(ShellIndex.tasks),
                child: const Text('Review'),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _ModelDashboard extends StatelessWidget {
  const _ModelDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _SectionHeading(
        title: 'Active Brain',
        subtitle: 'Provider state is reported by the runtime; it is not an authorization grant.',
      ),
      const SizedBox(height: UriSpace.md),
      _ModelSummaryCard(
        state: state,
        onTap: () =>
            onGoTo(ShellIndex.settings, settingsCategory: 'Model Providers'),
      ),
    ],
  );
}

class _ConnectionsDashboard extends StatelessWidget {
  const _ConnectionsDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _SectionHeading(
        title: 'Connections',
        subtitle: 'Live connector state only. URI does not invent inbox or Drive item counts.',
      ),
      const SizedBox(height: UriSpace.md),
      for (final connection in state.connections)
        Padding(
          padding: const EdgeInsets.only(bottom: UriSpace.sm),
          child: _ConnectionCard(
            connection: connection,
            onTap: () => onGoTo(ShellIndex.connections),
          ),
        ),
      if (state.connections.isEmpty)
        const _UnavailableDashboard(
          title: 'Connections unavailable',
          message: 'URI has not received a connection status report yet.',
        ),
    ],
  );
}

class _InsightsDashboard extends StatelessWidget {
  const _InsightsDashboard({required this.state, required this.onGoTo});
  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _SectionHeading(
        title: 'Operational insights',
        subtitle: 'Each panel is sourced separately; URI does not calculate a fabricated score.',
      ),
      const SizedBox(height: UriSpace.md),
      Wrap(
        spacing: UriSpace.sm,
        runSpacing: UriSpace.sm,
        children: [
          _InsightCard(
            title: 'Capabilities',
            value: state.hasLoadedCapabilities
                ? '${state.capabilities.where((item) => item.isUsable).length} usable'
                : 'Loading…',
            onTap: () =>
                onGoTo(ShellIndex.settings, settingsCategory: 'Capabilities'),
          ),
          _InsightCard(
            title: 'Memory',
            value: state.hasLoadedMemory
                ? '${state.memories.length} entries'
                : 'Loading…',
            onTap: () =>
                onGoTo(ShellIndex.settings, settingsCategory: 'Memory'),
          ),
          _InsightCard(
            title: 'Activity',
            value: state.hasLoadedActivity
                ? '${state.activity.length} events'
                : 'Loading…',
            onTap: () => onGoTo(ShellIndex.activity),
          ),
          const _InsightCard(title: 'Learning', value: 'Not yet connected'),
        ],
      ),
    ],
  );
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.subtitle});
  final String title;
  final String subtitle;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title, style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 2),
      Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
    ],
  );
}

class _ModelSummaryCard extends StatelessWidget {
  const _ModelSummaryCard({required this.state, required this.onTap});
  final AppState state;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final brain = state.activeBrain;
    final provider = state.activeBrainProvider;
    final configured = brain?.isConfigured ?? false;
    final available = configured && (provider?.available ?? false);
    final status = !configured
        ? 'Not configured'
        : available
        ? 'Available'
        : 'Unavailable';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.psychology_outlined, size: 18),
                const SizedBox(width: UriSpace.xs),
                Text(
                  'Current model',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: UriSpace.sm),
            Text(
              configured ? brain!.model : 'No Active Brain',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              configured ? '${brain!.providerId} · $status' : status,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Padding(
              padding: EdgeInsets.only(top: UriSpace.xs),
              child: Text(
                'Current context and cost are not reported.',
                style: Theme.of(context).textTheme.keyValue,
              ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: onTap,
                child: const Text('Change model'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConnectionCard extends StatelessWidget {
  const _ConnectionCard({required this.connection, required this.onTap});
  final ServiceConnection connection;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final status = switch (connection.status) {
      ConnectionStatus.connected => 'Connected',
      ConnectionStatus.needsAuthorization => 'Authorization required',
      ConnectionStatus.notConnected => 'Not connected',
    };
    return Card(
      child: ListTile(
        leading: const Icon(Icons.hub_outlined),
        title: Text(connection.name),
        subtitle: Text(status),
        trailing: TextButton(onPressed: onTap, child: const Text('Manage')),
      ),
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.event});
  final ActivityEvent event;
  @override
  Widget build(BuildContext context) => ListTile(
    leading: Icon(switch (event.kind) {
      ActivityKind.proposal => Icons.bolt_outlined,
      ActivityKind.approval => Icons.check_circle_outline,
      ActivityKind.execution => Icons.play_circle_outline,
      ActivityKind.cancellation => Icons.cancel_outlined,
      ActivityKind.system => Icons.settings_outlined,
    }),
    title: Text(event.summary),
    dense: true,
  );
}

class _CardAction extends StatelessWidget {
  const _CardAction({required this.label, required this.onTap});
  final String label;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.centerRight,
    child: TextButton(onPressed: onTap, child: Text(label)),
  );
}

class _InsightCard extends StatelessWidget {
  const _InsightCard({required this.title, required this.value, this.onTap});
  final String title;
  final String value;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 180,
    child: Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(UriRadius.md),
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(height: UriSpace.xs),
              Text(value, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
        ),
      ),
    ),
  );
}

class _UnavailableDashboard extends StatelessWidget {
  const _UnavailableDashboard({required this.title, required this.message});
  final String title;
  final String message;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(UriSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: UriSpace.xs),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    ),
  );
}
