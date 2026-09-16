import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../models/connection.dart';
import '../../theme/dashboard_manifest.dart';
import '../../theme/uri_theme.dart';
import '../app_shell.dart';

// Accent hues for icon badges/values - deliberately unchanged between
// themes (colorful accents read fine on both a white and a near-black
// card; only the surrounding card/text needs a light variant - see
// GlassPanel, inkFor, and link() below).
const blue = Color(0xff279bff);
const pink = Color(0xffdc56ff);
const mint = Color(0xff20e5b0);
const gold = Color(0xffffc437);
// The dark theme's own body-text color (unchanged, still used verbatim
// in dark mode). Not a compile-time-usable value in light mode - call
// sites needing the CURRENT theme's ink now go through inkFor/GlassPanel
// instead of this bare constant.
const ink = Color(0xffccdded);

Color inkFor(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark
    ? ink
    : UriColors.of(context).ink;
Color inkFaintFor(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark
    ? const Color(0xff86a8bf)
    : UriColors.of(context).inkFaint;

typedef DashboardNavigation = void Function(int, {String? settingsCategory});

enum DashboardCardState { loading, live, unavailable }

class GlassPanel extends StatelessWidget {
  const GlassPanel({super.key, required this.child, this.padding = 12});
  final Widget child;
  final double padding;
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = UriColors.of(context);
    return Container(
      padding: EdgeInsets.all(padding),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),
        border: Border.all(
          color: isDark ? const Color(0xff123149) : colors.border,
        ),
        gradient: isDark
            ? const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xff081928), Color(0xff030f1a)],
              )
            : null,
        color: isDark ? null : colors.surface,
        boxShadow: isDark
            ? const [BoxShadow(color: Color(0x180da5ff), blurRadius: 8)]
            : [
                BoxShadow(
                  color: Colors.black.withValues(alpha: .05),
                  blurRadius: 8,
                ),
              ],
      ),
      child: DefaultTextStyle(
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: isDark ? ink : colors.ink,
          fontSize: 11,
          height: 1.35,
        ),
        child: child,
      ),
    );
  }
}

Widget heading(
  String title, [
  IconData icon = Icons.dashboard_outlined,
  Color color = blue,
]) => Row(
  children: [
    Icon(icon, size: 16, color: color),
    const SizedBox(width: 7),
    Expanded(
      child: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
      ),
    ),
  ],
);
Widget link(BuildContext context, String label, VoidCallback action) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  final colors = UriColors.of(context);
  return Padding(
    padding: const EdgeInsets.only(top: 8),
    child: SizedBox(
      width: double.infinity,
      height: 30,
      child: OutlinedButton(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          foregroundColor: isDark ? ink : colors.ink,
          backgroundColor: isDark
              ? const Color(0xff092031)
              : colors.surfaceSunken,
          side: BorderSide(
            color: isDark ? const Color(0xff15334a) : colors.border,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        ),
        onPressed: action,
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                // metricCaption's own baked-in inkFaint color is right for
                // a de-emphasized caption but wrong here: it silently
                // overrode this button's own foregroundColor (set just
                // above), regressing an actionable link's contrast back
                // toward a muted caption look (Batch 4 audit finding).
                // .copyWith keeps the unified size/weight/spacing while
                // restoring the button's real foreground color.
                style: Theme.of(context).textTheme.metricCaption
                    .copyWith(color: isDark ? ink : colors.ink),
              ),
            ),
            const Text('›'),
          ],
        ),
      ),
    ),
  );
}

String gb(int bytes) => (bytes / 1073741824).toStringAsFixed(1);

class ReferenceDashboard extends StatefulWidget {
  const ReferenceDashboard({
    super.key,
    required this.state,
    required this.onGoTo,
    this.presentationStateOverride,
  });
  final AppState state;
  final DashboardNavigation onGoTo;
  final DashboardCardState? presentationStateOverride;
  @override
  State<ReferenceDashboard> createState() => _ReferenceDashboardState();
}

