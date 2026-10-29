import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../core/api.dart';
import 'model_explanation.dart';
import '../core/session.dart';
import '../ui/kit.dart';

class ScanPage extends StatefulWidget {
  const ScanPage({super.key});
  @override
  State<ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<ScanPage> {
  final link = TextEditingController();
  bool busy = false;
  double? progress;
  CancelToken? cancel;
  String? error;
  Json? job;
  @override
  void dispose() {
    link.dispose();
    cancel?.cancel();
    super.dispose();
  }

  Future<void> execute(Future<Json> Function() task) async {
    setState(() {
      busy = true;
      error = null;
      progress = null;
    });
    try {
      final result = await task();
      if (mounted) {
        setState(() => job = result);
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ScanProgress(result['id'].toString()),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = AppScope.of(context).t(Api.errorText(e)));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> upload() async {
    final app = AppScope.of(context);
    final chosen = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: [
        'jpg',
        'jpeg',
        'png',
        'webp',
        'mp4',
        'mov',
        'avi',
        'mkv',
        'webm',
      ],
    );
    if (chosen == null) return;
    final f = chosen;
    final size = await f.length() ?? 0;
    final image = [
      'jpg',
      'jpeg',
      'png',
      'webp',
    ].contains(f.extension?.toLowerCase());
    if (size > (image ? 20 * 1024 * 1024 : 50000000)) {
      if (mounted) {
        setState(
          () => error = app.t(
            image
                ? 'Maximum image size is 20 MiB.'
                : 'Maximum video size is 50 MB.',
          ),
        );
      }
      return;
    }
    if (size == 0) {
      if (mounted) setState(() => error = app.t('The uploaded file is empty.'));
      return;
    }
    await execute(() async {
      cancel = CancelToken();
      final MultipartFile file;
      if (f.path != null) {
        file = await MultipartFile.fromFile(f.path!, filename: f.name);
      } else {
        file = MultipartFile.fromStream(
          () => f.readAsByteStream(),
          size,
          filename: f.name,
        );
      }

      return app.api.upload(
        '/scans/upload',
        file,
        cancelToken: cancel,
        progress: (sent, total) {
          if (mounted) {
            setState(() => progress = total > 0 ? sent / total : null);
          }
        },
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return PageBody(
      children: [
        PageTitle(
          app.t('Check a file', 'ফাইল যাচাই করুন'),
          subtitle: app.t(
            'Upload an image or video for a private analysis.',
            'ব্যক্তিগতভাবে বিশ্লেষণ করতে ছবি বা ভিডিও আপলোড করুন।',
          ),
        ),
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                height: 100,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary
                      .withValues(alpha: .08),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  Icons.upload_file_outlined,
                  size: 46,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                app.t('Images & videos', 'ছবি ও ভিডিও'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Muted(
                app.t(
                  'JPG, PNG, WebP · 20 MiB\nMP4, MOV, AVI, MKV, WebM · 50 MB',
                  'JPG, PNG, WebP · ২০ MiB\nMP4, MOV, AVI, MKV, WebM · ৫০ MB',
                ),
              ),
              const SizedBox(height: 18),
              BusyButton(
                app.t('Choose file', 'ফাইল বেছে নিন'),
                busy: busy,
                onPressed: upload,
                icon: Icons.add,
              ),
              if (busy) ...[
                const SizedBox(height: 14),
                LinearProgressIndicator(value: progress),
                TextButton(
                  onPressed: () => cancel?.cancel(),
                  child: Text(app.t('Cancel upload', 'আপলোড বাতিল করুন')),
                ),
              ],
              const SizedBox(height: 16),
              Muted(
                app.t(
                  'Processed in your private DeepShield inference service. Image analysis is experimental; the model was trained on video.',
                  'DeepShield-এর private inference service-এ বিশ্লেষণ হয়। মডেলটি ভিডিওতে প্রশিক্ষিত; ছবির বিশ্লেষণ পরীক্ষামূলক।',
                ),
              ),
            ],
          ),
        ),
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                app.t('Public video link', 'পাবলিক ভিডিও লিংক'),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: link,
                keyboardType: TextInputType.url,
                decoration: InputDecoration(
                  labelText: app.t('Video URL', 'ভিডিওর লিংক'),
                  hintText: 'https://...',
                ),
              ),
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed: busy
                    ? null
                    : () {
                        if (Uri.tryParse(link.text.trim())?.scheme != 'https') {
                          setState(
                            () => error = app.t(
                              'Enter an HTTPS video link.',
                              'HTTPS ভিডিও লিংক দিন।',
                            ),
                          );
                          return;
                        }
                        execute(
                          () async => object(
                            await app.api.post('/scans/link', {
                              'url': link.text.trim(),
                            }),
                          ),
                        );
                      },
                icon: const Icon(Icons.link),
                label: Text(app.t('Analyze link', 'লিংক যাচাই করুন')),
              ),
            ],
          ),
        ),
        if (error != null) Notice(error!, error: true),
        if (job != null)
          ItemRow(
            app.t('Last scan', 'সর্বশেষ স্ক্যান'),
            subtitle: job!['source_name']?.toString(),
            onTap: () => openPage(
              context,
              app.t('Scan status', 'স্ক্যানের অবস্থা'),
              ScanProgress('${job!['id']}'),
            ),
          ),
        TextButton.icon(
          onPressed: () => openPage(
            context,
            app.t('Sample library', 'নমুনা ভিডিও'),
            const PresetsPage(),
          ),
          icon: const Icon(Icons.video_library_outlined),
          label: Text(app.t('Try a sample', 'নমুনা দিয়ে দেখুন')),
        ),
      ],
    );
  }
}

