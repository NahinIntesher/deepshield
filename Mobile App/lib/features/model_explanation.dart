import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';

Json? verifiedShap(Json result) {
  final evidence = object(result['shap_explanation']);
  if (evidence['method'] != 'SHAP' ||
      evidence['target_class'] != result['verdict']) {
    return null;
  }
  for (final name in ['branches', 'frames', 'spatial']) {
    if (name == 'frames' && evidence[name] == null) continue;
    final game = object(evidence[name]),
        values = game['values'],
        names = game['feature_names'];
    if (values is! List ||
        names is! List ||
        values.length != names.length ||
        values.length > 64 ||
        values.any((v) => v is! num || !v.isFinite)) {
      return null;
    }
    final base = game['base_value'], output = game['output_value'];
    if (base is! num || output is! num || !base.isFinite || !output.isFinite) {
      return null;
    }
    if ((base +
                values.fold<double>(
                  0,
                  (sum, v) => sum + (v as num).toDouble(),
                ) -
                output)
            .abs() >
        .001) {
      return null;
    }
  }
  final spatial = object(evidence['spatial']),
      regions = objects(spatial['regions']);
  bool image(dynamic data) =>
      data is String &&
      data.startsWith('data:image/png;base64,') &&
      data.length <= 1000000;
  final names = spatial['feature_names'] as List;
  final values = spatial['values'] as List;
  final ids = <String>{};
  if (!image(object(spatial['preview'])['original']) ||
      regions.length != 4 ||
      regions.any((r) {
        final index = names.indexOf(r['id']);
        return !const ['eyes', 'nose', 'mouth', 'other'].contains(r['id']) ||
            !ids.add('${r['id']}') ||
            index < 0 ||
            r['shap_value'] is! num ||
            !(r['shap_value'] as num).isFinite ||
            ((r['shap_value'] as num) - (values[index] as num)).abs() > .001 ||
            !image(r['preview']) ||
            r['masked_class_score_percent'] is! num ||
            !(r['masked_class_score_percent'] as num).isFinite ||
            number(r['masked_class_score_percent']) < 0 ||
            number(r['masked_class_score_percent']) > 100;
      })) {
    return null;
  }
  return evidence;
}

class ModelExplanation extends StatefulWidget {
  final Json result;
  const ModelExplanation(this.result, {super.key});
  @override
  State<ModelExplanation> createState() => _ModelExplanationState();
}

class _ModelExplanationState extends State<ModelExplanation> {
  String? selected;
  String area(String id, AppState app) => switch (id) {
    'eyes' => app.t('Around the eyes', 'চোখের চারপাশ'),
    'nose' => app.t('Around the nose', 'নাকের আশপাশ'),
    'mouth' => app.t('Mouth and lower face', 'ঠোঁটের আশপাশ'),
    _ => app.t('Rest of the face crop', 'মুখের ছবির বাকি অংশ'),
  };
  String score(num value, AppState app) {
    final text = value.toStringAsFixed(1);
    return app.bengali
        ? text.replaceAllMapped(
            RegExp(r'\d'),
            (m) => '০১২৩৪৫৬৭৮৯'[int.parse(m[0]!)],
          )
        : text;
  }