class _ReferenceDashboardState extends State<ReferenceDashboard> {
  final List<List<double>> history = [[], [], []];
  Object? lastSnapshot;
  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    final p = s.systemPerformance;
    final performanceState =
        widget.presentationStateOverride ??
        (p != null
            ? DashboardCardState.live
            : (s.hasLoadedSystemPerformance
                  ? DashboardCardState.unavailable
                  : DashboardCardState.loading));
    final activityState =
        widget.presentationStateOverride ??
        (s.hasLoadedActivity
            ? DashboardCardState.live
            : DashboardCardState.loading);
    if (p != null && !identical(p, lastSnapshot)) {
      lastSnapshot = p;
      final values = [p.cpuPercent, p.memoryUsedPercent, p.diskUsedPercent];
      for (var i = 0; i < 3; i++) {
        history[i].add(values[i]);
        if (history[i].length > 40) history[i].removeAt(0);
      }
    }
    return LayoutBuilder(
      builder: (context, c) {
        if (c.maxWidth >= 600 && c.maxWidth < 850) {
          return SizedBox(
            height: 480 * c.maxWidth / 900,
            width: c.maxWidth,
            child: FittedBox(
              alignment: Alignment.topLeft,
              fit: BoxFit.contain,
              child: SizedBox(
                width: 900,
                child: ReferenceDashboard(state: s, onGoTo: widget.onGoTo),
              ),
            ),
          );
        }
        final columns = c.maxWidth >= 600 ? 5 : 2;
        final width = (c.maxWidth - (columns - 1) * 8) / columns;
        final panelWidth = c.maxWidth >= 600
            ? (c.maxWidth - 24) / 4
            : (c.maxWidth - 8) / 2;
        Widget metric(
          String title,
          Color color,
          String value,
          String unit,
          List<double> points,
          IconData icon,
        ) => SizedBox(
          key: ValueKey('dashboard-metric-$title'),
          width: width,
          height: 210,
          child: GlassPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                heading(title, icon, color),
                const SizedBox(height: 17),
                FittedBox(
                  child: Text(
                    value,
                    style: TextStyle(
                      fontSize: DashboardManifest.metricValueFontSize,
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context).brightness == Brightness.dark
                          ? const Color(0xffe5f2fc)
                          : UriColors.of(context).ink,
                    ),
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  unit,
                  maxLines: 2,
                  style: Theme.of(context).textTheme.metricCaption,
                ),
                const Spacer(),
                SizedBox(
                  height: 54,
                  width: double.infinity,
                  child: CustomPaint(painter: TelemetryPainter(points, color)),
                ),
                Text(
                  performanceState == DashboardCardState.loading
                      ? 'Loading telemetry'
                      : performanceState == DashboardCardState.unavailable
                      ? unit
                      : 'Live runtime samples',
                  style: TextStyle(fontSize: 9, color: inkFaintFor(context)),
                ),
              ],
            ),
          ),
        );
        Widget panel(String key, Widget child) => SizedBox(
          key: ValueKey('dashboard-panel-$key'),
          width: panelWidth,
          height: 260,
          child: GlassPanel(child: child),
        );
        final now = DateTime.now();
        final today = s.activity
            .where(
              (e) =>
                  e.timestamp.toLocal().year == now.year &&
                  e.timestamp.toLocal().month == now.month &&
                  e.timestamp.toLocal().day == now.day,
            )
            .toList();
        final counts = List<double>.generate(
          6,
          (i) => today
              .where((e) => e.timestamp.toLocal().hour ~/ 4 == i)
              .length
              .toDouble(),
        );
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(
              label: 'System usage',
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  metric(
                    'CPU',
                    blue,
                    performanceState == DashboardCardState.live
                        ? '${p!.cpuPercent.round()}%'
                        : performanceState == DashboardCardState.loading
                        ? 'Loading'
                        : 'Not reported',
                    performanceState == DashboardCardState.live
                        ? '${p!.logicalCores} logical cores'
                        : 'CPU telemetry unavailable',
                    performanceState == DashboardCardState.live
                        ? history[0]
                        : const [],
                    Icons.memory,
                  ),
                  metric(
                    'GPU',
                    pink,
                    'Not reported',
                    'GPU telemetry unavailable',
                    const [],
                    Icons.memory,
                  ),
                  metric(
                    'RAM',
                    mint,
                    performanceState == DashboardCardState.live
                        ? '${p!.memoryUsedPercent.round()}%'
                        : performanceState == DashboardCardState.loading
                        ? 'Loading'
                        : 'Not reported',
                    performanceState == DashboardCardState.live
                        ? '${gb(p!.memoryTotalBytes - p.memoryAvailableBytes)} / ${gb(p.memoryTotalBytes)} GB'
                        : 'RAM telemetry unavailable',
                    performanceState == DashboardCardState.live
                        ? history[1]
                        : const [],
                    Icons.memory,
                  ),
                  metric(
                    'Disk',
                    gold,
                    performanceState == DashboardCardState.live
                        ? '${p!.diskUsedPercent.round()}%'
                        : performanceState == DashboardCardState.loading
                        ? 'Loading'
                        : 'Not reported',
                    performanceState == DashboardCardState.live
                        ? '${gb(p!.diskTotalBytes - p.diskFreeBytes)} / ${gb(p.diskTotalBytes)} GB'
                        : 'Disk telemetry unavailable',
                    performanceState == DashboardCardState.live
                        ? history[2]
                        : const [],
                    Icons.description_outlined,
                  ),
                  SizedBox(
                    key: const ValueKey('dashboard-metric-System Health'),
                    width: width,
                    height: 210,
                    child: GlassPanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'System Health',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 14),
                          for (final label in [
                            'CPU Temp',
                            'GPU Temp',
                            'Fan Speed',
                            'Power Draw',
                          ])
                            Padding(
                              padding: const EdgeInsets.only(bottom: 6),
                              child: Row(
                                children: [
                                  Icon(
                                    label.contains('Temp')
                                        ? Icons.thermostat
                                        : Icons.bolt,
                                    size: 14,
                                    color: label.contains('Temp') ? pink : blue,
                                  ),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      label,
                                      style: const TextStyle(fontSize: 9),
                                    ),
                                  ),
                                  Text(
                                    performanceState ==
                                            DashboardCardState.loading
                                        ? 'Loading'
                                        : 'Not reported',
                                    style: const TextStyle(fontSize: 7.4),
                                  ),
                                ],
                              ),
                            ),
                          const Spacer(),
                          const Text(
                            'Not reported',
                            style: TextStyle(color: gold, fontSize: 10),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                panel(
                  'Activity',
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      heading('Activity (Today)'),
                      const SizedBox(height: 18),
                      Expanded(
                        child: Row(
                          children: [
                            SizedBox(
                              width: 45,
                              child: CustomPaint(
                                size: const Size(45, 130),
                                painter: ActivityBars(
                                  activityState == DashboardCardState.live
                                      ? counts
                                      : const [],
                                  activityState,
                                ),
                              ),
                            ),
                            const SizedBox(width: 9),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    activityState == DashboardCardState.live
                                        ? '${today.length}'
                                        : activityState ==
                                              DashboardCardState.loading
                                        ? 'Loading'
                                        : 'Not reported',
                                    style: const TextStyle(
                                      fontSize: 23,
                                      color: blue,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    activityState == DashboardCardState.live
                                        ? 'runtime events'
                                        : 'Activity unavailable',
                                  ),
                                  const SizedBox(height: 10),
                                  for (final kind in [
                                    'proposal',
                                    'approval',
                                    'execution',
                                    'cancellation',
                                  ])
                                    Text(
                                      '${activityState == DashboardCardState.live ? today.where((e) => e.kind.name == kind).length : 0}  $kind',
                                      style: const TextStyle(
                                        fontSize: 10,
                                        height: 1.8,
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      link(
                        context,
                        'Open activity',
                        () => widget.onGoTo(ShellIndex.activity),
                      ),
                    ],
                  ),
                ),
                panel(
                  'Model Usage',
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      heading('Model Usage'),
                      const SizedBox(height: 15),
                      Expanded(
                        child: Center(
                          child: SizedBox(
                            width: DashboardManifest.donutSize,
                            height: DashboardManifest.donutSize,
                            child: CustomPaint(
                              painter: UsageRing(),
                              child: const Center(
                                child: Text(
                                  'Provider breakdown\nunavailable',
                                  textAlign: TextAlign.center,
                                  maxLines: 2,
                                  overflow: TextOverflow.visible,
                                  style: TextStyle(fontSize: 8),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      Text(
                        'Provider breakdown unavailable',
                        style: Theme.of(context).textTheme.footerCaption,
                      ),
                      link(
                        context,
                        'View details',
                        () => widget.onGoTo(
                          ShellIndex.settings,
                          settingsCategory: 'Model Providers',
                        ),
                      ),
                    ],
                  ),
                ),
                panel(
                  'Storage',
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      heading('Storage'),
                      const SizedBox(height: 18),
                      const Text(
                        'Storage breakdown unavailable',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(5),
                        child: LinearProgressIndicator(
                          value: 1,
                          color: blue.withValues(alpha: .32),
                          backgroundColor:
                              Theme.of(context).brightness == Brightness.dark
                              ? const Color(0xff304556)
                              : UriColors.of(context).surfaceSunken,
                          minHeight: 10,
                        ),
                      ),
                      const SizedBox(height: 12),
                      for (final item in [
                        ('Documents', blue),
                        ('Emails', gold),
                        ('Projects', pink),
                        ('Others', Colors.blueGrey),
                      ])
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(
                            children: [
                              Icon(Icons.square, size: 7, color: item.$2),
                              const SizedBox(width: 5),
                              Expanded(
                                child: Text(
                                  item.$1,
                                  style: const TextStyle(fontSize: 10),
                                ),
                              ),
                              const Flexible(
                                child: FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Text('Not reported'),
                                ),
                              ),
                            ],
                          ),
                        ),
                      const Spacer(),
                      link(
                        context,
                        'Open in Drive',
                        () => widget.onGoTo(ShellIndex.connections),
                      ),
                    ],
                  ),
                ),
                panel(
                  'Active Connections',
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      heading('Active Connections', Icons.link),
                      const SizedBox(height: 14),
                      for (final connection in s.connections.take(4))
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Row(
                            children: [
                              Icon(
                                connection.id == 'gmail'
                                    ? Icons.mail_outline
                                    : Icons.link,
                                color: connection.id == 'gmail' ? pink : gold,
                                size: 16,
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  connection.name,
                                  style: const TextStyle(fontSize: 10),
                                ),
                              ),
                              Text(
                                connection.status == ConnectionStatus.connected
                                    ? 'Connected'
                                    : 'Not connected',
                                style: TextStyle(
                                  fontSize: 8,
                                  color:
                                      connection.status ==
                                          ConnectionStatus.connected
                                      ? mint
                                      : Colors.blueGrey,
                                ),
                              ),
                            ],
                          ),
                        ),
                      const Text(
                        'Institute Portal: Not connected',
                        style: TextStyle(fontSize: 9, color: Colors.blueGrey),
                      ),
                      const Spacer(),
                      link(
                        context,
                        'Manage connections',
                        () => widget.onGoTo(ShellIndex.connections),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class TelemetryPainter extends CustomPainter {
  TelemetryPainter(this.points, this.color);
  final List<double> points;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color.withValues(alpha: .15)
      ..strokeWidth = 1;
    for (var i = 1; i < 4; i++) {
      canvas.drawLine(
        Offset(0, size.height * i / 4),
        Offset(size.width, size.height * i / 4),
        paint,
      );
    }
    if (points.isEmpty) {
      // Unavailable/loading still owns the live sparkline's bounding box.
      canvas.drawLine(
        Offset(0, size.height * .68),
        Offset(size.width, size.height * .68),
        Paint()
          ..color = color.withValues(alpha: .42)
          ..strokeWidth = 1.6,
      );
      return;
    }
    // A first real sample is still a filled live chart, not a dot which
    // would collapse the reference sparkline before a second poll arrives.
    final plottedPoints = points.length == 1
        ? [points.first, points.first]
        : points;
    final path = Path();
    for (var i = 0; i < plottedPoints.length; i++) {
      final x = size.width * i / (plottedPoints.length - 1);
      final y = size.height * (1 - plottedPoints[i].clamp(0, 100) / 100);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final area = Path.from(path)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(
      area,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: .35), color.withValues(alpha: 0)],
        ).createShader(Offset.zero & size),
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6,
    );
  }

  @override
  bool shouldRepaint(covariant TelemetryPainter oldDelegate) => true;
}

class ActivityBars extends CustomPainter {
  ActivityBars(this.values, this.state);
  final List<double> values;
  final DashboardCardState state;
  @override
  void paint(Canvas canvas, Size size) {
    final effectiveValues = values.isEmpty ? List<double>.filled(6, 1) : values;
    final maximum = effectiveValues.fold<double>(1, math.max);
    for (var i = 0; i < effectiveValues.length; i++) {
      final h = values.isEmpty
          ? size.height * .16
          : math.max(2.0, size.height * effectiveValues[i] / maximum);
      final rect = Rect.fromLTWH(
        i * size.width / 6,
        size.height - h,
        size.width / 6 - 2,
        h,
      );
      canvas.drawRect(
        rect,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: state == DashboardCardState.live
                ? const [blue, Color(0xff173dcc)]
                : [blue.withValues(alpha: .35), blue.withValues(alpha: .12)],
          ).createShader(Offset.zero & size),
      );
    }
  }

  @override
  bool shouldRepaint(covariant ActivityBars oldDelegate) => true;
}

