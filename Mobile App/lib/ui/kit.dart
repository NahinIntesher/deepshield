import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';

const green = Color(0xff185c3d);
ThemeData shieldTheme(bool dark, bool bn) {
  final scheme =
      ColorScheme.fromSeed(
        seedColor: green,
        brightness: dark ? Brightness.dark : Brightness.light,
      ).copyWith(
        primary: dark ? const Color(0xffa7d4b2) : green,
        surface: dark ? const Color(0xff1a1c20) : const Color(0xffffffff),
        onSurface: dark ? const Color(0xfff0f2f5) : const Color(0xff183326),
        outline: dark ? const Color(0xff535b64) : const Color(0xffc5d3c8),
        onSurfaceVariant: dark
            ? const Color(0xffb4bac4)
            : const Color(0xff53665a),
      );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'Quicksand',
    fontFamilyFallback: const ['BalooDa2', 'Quicksand'],
    scaffoldBackgroundColor: dark
        ? const Color(0xff101113)
        : const Color(0xfff5f7f4),
    textTheme: TextTheme(
      bodyLarge: const TextStyle(fontSize: 16, height: 1.5),
      bodyMedium: const TextStyle(fontSize: 15, height: 1.45),
      titleLarge: const TextStyle(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        height: 1.25,
      ),
      titleMedium: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
      headlineMedium: const TextStyle(
        fontSize: 26,
        fontWeight: FontWeight.w700,
        height: 1.18,
      ),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? const Color(0xff101113) : const Color(0xfff5f7f4),
      scrolledUnderElevation: 0,
      centerTitle: false,
    ),
    dividerTheme: DividerThemeData(
      color: scheme.outline.withValues(alpha: .2),
      space: 28,
    ),
    cardTheme: CardThemeData(
      elevation: 1,
      shadowColor: Colors.black.withValues(alpha: dark ? .16 : .06),
      surfaceTintColor: Colors.transparent,
      color: scheme.surface,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: dark ? const Color(0xff393d45) : const Color(0xffd8e3d7),
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      floatingLabelBehavior: FloatingLabelBehavior.always,
      labelStyle: TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        color: scheme.onSurfaceVariant,
      ),
      fillColor: scheme.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 17),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: scheme.outline.withValues(alpha: .4)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: green,
        foregroundColor: Colors.white,
        minimumSize: const Size(48, 52),
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(48, 50),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
    ),
    navigationBarTheme: const NavigationBarThemeData(
      height: 76,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
    ),
  );
}

/// The same shield, play mark and mint check paths as the website Logo.tsx.
class BrandMark extends StatelessWidget {
  final double height;
  const BrandMark({super.key, this.height = 38});
  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: CustomPaint(
      size: Size(height * 40 / 44, height),
      painter: _BrandPainter(Theme.of(context).colorScheme.onSurface),
    ),
  );
}

class _BrandPainter extends CustomPainter {
  final Color color;
  _BrandPainter(this.color);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 40, size.height / 44);
    final fill = Path()
      ..moveTo(20, 2)
      ..lineTo(36, 8)
      ..lineTo(36, 21)
      ..cubicTo(36, 31, 27, 38, 20, 42)
      ..cubicTo(13, 38, 4, 31, 4, 21)
      ..lineTo(4, 8)
      ..close();
    canvas.drawPath(fill, Paint()..color = color.withValues(alpha: .16));
    final border = Path()
      ..moveTo(20, 3)
      ..lineTo(35, 9)
      ..lineTo(35, 21)
      ..cubicTo(35, 30, 27, 37, 20, 41)
      ..cubicTo(13, 37, 5, 30, 5, 21)
      ..lineTo(5, 9)
      ..close();
    canvas.drawPath(
      border,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    canvas.drawPath(
      Path()
        ..moveTo(16, 14)
        ..lineTo(28, 22)
        ..lineTo(16, 30)
        ..close(),
      Paint()..color = color,
    );
    canvas.drawPath(
      Path()
        ..moveTo(24, 28)
        ..lineTo(27, 31)
        ..lineTo(34, 23),
      Paint()
        ..color = const Color(0xff8ce7b3)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _BrandPainter oldDelegate) =>
      oldDelegate.color != color;
}

