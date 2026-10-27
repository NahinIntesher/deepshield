import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import 'scans.dart';
import 'live_guard.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/profile',
      builder: (data, reload) {
        final d = object(data),
            u = object(d['user']),
            totals = object(d['totals']),
            requirements = object(d['requirements']);
        return PageBody(
          children: [
            PageTitle(app.t('Dashboard', 'ড্যাশবোর্ড')),
            ScanHero(
              onScan: () => openPage(context, app.t('Scan'), const ScanPage()),
              onHistory: () =>
                  openPage(context, app.t('History'), const HistoryPage()),
            ),
            Panel(
              child: ItemRow(
                'Live Guard',
                subtitle: app.t(
                  'Automatic checks while you watch social videos.',
                  'সোশ্যাল মিডিয়ায় ভিডিও দেখার সময় স্বয়ংক্রিয় যাচাই।',
                ),
                icon: Icons.sensors,
                onTap: () =>
                    openPage(context, 'Live Guard', const LiveGuardPage()),
              ),
            ),
            MetricGrid([
              (
                app.t('Scans', 'স্ক্যান'),
                '${totals['detections'] ?? 0}',
                Icons.document_scanner_outlined,
              ),
              (
                app.t('Lessons completed', 'শেষ করা পাঠ'),
                '${totals['lessons'] ?? 0}/${totals['lesson_count'] ?? 0}',
                Icons.school_outlined,
              ),
              (
                app.t('Practice points', 'চর্চার পয়েন্ট'),
                '${u['score'] ?? 0}',
                Icons.sports_esports_outlined,
              ),
              (
                app.t('Accuracy', 'সঠিক উত্তরের হার'),
                '${number(u['accuracy']).toStringAsFixed(1)}%',
                Icons.track_changes,
              ),
            ]),
            Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    app.t(
                      'Research eligibility',
                      'রিসার্চে অংশ নেওয়ার যোগ্যতা',
                    ),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    u['qualified'] == true
                        ? app.t(
                            'You are eligible for research challenges.',
                            'আপনি রিসার্চ চ্যালেঞ্জে অংশ নিতে পারবেন।',
                          )
                        : app.t(
                            'Reach ${requirements['score']} points and ${requirements['accuracy']}% accuracy.',
                            '${requirements['score']} পয়েন্ট এবং ${requirements['accuracy']}% সঠিক উত্তরের হার অর্জন করুন।',
                          ),
                  ),
                  const SizedBox(height: 16),
                  LinearProgressIndicator(
                    value:
                        (number(u['score']) /
                                number(requirements['score'])
                                    .clamp(1, double.infinity))
                            .clamp(0, 1),
                    minHeight: 8,
                    borderRadius: BorderRadius.circular(8),
                  ),
                ],
              ),
            ),
            ItemRow(
              app.t('Recent scans', 'সাম্প্রতিক স্ক্যান'),
              icon: Icons.history,
              onTap: () =>
                  openPage(context, app.t('History'), const HistoryPage()),
            ),
            ...objects(d['detections'])
                .take(5)
                .map(
                  (r) => Panel(
                    child: ItemRow(
                      '${r['source_name']}',
                      subtitle:
                          '${app.t('${r['verdict']}')} · ${dateLabel(r['created_at'])}',
                      icon: Icons.verified_outlined,
                      onTap: () => openPage(
                        context,
                        app.t('Result'),
                        RemoteView(
                          '/profile/detections/${r['id']}',
                          builder: (v, _) => ResultPage(object(v)),
                        ),
                      ),
                    ),
                  ),
                ),
          ],
        );
      },
    );
  }
}