class UsageRing extends CustomPainter {
  const UsageRing();
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawCircle(
      size.center(Offset.zero),
      size.shortestSide / 2 - 9,
      Paint()
        ..color = DashboardManifest.tokenMuted.withValues(alpha: .52)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 12,
    );
  }

  @override
  bool shouldRepaint(covariant UsageRing oldDelegate) => false;
}

class ReferenceRail extends StatelessWidget {
  const ReferenceRail({
    super.key,
    required this.state,
    required this.onGoTo,
    this.presentationStateOverride,
  });
  final AppState state;
  final DashboardNavigation onGoTo;
  final DashboardCardState? presentationStateOverride;
  @override
  Widget build(BuildContext context) {
    final name =
        state.accountInfo?.username ?? state.currentUsername ?? 'Profile';
    final unreadEmailValue = state.unreadEmailCount == null
        ? (state.hasLoadedUnreadEmailCount ? 'Not reported' : 'Loading…')
        : '${state.unreadEmailCount}';
    final now = DateTime.now();
    Widget card(String key, Widget child) => Padding(
      key: ValueKey('dashboard-rail-$key'),
      padding: const EdgeInsets.only(bottom: 4),
      child: GlassPanel(padding: 7, child: child),
    );
    Widget kv(String key, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Expanded(child: Text(key)),
          Text(value),
        ],
      ),
    );
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final railColors = UriColors.of(context);
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xaa020910) : railColors.surface,
        border: Border(
          left: BorderSide(
            color: isDark ? const Color(0xff15334a) : railColors.border,
          ),
        ),
      ),
      padding: const EdgeInsets.all(10),
      child: ListView(
        children: [
          const SizedBox(height: 6),
          Row(
            children: [
              CircleAvatar(
                backgroundColor: blue,
                child: Text(
                  name.substring(0, 1).toUpperCase(),
                  style: const TextStyle(color: Colors.white),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  name,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: inkFor(context),
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Profile',
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: () =>
                    onGoTo(ShellIndex.settings, settingsCategory: 'Profile'),
                icon: Icon(Icons.expand_more, size: 16, color: inkFor(context)),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Text(
              '${now.day}/${now.month}/${now.year}   ${TimeOfDay.fromDateTime(now).format(context)}',
              style: TextStyle(color: inkFor(context), fontSize: 10),
            ),
          ),
          card(
            'Today at a glance',
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                heading('Today at a glance'),
                const SizedBox(height: 6),
                kv('Unread emails', unreadEmailValue),
                kv('Pending approvals', '${state.tasks.length}'),
                kv('Upcoming event', 'Not reported'),
                link(
                  context,
                  'View full calendar',
                  () => onGoTo(ShellIndex.connections),
                ),
              ],
            ),
          ),
          card(
            'Current Model',
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                heading('Current Model', Icons.psychology_outlined),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: const Color(0xff7136c8),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Text(
                        'A',
                        style: Theme.of(context).textTheme.metricValue,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        state.activeBrain?.model ?? 'No Active Brain',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(state.activeBrain?.providerId ?? 'Not configured'),
                kv('Requests (today)', 'Not reported'),
                kv('Context Used', 'Not reported'),
                kv('Cost (est.)', 'Not reported'),
                link(
                  context,
                  'Change model',
                  () => onGoTo(
                    ShellIndex.settings,
                    settingsCategory: 'Model Providers',
                  ),
                ),
              ],
            ),
          ),
          card(
            'Sandbox & permissions',
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                heading('Sandbox & permissions', Icons.shield_outlined, mint),
                const SizedBox(height: 6),
                const Text('Sandbox Mode · Not reported'),
                const SizedBox(height: 4),
                Text(
                  'Execution isolation status unavailable',
                  style: Theme.of(context).textTheme.keyValue,
                ),
                link(
                  context,
                  'Manage Permissions',
                  () => onGoTo(
                    ShellIndex.settings,
                    settingsCategory: 'Capabilities',
                  ),
                ),
              ],
            ),
          ),
          card(
            'Tools & Skills',
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                heading('Tools & Skills', Icons.extension_outlined),
                const SizedBox(height: 6),
                Text(
                  '✓ ${state.capabilities.where((c) => c.isUsable).length} tools enabled',
                  style: Theme.of(context).textTheme.keyValue
                      .copyWith(color: mint),
                ),
                const SizedBox(height: 4),
                const Text('◉ Installed skills: Not reported'),
                link(
                  context,
                  'Manage Tools & Skills',
                  () => onGoTo(
                    ShellIndex.settings,
                    settingsCategory: 'Capabilities',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
