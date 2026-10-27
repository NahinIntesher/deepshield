import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import '../ui/media.dart';
import 'member.dart';

class AdminOverview extends StatelessWidget {
  const AdminOverview({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/admin/analytics?days=14',
      builder: (data, reload) {
        final d = object(data), s = object(d['summary']);
        return PageBody(
          children: [
            PageTitle(
              app.t('Admin overview', 'অ্যাডমিন ড্যাশবোর্ড'),
              subtitle: app.t(
                'Account activity and service performance.',
                'অ্যাকাউন্টের অ্যাক্টিভিটি ও সার্ভিসের তথ্য।',
              ),
            ),
            MetricGrid([
              (
                app.t('Members', 'মেম্বার'),
                '${s['members']}',
                Icons.people_outline,
              ),
              (
                app.t('Active in 14 days', '১৪ দিনে সক্রিয়'),
                '${s['active']}',
                Icons.insights_outlined,
              ),
              (
                app.t('Scans', 'স্ক্যান'),
                '${s['detections']}',
                Icons.document_scanner_outlined,
              ),
              (
                app.t('Pending reviews', 'অপেক্ষায় থাকা রিভিউ'),
                '${s['pending_reviews']}',
                Icons.fact_check_outlined,
              ),
            ]),
            BarPanel(
              app.t('Daily scans · last 14 days', 'গত ১৪ দিনের স্ক্যান'),
              objects(d['daily'])
                  .map(
                    (r) =>
                        ('${r['date']}'.substring(5), number(r['detections'])),
                  )
                  .toList(),
            ),
            BarPanel(
              app.t('Account roles', 'অ্যাকাউন্টের রোল'),
              objects(d['roles'])
                  .map((r) => (app.t('${r['label']}'), number(r['value'])))
                  .toList(),
            ),
            BarPanel(
              app.t('Game accuracy', 'গেমে সঠিক উত্তরের হার'),
              objects(d['accuracy_bands'])
                  .map((r) => (app.t('${r['label']}'), number(r['value'])))
                  .toList(),
            ),
            Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    app.t('Top members', 'সেরা মেম্বার'),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  ...objects(d['top_members']).map(
                    (r) => ItemRow(
                      '${r['name']}',
                      subtitle: '${number(r['accuracy']).toStringAsFixed(1)}%',
                      icon: Icons.emoji_events_outlined,
                      trailing: Text('${r['score']}'),
                    ),
                  ),
                ],
              ),
            ),
            Muted(
              '${app.t('Generated at', 'আপডেট')} ${dateLabel(d['generated_at'])}',
            ),
          ],
        );
      },
    );
  }
}