class Brand extends StatelessWidget {
  final bool compact;
  final bool showName;
  const Brand({super.key, this.compact = false, this.showName = true});
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      BrandMark(height: compact ? 36 : 42),
      if (showName) const SizedBox(width: 9),
      if (showName)
        const Text(
          'DeepShield',
          style: TextStyle(
            fontSize: 21,
            fontWeight: FontWeight.w700,
            letterSpacing: -.7,
          ),
        ),
    ],
  );
}

class PageBody extends StatelessWidget {
  final List<Widget> children;
  const PageBody({super.key, required this.children});
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    key: const PageStorageKey('page-scroll'),
    padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
    child: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1100),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children
              .expand((e) => [e, const SizedBox(height: 20)])
              .toList(),
        ),
      ),
    ),
  );
}

class Panel extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final Color? color;
  const Panel({
    super.key,
    required this.child,
    this.color,
    this.padding = const EdgeInsets.all(20),
  });
  @override
  Widget build(BuildContext context) => Card(
    color: color,
    child: Padding(padding: padding, child: child),
  );
}

class ScanHero extends StatelessWidget {
  final VoidCallback onScan;
  final VoidCallback onHistory;
  const ScanHero({super.key, required this.onScan, required this.onHistory});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context),
        dark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: dark ? const Color(0xff203d2d) : const Color(0xff164d36),
        borderRadius: BorderRadius.circular(24),
      ),
      child: LayoutBuilder(
        builder: (context, size) {
          final primary = FilledButton.icon(
            onPressed: onScan,
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xfff4faf5),
              foregroundColor: const Color(0xff164d36),
            ),
            icon: const Icon(Icons.document_scanner_outlined),
            label: Text(app.t('Start a scan', 'স্ক্যান শুরু করুন')),
          );
          final history = OutlinedButton.icon(
            onPressed: onHistory,
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: const BorderSide(color: Colors.white54),
            ),
            icon: const Icon(Icons.history),
            label: Text(app.t('Scan history', 'স্ক্যান হিস্ট্রি')),
          );
          final content = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                app.t('MEDIA CHECK', 'মিডিয়া যাচাই'),
                style: const TextStyle(
                  color: Color(0xffd1e2d7),
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                app.t('Check a photo or video', 'ছবি বা ভিডিও যাচাই করুন'),
                style: Theme.of(context).textTheme.headlineMedium
                    ?.copyWith(color: Colors.white),
              ),
              const SizedBox(height: 14),
              Text(
                app.t(
                  'Upload a file, review the result and see what affected the answer.',
                  'ফাইল দিন, ফলাফল দেখুন এবং কোন তথ্য ফলকে প্রভাবিত করেছে বুঝে নিন।',
                ),
                style: const TextStyle(
                  color: Color(0xffd1e2d7),
                  fontSize: 16,
                  height: 1.6,
                ),
              ),
              const SizedBox(height: 24),
              if (size.maxWidth < 420)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [primary, const SizedBox(height: 12), history],
                )
              else
                Wrap(spacing: 12, runSpacing: 12, children: [primary, history]),
            ],
          );
          return Row(
            children: [
              Expanded(child: content),
              if (size.maxWidth > 650)
                Padding(
                  padding: const EdgeInsets.only(left: 28),
                  child: Container(
                    width: 128,
                    height: 128,
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.white24),
                      borderRadius: BorderRadius.circular(30),
                    ),
                    child: const Icon(
                      Icons.document_scanner_outlined,
                      color: Color(0xffd9efde),
                      size: 72,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class PageTitle extends StatelessWidget {
  final String title;
  final String? subtitle;
  const PageTitle(this.title, {super.key, this.subtitle});
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title, style: Theme.of(context).textTheme.headlineMedium),
      if (subtitle != null) ...[const SizedBox(height: 8), Muted(subtitle!)],
    ],
  );
}