  Widget picture(String? data, String caption) {
    Widget image;
    try {
      if (data == null ||
          !data.startsWith('data:image/png;base64,') ||
          data.length > 1000000) {
        throw const FormatException();
      }
      final bytes = base64Decode(data.split(',').last);
      image = Image.memory(
        bytes,
        fit: BoxFit.contain,
        semanticLabel: caption,
        errorBuilder: (_, _, _) =>
            const Icon(Icons.image_not_supported_outlined),
      );
    } catch (_) {
      image = const Icon(Icons.image_not_supported_outlined);
    }
    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: ColoredBox(
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: InkWell(
                onTap: () => showDialog<void>(
                  context: context,
                  builder: (dialogContext) => Dialog(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Align(
                            alignment: Alignment.centerRight,
                            child: IconButton(
                              tooltip: MaterialLocalizations.of(context)
                                  .closeButtonTooltip,
                              onPressed: () => Navigator.pop(dialogContext),
                              icon: const Icon(Icons.close),
                            ),
                          ),
                          Flexible(
                            child: InteractiveViewer(
                              minScale: 1,
                              maxScale: 5,
                              child: image,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(caption),
                        ],
                      ),
                    ),
                  ),
                ),
                child: image,
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          caption,
          textAlign: TextAlign.center,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context),
        result = widget.result,
        evidence = verifiedShap(result),
        fake = result['verdict'] == 'Fake';
    final regions = objects(object(evidence?['spatial'])['regions']);
    if (regions.isNotEmpty) {
      regions.sort(
        (a, b) =>
            number(b['shap_value'])
                .abs()
                .compareTo(number(a['shap_value']).abs()),
      );
    }
    final chosen =
        regions.where((r) => r['id'] == selected).firstOrNull ??
        regions.firstOrNull;
    final label = app.t(fake ? 'Fake' : 'Real', fake ? 'নকল' : 'আসল');
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            app.t('What does this result mean?', 'এই ফলের মানে কী?'),
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          Text(
            fake
                ? app.t(
                    'The model thinks the face may have been altered. Find the original before sharing it.',
                    'মডেলের মতে, মুখের ছবি বদলানো হয়ে থাকতে পারে। শেয়ার করার আগে আসল ${result['media_type'] == 'image' ? 'ছবিটি' : 'ভিডিওটি'} খুঁজে দেখুন।',
                  )
                : app.t(
                    'The model chose Real. This does not verify the person, their statement or the truth of a claim.',
                    'মডেল এটিকে আসল হিসেবে বেছে নিয়েছে। তবুও মানুষটি কে বা তাঁর কথা সত্য কি না, এই পরীক্ষা তা যাচাই করে না।',
                  ),
            style: const TextStyle(
              fontSize: 17,
              height: 1.55,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (evidence != null && chosen != null) ...[
            const SizedBox(height: 24),
            Text(
              app.t(
                'See what affected the answer',
                'কোন তথ্য ফলকে প্রভাবিত করেছে, দেখুন',
              ),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Text(
              app.t(
                'We tested the same input again, blurring one area at a time. Choose an area to compare.',
                'একই ছবি বা ভিডিওতে একবারে একটি অংশ ঝাপসা করে আবার পরীক্ষা করেছি। নিচে একটি অংশ বেছে নিয়ে মিলিয়ে দেখুন।',
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: regions
                  .map(
                    (r) => ChoiceChip(
                      label: Text(area('${r['id']}', app)),
                      selected: chosen['id'] == r['id'],
                      onSelected: (_) =>
                          setState(() => selected = '${r['id']}'),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 20),
            LayoutBuilder(
              builder: (context, size) {
                final original = picture(
                  object(object(evidence['spatial'])['preview'])['original']
                      as String?,
                  app.t('Original', 'আগের ছবি'),
                );
                final blurred = picture(
                  chosen['preview'] as String?,
                  app.t('Blurred for the test', 'ঝাপসা করে পরীক্ষা'),
                );
                if (size.maxWidth < 340) {
                  return Column(
                    children: [original, const SizedBox(height: 20), blurred],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: original),
                    const SizedBox(width: 16),
                    Expanded(child: blurred),
                  ],
                );
              },
            ),
            const SizedBox(height: 20),
            Notice(
              app.t(
                'When we blurred ${area('${chosen['id']}', app).toLowerCase()}, the model’s $label score went from ${score(number(result['confidence_percentage']), app)}% to ${score(number(chosen['masked_class_score_percent']), app)}%. The score is not proof.',
                '${area('${chosen['id']}', app)} ঝাপসা করে আবার পরীক্ষা করলে মডেলের $label স্কোর ${score(number(result['confidence_percentage']), app)}% থেকে ${score(number(chosen['masked_class_score_percent']), app)}% হয়েছে। এই স্কোর নিশ্চিত প্রমাণ নয়।',
              ),
            ),
            const SizedBox(height: 14),
            Text(
              app.t(
                'A part affecting the answer does not prove it was edited. This check helps explain the model’s answer.',
                'কোনো অংশ ফলকে প্রভাবিত করেছে মানেই সেখানে জালিয়াতি ধরা পড়েছে, এমন নয়। এই পরীক্ষা শুধু মডেলের উত্তর বুঝতে সাহায্য করে।',
              ),
            ),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text(
                app.t(
                  'How this check works · SHAP',
                  'কীভাবে এই পরীক্ষা করা হয়েছে · SHAP',
                ),
              ),
              children: [
                Text(
                  app.t(
                    'SHAP compares tests with different parts blurred to estimate how each part affects the model’s answer. Some parts support the answer; others push against it.',
                    'সহজ করে বললে, SHAP দেখে ছবির কোন অংশ দেখা গেলে মডেলের উত্তর কতটা বদলায়। কখনো একটি অংশ, কখনো কয়েকটি অংশ একসঙ্গে ঝাপসা করে তুলনা করা হয়।',
                  ),
                ),
                const SizedBox(height: 14),
                for (final r in regions)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(area('${r['id']}', app)),
                    subtitle: Text(
                      number(r['shap_value']) >= 0
                          ? app.t('Towards $label', '$label উত্তরের পক্ষে')
                          : app.t('Away from $label', '$label উত্তরের বিপক্ষে'),
                    ),
                    trailing: Text(
                      '${number(r['shap_value']) >= 0 ? '+' : ''}${number(r['shap_value']).toStringAsFixed(3)}',
                    ),
                  ),
                Text(
                  app.t(
                    'These are internal model score units, not percentages or the chance that an area is fake. The reference is this face with its fine detail blurred.',
                    'এই সংখ্যাগুলো মডেলের ভেতরের স্কোরের হিসাবে দেখানো হয়েছে। এগুলো শতকরা মান নয়; কোনো অংশ কতটা নকল, তার সম্ভাবনাও নয়। তুলনার জন্য একই মুখের বিস্তারিত ঝাপসা করা হয়েছে।',
                  ),
                ),
                const SizedBox(height: 14),
                for (final gameName in ['branches', 'frames'])
                  if (evidence[gameName] != null) ...[
                    Text(
                      gameName == 'branches'
                          ? app.t(
                              'Appearance, texture and change over time',
                              'চেহারা, ছবির সূক্ষ্ম ধরন ও সময়ের সঙ্গে পরিবর্তন',
                            )
                          : app.t(
                              'Sampled video moments',
                              'ভিডিওর বেছে নেওয়া মুহূর্ত',
                            ),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    for (
                      var i = 0;
                      i < (object(evidence[gameName])['values'] as List).length;
                      i++
                    )
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Text(
                                gameName == 'frames'
                                    ? app.t(
                                        'Moment ${i + 1}',
                                        '${i + 1} নম্বর মুহূর্ত',
                                      )
                                    : switch ('${(object(evidence[gameName])['feature_names'] as List)[i]}'
                                          .toLowerCase()) {
                                        'rgb' => app.t(
                                          'Face appearance',
                                          'মুখের চেহারা',
                                        ),
                                        'frequency' || 'dct' => app.t(
                                          'Fine image patterns',
                                          'ছবির সূক্ষ্ম ধরন',
                                        ),
                                        'temporal' => app.t(
                                          'Changes across frames',
                                          'এক ফ্রেম থেকে অন্য ফ্রেমে পরিবর্তন',
                                        ),
                                        final name => name,
                                      },
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              '${number((object(evidence[gameName])['values'] as List)[i]) >= 0 ? '+' : ''}${number((object(evidence[gameName])['values'] as List)[i]).toStringAsFixed(3)}',
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 14),
                  ],
              ],
            ),
          ] else ...[
            const SizedBox(height: 18),
            Notice(
              app.t(
                'This saved result has no verified SHAP comparison. Its heatmap does not identify an editing defect. New scans can include SHAP.',
                'এই সংরক্ষিত ফলে যাচাই করা SHAP তুলনা নেই। Heatmap দিয়ে কোথায় জালিয়াতি হয়েছে বলা যায় না। নতুন স্ক্যানে SHAP পাওয়া যাবে।',
              ),
            ),
          ],
          const Divider(),
          Text(
            app.t('Before you trust or share it', 'বিশ্বাস বা শেয়ার করার আগে'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          Text(
            app.t(
              '1. Find where the video was first published. A familiar face or many views is not proof.',
              '১. ভিডিওটি প্রথম কোথায় প্রকাশ হয়েছে, খুঁজে দেখুন। পরিচিত মুখ বা অনেক মানুষ দেখেছে বলেই সত্য ধরে নেবেন না।',
            ),
          ),
          const SizedBox(height: 12),
          Text(
            app.t(
              '2. If it asks for money or personal details, check using a contact method you already trust.',
              '২. টাকা বা ব্যক্তিগত তথ্য চাইলে, আগে থেকে চেনা নম্বর বা মাধ্যম দিয়ে আলাদা করে যাচাই করুন।',
            ),
          ),
        ],
      ),
    );
  }
}
