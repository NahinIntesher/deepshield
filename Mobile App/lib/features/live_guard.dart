import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/api.dart';
import '../core/guard.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import 'scans.dart';

class LiveGuardPage extends StatefulWidget {
  const LiveGuardPage({super.key});
  @override
  State<LiveGuardPage> createState() => _LiveGuardPageState();
}

class _LiveGuardPageState extends State<LiveGuardPage>
    with WidgetsBindingObserver {
  Timer? timer;
  Json status = {}, billing = {};
  bool busy = false, automatic = true, consent = false;
  final Set<String> allowedSources = {'YouTube', 'Facebook', 'Instagram'};
  Json otherApp = {};
  int interval = 120, budget = 3;
  String? error;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    timer = Timer.periodic(const Duration(seconds: 2), (_) => refresh());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (billing.isEmpty) {
      refresh();
      load();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      refresh();
      load();
    }
  }

  Future<void> refresh() async {
    try {
      final s = await NativeGuard.status();
      if (mounted) setState(() => status = s);
    } catch (e) {
      if (mounted) setState(() => error = message(e));
    }
  }

  Future<void> load() async {
    try {
      final b = object(await AppScope.of(context).api.get('/billing'));
      if (mounted) setState(() => billing = b);
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    }
  }

  String message(Object e) => e is PlatformException
      ? e.message ?? 'Could not complete the request.'
      : Api.errorText(e);
  Future<void> permission(String name) async {
    setState(() => busy = true);
    try {
      await NativeGuard.permission(name);
      await refresh();
    } catch (e) {
      if (mounted) setState(() => error = message(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> start() async {
    final app = AppScope.of(context);
    if (app.api.token == null || !consent) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await load();
      final remaining = (number(billing['limit']) - number(billing['used']))
          .toInt();
      if (remaining <= 0) throw const ApiFailure('Daily scan allowance used.');
      if (status['overlayAllowed'] != true) {
        throw const ApiFailure('Allow the floating panel first.');
      }
      if (status['usageAllowed'] != true || allowedSources.isEmpty) {
        throw const ApiFailure('Choose your apps and allow app access first.');
      }
      final started = await NativeGuard.start({
        'apiBase': apiBase,
        'token': app.api.token,
        'source': allowedSources.first,
        'allowedSources': allowedSources.toList(),
        'otherPackage': otherApp['package'],
        'language': app.language,
        'automatic': automatic,
        'interval': interval,
        'budget': budget.clamp(1, remaining),
      });
      if (!started && mounted) {
        setState(
          () => error = app.t(
            'Screen sharing was not started. You can try again whenever you are ready.',
            'স্ক্রিন শেয়ারিং চালু হয়নি। চাইলে পরে আবার শুরু করতে পারেন।',
          ),
        );
      }
      await refresh();
    } catch (e) {
      if (mounted) setState(() => error = app.t(message(e)));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final running = status['running'] == true,
        remaining = (number(billing['limit']) - number(billing['used']))
            .toInt()
            .clamp(0, 10000);
    final overlay = status['overlayAllowed'] == true;
    return PageBody(
      children: [
        PageTitle(
          'Live Guard',
          subtitle: app.t(
            'Check social videos while you watch.',
            'সোশ্যাল মিডিয়ায় ভিডিও দেখার সময় যাচাই করুন।',
          ),
        ),
        if (!NativeGuard.supported)
          Notice(
            app.t(
              'Live Guard screen sharing is available in the Android app.',
              'Live Guard screen sharing Android অ্যাপে পাওয়া যায়।',
            ),
          ),
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(
                    running ? Icons.sensors : Icons.shield_outlined,
                    size: 36,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      running
                          ? app.t('${status['title'] ?? 'Live Guard is on'}')
                          : app.t(
                              'You control screen sharing',
                              'স্ক্রিন শেয়ারিং আপনার নিয়ন্ত্রণে',
                            ),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                running
                    ? app.t('${status['detail'] ?? ''}')
                    : app.t(
                        'A small floating panel shows capture status and model results over the app you choose.',
                        'বেছে দেওয়া অ্যাপে ভিডিও দেখার সময় ছোট প্যানেল থাকবে। সম্ভাব্য ডিপফেক হলেই সতর্ক করা হবে।',
                      ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 8,
                children: [
                  StatusBadge(
                    running
                        ? '${status['used'] ?? 0}/${status['budget'] ?? budget} ${app.t('session scans', 'session স্ক্যান')}'
                        : app.t('Off', 'বন্ধ'),
                  ),
                  StatusBadge(
                    '$remaining ${app.t('scans left today', 'স্ক্যান আজ বাকি')}',
                  ),
                ],
              ),
              if (running) ...[
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 10,
                  children: [
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 12,
                        ),
                      ),
                      onPressed: () => NativeGuard.command(
                        status['paused'] == true ? 'resume' : 'pause',
                      ).then((_) => refresh()),
                      icon: Icon(
                        status['paused'] == true
                            ? Icons.play_arrow
                            : Icons.pause,
                      ),
                      label: Text(
                        app.t(
                          status['paused'] == true ? 'Resume' : 'Pause',
                          status['paused'] == true ? 'চালু করুন' : 'বিরতি',
                        ),
                      ),
                    ),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: Theme.of(context).colorScheme.error,
                        foregroundColor: Theme.of(context).colorScheme.onError,
                      ),
                      onPressed: () async {
                        await NativeGuard.stop();
                        await refresh();
                        await load();
                      },
                      icon: const Icon(Icons.stop_circle_outlined),
                      label: Text(app.t('Stop sharing', 'শেয়ারিং বন্ধ করুন')),
                    ),
                  ],
                ),
                if (status['resultId'] != null)
                  TextButton.icon(
                    icon: const Icon(Icons.open_in_new),
                    label: Text(
                      app.t(
                        'Inspect last result',
                        'সর্বশেষ ফল বিস্তারিত দেখুন',
                      ),
                    ),
                    onPressed: () => openPage(
                      context,
                      app.t('Result'),
                      RemoteView(
                        '/profile/detections/${status['resultId']}',
                        builder: (d, _) => ResultPage(object(d)),
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
        if (!running) ...[
          Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  app.t(
                    '1. Allow the floating panel',
                    '১. Floating panel-এর অনুমতি',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Muted(
                  app.t(
                    'Lets DeepShield show status and Stop controls over other apps. It cannot read your screen by itself.',
                    'অন্য অ্যাপের ওপর status ও Stop button দেখানোর অনুমতি। শুধু এই permission দিয়ে স্ক্রিন পড়া যায় না।',
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 12,
                    ),
                  ),
                  onPressed: busy || !NativeGuard.supported
                      ? null
                      : () => permission('overlayPermission'),
                  icon: Icon(
                    overlay
                        ? Icons.check_circle_outline
                        : Icons.layers_outlined,
                  ),
                  label: Text(
                    app.t(
                      overlay
                          ? 'Allowed · manage in Settings'
                          : 'Allow floating panel',
                      overlay
                          ? 'অনুমতি আছে · Settings-এ দেখুন'
                          : 'Floating panel-এর অনুমতি দিন',
                    ),
                  ),
                ),
                const Divider(),
                Text(
                  app.t(
                    '2. Keep session controls visible',
                    '২. Session control সহজে খুঁজে পান',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Muted(
                  app.t(
                    'Allow warnings for possible deepfakes. Real results do not send an alert. Android also keeps a quiet screen-sharing notification with Stop controls.',
                    'সম্ভাব্য ডিপফেকের সতর্কতা পেতে অনুমতি দিন। আসল ফলের জন্য alert আসবে না। স্ক্রিন শেয়ারিং চালু থাকলে Android-এর নীরব নোটিফিকেশনে বন্ধ করার বোতামও থাকবে।',
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 12,
                    ),
                  ),
                  onPressed: busy || !NativeGuard.supported
                      ? null
                      : () => permission('notificationPermission'),
                  icon: const Icon(Icons.notifications_active_outlined),
                  label: Text(
                    app.t(
                      status['notificationsAllowed'] == true
                          ? 'Notifications allowed'
                          : 'Allow notifications',
                      status['notificationsAllowed'] == true
                          ? 'নোটিফিকেশনের অনুমতি আছে'
                          : 'নোটিফিকেশনের অনুমতি দিন',
                    ),
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
                  app.t(
                    '3. Allow app access',
                    '৩. কোন অ্যাপ খোলা আছে জানার অনুমতি',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Muted(
                  app.t(
                    'Android Usage Access lets DeepShield identify the app currently on screen and pause outside your choices. App usage history is not saved or sent to the server.',
                    'Android-এর Usage Access দিয়ে শুধু কোন অ্যাপ সামনে খোলা আছে তা বোঝা হয়। এতে বেছে দেওয়া অ্যাপের বাইরে স্ক্যান বন্ধ থাকে। অ্যাপ ব্যবহারের ইতিহাস সেভ করা বা সার্ভারে পাঠানো হয় না।',
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: busy || !NativeGuard.supported
                      ? null
                      : () => permission('usagePermission'),
                  icon: Icon(
                    status['usageAllowed'] == true
                        ? Icons.check_circle_outline
                        : Icons.apps,
                  ),
                  label: Text(
                    app.t(
                      status['usageAllowed'] == true
                          ? 'App access allowed · manage'
                          : 'Allow app access',
                      status['usageAllowed'] == true
                          ? 'অ্যাপ চেনার অনুমতি আছে · দেখুন'
                          : 'অ্যাপ চেনার অনুমতি দিন',
                    ),
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
                  app.t('4. Choose how to scan', '৪. স্ক্যানের ধরন বেছে নিন'),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 18),
                Text(
                  app.t(
                    'Scan only in these apps',
                    'শুধু এই অ্যাপগুলোতে স্ক্যান করুন',
                  ),
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final name in [
                      'YouTube',
                      'Facebook',
                      'Instagram',
                      'TikTok',
                    ])
                      FilterChip(
                        label: Text(name),
                        selected: allowedSources.contains(name),
                        onSelected: busy
                            ? null
                            : (selected) => setState(() {
                                if (selected) {
                                  allowedSources.add(name);
                                } else {
                                  allowedSources.remove(name);
                                }
                              }),
                      ),
                    if (otherApp['package'] != null)
                      FilterChip(
                        label: Text(otherApp['name'].toString()),
                        selected: allowedSources.contains('Other'),
                        onSelected: busy
                            ? null
                            : (selected) => setState(() {
                                if (selected) {
                                  allowedSources.add('Other');
                                } else {
                                  allowedSources.remove('Other');
                                }
                              }),
                      ),
                  ],
                ),
                TextButton.icon(
                  onPressed: busy || !NativeGuard.supported
                      ? null
                      : () async {
                          setState(() => busy = true);
                          try {
                            final selected = object(
                              await NativeGuard.channel.invokeMethod(
                                'chooseApp',
                              ),
                            );
                            if (mounted && selected['package'] != null) {
                              setState(() {
                                otherApp = selected;
                                allowedSources.add('Other');
                              });
                            }
                          } catch (e) {
                            if (mounted) setState(() => error = message(e));
                          } finally {
                            if (mounted) setState(() => busy = false);
                          }
                        },
                  icon: const Icon(Icons.add),
                  label: Text(
                    app.t('Choose another app', 'অন্য অ্যাপ বেছে নিন'),
                  ),
                ),
                Muted(
                  app.t(
                    'No Facebook, YouTube or Instagram account login is needed. Scanning pauses when you leave the apps you allow.',
                    'Facebook, YouTube বা Instagram-এর অ্যাকাউন্টে লগইন দিতে হবে না। বেছে দেওয়া অ্যাপের বাইরে গেলে স্ক্যান থেমে থাকবে।',
                  ),
                ),
                const SizedBox(height: 14),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: automatic,
                  title: Text(
                    app.t('Automatic scanning', 'স্বয়ংক্রিয় স্ক্যান'),
                  ),
                  subtitle: Text(
                    app.t(
                      'Turn off to scan only when you tap Scan in the floating panel.',
                      'বন্ধ রাখলে floating panel-এর Scan চাপলেই শুধু স্ক্যান হবে।',
                    ),
                  ),
                  onChanged: busy ? null : (v) => setState(() => automatic = v),
                ),
                if (automatic) ...[
                  const SizedBox(height: 12),
                  DropdownButtonFormField<int>(
                    isExpanded: true,
                    initialValue: interval,
                    decoration: InputDecoration(
                      labelText: app.t(
                          'Rescan the same video after',
                          'একই ভিডিও আবার পরীক্ষার বিরতি',
                      ),
                    ),
                    items: [60, 120, 300, 600]
                        .map(
                          (v) => DropdownMenuItem(
                            value: v,
                            child: Text(
                              '${v ~/ 60} ${app.t('minutes', 'মিনিট')}',
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setState(() => interval = v!),
                  ),
                ],
                const SizedBox(height: 18),
                DropdownButtonFormField<int>(
                  isExpanded: true,
                  initialValue: budget,
                  decoration: InputDecoration(
                    labelText: app.t(
                      'Maximum scans this session',
                      'এই session-এ সর্বোচ্চ স্ক্যান',
                    ),
                  ),
                  items: [1, 3, 5, 10]
                      .map((v) => DropdownMenuItem(value: v, child: Text('$v')))
                      .toList(),
                  onChanged: (v) => setState(() => budget = v!),
                ),
                const SizedBox(height: 10),
                Muted(
                  app.t(
                    'Every successful scan uses your shared daily allowance. Capture stops at the session limit.',
                    'প্রতি সফল স্ক্যান daily allowance থেকে ধরা হয়। Session limit হলে capture বিরতিতে যাবে।',
                  ),
                ),
              ],
            ),
          ),
          Notice(
            app.t(
              'Screen capture is sent to your DeepShield backend and private Hugging Face inference service. Raw captures are temporary; results and face explanations are saved in your private history. Avoid sharing chats, passwords or sensitive screens. There is no audio recording.',
              'Screen capture DeepShield backend ও private Hugging Face inference service-এ পাঠানো হবে। Raw capture অস্থায়ী; ফল ও মুখের visual explanation আপনার private history-তে থাকবে। Chat, password বা সংবেদনশীল স্ক্রিন শেয়ার করবেন না। Audio record হয় না।',
            ),
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: consent,
            onChanged: busy
                ? null
                : (v) => setState(() => consent = v ?? false),
            title: Text(
              app.t(
                'I agree to send this session’s captures for private analysis.',
                'এই session-এর capture private analysis-এর জন্য পাঠাতে সম্মত।',
              ),
            ),
          ),
          BusyButton(
            app.t('Start Live Guard', 'Live Guard চালু করুন'),
            busy: busy,
            icon: Icons.sensors,
            onPressed:
                !NativeGuard.supported ||
                    !overlay ||
                    status['usageAllowed'] != true ||
                    allowedSources.isEmpty ||
                    !consent ||
                    remaining <= 0
                ? null
                : start,
          ),
          Muted(
            app.t(
              'Android will ask what to share each time. Choose a single app when available. Keep one video visible for 8 seconds. Analysis takes additional time; this is sampled analysis, not instant verification of every video.',
              'প্রতিবার Android কী শেয়ার করবেন তা জানতে চাইবে। সুযোগ থাকলে একটি অ্যাপ বেছে নিন। একটি ভিডিও অন্তত ৮ সেকেন্ড দেখুন। বিশ্লেষণে অতিরিক্ত সময় লাগে; প্রতিটি ভিডিও সঙ্গে সঙ্গে যাচাই হয় না।',
            ),
          ),
        ],
        if (error != null) Notice(app.t(error!), error: true),
        Notice(
          app.t(
            'A model result is not proof. Blank, protected or faceless content may have no usable result.',
            'মডেলের ফল নিশ্চিত প্রমাণ নয়। ফাঁকা, সুরক্ষিত বা মুখ ছাড়া ভিডিওতে ফল নাও পাওয়া যেতে পারে।',
          ),
        ),
      ],
    );
  }
}
