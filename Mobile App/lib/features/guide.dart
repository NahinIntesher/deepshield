import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';

class GuidePage extends StatelessWidget {
  const GuidePage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context), lang = app.bengali ? 'bn' : 'en';
    final sections = app.guideSections;

    return PageBody(
      children: [
        PageTitle(app.t('User guide', 'ব্যবহারবিধি')),
        Panel(
          child: Column(
            children: sections
                .map(
                  (section) => ExpansionTile(
                    title: Text('${object(section['title'])[lang]}'),
                    tilePadding: EdgeInsets.zero,
                    childrenPadding: const EdgeInsets.only(bottom: 16),
                    children: objects(section['steps'])
                        .asMap()
                        .entries
                        .map(
                          (step) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${step.key + 1}. '),
                                Expanded(child: Text('${step.value[lang]}')),
                              ],
                            ),
                          ),
                        )
                        .toList(),
                  ),
                )
                .toList(),
          ),
        ),
      ],
    );
  }
}