class LearnPage extends StatelessWidget {
  const LearnPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/profile/lessons',
      builder: (data, reload) => RemoteView(
        '/profile/course',
        builder: (progress, refresh) {
          final completed = objects(progress)
              .where((p) => p['completed'] == true)
              .map((p) => p['lesson_id'])
              .toSet();
          return PageBody(
            children: [
              PageTitle(
                app.t('Learning academy', 'লার্নিং একাডেমি'),
                subtitle: app.t(
                  'Short lessons and a quick check of what you learned.',
                  'ছোট লেসন পড়ুন, তারপর প্রশ্নের উত্তর দিয়ে নিজেকে যাচাই করুন।',
                ),
              ),
              StatusBadge(
                '${completed.length} / ${objects(data).length} ${app.t('completed', 'সম্পূর্ণ')}',
              ),
              ...objects(data).map((lesson) {
                final copy = object(lesson[app.language]);
                return Panel(
                  child: ItemRow(
                    app.t('${copy['title']}'),
                    subtitle:
                        '${copy['time']} · ${completed.contains(lesson['id']) ? app.t('Completed', 'সম্পূর্ণ') : app.t('Start lesson', 'লেসন পড়ুন')}',
                    icon: completed.contains(lesson['id'])
                        ? Icons.check_circle_outline
                        : Icons.menu_book_outlined,
                    onTap: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => Scaffold(
                            appBar: AppBar(
                              title: Text(app.t('${copy['title']}')),
                            ),
                            body: LessonPage(lesson),
                          ),
                        ),
                      );
                      refresh();
                    },
                  ),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}

class LessonPage extends StatefulWidget {
  final Json lesson;
  const LessonPage(this.lesson, {super.key});
  @override
  State<LessonPage> createState() => _LessonPageState();
}

class _LessonPageState extends State<LessonPage> {
  int? choice;
  bool busy = false;
  Json? result;
  String? error;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context),
        copy = object(widget.lesson[app.language]);
    return PageBody(
      children: [
        PageTitle(
          app.t('${copy['title']}'),
          subtitle: app.t('${copy['intro']}'),
        ),
        ...((copy['sections'] as List?) ?? []).map(
          (v) => Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  app.t('${v[0]}'),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                Text(app.t('${v[1]}')),
              ],
            ),
          ),
        ),
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                app.t('Try this approach', 'এভাবে যাচাই করুন'),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              ...((copy['flow'] as List?) ?? []).map(
                (v) => ItemRow(
                  app.t('${v[0]}'),
                  subtitle: app.t('${v[1]}'),
                  icon: Icons.check_circle_outline,
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
                app.t('${copy['question']}'),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              ...List.generate(
                (copy['choices'] as List? ?? []).length,
                (i) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      backgroundColor: choice == i
                          ? Theme.of(context).colorScheme.primaryContainer
                          : null,
                    ),
                    onPressed: busy ? null : () => setState(() => choice = i),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(app.t('${copy['choices'][i]}')),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              BusyButton(
                app.t('Check answer', 'উত্তর যাচাই করুন'),
                busy: busy,
                onPressed: choice == null
                    ? null
                    : () async {
                        setState(() => busy = true);
                        try {
                          final r = object(
                            await app.api.post(
                              '/profile/course/${widget.lesson['id']}',
                              {'choice': choice},
                            ),
                          );
                          if (mounted) {
                            setState(() {
                              result = r;
                              error = null;
                            });
                          }
                        } catch (e) {
                          if (mounted) setState(() => error = Api.errorText(e));
                        } finally {
                          if (mounted) setState(() => busy = false);
                        }
                      },
              ),
              if (result != null) ...[
                const SizedBox(height: 16),
                Notice(
                  result!['correct'] == true
                      ? app.t('${copy['feedback']}')
                      : app.t(
                          'Try another answer.',
                          'আরেকটি উত্তর চেষ্টা করুন।',
                        ),
                  error: result!['correct'] != true,
                ),
              ],
              if (error != null) Notice(app.t(error!), error: true),
            ],
          ),
        ),
      ],
    );
  }
}