class Muted extends StatelessWidget {
  final String text;
  final Color? color;
  const Muted(this.text, {super.key, this.color});
  @override
  Widget build(BuildContext context) => Text(
    text,
    style: TextStyle(
      color: color ?? Theme.of(context).colorScheme.onSurfaceVariant,
      height: 1.6,
    ),
  );
}

class StatusBadge extends StatelessWidget {
  final String text;
  const StatusBadge(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.primary.withValues(alpha: .12),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      text,
      style: TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        color: Theme.of(context).colorScheme.primary,
      ),
    ),
  );
}

class Notice extends StatelessWidget {
  final String text;
  final bool error;
  const Notice(this.text, {super.key, this.error = false});
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: error
            ? Theme.of(context).colorScheme.errorContainer
            : Theme.of(context).colorScheme.primary.withValues(alpha: .10),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            error ? Icons.error_outline : Icons.info_outline,
            color: error
                ? Theme.of(context).colorScheme.onErrorContainer
                : Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: error
                    ? Theme.of(context).colorScheme.onErrorContainer
                    : Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class BusyButton extends StatelessWidget {
  final String label;
  final bool busy;
  final VoidCallback? onPressed;
  final IconData? icon;
  const BusyButton(
    this.label, {
    super.key,
    this.busy = false,
    this.onPressed,
    this.icon,
  });
  @override
  Widget build(BuildContext context) => FilledButton(
    onPressed: busy ? null : onPressed,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (busy) ...[
          const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          const SizedBox(width: 10),
        ] else if (icon != null) ...[
          Icon(icon, size: 20),
          const SizedBox(width: 10),
        ],
        Flexible(child: Text(label, textAlign: TextAlign.center)),
      ],
    ),
  );
}

class EmptyState extends StatelessWidget {
  final String title;
  final String? detail;
  final IconData icon;
  const EmptyState(
    this.title, {
    super.key,
    this.detail,
    this.icon = Icons.inbox_outlined,
  });
  @override
  Widget build(BuildContext context) => Panel(
    child: Column(
      children: [
        Icon(icon, size: 40, color: Theme.of(context).colorScheme.primary),
        const SizedBox(height: 14),
        Text(
          title,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (detail != null) ...[const SizedBox(height: 8), Muted(detail!)],
      ],
    ),
  );
}

class RemoteView extends StatefulWidget {
  final String path;
  final Widget Function(dynamic data, VoidCallback reload) builder;
  const RemoteView(this.path, {super.key, required this.builder});
  @override
  State<RemoteView> createState() => _RemoteViewState();
}

class _RemoteViewState extends State<RemoteView> {
  Future<dynamic>? pending;
  void reload() =>
      setState(() => pending = AppScope.of(context).api.get(widget.path));
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    pending ??= AppScope.of(context).api.get(widget.path);
  }

  @override
  void didUpdateWidget(covariant RemoteView old) {
    super.didUpdateWidget(old);
    if (old.path != widget.path) {
      pending = AppScope.of(context).api.get(widget.path);
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
    future: pending,
    builder: (context, snapshot) {
      final app = AppScope.of(context);
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(
          child: Padding(
            padding: EdgeInsets.all(40),
            child: CircularProgressIndicator(),
          ),
        );
      }
      if (snapshot.hasError) {
        return PageBody(
          children: [
            Notice(app.t(Api.errorText(snapshot.error!)), error: true),
            OutlinedButton.icon(
              onPressed: reload,
              icon: const Icon(Icons.refresh),
              label: Text(app.t('Try again', 'আবার চেষ্টা করুন')),
            ),
          ],
        );
      }
      return RefreshIndicator(
        onRefresh: () async {
          reload();
          await pending;
        },
        child: widget.builder(snapshot.data, reload),
      );
    },
  );
}

