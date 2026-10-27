import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import '../ui/media.dart';
import 'member.dart';

class ContentPage extends StatefulWidget {
  const ContentPage({super.key});
  @override
  State<ContentPage> createState() => _ContentPageState();
}

class _ContentPageState extends State<ContentPage> {
  bool lessons = true;
  String? error;
  bool uploading = false;
  Future<void> libraryForm(Json? row) async {
    final app = AppScope.of(context);
    await openForm(
      context,
      title: app.t(row == null ? 'Upload library video' : 'Edit video'),
      fields: [
        FieldSpec(
          'title',
          app.t('Title'),
          min: 2,
          max: 128,
          initial: '${row?['title'] ?? ''}',
        ),
        FieldSpec(
          'description',
          app.t('Description'),
          min: 0,
          max: 4000,
          lines: 4,
          initial: '${row?['description'] ?? ''}',
        ),
        FieldSpec(
          'ground_truth',
          app.t('Verified label'),
          options: const ['Real', 'Fake'],
          initial: '${row?['ground_truth'] ?? 'Real'}',
        ),
        FieldSpec(
          'difficulty',
          app.t('Difficulty'),
          options: const ['Not rated', 'Easy', 'Medium', 'Hard'],
          initial: '${row?['difficulty'] ?? 'Not rated'}',
        ),
      ],
      submit: (v) async {
        if (row != null) {
          return app.api.put('/admin/content/library/${row['id']}', {
            ...v,
            'archived': row['archived'],
          });
        }
        final pick = await FilePicker.pickFile(
          type: FileType.custom,
          allowedExtensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'],
        );
        if (pick == null) throw const ApiFailure('No file selected.');
        final f = pick;
        final size = await f.length() ?? 0;
        if (size > 50000000) {
          throw const ApiFailure('Maximum video size is 50 MB.');
        }
        final file = f.path != null
            ? await MultipartFile.fromFile(f.path!, filename: f.name)
            : MultipartFile.fromStream(
                () => f.readAsByteStream(),
                size,
                filename: f.name,
              );
        return app.api.upload('/admin/content/library', file, fields: v);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: SegmentedButton<bool>(
            segments: [
              ButtonSegment(
                value: true,
                label: Text(app.t('Lessons', 'লেসন')),
                icon: const Icon(Icons.menu_book_outlined),
              ),
              ButtonSegment(
                value: false,
                label: Text(app.t('Video library', 'ভিডিও লাইব্রেরি')),
                icon: const Icon(Icons.video_library_outlined),
              ),
            ],
            selected: {lessons},
            onSelectionChanged: (v) => setState(() => lessons = v.first),
          ),
        ),
        Expanded(
          child: RemoteView(
            lessons ? '/admin/content/lessons' : '/admin/content/library',
            builder: (data, reload) => PageBody(
              children: [
                BusyButton(
                  app.t(lessons ? 'Create lesson' : 'Upload video'),
                  icon: Icons.add,
                  onPressed: () async {
                    if (lessons) {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const LessonEditor()),
                      );
                    } else {
                      await libraryForm(null);
                    }
                    reload();
                  },
                ),
                if (error != null) Notice(app.t(error!), error: true),
                if (objects(data).isEmpty) EmptyState(app.t('No content yet')),
                ...objects(data).map((r) {
                  final title = lessons
                      ? object(r[app.language])['title']
                      : r['title'];
                  return Panel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        StatusBadge(
                          app.t(
                            r['archived'] == true ? 'Archived' : 'Published',
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          '$title',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        if (!lessons) ...[
                          const SizedBox(height: 14),
                          MediaPlayer('${r['media_url']}'),
                          Text(
                            '${app.t('${r['ground_truth']}')} · ${app.t('${r['difficulty']}')}',
                          ),
                        ],
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          children: [
                            OutlinedButton.icon(
                              onPressed: () async {
                                if (lessons) {
                                  await Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => LessonEditor(row: r),
                                    ),
                                  );
                                } else {
                                  await libraryForm(r);
                                }
                                reload();
                              },
                              icon: const Icon(Icons.edit_outlined),
                              label: Text(app.t('Edit')),
                            ),
                            if (r['archived'] != true)
                              IconButton(
                                tooltip: app.t('Archive'),
                                icon: const Icon(Icons.archive_outlined),
                                onPressed: () async {
                                  if (!await confirmAction(
                                    context,
                                    app.t('Archive content?'),
                                    app.t(
                                      'It will no longer be available for new lessons or games. History is preserved.',
                                      'নতুন লেসন বা গেমে এটি দেখা যাবে না। আগের ইতিহাস সংরক্ষিত থাকবে।',
                                    ),
                                  )) {
                                    return;
                                  }
                                  try {
                                    await app.api.delete(
                                      '/admin/content/${lessons ? 'lessons' : 'library'}/${r['id']}',
                                    );
                                    reload();
                                  } catch (e) {
                                    if (mounted) {
                                      setState(() => error = Api.errorText(e));
                                    }
                                  }
                                },
                              ),
                          ],
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class LessonEditor extends StatefulWidget {
  final Json? row;
  const LessonEditor({super.key, this.row});
  @override
  State<LessonEditor> createState() => _LessonEditorState();
}

class _LessonEditorState extends State<LessonEditor> {
  final form = GlobalKey<FormState>();
  late Json en, bn;
  int answer = 0;
  bool archived = false, busy = false;
  String? error;
  final controllers = <String, TextEditingController>{};
  Json fresh() => {
    'title': '',
    'time': '5 min',
    'intro': '',
    'sections': [
      ['', ''],
    ],
    'flow': [
      ['', ''],
      ['', ''],
      ['', ''],
    ],
    'question': '',
    'choices': ['', '', ''],
    'feedback': '',
  };
  @override
  void initState() {
    super.initState();
    en = widget.row == null ? fresh() : object(widget.row!['en']);
    bn = widget.row == null ? fresh() : object(widget.row!['bn']);
    answer = number(widget.row?['answer']).toInt();
    archived = widget.row?['archived'] == true;
  }

  @override
  void dispose() {
    for (final c in controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Widget field(
    String lang,
    Json copy,
    String key,
    String label, {
    int lines = 1,
    int min = 1,
    int max = 4000,
  }) {
    final id = '$lang:$key';
    final c = controllers.putIfAbsent(
      id,
      () => TextEditingController(text: '${copy[key] ?? ''}'),
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: TextFormField(
        controller: c,
        maxLines: lines,
        maxLength: max,
        decoration: InputDecoration(labelText: label, alignLabelWithHint: true),
        validator: (v) =>
            (v ?? '').trim().length < min ? 'Minimum $min characters' : null,
        onSaved: (v) => copy[key] = v!.trim(),
      ),
    );
  }

  Widget pairField(
    String lang,
    Json copy,
    String group,
    int index,
    int part,
    String label,
  ) {
    final id = '$lang:$group:$index:$part';
    final c = controllers.putIfAbsent(
      id,
      () => TextEditingController(text: '${copy[group][index][part]}'),
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: c,
        maxLines: part == 0 ? 1 : 4,
        maxLength: part == 0 ? 200 : 4000,
        decoration: InputDecoration(labelText: label),
        validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null,
        onSaved: (v) => copy[group][index][part] = v!.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(app.t('Lesson editor', 'লেসন এডিটর'))),
      body: Form(
        key: form,
        child: PageBody(
          children: [
            Notice(
              app.t(
                'Changing quiz questions or the correct answer resets completion for this lesson.',
                'প্রশ্ন বা সঠিক উত্তর বদলালে এই লেসনের completion reset হবে।',
              ),
            ),
            for (final lang in ['en', 'bn'])
              Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      lang == 'en' ? 'English' : 'বাংলা',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    ...buildCopy(lang, lang == 'en' ? en : bn, app),
                  ],
                ),
              ),
            DropdownButtonFormField<int>(
              isExpanded: true,
              initialValue: answer,
              decoration: InputDecoration(
                labelText: app.t('Correct answer', 'সঠিক উত্তর'),
              ),
              items: List.generate(
                3,
                (i) => DropdownMenuItem(value: i, child: Text('${i + 1}')),
              ),
              onChanged: (v) => answer = v ?? 0,
            ),
            SwitchListTile(
              title: Text(app.t('Archived', 'আর্কাইভ')),
              value: archived,
              onChanged: (v) => setState(() => archived = v),
            ),
            if (error != null) Notice(app.t(error!), error: true),
            BusyButton(
              app.t('Save lesson', 'লেসন সেভ করুন'),
              busy: busy,
              onPressed: () async {
                if (!form.currentState!.validate()) return;
                form.currentState!.save();
                setState(() => busy = true);
                try {
                  final payload = {
                    'en': en,
                    'bn': bn,
                    'answer': answer,
                    'archived': archived,
                  };
                  if (widget.row == null) {
                    await app.api.post('/admin/content/lessons', payload);
                  } else {
                    await app.api.put(
                      '/admin/content/lessons/${widget.row!['id']}',
                      payload,
                    );
                  }
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
    );
  }

  List<Widget> buildCopy(String lang, Json copy, AppState app) => [
    field(lang, copy, 'title', app.t('Title'), min: 2, max: 160),
    field(lang, copy, 'time', app.t('Reading time', 'পড়ার সময়'), max: 30),
    field(
      lang,
      copy,
      'intro',
      app.t('Introduction', 'পরিচিতি'),
      lines: 4,
      min: 5,
    ),
    for (int i = 0; i < (copy['sections'] as List).length; i++) ...[
      pairField(
        lang,
        copy,
        'sections',
        i,
        0,
        '${app.t('Section')} ${i + 1} · ${app.t('Heading')}',
      ),
      pairField(lang, copy, 'sections', i, 1, app.t('Text')),
    ],
    if ((copy['sections'] as List).length < 8)
      TextButton.icon(
        onPressed: () =>
            setState(() => (copy['sections'] as List).add(['', ''])),
        icon: const Icon(Icons.add),
        label: Text(app.t('Add section')),
      ),
    for (int i = 0; i < 3; i++) ...[
      pairField(lang, copy, 'flow', i, 0, '${app.t('Step')} ${i + 1}'),
      pairField(lang, copy, 'flow', i, 1, app.t('Instructions')),
    ],
    field(
      lang,
      copy,
      'question',
      app.t('Quiz question'),
      lines: 3,
      min: 5,
      max: 1000,
    ),
    for (int i = 0; i < 3; i++)
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          initialValue: '${copy['choices'][i]}',
          maxLength: 500,
          decoration: InputDecoration(labelText: '${app.t('Choice')} ${i + 1}'),
          validator: (v) => (v ?? '').trim().isEmpty ? 'Required' : null,
          onSaved: (v) => copy['choices'][i] = v!.trim(),
        ),
      ),
    field(
      lang,
      copy,
      'feedback',
      app.t('Answer explanation'),
      lines: 4,
      min: 5,
      max: 2000,
    ),
  ];
}