class SupportPage extends StatelessWidget {
  const SupportPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/support',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(app.t('Support', 'সাপোর্ট')),
          BusyButton(
            app.t('New request', 'নতুন অনুরোধ'),
            icon: Icons.add,
            onPressed: () async {
              await openForm(
                context,
                title: app.t('Contact support', 'সাপোর্টে লিখুন'),
                fields: [
                  FieldSpec(
                    'subject',
                    app.t('Subject', 'বিষয়'),
                    min: 4,
                    max: 160,
                  ),
                  FieldSpec(
                    'message',
                    app.t('Message', 'বিস্তারিত'),
                    min: 10,
                    max: 3000,
                    lines: 5,
                  ),
                ],
                submit: (v) => app.api.post('/support', v),
              );
              reload();
            },
          ),
          if (objects(data).isEmpty)
            EmptyState(app.t('No support requests', 'কোনো সাপোর্ট অনুরোধ নেই')),
          ...objects(data).map(
            (r) => Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StatusBadge(app.t('${r['status']}')),
                  const SizedBox(height: 12),
                  Text(
                    '${r['subject']}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  Text('${r['message']}'),
                  if ((r['reply'] ?? '').toString().isNotEmpty) ...[
                    const Divider(),
                    Text(
                      app.t('Reply', 'উত্তর'),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text('${r['reply']}'),
                  ],
                  const SizedBox(height: 12),
                  Muted(dateLabel(r['created_at'])),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class NotificationsPage extends StatelessWidget {
  const NotificationsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/notifications',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(app.t('Notifications', 'নোটিফিকেশন')),
          OutlinedButton(
            onPressed: () async {
              try {
                await app.api.post('/notifications/read');
                reload();
              } catch (e) {
                if (context.mounted) snack(context, app.t(Api.errorText(e)));
              }
            },
            child: Text(app.t('Mark all read', 'সব পড়া হয়েছে')),
          ),
          if (objects(data).isEmpty)
            EmptyState(app.t('No new notifications', 'নতুন নোটিফিকেশন নেই')),
          ...objects(data).map(
            (r) => Panel(
              child: ItemRow(
                app.t('${r['title']}'),
                subtitle:
                    '${app.t('${r['message']}')}\n${dateLabel(r['created_at'])}',
                icon: r['read'] == true
                    ? Icons.notifications_none
                    : Icons.notifications_active_outlined,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SubscriptionPage extends StatelessWidget {
  const SubscriptionPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/billing',
      builder: (data, reload) {
        final d = object(data), p = object(d['payment']);
        return PageBody(
          children: [
            PageTitle(app.t('Your plan', 'আপনার প্ল্যান')),
            MetricGrid([
              (
                app.t('Current plan', 'বর্তমান প্ল্যান'),
                app.t('${d['plan']}'),
                Icons.workspace_premium_outlined,
              ),
              (
                app.t('Daily scans remaining', 'আজ বাকি স্ক্যান'),
                '${number(d['limit']) - number(d['used'])}',
                Icons.document_scanner_outlined,
              ),
            ]),
            Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'DeepShield Premium',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '৳${d['price_bdt']} / ${app.t('30 days', '৩০ দিন')}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    app.t(
                      '100 image or video scans per day, CSV export and Browser Companion.',
                      'প্রতিদিন ১০০টি ছবি বা ভিডিও স্ক্যান, CSV export এবং Browser Companion।',
                    ),
                  ),
                  const Divider(),
                  Text(
                    'bKash: ${p['number']}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Muted(
                    app.t(
                      'Send the displayed amount, then submit the transaction ID. The admin will verify it before activation. Never share your PIN or OTP.',
                      'দেখানো টাকা পাঠিয়ে transaction ID দিন। অ্যাডমিন যাচাই করে Premium চালু করবেন। PIN বা OTP কাউকে দেবেন না।',
                    ),
                  ),
                  const SizedBox(height: 18),
                  BusyButton(
                    app.t('Request Premium', 'Premium-এর অনুরোধ'),
                    onPressed: d['plan'] == 'premium'
                        ? null
                        : () async {
                            await openForm(
                              context,
                              title: app.t('Payment details', 'পেমেন্টের তথ্য'),
                              fields: [
                                FieldSpec(
                                  'reference',
                                  app.t(
                                    'bKash transaction ID',
                                    'bKash transaction ID',
                                  ),
                                  min: 6,
                                  max: 40,
                                ),
                                FieldSpec(
                                  'note',
                                  app.t('Payment note', 'পেমেন্টের বিবরণ'),
                                  min: 5,
                                  max: 1000,
                                  lines: 3,
                                ),
                              ],
                              submit: (v) => app.api.post('/billing/request', {
                                ...v,
                                'request_type': 'manual_payment',
                              }),
                            );
                            reload();
                          },
                  ),
                ],
              ),
            ),
            ...objects(d['requests']).map(
              (r) => Panel(
                child: ItemRow(
                  app.t('${r['status']}'),
                  subtitle:
                      '${r['reference']}\n${r['review'] ?? r['note'] ?? ''}\n${dateLabel(r['created_at'])}',
                  icon: Icons.receipt_long_outlined,
                ),
              ),
            ),
            if (d['plan'] == 'premium')
              OutlinedButton.icon(
                icon: const Icon(Icons.download_outlined),
                label: Text(
                  app.t('Export scan history', 'স্ক্যানের ইতিহাস export করুন'),
                ),
                onPressed: () async {
                  try {
                    final csv = await app.api.request('/billing/export/scans');
                    await SharePlus.instance.share(
                      ShareParams(
                        files: [
                          XFile.fromData(
                            utf8.encode('$csv'),
                            mimeType: 'text/csv',
                          ),
                        ],
                        fileNameOverrides: ['deepshield-scans.csv'],
                      ),
                    );
                  } catch (e) {
                    if (context.mounted) {
                      snack(context, app.t(Api.errorText(e)));
                    }
                  }
                },
              ),
          ],
        );
      },
    );
  }
}

class CompanionPage extends StatefulWidget {
  const CompanionPage({super.key});
  @override
  State<CompanionPage> createState() => _CompanionPageState();
}

class _CompanionPageState extends State<CompanionPage> {
  String? code;
  DateTime? expiry;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/extension/tokens',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(
            app.t('Browser Companion', 'Browser Companion'),
            subtitle: app.t(
              'Manage your desktop browser connections.',
              'কম্পিউটারের ব্রাউজারের সংযোগ নিয়ন্ত্রণ করুন।',
            ),
          ),
          Notice(
            app.t(
              'Install the DeepShield browser extension on your computer, then enter a pairing code.',
              'কম্পিউটারে DeepShield browser extension install করে pairing code দিন।',
            ),
          ),
          BusyButton(
            app.t('Generate pairing code', 'Pairing code তৈরি করুন'),
            onPressed: () async {
              try {
                final d = object(await app.api.post('/extension/pair'));
                if (mounted) {
                  setState(() {
                    code = d['code'];
                    expiry = DateTime.now().add(
                      Duration(seconds: number(d['expires_in']).toInt()),
                    );
                  });
                }
              } catch (e) {
                if (context.mounted) snack(context, app.t(Api.errorText(e)));
              }
            },
          ),
          if (code != null)
            Panel(
              child: Column(
                children: [
                  SelectableText(
                    code!,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text(
                    '${app.t('Expires at', 'মেয়াদ শেষ')} ${dateLabel(expiry?.toIso8601String())}',
                  ),
                  TextButton.icon(
                    onPressed: () =>
                        Clipboard.setData(ClipboardData(text: code!)),
                    icon: const Icon(Icons.copy),
                    label: Text(app.t('Copy', 'কপি')),
                  ),
                ],
              ),
            ),
          if (objects(data).isEmpty)
            EmptyState(
              app.t('No connected browsers', 'কোনো ব্রাউজার যুক্ত নেই'),
            ),
          ...objects(data).map(
            (r) => Panel(
              child: ItemRow(
                app.t('Connected browser', 'যুক্ত ব্রাউজার'),
                subtitle:
                    '${app.t('Expires')} ${dateLabel(DateTime.fromMillisecondsSinceEpoch((number(r['expires']) * 1000).round()).toIso8601String())}',
                icon: Icons.web,
                trailing: IconButton(
                  tooltip: app.t('Revoke', 'সংযোগ বাতিল'),
                  icon: const Icon(Icons.link_off),
                  onPressed: () async {
                    if (!await confirmAction(
                      context,
                      app.t('Revoke connection?', 'সংযোগ বাতিল করবেন?'),
                      app.t(
                        'This browser will need a new pairing code.',
                        'এই ব্রাউজারে নতুন pairing code লাগবে।',
                      ),
                    )) {
                      return;
                    }
                    try {
                      await app.api.delete('/extension/tokens/${r['id']}');
                      reload();
                    } catch (e) {
                      if (context.mounted) {
                        snack(context, app.t(Api.errorText(e)));
                      }
                    }
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/profile',
      builder: (data, reload) {
        final d = object(data), u = object(d['user']);
        return PageBody(
          children: [
            PageTitle(app.t('Your account', 'আপনার অ্যাকাউন্ট')),
            Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 30,
                    child: Text(
                      '${u['display_name']}'.substring(0, 1),
                      style: const TextStyle(fontSize: 28),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '${u['display_name']}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text('@${u['username']}'),
                  const SizedBox(height: 12),
                  StatusBadge(app.t('${u['role']}')),
                  const SizedBox(height: 16),
                  Muted(
                    '${app.t('Joined', 'যোগ দিয়েছেন')} ${dateLabel(u['created_at'])}',
                  ),
                ],
              ),
            ),
            if (app.user?['has_password'] == true)
              OutlinedButton.icon(
                icon: const Icon(Icons.lock_outline),
                label: Text(app.t('Change password', 'পাসওয়ার্ড বদলান')),
                onPressed: () async {
                  await openForm(
                    context,
                    title: app.t('Change password'),
                    fields: [
                      FieldSpec(
                        'current_password',
                        app.t('Current password', 'বর্তমান পাসওয়ার্ড'),
                        min: 8,
                        max: 128,
                        secret: true,
                      ),
                      FieldSpec(
                        'new_password',
                        app.t('New password', 'নতুন পাসওয়ার্ড'),
                        min: 12,
                        max: 128,
                        secret: true,
                      ),
                    ],
                    submit: (v) async {
                      await app.api.post('/auth/password', v);
                      await app.forgetSession();
                    },
                  );
                },
              ),
            Text(
              app.t('Recent game rounds', 'সাম্প্রতিক গেম রাউন্ড'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (objects(d['rounds']).isEmpty)
              EmptyState(app.t('No rounds yet', 'এখনও কোনো রাউন্ড খেলেননি')),
            ...objects(d['rounds'])
                .take(20)
                .map(
                  (r) => Panel(
                    child: ItemRow(
                      '${app.t('${r['prediction']}')} · ${r['points']} ${app.t('points', 'পয়েন্ট')}',
                      subtitle: dateLabel(r['created_at']),
                      icon: r['correct'] == true
                          ? Icons.check_circle_outline
                          : Icons.cancel_outlined,
                    ),
                  ),
                ),
          ],
        );
      },
    );
  }
}

class FieldSpec {
  final String key, label;
  final int min, max, lines;
  final bool secret;
  final List<String>? options;
  final String initial;
  const FieldSpec(
    this.key,
    this.label, {
    this.min = 1,
    this.max = 200,
    this.lines = 1,
    this.secret = false,
    this.options,
    this.initial = '',
  });
}

Future<bool> openForm(
  BuildContext context, {
  required String title,
  required List<FieldSpec> fields,
  required Future<dynamic> Function(Json) submit,
  String? explanation,
}) async =>
    await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => _FormPage(title, fields, submit, explanation),
      ),
    ) ??
    false;

class _FormPage extends StatefulWidget {
  final String title;
  final List<FieldSpec> fields;
  final Future<dynamic> Function(Json) submit;
  final String? explanation;
  const _FormPage(this.title, this.fields, this.submit, this.explanation);
  @override
  State<_FormPage> createState() => _FormPageState();
}

class _FormPageState extends State<_FormPage> {
  final form = GlobalKey<FormState>();
  late final Map<String, TextEditingController> values = {
    for (final f in widget.fields)
      f.key: TextEditingController(text: f.initial),
  };
  final visible = <String>{};
  bool busy = false;
  String? error;
  @override
  void dispose() {
    for (final c in values.values) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: PageBody(
        children: [
          if (widget.explanation != null) Notice(widget.explanation!),
          Panel(
            child: Form(
              key: form,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ...widget.fields.expand(
                    (f) => [
                      if (f.options != null)
                        DropdownButtonFormField<String>(
                          initialValue: f.initial.isEmpty
                              ? f.options!.first
                              : f.initial,
                          isExpanded: true,
                          decoration: InputDecoration(labelText: f.label),
                          items: f.options!
                              .map(
                                (o) => DropdownMenuItem(
                                  value: o,
                                  child: Text(app.t(o)),
                                ),
                              )
                              .toList(),
                          onChanged: busy
                              ? null
                              : (v) => values[f.key]!.text = v ?? '',
                          onSaved: (v) =>
                              values[f.key]!.text = v ?? f.options!.first,
                        )
                      else
                        TextFormField(
                          controller: values[f.key],
                          enabled: !busy,
                          obscureText: f.secret && !visible.contains(f.key),
                          minLines: f.secret ? 1 : f.lines,
                          maxLines: f.secret ? 1 : f.lines,
                          maxLength: f.max,
                          decoration: InputDecoration(
                            labelText: f.label,
                            alignLabelWithHint: true,
                            suffixIcon: f.secret
                                ? IconButton(
                                    tooltip: app.t('Show or hide password'),
                                    onPressed: () => setState(
                                      () => visible.contains(f.key)
                                          ? visible.remove(f.key)
                                          : visible.add(f.key),
                                    ),
                                    icon: Icon(
                                      visible.contains(f.key)
                                          ? Icons.visibility_off_outlined
                                          : Icons.visibility_outlined,
                                    ),
                                  )
                                : null,
                          ),
                          validator: (v) => (v ?? '').trim().length < f.min
                              ? app.t(
                                  'Enter at least ${f.min} characters.',
                                  'অন্তত ${f.min} অক্ষর লিখুন।',
                                )
                              : null,
                        ),
                      const SizedBox(height: 18),
                    ],
                  ),
                  if (error != null) ...[
                    Notice(app.t(error!), error: true),
                    const SizedBox(height: 16),
                  ],
                  BusyButton(
                    app.t('Save', 'সেভ করুন'),
                    busy: busy,
                    onPressed: () async {
                      if (!form.currentState!.validate()) return;
                      form.currentState!.save();
                      setState(() => busy = true);
                      try {
                        await widget.submit({
                          for (final e in values.entries) e.key: e.value.text,
                        });
                        if (context.mounted) Navigator.pop(context, true);
                      } catch (e) {
                        if (mounted) setState(() => error = Api.errorText(e));
                      } finally {
                        if (mounted) setState(() => busy = false);
                      }
                    },
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