class ScanProgress extends StatefulWidget {
  final String id;
  const ScanProgress(this.id, {super.key});
  @override
  State<ScanProgress> createState() => _ScanProgressState();
}

class _ScanProgressState extends State<ScanProgress> {
  Timer? timer;
  Json? job;
  String? error;
  bool inFlight = false;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (timer == null) {
      poll();
      timer = Timer.periodic(const Duration(seconds: 3), (_) => poll());
    }
  }

  Future<void> poll() async {
    if (inFlight) return;
    inFlight = true;
    try {
      final result = object(
        await AppScope.of(context).api.get('/scans/${widget.id}'),
      );
      if (mounted) {
        setState(() {
          job = result;
          error = null;
        });
      }
      if (['completed', 'failed'].contains(result['state'])) timer?.cancel();
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      inFlight = false;
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final r = object(job?['result']);
    return Scaffold(
      appBar: AppBar(title: Text(app.t('Scan result', 'স্ক্যানের ফলাফল'))),
      body: r.isNotEmpty
          ? ResultPage(r)
          : PageBody(
              children: [
                PageTitle(app.t('Analysis status', 'বিশ্লেষণের অবস্থা')),
                Panel(
                  child: Column(
                    children: [
                      if (job?['state'] != 'failed')
                        const StatusArt(StatusMotion.scan, size: 120),
                      const SizedBox(height: 20),
                      Text(app.t('${job?['state'] ?? 'Loading…'}')),
                      const SizedBox(height: 12),
                      Muted(
                        app.t(
                          '${job?['message'] ?? 'Your scan will also appear in History.'}',
                        ),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        '${job?['source_name'] ?? ''}',
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
                if (error != null) ...[
                  Notice(app.t(error!), error: true),
                  OutlinedButton(
                    onPressed: poll,
                    child: Text(app.t('Try again')),
                  ),
                ],
              ],
            ),
    );
  }
}

class PresetsPage extends StatefulWidget {
  const PresetsPage({super.key});
  @override
  State<PresetsPage> createState() => _PresetsPageState();
}

class _PresetsPageState extends State<PresetsPage> {
  bool busy = false;
  String? error;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/detector/presets',
      builder: (data, reload) => PageBody(
        children: [
          if (error != null) Notice(app.t(error!), error: true),
          ...objects(data is List ? data : object(data)['presets']).map(
            (p) => Panel(
              child: ItemRow(
                '${p['title']}',
                icon: Icons.play_circle_outline,
                subtitle: app.t('${p['category'] ?? ''}'),
                trailing: busy ? const CircularProgressIndicator() : null,
                onTap: busy
                    ? null
                    : () async {
                        setState(() => busy = true);
                        try {
                          final r = object(
                            await app.api.post(
                              '/detector/analyze-preset/${p['id']}',
                            ),
                          );
                          if (context.mounted) {
                            openPage(
                              context,
                              app.t('Result', 'ফলাফল'),
                              ResultPage(r),
                            );
                          }
                        } catch (e) {
                          if (mounted) setState(() => error = Api.errorText(e));
                        } finally {
                          if (mounted) setState(() => busy = false);
                        }
                      },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});
  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  String query = '', filter = 'all';
  int page = 0;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/scans',
      builder: (data, reload) => RemoteView(
        '/profile',
        builder: (profile, refresh) {
          final jobs = objects(data),
              linked = jobs.map((r) => r['result_id']).toSet();
          final all = <Json>[
            ...jobs,
            ...objects(object(profile)['detections'])
                .where((r) => !linked.contains(r['id']))
                .map((r) => {...r, 'recordOnly': true, 'state': 'completed'}),
          ];
          all.sort(
            (a, b) => '${b['created_at']}'.compareTo('${a['created_at']}'),
          );
          final rows = all
              .where(
                (r) =>
                    '${r['source_name']}'.toLowerCase().contains(
                      query.toLowerCase(),
                    ) &&
                    (filter == 'all' ||
                        (filter == 'guard'
                            ? '${r['source_name']}'.startsWith(
                                'Android Live Guard:',
                              )
                            : r['recordOnly'] != true)),
              )
              .toList();
          void refreshAll() {
            reload();
            refresh();
          }

          return PageBody(
            children: [
              PageTitle(app.t('Scan history', 'স্ক্যানের ইতিহাস')),
              TextField(
                decoration: InputDecoration(
                  labelText: app.t('Search scans', 'স্ক্যান খুঁজুন'),
                  prefixIcon: const Icon(Icons.search),
                ),
                onChanged: (v) => setState(() {
                  query = v;
                  page = 0;
                }),
              ),
              Wrap(
                spacing: 8,
                children: ['all', 'guard', 'uploads']
                    .map(
                      (f) => ChoiceChip(
                        label: Text(
                          app.t(
                            f == 'all'
                                ? 'All'
                                : f == 'guard'
                                ? 'Live Guard'
                                : 'Uploads & links',
                            f == 'all'
                                ? 'সব'
                                : f == 'guard'
                                ? 'Live Guard'
                                : 'আপলোড ও লিংক',
                          ),
                        ),
                        selected: filter == f,
                        onSelected: (_) => setState(() {
                          filter = f;
                          page = 0;
                        }),
                      ),
                    )
                    .toList(),
              ),
              if (rows.isEmpty)
                EmptyState(
                  app.t('No scans yet', 'এখনও স্ক্যান করেননি'),
                  detail: app.t(
                    'Uploads, Live Guard and sample results appear here.',
                    'আপলোড, Live Guard ও নমুনা বিশ্লেষণের ফল এখানে দেখা যাবে।',
                  ),
                ),
              ...rows
                  .skip(page * 12)
                  .take(12)
                  .map(
                    (r) => Panel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          StatusBadge(app.t('${r['state']}')),
                          const SizedBox(height: 12),
                          Text(
                            '${r['source_name']}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          if (r['verdict'] != null)
                            Text(
                              '${app.t('${r['verdict']}')} · ${number(r['confidence']).toStringAsFixed(1)}%',
                            ),
                          const SizedBox(height: 8),
                          Muted(dateLabel(r['created_at'])),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 10,
                            children: [
                              OutlinedButton(
                                onPressed: () => r['recordOnly'] == true
                                    ? openPage(
                                        context,
                                        app.t('Result'),
                                        RemoteView(
                                          '/profile/detections/${r['id']}',
                                          builder: (d, _) =>
                                              ResultPage(object(d)),
                                        ),
                                      )
                                    : Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) =>
                                              ScanProgress('${r['id']}'),
                                        ),
                                      ),
                                child: Text(app.t('View', 'দেখুন')),
                              ),
                              if (![
                                'processing',
                                'downloading',
                              ].contains(r['state']))
                                IconButton(
                                  tooltip: app.t(
                                    'Delete scan',
                                    'স্ক্যান ডিলিট করুন',
                                  ),
                                  icon: const Icon(Icons.delete_outline),
                                  onPressed: () async {
                                    if (!await confirmAction(
                                      context,
                                      app.t(
                                        'Delete this scan?',
                                        'স্ক্যানটি ডিলিট করবেন?',
                                      ),
                                      app.t(
                                        'The file and saved result will be permanently removed.',
                                        'ফাইল ও সংরক্ষিত ফলাফল স্থায়ীভাবে ডিলিট হবে।',
                                      ),
                                      destructive: true,
                                    )) {
                                      return;
                                    }
                                    try {
                                      await app.api.delete(
                                        r['recordOnly'] == true
                                            ? '/profile/detections/${r['id']}'
                                            : '/scans/${r['id']}',
                                      );
                                      refreshAll();
                                    } catch (e) {
                                      if (context.mounted) {
                                        snack(context, app.t(Api.errorText(e)));
                                      }
                                    }
                                  },
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
              if (rows.length > 12)
                Row(
                  children: [
                    IconButton(
                      tooltip: app.t('Previous page'),
                      onPressed: page == 0
                          ? null
                          : () => setState(() => page--),
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Expanded(
                      child: Text(
                        '${page + 1} / ${(rows.length / 12).ceil()}',
                        textAlign: TextAlign.center,
                      ),
                    ),
                    IconButton(
                      tooltip: app.t('Next page'),
                      onPressed: (page + 1) * 12 >= rows.length
                          ? null
                          : () => setState(() => page++),
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
            ],
          );
        },
      ),
    );
  }
}

class ResultPage extends StatefulWidget {
  final Json result;
  const ResultPage(this.result, {super.key});
  @override
  State<ResultPage> createState() => _ResultPageState();
}

class _ResultPageState extends State<ResultPage> {
  int selected = 0;
  @override
  void initState() {
    super.initState();
    selected = number(widget.result['focus_frame']).toInt();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context), r = widget.result;
    final frames = objects(r['frame_details']);
    final frame = frames.isEmpty
        ? <String, dynamic>{}
        : frames[selected.clamp(0, frames.length - 1)];
    final pct = number(r['confidence_percentage']);
    return PageBody(
      children: [
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StatusBadge(
                app.t(
                  r['media_type'] == 'image'
                      ? 'Experimental image result'
                      : 'Trained detector result',
                ),
              ),
              const SizedBox(height: 18),
              Text(
                app.t(
                  r['verdict'] == 'Fake'
                      ? 'The model chose Fake'
                      : 'The model chose Real',
                  r['verdict'] == 'Fake'
                      ? 'মডেলের মতে: নকল হতে পারে'
                      : 'মডেলের মতে: আসল',
                ),
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 16),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  app.t('See the model scores', 'মডেলের স্কোর দেখুন'),
                ),
                children: [
                  Text(
                    '${pct.toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 48,
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                  Muted(
                    '${app.t('Model score for', 'মডেলের স্কোর:')} ${app.t('${r['verdict']}')}',
                  ),
                  const SizedBox(height: 18),
                  LinearProgressIndicator(
                    value: number(r['fake_probability']).clamp(0, 1),
                    minHeight: 9,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Fake ${(number(r['fake_probability']) * 100).toStringAsFixed(1)}% · Real ${((1 - number(r['fake_probability'])) * 100).toStringAsFixed(1)}%',
                  ),
                ],
              ),
            ],
          ),
        ),
        Notice(
          app.t(
            'This score describes the model’s preference. It is not a verified chance that the file is fake or real. Check the original source before acting.',
          ),
        ),
        ModelExplanation(r),
        if (r['media_type'] == 'image')
          Notice(
            app.t(
              'Image analysis is experimental. A single face is repeated across 16 inputs; motion evidence is absent.',
              'ছবির বিশ্লেষণ পরীক্ষামূলক। একই মুখ ১৬টি ইনপুটে ব্যবহার হয়; গতির তথ্য থাকে না।',
            ),
          ),
        ExpansionTile(
          title: Text(app.t('Inspect the heatmap', 'Heatmap দেখুন')),
          children: [
            if (frame.isNotEmpty) ...[
              PageTitle(
                app.t(
                  'Where the model is sensitive',
                  'মডেল কোন অংশে বেশি সাড়া দিয়েছে',
                ),
              ),
              HeatmapPanel(frame, key: ValueKey(selected)),
              if (frames.length > 1)
                Panel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        app.t('Sampled moments', 'ভিডিওর নির্বাচিত মুহূর্ত'),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: List.generate(
                          frames.length,
                          (i) => ChoiceChip(
                            label: Text('${i + 1}'),
                            selected: selected == i,
                            onSelected: (_) => setState(() => selected = i),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Muted(
                        '${app.t('Selected moment:')} ${frame['timestamp'] ?? frame['source_frame']}',
                      ),
                    ],
                  ),
                ),
            ] else
              EmptyState(app.t('Visual explanation unavailable')),
          ],
        ),
        ExpansionTile(
          title: Text(app.t('Model and analysis details')),
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${r['model_name'] ?? ''}'),
                  Text('ID: ${r['model_id'] ?? '—'}'),
                  Text('Epoch: ${r['checkpoint_epoch'] ?? '—'}'),
                  ...((r['detected_artifacts'] as List?) ?? []).map(
                    (s) => Text(app.t('$s')),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class HeatmapPanel extends StatefulWidget {
  final Json frame;
  const HeatmapPanel(this.frame, {super.key});
  @override
  State<HeatmapPanel> createState() => _HeatmapPanelState();
}

class _HeatmapPanelState extends State<HeatmapPanel> {
  double opacity = .85;
  bool enhanced = false;
  int mode = 1;
  Uint8List? overlay;
  String? error;
  @override
  void initState() {
    super.initState();
    enhance();
  }

  Future<void> enhance() async {
    try {
      final source = base64Decode(
        Api.normalizeImage('${widget.frame['overlay']}'),
      );
      if (!enhanced) {
        if (mounted) setState(() => overlay = source);
        return;
      }
      final codec = await ui.instantiateImageCodec(source);
      final f = await codec.getNextFrame();
      final bytes = await f.image.toByteData(
        format: ui.ImageByteFormat.rawStraightRgba,
      );
      final rgba = bytes!.buffer.asUint8List();
      final nonzero = <int>[];
      for (int i = 3; i < rgba.length; i += 4) {
        if (rgba[i] > 0) nonzero.add(rgba[i]);
      }
      nonzero.sort();
      final scale = nonzero.isEmpty
          ? 255
          : nonzero[(nonzero.length * .98).floor().clamp(
              0,
              nonzero.length - 1,
            )];
      for (int i = 3; i < rgba.length; i += 4) {
        final a = rgba[i];
        if (a > 0) rgba[i] = (math.sqrt((a / scale).clamp(0, 1)) * 255).round();
      }
      final completer = Completer<ui.Image>();
      ui.decodeImageFromPixels(
        rgba,
        f.image.width,
        f.image.height,
        ui.PixelFormat.rgba8888,
        completer.complete,
      );
      final image = await completer.future;
      final png = await image.toByteData(format: ui.ImageByteFormat.png);
      if (mounted) setState(() => overlay = png!.buffer.asUint8List());
      image.dispose();
      f.image.dispose();
      codec.dispose();
    } catch (_) {
      if (mounted) {
        setState(
          () => error = AppScope.of(
            context,
          ).t('Could not render this heatmap.', 'হিটম্যাপটি দেখা যাচ্ছে না।'),
        );
      }
    }
  }

  Widget picture() => AspectRatio(
    aspectRatio: 1,
    child: Stack(
      fit: StackFit.expand,
      children: [
        if (mode != 2)
          DataImage('${widget.frame['image']}')
        else
          const ColoredBox(color: Color(0xff121514)),
        if (mode != 0 && overlay != null)
          Opacity(
            opacity: opacity,
            child: Image.memory(
              overlay!,
              fit: BoxFit.contain,
              gaplessPlayback: true,
            ),
          ),
      ],
    ),
  );
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: List.generate(
              3,
              (i) => ChoiceChip(
                label: Text(
                  app.t(
                    ['Original', 'Overlay', 'Heatmap'][i],
                    ['আসল ছবি', 'ছবির ওপর', 'হিটম্যাপ'][i],
                  ),
                ),
                selected: mode == i,
                onSelected: (_) => setState(() => mode = i),
              ),
            ),
          ),
          const SizedBox(height: 16),
          ClipRRect(borderRadius: BorderRadius.circular(16), child: picture()),
          if (error != null) Notice(error!, error: true),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.circle, color: Colors.blue, size: 14),
              const SizedBox(width: 6),
              Text(app.t('Lower', 'কম')),
              const Spacer(),
              Text(app.t('Higher sensitivity', 'বেশি সাড়া')),
              const SizedBox(width: 6),
              const Icon(Icons.circle, color: Colors.red, size: 14),
            ],
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(app.t('Enhance visibility', 'আরও স্পষ্টভাবে দেখুন')),
            subtitle: Text(
              app.t(
                'Visual contrast only; model scores stay unchanged.',
                'শুধু ছবির কনট্রাস্ট বদলায়; মডেলের স্কোর বদলায় না।',
              ),
            ),
            value: enhanced,
            onChanged: (v) {
              setState(() => enhanced = v);
              enhance();
            },
          ),
          Text(app.t('Heatmap opacity', 'হিটম্যাপের দৃশ্যমানতা')),
          Slider(
            value: opacity,
            min: .1,
            max: 1,
            divisions: 18,
            label: '${(opacity * 100).round()}%',
            onChanged: (v) => setState(() => opacity = v),
          ),
          OutlinedButton.icon(
            onPressed: () => showDialog(
              context: context,
              builder: (c) => Dialog.fullscreen(
                child: Scaffold(
                  appBar: AppBar(
                    title: Text(app.t('Inspect heatmap', 'হিটম্যাপ দেখুন')),
                    leading: IconButton(
                      tooltip: app.t('Close'),
                      onPressed: () => Navigator.pop(c),
                      icon: const Icon(Icons.close),
                    ),
                  ),
                  body: Center(
                    child: InteractiveViewer(
                      minScale: 1,
                      maxScale: 5,
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 800),
                        child: picture(),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            icon: const Icon(Icons.zoom_in),
            label: Text(app.t('Enlarge & zoom', 'বড় করে দেখুন')),
          ),
          const SizedBox(height: 12),
          Muted(
            app.t(
              'Highlighted areas show sensitivity, not proof of manipulation.',
              'রঙিন অংশ মডেলের সাড়া বোঝায়; এটি বিকৃতির প্রমাণ নয়।',
            ),
          ),
        ],
      ),
    );
  }
}