class MetricGrid extends StatelessWidget {
  final List<(String, String, IconData)> values;
  const MetricGrid(this.values, {super.key});
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, c) {
      final count = c.maxWidth < 260
          ? 1
          : c.maxWidth < 750
          ? 2
          : 4;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: values
            .map(
              (v) => SizedBox(
                width: (c.maxWidth - (count - 1) * 12) / count,
                child: Panel(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        v.$3,
                        color: Theme.of(context).colorScheme.primary,
                        size: 22,
                      ),
                      const SizedBox(height: 14),
                      Text(v.$2, style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 3),
                      Muted(v.$1),
                    ],
                  ),
                ),
              ),
            )
            .toList(),
      );
    },
  );
}

class ItemRow extends StatelessWidget {
  final String title;
  final String? subtitle;
  final IconData icon;
  final VoidCallback? onTap;
  final Widget? trailing;
  const ItemRow(
    this.title, {
    super.key,
    this.subtitle,
    this.icon = Icons.chevron_right,
    this.onTap,
    this.trailing,
  });
  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 7),
    leading: Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primary.withValues(alpha: .10),
        borderRadius: BorderRadius.circular(13),
      ),
      child: Icon(icon, color: Theme.of(context).colorScheme.primary, size: 22),
    ),
    title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
    subtitle: subtitle == null ? null : Text(subtitle!),
    trailing:
        trailing ??
        (onTap == null ? null : const Icon(Icons.arrow_forward_ios, size: 16)),
    onTap: onTap,
  );
}

Future<bool> confirmAction(
  BuildContext context,
  String title,
  String body, {
  bool destructive = false,
}) async {
  final app = AppScope.of(context);
  return await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: Text(app.t('Cancel', 'বাতিল')),
            ),
            FilledButton(
              style: destructive
                  ? FilledButton.styleFrom(
                      backgroundColor: Theme.of(c).colorScheme.error,
                    )
                  : null,
              onPressed: () => Navigator.pop(c, true),
              child: Text(app.t('Confirm', 'নিশ্চিত করুন')),
            ),
          ],
        ),
      ) ??
      false;
}

void openPage(BuildContext context, String title, Widget child) =>
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (c) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: child,
        ),
      ),
    );
void snack(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
String dateLabel(dynamic value) {
  final d = DateTime.tryParse('$value')?.toLocal();
  return d == null
      ? '—'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year} · ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}

class DataImage extends StatelessWidget {
  final String? data;
  const DataImage(this.data, {super.key});
  @override
  Widget build(BuildContext context) {
    if (data == null || data!.isEmpty) {
      return const EmptyState(
        'No image available',
        icon: Icons.image_not_supported_outlined,
      );
    }
    try {
      return Image.memory(
        base64Decode(Api.normalizeImage(data!)),
        fit: BoxFit.contain,
        gaplessPlayback: true,
        errorBuilder: (_, e, s) => const Icon(Icons.broken_image_outlined),
      );
    } catch (_) {
      return const Icon(Icons.broken_image_outlined);
    }
  }
}

class BarPanel extends StatelessWidget {
  final String title;
  final List<(String, double)> bars;
  const BarPanel(this.title, this.bars, {super.key});
  @override
  Widget build(BuildContext context) {
    final maximum = bars.fold<double>(1, (m, e) => e.$2 > m ? e.$2 : m);
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 18),
          ...bars.map(
            (b) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(b.$1)),
                      Text(
                        b.$2 == b.$2.roundToDouble()
                            ? '${b.$2.toInt()}'
                            : b.$2.toStringAsFixed(1),
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Semantics(
                    label: '${b.$1}: ${b.$2}',
                    child: LinearProgressIndicator(
                      value: (b.$2 / maximum).clamp(0, 1),
                      minHeight: 9,
                      borderRadius: BorderRadius.circular(9),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
