import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:web_socket_channel/io.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import '../ui/media.dart';
import 'model_explanation.dart';
import 'scans.dart';

class PlayPage extends StatelessWidget {
  const PlayPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return PageBody(
      children: [
        PageTitle(
          app.t('Real or fake?', 'আসল নাকি নকল?'),
          subtitle: app.t(
            'Practice spotting manipulated media.',
            'মিডিয়ার বিকৃতি শনাক্ত করার চর্চা করুন।',
          ),
        ),
        Panel(
          child: ItemRow(
            app.t('Solo challenge', 'একাই খেলুন'),
            subtitle: app.t(
              'Five videos. Make your call.',
              'পাঁচটি ভিডিও দেখে সিদ্ধান্ত দিন।',
            ),
            icon: Icons.sports_esports_outlined,
            onTap: () =>
                openPage(context, app.t('Solo challenge'), const SoloPage()),
          ),
        ),
        Panel(
          child: ItemRow(
            app.t('Play with friends', 'বন্ধুদের সঙ্গে খেলুন'),
            subtitle: app.t(
              'Create a room or join with a code.',
              'রুম তৈরি করুন অথবা কোড দিয়ে যুক্ত হন।',
            ),
            icon: Icons.groups_outlined,
            onTap: () =>
                openPage(context, app.t('Multiplayer'), const RoomsPage()),
          ),
        ),
        Panel(
          child: ItemRow(
            app.t('Leaderboard', 'লিডারবোর্ড'),
            icon: Icons.emoji_events_outlined,
            onTap: () => openPage(
              context,
              app.t('Leaderboard'),
              const LeaderboardPage(),
            ),
          ),
        ),
      ],
    );
  }
}

class SoloPage extends StatefulWidget {
  const SoloPage({super.key});
  @override
  State<SoloPage> createState() => _SoloPageState();
}