class UsersPage extends StatefulWidget {
  const UsersPage({super.key});
  @override
  State<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends State<UsersPage> {
  String query = '', role = 'all';
  int page = 0;
  Future<void> edit(Json? user) async {
    final app = AppScope.of(context);
    await openForm(
      context,
      title: app.t(
        user == null ? 'Create account' : 'Edit account',
        user == null ? 'অ্যাকাউন্ট তৈরি' : 'অ্যাকাউন্ট এডিট',
      ),
      fields: [
        FieldSpec(
          'username',
          app.t('Username'),
          min: 2,
          max: 50,
          initial: '${user?['username'] ?? ''}',
        ),
        FieldSpec(
          'display_name',
          app.t('Display name', 'আপনার নাম'),
          max: 64,
          initial: '${user?['display_name'] ?? ''}',
        ),
        FieldSpec(
          'role',
          app.t('Role', 'রোল'),
          options: const ['participant', 'researcher'],
          initial: '${user?['role'] ?? 'participant'}',
        ),
        if (user == null)
          FieldSpec(
            'password',
            app.t('Password'),
            min: 12,
            max: 128,
            secret: true,
          ),
      ],
      submit: (v) => user == null
          ? app.api.post('/admin/users', v)
          : app.api.patch('/admin/users/${user['id']}', v),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/admin/users',
      builder: (data, reload) {
        final all = objects(data),
            filtered = all
                .where(
                  (r) =>
                      (role == 'all' || r['role'] == role) &&
                      '${r['display_name']} ${r['username']}'
                          .toLowerCase()
                          .contains(query.toLowerCase()),
                )
                .toList(),
            rows = filtered.skip(page * 12).take(12);
        return PageBody(
          children: [
            PageTitle(app.t('Users', 'ইউজার ম্যানেজমেন্ট')),
            MetricGrid([
              (
                app.t('All accounts', 'সব অ্যাকাউন্ট'),
                '${all.length}',
                Icons.people_outline,
              ),
              (
                app.t('Researchers', 'রিসার্চার'),
                '${all.where((r) => r['role'] == 'researcher').length}',
                Icons.science_outlined,
              ),
            ]),
            BusyButton(
              app.t('Create account', 'অ্যাকাউন্ট তৈরি করুন'),
              icon: Icons.person_add_outlined,
              onPressed: () async {
                await edit(null);
                reload();
              },
            ),
            TextField(
              onChanged: (v) => setState(() {
                query = v;
                page = 0;
              }),
              decoration: InputDecoration(
                labelText: app.t('Search accounts', 'অ্যাকাউন্ট খুঁজুন'),
                prefixIcon: const Icon(Icons.search),
              ),
            ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['all', 'participant', 'researcher', 'admin']
                  .map(
                    (v) => ChoiceChip(
                      label: Text(app.t(v == 'all' ? 'All roles' : v)),
                      selected: role == v,
                      onSelected: (_) => setState(() {
                        role = v;
                        page = 0;
                      }),
                    ),
                  )
                  .toList(),
            ),
            if (filtered.isEmpty)
              EmptyState(
                app.t('No matching accounts', 'কোনো অ্যাকাউন্ট পাওয়া যায়নি'),
              ),
            ...rows.map(
              (r) => Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '${r['display_name']}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text('@${r['username']}'),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: StatusBadge(app.t('${r['role']}')),
                    ),
                    const Divider(),
                    Wrap(
                      spacing: 22,
                      runSpacing: 12,
                      children: [
                        Text('${app.t('Score')}: ${r['score']}'),
                        Text(
                          '${app.t('Accuracy')}: ${number(r['accuracy']).toStringAsFixed(1)}%',
                        ),
                        Text('${app.t('Games')}: ${r['games_played']}'),
                      ],
                    ),
                    const SizedBox(height: 14),
                    if (r['role'] == 'admin')
                      Muted(
                        app.t(
                          'Owner account is protected.',
                          'মূল অ্যাডমিন অ্যাকাউন্ট সুরক্ষিত।',
                        ),
                      )
                    else
                      Wrap(
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          OutlinedButton.icon(
                            onPressed: () async {
                              await edit(r);
                              reload();
                            },
                            icon: const Icon(Icons.edit_outlined),
                            label: Text(app.t('Edit', 'এডিট')),
                          ),
                          OutlinedButton.icon(
                            onPressed: () async {
                              await openForm(
                                context,
                                title: app.t(
                                  'Reset password',
                                  'পাসওয়ার্ড রিসেট',
                                ),
                                fields: [
                                  FieldSpec(
                                    'new_password',
                                    app.t('New password'),
                                    min: 12,
                                    max: 128,
                                    secret: true,
                                  ),
                                ],
                                explanation: app.t(
                                  'All existing sessions for this account will be revoked.',
                                  'এই অ্যাকাউন্টের সব পুরোনো login session বাতিল হবে।',
                                ),
                                submit: (v) =>
                                    app.api.patch('/admin/users/${r['id']}', {
                                      'username': r['username'],
                                      'display_name': r['display_name'],
                                      'role': r['role'],
                                      ...v,
                                    }),
                              );
                              reload();
                            },
                            icon: const Icon(Icons.lock_reset),
                            label: Text(
                              app.t('Reset password', 'পাসওয়ার্ড রিসেট'),
                            ),
                          ),
                          IconButton(
                            tooltip: app.t(
                              'Delete account',
                              'অ্যাকাউন্ট ডিলিট করুন',
                            ),
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () async {
                              await openForm(
                                context,
                                title: app.t(
                                  'Delete account',
                                  'অ্যাকাউন্ট ডিলিট',
                                ),
                                explanation: app.t(
                                  'This permanently removes @${r['username']} and their history. Type the exact username to confirm.',
                                  '@${r['username']} ও তার সব তথ্য স্থায়ীভাবে ডিলিট হবে। নিশ্চিত করতে একই ইউজারনেম লিখুন।',
                                ),
                                fields: [
                                  FieldSpec(
                                    'confirm_username',
                                    app.t('Confirm username', 'ইউজারনেম লিখুন'),
                                    min: 2,
                                    max: 50,
                                  ),
                                ],
                                submit: (v) {
                                  if (v['confirm_username'] != r['username']) {
                                    throw const ApiFailure(
                                      'Username does not match.',
                                    );
                                  }
                                  return app.api.delete(
                                    '/admin/users/${r['id']}',
                                    v,
                                  );
                                },
                              );
                              reload();
                            },
                          ),
                        ],
                      ),
                  ],
                ),
              ),
            ),
            Row(
              children: [
                IconButton(
                  tooltip: app.t('Previous page'),
                  onPressed: page == 0 ? null : () => setState(() => page--),
                  icon: const Icon(Icons.chevron_left),
                ),
                Expanded(
                  child: Text(
                    '${page + 1} / ${(filtered.length / 12).ceil().clamp(1, 999)}',
                    textAlign: TextAlign.center,
                  ),
                ),
                IconButton(
                  tooltip: app.t('Next page'),
                  onPressed: (page + 1) * 12 >= filtered.length
                      ? null
                      : () => setState(() => page++),
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class RecordsPage extends StatefulWidget {
  const RecordsPage({super.key});
  @override
  State<RecordsPage> createState() => _RecordsPageState();
}

class _RecordsPageState extends State<RecordsPage> {
  String resource = 'scans';
  int offset = 0;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ['scans', 'research', 'support', 'subscriptions']
                .map(
                  (v) => ChoiceChip(
                    label: Text(app.t(v)),
                    selected: resource == v,
                    onSelected: (_) => setState(() {
                      resource = v;
                      offset = 0;
                    }),
                  ),
                )
                .toList(),
          ),
        ),
        Expanded(
          child: RemoteView(
            '/admin/records/$resource?offset=$offset&limit=20',
            builder: (data, reload) {
              final d = object(data), rows = objects(d['rows']);
              return PageBody(
                children: [
                  if (rows.isEmpty)
                    EmptyState(app.t('No records', 'কোনো রেকর্ড নেই')),
                  ...rows.map(
                    (r) => Panel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          StatusBadge(app.t('${r['status']}')),
                          const SizedBox(height: 12),
                          Text(
                            '${r['title']}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text('@${r['username']}'),
                          if ('${r['note'] ?? ''}'.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            Text(app.t('${r['note']}')),
                          ],
                          const SizedBox(height: 10),
                          Muted(dateLabel(r['created_at'])),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 10,
                            children: [
                              OutlinedButton(
                                onPressed: () async {
                                  final key = resource == 'scans'
                                      ? 'title'
                                      : 'note';
                                  await openForm(
                                    context,
                                    title: app.t('Edit record', 'রেকর্ড এডিট'),
                                    fields: [
                                      FieldSpec(
                                        key,
                                        app.t(
                                          key == 'title' ? 'Title' : 'Note',
                                        ),
                                        min: key == 'title' ? 2 : 5,
                                        max: key == 'title' ? 160 : 3000,
                                        lines: key == 'title' ? 1 : 4,
                                        initial: '${r[key] ?? ''}',
                                      ),
                                    ],
                                    submit: (v) => app.api.patch(
                                      '/admin/records/$resource/${r['id']}',
                                      v,
                                    ),
                                  );
                                  reload();
                                },
                                child: Text(app.t('Edit')),
                              ),
                              IconButton(
                                tooltip: app.t('Delete record'),
                                icon: const Icon(Icons.delete_outline),
                                onPressed: () async {
                                  if (!await confirmAction(
                                    context,
                                    app.t('Delete record?'),
                                    app.t(
                                      'This permanently removes record ${r['id']}.',
                                      'রেকর্ড ${r['id']} স্থায়ীভাবে ডিলিট হবে।',
                                    ),
                                    destructive: true,
                                  )) {
                                    return;
                                  }
                                  try {
                                    await app.api.delete(
                                      '/admin/records/$resource/${r['id']}',
                                      {'confirm_id': '${r['id']}'},
                                    );
                                    reload();
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
                  Row(
                    children: [
                      IconButton(
                        tooltip: app.t('Previous page'),
                        onPressed: offset == 0
                            ? null
                            : () => setState(() => offset -= 20),
                        icon: const Icon(Icons.chevron_left),
                      ),
                      Expanded(
                        child: Text(
                          '${offset + 1}–${offset + rows.length} / ${d['total']}',
                          textAlign: TextAlign.center,
                        ),
                      ),
                      IconButton(
                        tooltip: app.t('Next page'),
                        onPressed: offset + 20 >= number(d['total'])
                            ? null
                            : () => setState(() => offset += 20),
                        icon: const Icon(Icons.chevron_right),
                      ),
                    ],
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class OperationsPage extends StatelessWidget {
  const OperationsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/operations',
      builder: (data, reload) {
        final d = object(data);
        return PageBody(
          children: [
            PageTitle(app.t('Payments & support', 'পেমেন্ট ও সাপোর্ট')),
            Text(
              app.t('Premium requests', 'Premium-এর অনুরোধ'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (objects(d['subscriptions']).isEmpty)
              EmptyState(app.t('No requests', 'কোনো অনুরোধ নেই')),
            ...objects(d['subscriptions']).map(
              (r) => Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    StatusBadge(app.t('${r['status']}')),
                    Text(
                      '@${r['username']}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    SelectableText('bKash: ${r['reference']}'),
                    Text('${r['note']}'),
                    if (r['status'] == 'pending')
                      ...['approved', 'rejected'].map(
                        (decision) => TextButton(
                          onPressed: () async {
                            await openForm(
                              context,
                              title: app.t(
                                decision == 'approved'
                                    ? 'Approve request'
                                    : 'Reject request',
                              ),
                              explanation: decision == 'approved'
                                  ? app.t(
                                      'Verify the transaction, amount and recipient in bKash before approval. Select manual_payment only after independent verification.',
                                      'অনুমোদনের আগে bKash-এ transaction, টাকার পরিমাণ ও প্রাপকের নম্বর যাচাই করুন। যাচাই শেষে manual_payment বেছে নিন।',
                                    )
                                  : null,
                              fields: [
                                FieldSpec(
                                  'note',
                                  app.t('Review note', 'রিভিউ নোট'),
                                  min: 5,
                                  max: 1000,
                                  lines: 3,
                                ),
                                if (decision == 'approved')
                                  FieldSpec(
                                    'activation',
                                    app.t('Activation type', 'চালু করার ধরন'),
                                    options: const [
                                      'manual_payment',
                                      'academic_demo',
                                    ],
                                    initial: 'manual_payment',
                                  ),
                              ],
                              submit: (v) => app.api.post(
                                '/operations/subscriptions/${r['id']}',
                                {
                                  ...v,
                                  'decision': decision,
                                  'payment_verified':
                                      v['activation'] == 'manual_payment',
                                },
                              ),
                            );
                            reload();
                          },
                          child: Text(
                            app.t(
                              decision == 'approved' ? 'Approve' : 'Reject',
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            Text(
              app.t('Support requests', 'সাপোর্ট অনুরোধ'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (objects(d['tickets']).isEmpty)
              EmptyState(app.t('No support requests')),
            ...objects(d['tickets']).map(
              (r) => Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    StatusBadge(app.t('${r['status']}')),
                    Text(
                      '${r['subject']}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text('${r['message']}'),
                    if ('${r['reply'] ?? ''}'.isNotEmpty) Text('${r['reply']}'),
                    TextButton(
                      onPressed: () async {
                        await openForm(
                          context,
                          title: app.t('Reply', 'উত্তর দিন'),
                          fields: [
                            FieldSpec(
                              'reply',
                              app.t('Reply'),
                              min: 5,
                              max: 3000,
                              lines: 5,
                            ),
                          ],
                          submit: (v) =>
                              app.api.post('/operations/support/${r['id']}', v),
                        );
                        reload();
                      },
                      child: Text(app.t('Reply', 'উত্তর দিন')),
                    ),
                  ],
                ),
              ),
            ),
            Text(
              app.t('Scan queue', 'স্ক্যান কিউ'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            ...objects(d['queue']).map(
              (r) => Panel(
                child: ItemRow(
                  '${r['source_name']}',
                  subtitle: app.t('${r['state']}'),
                  icon: Icons.queue_outlined,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class TrainingPage extends StatelessWidget {
  final bool reviewOnly;
  const TrainingPage({super.key, this.reviewOnly = false});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/admin/learning',
      builder: (data, reload) {
        final d = object(data), training = object(d['training']);
        return PageBody(
          children: [
            PageTitle(
              reviewOnly
                  ? app.t('Research reviews', 'রিসার্চ রিভিউ')
                  : app.t('Continual learning', 'মডেল ট্রেনিং'),
            ),
            if (!reviewOnly) InfoFields(training),
            if (!reviewOnly)
              BusyButton(
                app.t(
                  'Train & evaluate candidate',
                  'Candidate ট্রেনিং ও মূল্যায়ন',
                ),
                icon: Icons.model_training,
                onPressed: () async {
                  if (!await confirmAction(
                    context,
                    app.t(
                      'Start candidate training?',
                      'Candidate ট্রেনিং শুরু করবেন?',
                    ),
                    app.t(
                      'This starts evaluation on reviewed samples and replay memory.',
                      'রিভিউ করা নমুনা ও replay memory দিয়ে মূল্যায়ন শুরু হবে।',
                    ),
                  )) {
                    return;
                  }
                  try {
                    await app.api.post('/admin/learning/train');
                    reload();
                  } catch (e) {
                    if (context.mounted) {
                      snack(context, app.t(Api.errorText(e)));
                    }
                  }
                },
              ),
            Text(
              app.t('Research samples', 'রিসার্চ নমুনা'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (objects(d['samples']).isEmpty)
              EmptyState(
                app.t('No samples awaiting review', 'রিভিউয়ের জন্য নমুনা নেই'),
              ),
            ...objects(d['samples']).map(
              (r) => Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    StatusBadge(app.t('${r['status']}')),
                    const SizedBox(height: 12),
                    MediaPlayer('${r['media_url']}'),
                    Text(
                      '${app.t('Human answer')}: ${app.t('${r['human_prediction']}')}',
                    ),
                    if (r['status'] == 'pending')
                      OutlinedButton(
                        onPressed: () async {
                          await openForm(
                            context,
                            title: app.t('Review sample', 'নমুনা রিভিউ'),
                            fields: [
                              FieldSpec(
                                'decision',
                                app.t('Decision'),
                                options: const ['approved', 'rejected'],
                                initial: 'approved',
                              ),
                              FieldSpec(
                                'label',
                                app.t('Verified label'),
                                options: const ['Real', 'Fake'],
                                initial: 'Real',
                              ),
                              FieldSpec(
                                'note',
                                app.t('Review note'),
                                min: 5,
                                max: 1000,
                                lines: 3,
                              ),
                            ],
                            submit: (v) => app.api.post(
                              '/admin/learning/${r['id']}/review',
                              v,
                            ),
                          );
                          reload();
                        },
                        child: Text(app.t('Review', 'রিভিউ')),
                      ),
                  ],
                ),
              ),
            ),
            ItemRow(
              app.t('Training history', 'ট্রেনিংয়ের ইতিহাস'),
              icon: Icons.history,
              onTap: () => openPage(
                context,
                app.t('Training history'),
                const AuditPage(training: true),
              ),
            ),
          ],
        );
      },
    );
  }
}

class AuditPage extends StatelessWidget {
  final bool training;
  const AuditPage({super.key, this.training = false});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      training ? '/admin/training-jobs' : '/admin/audit',
      builder: (data, reload) => PageBody(
        children: [
          PageTitle(app.t(training ? 'Training history' : 'Audit trail')),
          if (objects(data).isEmpty) EmptyState(app.t('No records')),
          ...objects(data).map(
            (r) => Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    app.t('${r[training ? 'status' : 'action']}'),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    training
                        ? '${r['message']}'
                        : '${r['actor']} · ${r['target']}',
                  ),
                  Muted(dateLabel(r['created_at'])),
                  if ((training ? r['report'] : r['detail']) != null)
                    InfoFields(object(training ? r['report'] : r['detail'])),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class InfoFields extends StatelessWidget {
  final Json values;
  const InfoFields(this.values, {super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: values.entries
            .map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Muted(app.t(e.key.replaceAll('_', ' '))),
                    if (e.value is Map)
                      InfoFields(object(e.value))
                    else if (e.value is List)
                      Text(
                        (e.value as List)
                            .map(
                              (v) => v is Map
                                  ? object(v).values.join(' · ')
                                  : '$v',
                            )
                            .join('\n'),
                      )
                    else
                      SelectableText(
                        app.t('${e.value ?? '—'}'),
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                  ],
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

class InsightsPage extends StatelessWidget {
  const InsightsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return RemoteView(
      '/dashboard/metrics',
      builder: (data, reload) {
        final d = object(data);
        return PageBody(
          children: [
            PageTitle(app.t('Research insights', 'রিসার্চ রিপোর্ট')),
            MetricGrid([
              (
                app.t('Evaluations', 'মূল্যায়ন'),
                '${d['total_evaluations']}',
                Icons.science_outlined,
              ),
              (
                app.t('Human accuracy', 'মানুষের সঠিক উত্তর'),
                '${number(d['human_accuracy']).toStringAsFixed(1)}%',
                Icons.person_outline,
              ),
              (
                app.t('Model accuracy', 'মডেলের সঠিক উত্তর'),
                '${number(d['ai_accuracy']).toStringAsFixed(1)}%',
                Icons.model_training,
              ),
              (
                app.t('Hybrid accuracy', 'যৌথ সঠিক উত্তর'),
                '${number(d['hybrid_accuracy']).toStringAsFixed(1)}%',
                Icons.hub_outlined,
              ),
            ]),
            BarPanel(
              app.t('Agreement quadrants', 'মানুষ ও মডেলের ফলাফলের তুলনা'),
              object(d['quadrant_breakdown']).entries
                  .map((e) => (e.key, number(e.value)))
                  .toList(),
            ),
            Notice(
              app.t(
                'Q1: both correct · Q2: human correct · Q3: model correct · Q4: both incorrect',
                'Q1: দুজনই সঠিক · Q2: মানুষ সঠিক · Q3: মডেল সঠিক · Q4: দুজনই ভুল',
              ),
            ),
            BarPanel(
              app.t('Precision, recall & F1', 'Precision, recall ও F1'),
              [
                ('Human · Precision', number(d['human_precision'])),
                ('Human · Recall', number(d['human_recall'])),
                ('Human · F1', number(d['human_f1'])),
                ('AI · Precision', number(d['ai_precision'])),
                ('AI · Recall', number(d['ai_recall'])),
                ('AI · F1', number(d['ai_f1'])),
              ],
            ),
            BarPanel(
              app.t(
                'Confidence calibration · actual accuracy',
                'নিশ্চয়তার মাত্রা অনুযায়ী সঠিক উত্তরের হার',
              ),
              objects(d['calibration_data'])
                  .map(
                    (r) => (
                      '${r['confidence_level']}/5 · n=${r['sample_count']}',
                      number(r['actual_accuracy']),
                    ),
                  )
                  .toList(),
            ),
            InfoFields({
              'human_confusion_matrix': d['human_confusion_matrix'],
              'ai_confusion_matrix': d['ai_confusion_matrix'],
            }),
            ...['ALL', 'Q1', 'Q2', 'Q3', 'Q4'].map(
              (q) => OutlinedButton(
                onPressed: () => openPage(
                  context,
                  q,
                  RemoteView(
                    '/dashboard/quadrants/$q',
                    builder: (v, _) => PageBody(
                      children: objects(v)
                          .map(
                            (r) => Panel(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${r['title']}',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium,
                                  ),
                                  MediaPlayer('${r['media_url']}'),
                                  InfoFields({
                                    'human_prediction': r['human_prediction'],
                                    'ai_prediction': r['ai_prediction'],
                                    'ground_truth': r['ground_truth'],
                                    'quadrant': r['disagreement_quadrant'],
                                  }),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
                child: Text(q),
              ),
            ),
            if (app.admin || app.user?['qualified_for_research'] == true)
              Wrap(
                spacing: 12,
                children: ['csv', 'json']
                    .map(
                      (type) => OutlinedButton.icon(
                        icon: const Icon(Icons.download_outlined),
                        label: Text('Export ${type.toUpperCase()}'),
                        onPressed: () async {
                          try {
                            final value = await app.api.get(
                              '/dashboard/export/$type',
                            );
                            await SharePlus.instance.share(
                              ShareParams(
                                files: [
                                  XFile.fromData(
                                    utf8.encode(
                                      type == 'json'
                                          ? jsonEncode(value)
                                          : '$value',
                                    ),
                                    mimeType: type == 'json'
                                        ? 'application/json'
                                        : 'text/csv',
                                  ),
                                ],
                                fileNameOverrides: [
                                  'deepshield-research.$type',
                                ],
                              ),
                            );
                          } catch (e) {
                            if (context.mounted) {
                              snack(context, app.t(Api.errorText(e)));
                            }
                          }
                        },
                      ),
                    )
                    .toList(),
              ),
          ],
        );
      },
    );
  }
}