class _SoloPageState extends State<SoloPage> {
  List<Json>? items;
  final rounds = <Json>[];
  int index = 0;
  DateTime started = DateTime.now();
  Json? feedback, summary;
  bool busy = false;
  String? error;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (items == null) load();
  }

  Future<void> load() async {
    try {
      final d = objects(
        await AppScope.of(context).api.get('/game/items?count=5'),
      );
      if (mounted) {
        setState(() {
          items = d;
          started = DateTime.now();
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    }
  }

  Future<void> answer(String prediction) async {
    final app = AppScope.of(context), item = items![index];
    setState(() => busy = true);
    try {
      final d = object(
        await app.api.post('/game/submit-round', {
          'user_id': app.user!['id'],
          'item_id': item['id'],
          'ticket': item['ticket'],
          'prediction': prediction,
          'time_taken_ms': DateTime.now().difference(started).inMilliseconds,
        }),
      );
      rounds.add({'item_id': item['id'], 'ticket': item['ticket']});
      if (mounted) setState(() => feedback = d);
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> next() async {
    if (index + 1 < items!.length) {
      setState(() {
        index++;
        feedback = null;
        error = null;
        started = DateTime.now();
      });
      return;
    }
    setState(() => busy = true);
    try {
      final app = AppScope.of(context);
      final d = object(
        await app.api.post('/game/complete-session', {
          'user_id': app.user!['id'],
          'rounds': rounds,
        }),
      );
      await app.refresh();
      if (mounted) setState(() => summary = d);
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (items == null) {
      return PageBody(
        children: [
          if (error != null) ...[
            Notice(app.t(error!), error: true),
            OutlinedButton(onPressed: load, child: Text(app.t('Try again'))),
          ] else
            const Center(child: StatusArt(StatusMotion.loading, size: 64)),
        ],
      );
    }
    if (items!.isEmpty) {
      return EmptyState(
        app.t('No game videos available', 'খেলার ভিডিও পাওয়া যাচ্ছে না'),
      );
    }
    if (summary != null) {
      return PageBody(
        children: [
          EmptyState(
            app.t('Challenge complete', 'চ্যালেঞ্জ শেষ'),
            icon: Icons.emoji_events_outlined,
            success: true,
          ),
          MetricGrid([
            (
              app.t('Score', 'স্কোর'),
              '${summary!['user_score']}',
              Icons.star_outline,
            ),
            (
              app.t('Accuracy'),
              '${summary!['user_accuracy']}%',
              Icons.track_changes,
            ),
          ]),
          BusyButton(
            app.t('Done', 'শেষ'),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      );
    }
    final item = items![index];
    return PageBody(
      children: [
        PageTitle(
          app.t(
            'Round ${index + 1} of ${items!.length}',
            'রাউন্ড ${index + 1} / ${items!.length}',
          ),
        ),
        LinearProgressIndicator(value: (index + 1) / items!.length),
        MediaPlayer('${item['media_url']}', key: ValueKey(item['id'])),
        Text(
          '${item['title']}',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (feedback == null)
          VerdictButtons(onAnswer: busy ? null : answer)
        else
          Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                StatusBadge(
                  app.t(
                    feedback!['is_correct'] == true ? 'Correct' : 'Incorrect',
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  '${app.t('Dataset label:')} ${app.t('${feedback!['ground_truth']}')}',
                ),
                Text('+${feedback!['points_awarded']} ${app.t('points')}'),
                const SizedBox(height: 12),
                Text(app.t('${feedback!['explanation']}')),
                if (feedback!['ai_prediction'] != null)
                  Text('AI: ${feedback!['ai_prediction']}'),
                const SizedBox(height: 18),
                BusyButton(
                  app.t(index + 1 == items!.length ? 'Finish' : 'Next round'),
                  busy: busy,
                  onPressed: next,
                ),
              ],
            ),
          ),
        if (busy) const LinearProgressIndicator(),
        if (error != null) Notice(app.t(error!), error: true),
      ],
    );
  }
}

class VerdictButtons extends StatelessWidget {
  final void Function(String)? onAnswer;
  const VerdictButtons({super.key, this.onAnswer});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: onAnswer == null ? null : () => onAnswer!('Real'),
            icon: const Icon(Icons.check_circle_outline),
            label: Text(app.t('Real', 'আসল')),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: FilledButton.icon(
            onPressed: onAnswer == null ? null : () => onAnswer!('Fake'),
            icon: const Icon(Icons.rule_outlined),
            label: Text(app.t('Fake', 'নকল')),
          ),
        ),
      ],
    );
  }
}

class LeaderboardPage extends StatelessWidget {
  const LeaderboardPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/game/leaderboard',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(app.t('Leaderboard', 'লিডারবোর্ড')),
          if (objects(data).isEmpty)
            EmptyState(app.t('No scores yet', 'এখনও স্কোর নেই')),
          ...objects(data).map(
            (r) => Panel(
              child: ItemRow(
                '${r['rank']}. ${r['display_name']}',
                subtitle:
                    '${r['games_played']} ${app.t('games')} · ${number(r['accuracy']).toStringAsFixed(1)}%',
                icon: Icons.emoji_events_outlined,
                trailing: Text(
                  '${r['score']}',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class RoomsPage extends StatefulWidget {
  const RoomsPage({super.key});
  @override
  State<RoomsPage> createState() => _RoomsPageState();
}

class _RoomsPageState extends State<RoomsPage> {
  final code = TextEditingController();
  bool busy = false;
  String? error;
  @override
  void dispose() {
    code.dispose();
    super.dispose();
  }

  Future<void> enter(bool create) async {
    final app = AppScope.of(context);
    setState(() => busy = true);
    try {
      final d = object(
        await app.api.post(create ? '/rooms/create' : '/rooms/join', {
          'user_id': app.user!['id'],
          if (create) 'total_rounds': 5,
          if (!create) 'room_code': code.text.trim().toUpperCase(),
          if (!create) 'display_name': app.user!['display_name'],
        }),
      );
      if (mounted) {
        await Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => RoomPage('${d['room_code']}')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return PageBody(
      children: [
        PageTitle(app.t('Play with friends', 'বন্ধুদের সঙ্গে খেলুন')),
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.groups_outlined, size: 56),
              const SizedBox(height: 24),
              BusyButton(
                app.t('Create a room', 'রুম তৈরি করুন'),
                busy: busy,
                onPressed: () => enter(true),
              ),
              const Divider(),
              TextField(
                controller: code,
                textCapitalization: TextCapitalization.characters,
                maxLength: 6,
                decoration: InputDecoration(
                  labelText: app.t('Room code', 'রুম কোড'),
                ),
              ),
              OutlinedButton(
                onPressed: busy ? null : () => enter(false),
                child: Text(app.t('Join room', 'রুমে যুক্ত হন')),
              ),
            ],
          ),
        ),
        if (error != null) Notice(app.t(error!), error: true),
      ],
    );
  }
}

class RoomPage extends StatefulWidget {
  final String code;
  const RoomPage(this.code, {super.key});
  @override
  State<RoomPage> createState() => _RoomPageState();
}

class _RoomPageState extends State<RoomPage> {
  IOWebSocketChannel? socket;
  StreamSubscription? subscription;
  Timer? clock;
  Json? state, feedback;
  String? error;
  bool connected = false;
  double remaining = 0;
  int? answeredRound;
  DateTime received = DateTime.now();
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (socket == null) connect();
  }

  Future<void> connect() async {
    final app = AppScope.of(context);
    try {
      final base = Uri.parse(apiBase);
      final url = base.replace(
        scheme: base.scheme == 'https' ? 'wss' : 'ws',
        path: '/api/rooms/ws/${widget.code}/${app.user!['id']}',
      );
      final channel = IOWebSocketChannel.connect(
        url,
        headers: app.api.headers,
        connectTimeout: const Duration(seconds: 45),
      );
      socket = channel;
      await channel.ready;
      if (!mounted) {
        await channel.sink.close();
        return;
      }
      setState(() {
        connected = true;
        error = null;
      });
      subscription = channel.stream.listen(
        (raw) {
          final data = object(jsonDecode('$raw'));
          if (!mounted) return;
          setState(() {
            if (data['type'] == 'STATE') {
              if (state?['round'] != data['round']) feedback = null;
              state = data;
              received = DateTime.now();
              remaining =
                  (number(data['deadline']) - number(data['server_time']))
                      .clamp(0, 60);
            } else if (data['type'] == 'ANSWER_FEEDBACK') {
              feedback = data;
            } else if (data['type'] == 'ERROR') {
              error = '${data['message']}';
            }
          });
        },
        onError: (e) {
          if (mounted) {
            setState(() {
              connected = false;
              error = app.t(
                'Connection interrupted. Reconnect to resume.',
                'সংযোগ বিচ্ছিন্ন হয়েছে। আবার যুক্ত হন।',
              );
            });
          }
        },
        onDone: () {
          if (mounted) setState(() => connected = false);
        },
      );
      clock?.cancel();
      clock = Timer.periodic(const Duration(milliseconds: 250), (_) {
        if (mounted && state != null) {
          setState(
            () => remaining =
                (number(state!['deadline']) -
                        number(state!['server_time']) -
                        DateTime.now().difference(received).inMilliseconds /
                            1000)
                    .clamp(0, 60),
          );
        }
      });
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    }
  }

  void send(Json data) {
    try {
      socket?.sink.add(jsonEncode(data));
    } catch (_) {
      setState(() => error = 'Connection interrupted.');
    }
  }

  @override
  void dispose() {
    clock?.cancel();
    subscription?.cancel();
    socket?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context), s = state ?? {}, item = object(s['item']);
    final host = s['host_id'] == app.user!['id'];
    final answered =
        objects(s['players']).any(
          (p) => p['user_id'] == app.user!['id'] && p['answered'] == true,
        ) ||
        answeredRound == s['round'];
    return Scaffold(
      appBar: AppBar(title: Text('${app.t('Room')} ${widget.code}')),
      body: PageBody(
        children: [
          Panel(
            child: Row(
              children: [
                Expanded(
                  child: SelectableText(
                    widget.code,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                ),
                IconButton(
                  tooltip: app.t('Copy code'),
                  icon: const Icon(Icons.copy),
                  onPressed: () =>
                      Clipboard.setData(ClipboardData(text: widget.code)),
                ),
              ],
            ),
          ),
          if (!connected)
            BusyButton(
              app.t('Reconnect', 'আবার যুক্ত হন'),
              onPressed: () async {
                await subscription?.cancel();
                await socket?.sink.close();
                await connect();
              },
            ),
          if (error != null) Notice(app.t(error!), error: true),
          if (s['status'] == 'waiting')
            Panel(
              child: Column(
                children: [
                  Text(app.t('Waiting for players', 'খেলোয়াড়দের জন্য অপেক্ষা')),
                  const SizedBox(height: 16),
                  if (host)
                    BusyButton(
                      app.t('Start game', 'খেলা শুরু করুন'),
                      onPressed: connected
                          ? () => send({'action': 'START_GAME'})
                          : null,
                    ),
                ],
              ),
            ),
          if (['playing', 'preparing'].contains(s['status'])) ...[
            PageTitle(
              '${app.t('Round')} ${s['round']}/${s['total_rounds']}',
              subtitle: '${remaining.ceil()}s',
            ),
            if (s['status'] == 'playing')
              MediaPlayer(
                '${item['media_url']}',
                key: ValueKey('${item['id']}:${s['round']}'),
              ),
            if (s['status'] == 'preparing')
              Notice(
                app.t('Next round is starting…', 'পরের রাউন্ড শুরু হচ্ছে…'),
              )
            else
              VerdictButtons(
                onAnswer: !connected || answered || remaining <= 0
                    ? null
                    : (v) {
                        setState(() => answeredRound = s['round']);
                        send({
                          'action': 'SUBMIT_ANSWER',
                          'item_id': item['id'],
                          'prediction': v,
                        });
                      },
              ),
            if (feedback != null)
              Notice(
                '${app.t(feedback!['is_correct'] == true ? 'Correct' : 'Incorrect')} · +${feedback!['points']}',
              ),
            if (host && s['can_advance'] == true)
              BusyButton(
                app.t('Next round'),
                onPressed: () => send({'action': 'NEXT_ROUND'}),
              ),
          ],
          if (s['status'] == 'finished')
            EmptyState(
              app.t('Game complete', 'খেলা শেষ'),
              icon: Icons.emoji_events_outlined,
            ),
          ...objects(s['players']).map(
            (p) => Panel(
              child: ItemRow(
                '${p['display_name']}',
                subtitle: p['answered'] == true
                    ? app.t('Answered', 'উত্তর দিয়েছেন')
                    : null,
                icon: Icons.person_outline,
                trailing: Text(
                  '${p['score']}',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AssessmentPage extends StatefulWidget {
  const AssessmentPage({super.key});
  @override
  State<AssessmentPage> createState() => _AssessmentPageState();
}

class _AssessmentPageState extends State<AssessmentPage> {
  Json? data;
  bool loaded = false, busy = false, consent = false;
  String? error;
  final answers = <int, String>{};
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!loaded) load();
  }

  Future<void> load() async {
    try {
      final d = await AppScope.of(context).api.get('/assessment');
      if (mounted) {
        setState(() {
          data = d == null ? null : object(d);
          loaded = true;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    }
  }

  Future<void> act() async {
    final app = AppScope.of(context);
    setState(() => busy = true);
    try {
      final d = object(
        await app.api.post(
          data == null
              ? '/assessment/start'
              : '/assessment/${data!['id']}/submit',
          data == null
              ? {'consent': true}
              : {
                  'phase': data!['state'],
                  'answers': answers.entries
                      .map((e) => {'item_id': e.key, 'prediction': e.value})
                      .toList(),
                },
        ),
      );
      if (mounted) {
        setState(() {
          data = d;
          answers.clear();
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (!loaded && error == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final items = objects(data?['items']);
    return PageBody(
      children: [
        PageTitle(app.t('Learning assessment', 'শেখার অগ্রগতি যাচাই')),
        if (data == null) ...[
          Notice(
            app.t(
              'Answer four videos before learning, then four different videos after practice. Your answers and scores are saved to your account.',
              'শেখার আগে চারটি এবং চর্চার পরে ভিন্ন চারটি ভিডিওর উত্তর দিন। উত্তর ও স্কোর আপনার অ্যাকাউন্টে সংরক্ষিত হবে।',
            ),
          ),
          CheckboxListTile(
            value: consent,
            onChanged: (v) => setState(() => consent = v ?? false),
            title: Text(
              app.t(
                'I agree to take part and save my responses.',
                'অংশ নিতে এবং আমার উত্তর সংরক্ষণ করতে সম্মত।',
              ),
            ),
          ),
          BusyButton(
            app.t('Start assessment', 'শুরু করুন'),
            busy: busy,
            onPressed: consent ? act : null,
          ),
        ] else if (data!['state'] == 'completed')
          MetricGrid([
            (
              app.t('Before learning', 'শেখার আগে'),
              '${data!['pre_score']}%',
              Icons.flag_outlined,
            ),
            (
              app.t('After learning', 'শেখার পরে'),
              '${data!['post_score']}%',
              Icons.school_outlined,
            ),
          ])
        else ...[
          StatusBadge(
            app.t(
              data!['state'] == 'pre' ? 'Before learning' : 'After learning',
            ),
          ),
          if (data!['state'] == 'post')
            Notice(
              app.t(
                'Complete a lesson or game round before submitting this follow-up.',
                'এই ধাপ জমা দেওয়ার আগে একটি লেসন বা গেম রাউন্ড শেষ করুন।',
              ),
            ),
          ...items.map(
            (i) => Panel(
              child: Column(
                children: [
                  MediaPlayer(
                    '${i['media_path']}',
                    key: ValueKey('${data!['state']}:${i['id']}'),
                  ),
                  const SizedBox(height: 16),
                  if (answers[i['id']] != null)
                    StatusBadge(app.t(answers[i['id']]!)),
                  const SizedBox(height: 8),
                  VerdictButtons(
                    onAnswer: busy
                        ? null
                        : (v) => setState(() => answers[i['id']] = v),
                  ),
                ],
              ),
            ),
          ),
          BusyButton(
            app.t('Submit answers', 'উত্তর জমা দিন'),
            busy: busy,
            onPressed: answers.length == items.length && items.isNotEmpty
                ? act
                : null,
          ),
        ],
        if (error != null) Notice(app.t(error!), error: true),
      ],
    );
  }
}

class ResearchPage extends StatelessWidget {
  const ResearchPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/research/items?user_id=${app.user!['id']}',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(app.t('Research challenge', 'রিসার্চ চ্যালেঞ্জ')),
          if (objects(data).isEmpty)
            EmptyState(
              app.t(
                'All available samples completed',
                'সব নমুনার মূল্যায়ন শেষ',
              ),
            ),
          ...objects(data).map(
            (r) => Panel(
              child: ItemRow(
                '${r['title']}',
                icon: Icons.science_outlined,
                onTap: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => Scaffold(
                        appBar: AppBar(title: Text('${r['title']}')),
                        body: ResearchEvaluation(r),
                      ),
                    ),
                  );
                  reload();
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ResearchEvaluation extends StatefulWidget {
  final Json item;
  const ResearchEvaluation(this.item, {super.key});
  @override
  State<ResearchEvaluation> createState() => _ResearchEvaluationState();
}

class _ResearchEvaluationState extends State<ResearchEvaluation> {
  String? verdict, error;
  double confidence = 3;
  final clues = <String>{};
  bool busy = false;
  Json? result;
  final started = DateTime.now();
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return PageBody(
      children: [
        MediaPlayer('${widget.item['media_url']}'),
        if (result == null) ...[
          PageTitle(app.t('Your assessment', 'আপনার মূল্যায়ন')),
          VerdictButtons(
            onAnswer: busy ? null : (v) => setState(() => verdict = v),
          ),
          if (verdict != null) StatusBadge(app.t(verdict!)),
          Text(
            '${app.t('Confidence', 'আপনার নিশ্চয়তা')} ${confidence.round()}/5',
          ),
          Slider(
            value: confidence,
            min: 1,
            max: 5,
            divisions: 4,
            label: '${confidence.round()}',
            onChanged: busy ? null : (v) => setState(() => confidence = v),
          ),
          Text(app.t('What did you notice?', 'কোন বিষয়গুলো খেয়াল করেছেন?')),
          Wrap(
            spacing: 8,
            children:
                [
                      'Face edges',
                      'Lip sync',
                      'Lighting',
                      'Texture',
                      'Movement',
                      'No obvious clue',
                    ]
                    .map(
                      (c) => FilterChip(
                        label: Text(app.t(c)),
                        selected: clues.contains(c),
                        onSelected: busy
                            ? null
                            : (v) => setState(
                                () => v ? clues.add(c) : clues.remove(c),
                              ),
                      ),
                    )
                    .toList(),
          ),
          BusyButton(
            app.t('Submit evaluation', 'মূল্যায়ন জমা দিন'),
            busy: busy,
            onPressed: verdict == null
                ? null
                : () async {
                    setState(() => busy = true);
                    try {
                      final d = object(
                        await app.api.post('/research/submit', {
                          'user_id': app.user!['id'],
                          'item_id': widget.item['id'],
                          'human_prediction': verdict,
                          'human_confidence': confidence.round(),
                          'clue_tags': clues.toList(),
                          'reaction_time_ms': DateTime.now()
                              .difference(started)
                              .inMilliseconds,
                        }),
                      );
                      if (mounted) setState(() => result = d);
                    } catch (e) {
                      if (mounted) setState(() => error = Api.errorText(e));
                    } finally {
                      if (mounted) setState(() => busy = false);
                    }
                  },
          ),
        ] else
          Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusBadge('${result!['disagreement_quadrant'] ?? ''}'),
                Text(
                  '${app.t('Your answer')}: ${app.t('${result!['human_prediction']}')}',
                ),
                Text(
                  '${app.t('Model answer', 'মডেলের উত্তর')}: ${app.t('${result!['ai_prediction']}')}',
                ),
                Text(
                  '${app.t('Dataset label:', 'ডেটাসেটের উত্তর:')} ${app.t('${result!['ground_truth']}')}',
                ),
                const SizedBox(height: 12),
                Text(app.t('${result!['explanation'] ?? ''}')),
                if (result!['analysis'] == null &&
                    result!['xai_heatmap_url'] != null)
                  DataImage('${result!['xai_heatmap_url']}'),
                if (result!['analysis'] == null &&
                    result!['temporal_anomaly_scores'] is List)
                  BarPanel(
                    app.t('Temporal sensitivity', 'সময় অনুযায়ী মডেলের সাড়া'),
                    List.generate(
                      (result!['temporal_anomaly_scores'] as List).length,
                      (i) => (
                        '${i + 1}',
                        number(result!['temporal_anomaly_scores'][i]),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        if (result != null && result!['analysis'] is Map) ...[
          ModelExplanation(object(result!['analysis'])),
          OutlinedButton.icon(
            onPressed: () => openPage(
              context,
              app.t('Model details', 'মডেলের বিস্তারিত'),
              ResultPage(object(result!['analysis'])),
            ),
            icon: const Icon(Icons.insights_outlined),
            label: Text(
              app.t(
                'Inspect the heatmap and model scores',
                'Heatmap ও মডেলের স্কোর দেখুন',
              ),
            ),
          ),
        ],
        if (result != null)
          BusyButton(
            app.t('Back to research samples', 'রিসার্চ নমুনায় ফিরুন'),
            onPressed: () => Navigator.pop(context),
          ),
        if (error != null) Notice(app.t(error!), error: true),
      ],
    );
  }
}
